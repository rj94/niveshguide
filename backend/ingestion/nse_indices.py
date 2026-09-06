"""Scrape live NSE index quotes from the unofficial www.nseindia.com API.

Personal / research use only. NSE endpoints are undocumented and may rate-limit
or change without notice. One `allIndices` call covers every listed index.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import MarketIndex, MarketIndexPrice, MarketIndexSnapshot

logger = logging.getLogger(__name__)

ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"
HOME_URL = "https://www.nseindia.com"

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/live-market-indices",
}

# Broad-market keys used on the dashboard strip.
FEATURED_INDICES: tuple[tuple[str, str], ...] = (
    ("NIFTY 50", "Nifty 50"),
    ("NIFTY BANK", "Bank Nifty"),
    ("NIFTY NEXT 50", "Nifty Next 50"),
    ("NIFTY 500", "Nifty 500"),
    ("NIFTY 100", "Nifty 100"),
)

_BROAD_KEYS = {
    "NIFTY 50",
    "NIFTY BANK",
    "NIFTY NEXT 50",
    "NIFTY 100",
    "NIFTY 200",
    "NIFTY 500",
    "NIFTY MIDCAP 50",
    "NIFTY MIDCAP 100",
    "NIFTY MIDCAP 150",
    "NIFTY SMLCAP 50",
    "NIFTY SMLCAP 100",
    "NIFTY SMLCAP 250",
    "NIFTY TOTAL MKT",
    "INDIA VIX",
}


def _f(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def classify_kind(key: str) -> str:
    upper = (key or "").strip().upper()
    if upper in _BROAD_KEYS:
        return "broad"
    if any(tok in upper for tok in ("MIDCAP", "SMLCAP", "SMALLCAP", "TOTAL MKT")):
        return "broad"
    if upper.startswith("NIFTY"):
        return "sectoral"
    return "other"


def nse_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(NSE_HEADERS)
    try:
        sess.get(HOME_URL, timeout=20)
    except requests.RequestException as exc:
        logger.warning("NSE cookie warm-up failed: %s", exc)
    return sess


def fetch_all_indices(*, retries: int = 3, pause_s: float = 1.5) -> list[dict[str, Any]]:
    """Fetch and normalize every index from NSE `allIndices`."""
    sess = nse_session()
    last_err: Exception | None = None
    payload: dict[str, Any] | list[Any] | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = sess.get(ALL_INDICES_URL, timeout=30)
            if resp.status_code in {401, 403}:
                logger.warning("NSE allIndices HTTP %s — re-warming session", resp.status_code)
                sess = nse_session()
                time.sleep(pause_s * attempt)
                continue
            resp.raise_for_status()
            payload = resp.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_err = exc
            logger.warning("NSE allIndices attempt %s failed: %s", attempt, exc)
            time.sleep(pause_s * attempt)
            sess = nse_session()
    if payload is None:
        raise RuntimeError(f"Failed to fetch NSE allIndices: {last_err}")

    raw_rows: list[Any]
    if isinstance(payload, dict):
        raw_rows = payload.get("data") or payload.get("indices") or []
    elif isinstance(payload, list):
        raw_rows = payload
    else:
        raw_rows = []

    out: list[dict[str, Any]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        key = (
            str(row.get("index") or row.get("indexSymbol") or row.get("key") or "")
            .strip()
        )
        if not key:
            continue
        name = str(row.get("index") or row.get("indexSymbol") or key).strip()
        last = _f(row.get("last") if row.get("last") is not None else row.get("lastPrice"))
        prev = _f(
            row.get("previousClose") if row.get("previousClose") is not None else row.get("prevClose")
        )
        change = _f(row.get("variation") if row.get("variation") is not None else row.get("change"))
        change_pct = _f(
            row.get("percentChange") if row.get("percentChange") is not None else row.get("pChange")
        )
        if change is None and last is not None and prev is not None:
            change = last - prev
        if change_pct is None and change is not None and prev:
            change_pct = (change / prev) * 100.0
        out.append(
            {
                "key": key,
                "name": name,
                "kind": classify_kind(key),
                "last": last,
                "prev_close": prev,
                "change": change,
                "change_pct": round(change_pct, 4) if change_pct is not None else None,
                "open": _f(row.get("open")),
                "high": _f(row.get("high")),
                "low": _f(row.get("low")),
                "year_high": _f(
                    row.get("yearHigh") if row.get("yearHigh") is not None else row.get("yrHigh")
                ),
                "year_low": _f(
                    row.get("yearLow") if row.get("yearLow") is not None else row.get("yrLow")
                ),
            }
        )
    return out


def upsert_indices(
    session: Session,
    rows: list[dict[str, Any]],
    *,
    as_of: date | None = None,
) -> dict[str, int]:
    """Upsert master rows, today's snapshot, and daily close history."""
    as_of = as_of or date.today()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = updated = snaps = prices = 0

    for row in rows:
        key = row["key"]
        idx = session.scalar(select(MarketIndex).where(MarketIndex.key == key))
        if idx is None:
            idx = MarketIndex(
                key=key,
                name=row["name"],
                kind=row.get("kind") or "index",
                is_active=True,
            )
            session.add(idx)
            session.flush()
            created += 1
        else:
            idx.name = row["name"]
            idx.kind = row.get("kind") or idx.kind or "index"
            idx.is_active = True
            updated += 1

        snap = session.scalar(
            select(MarketIndexSnapshot).where(
                MarketIndexSnapshot.index_id == idx.id,
                MarketIndexSnapshot.as_of == as_of,
            )
        )
        if snap is None:
            snap = MarketIndexSnapshot(index_id=idx.id, as_of=as_of)
            session.add(snap)
        snap.last = row.get("last")
        snap.prev_close = row.get("prev_close")
        snap.change = row.get("change")
        snap.change_pct = row.get("change_pct")
        snap.open = row.get("open")
        snap.high = row.get("high")
        snap.low = row.get("low")
        snap.year_high = row.get("year_high")
        snap.year_low = row.get("year_low")
        snap.fetched_at = now
        snaps += 1

        close = row.get("last")
        if close is not None:
            price = session.scalar(
                select(MarketIndexPrice).where(
                    MarketIndexPrice.index_id == idx.id,
                    MarketIndexPrice.price_date == as_of,
                )
            )
            if price is None:
                price = MarketIndexPrice(index_id=idx.id, price_date=as_of)
                session.add(price)
            price.close = close
            prices += 1

    session.commit()
    return {
        "indices_total": len(rows),
        "created": created,
        "updated": updated,
        "snapshots": snaps,
        "prices": prices,
        "as_of": as_of.isoformat(),
    }


def scrape_and_store(session: Session) -> dict[str, Any]:
    rows = fetch_all_indices()
    stats = upsert_indices(session, rows)
    stats["ok"] = True
    return stats
