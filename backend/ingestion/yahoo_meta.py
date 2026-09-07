"""Backfill Stock.sector/industry and StockFundamental market_cap/pe.

Primary: Yahoo Finance info (market cap / PE; sector when present).
Fallback for sector/industry: Screener.in peers taxonomy (HTML cache or live fetch).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import BACKEND_ROOT
from database.models import Stock, StockFundamental, StockSnapshot
from database.session import init_db
from ingestion.screener_in.parse import parse_peers_taxonomy

logger = logging.getLogger(__name__)

# Yahoo marketCap is absolute INR; site / screener store ₹ Crores.
INR_PER_CRORE = 10_000_000.0
SCREENER_CACHE = BACKEND_ROOT / "data" / "screener_in" / "cache" / "html"


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:  # NaN
        return None
    return out


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return None
    return text


def gap_symbols(session: Session, *, limit: int | None = None) -> list[str]:
    """Active stocks missing sector and/or with no market_cap on fundamentals or snapshots."""
    stocks = session.scalars(select(Stock).where(Stock.is_active.is_(True)).order_by(Stock.symbol)).all()
    fund_mcap: set[int] = set()
    for sid, mcap in session.execute(
        select(StockFundamental.stock_id, StockFundamental.market_cap).where(
            StockFundamental.market_cap.is_not(None)
        )
    ):
        if mcap is not None:
            fund_mcap.add(int(sid))
    snap_mcap: set[int] = set()
    for sid, mcap in session.execute(
        select(StockSnapshot.stock_id, StockSnapshot.market_cap).where(StockSnapshot.market_cap.is_not(None))
    ):
        if mcap is not None:
            snap_mcap.add(int(sid))

    out: list[str] = []
    for stock in stocks:
        sector_missing = not (stock.sector and str(stock.sector).strip())
        mcap_missing = stock.id not in fund_mcap and stock.id not in snap_mcap
        if sector_missing or mcap_missing:
            out.append(stock.symbol)
            if limit is not None and len(out) >= limit:
                break
    return out


def sector_gap_symbols(session: Session, *, limit: int | None = None) -> list[str]:
    q = (
        select(Stock.symbol)
        .where(
            Stock.is_active.is_(True),
            (Stock.sector.is_(None)) | (Stock.sector == ""),
        )
        .order_by(Stock.symbol)
    )
    if limit is not None:
        q = q.limit(limit)
    return [str(s) for s in session.scalars(q).all()]


def fetch_yahoo_meta(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch sector/industry/marketCap/trailingPE for NSE tickers via yfinance."""
    import yfinance as yf

    result: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        ticker = f"{symbol}.NS"
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Yahoo meta failed for %s: %s", symbol, exc)
            continue
        sector = _str(info.get("sector")) or _str(info.get("sectorDisp"))
        industry = _str(info.get("industry")) or _str(info.get("industryDisp"))
        market_cap_inr = _f(info.get("marketCap"))
        market_cap_cr = round(market_cap_inr / INR_PER_CRORE, 4) if market_cap_inr else None
        pe = _f(info.get("trailingPE")) or _f(info.get("forwardPE"))
        eps = _f(info.get("trailingEps"))
        name = _str(info.get("longName")) or _str(info.get("shortName"))
        if not any([sector, industry, market_cap_cr, pe, eps, name]):
            continue
        result[symbol] = {
            "sector": sector,
            "industry": industry,
            "broad_sector": None,
            "broad_industry": None,
            "market_cap": market_cap_cr,
            "pe": pe,
            "eps": eps,
            "company_name": name,
            "source": "yahoo",
        }
    return result


def _taxonomy_from_html(html: str) -> dict[str, str | None]:
    soup = BeautifulSoup(html, "lxml")
    return parse_peers_taxonomy(soup)


def fetch_screener_sectors(
    symbols: list[str],
    *,
    delay_min: float = 2.0,
    delay_max: float = 4.0,
    cache_only: bool = False,
) -> dict[str, dict[str, Any]]:
    """Sector/industry from Screener.in HTML cache or live pages."""
    from ingestion.screener_in.client import ScreenerClient

    result: dict[str, dict[str, Any]] = {}
    cache_dir = SCREENER_CACHE
    cache_dir.mkdir(parents=True, exist_ok=True)

    with ScreenerClient(
        cache_dir,
        delay_min=delay_min,
        delay_max=delay_max,
        allow_fast=True,
        cache_ttl_days=30,
    ) as client:
        for symbol in symbols:
            path = cache_dir / f"{symbol.upper()}.html"
            html: str | None = None
            if path.exists():
                html = path.read_text(encoding="utf-8", errors="replace")
            elif not cache_only:
                try:
                    html, _url, _hit, _status = client.fetch_company(symbol)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Screener sector failed for %s: %s", symbol, exc)
                    continue
            if not html:
                continue
            tax = _taxonomy_from_html(html)
            sector = tax.get("sector") or tax.get("broad_sector")
            industry = tax.get("industry") or tax.get("broad_industry")
            if not sector and not industry:
                continue
            result[symbol] = {
                "sector": sector,
                "industry": industry,
                "broad_sector": tax.get("broad_sector"),
                "broad_industry": tax.get("broad_industry"),
                "market_cap": None,
                "pe": None,
                "eps": None,
                "company_name": None,
                "source": "screener.in",
            }
    return result


def _upsert_fundamental_meta(
    session: Session,
    stock: Stock,
    *,
    market_cap: float | None,
    pe: float | None,
    eps: float | None,
    as_of: date,
    source: str,
) -> bool:
    """Fill null fundamental fields. Returns True if any field written."""
    if market_cap is None and pe is None and eps is None:
        return False
    row = session.scalar(
        select(StockFundamental)
        .where(StockFundamental.stock_id == stock.id)
        .order_by(StockFundamental.as_of_date.desc())
        .limit(1)
    )
    created = False
    if row is None:
        row = StockFundamental(
            stock_id=stock.id,
            as_of_date=as_of,
            source=source,
            source_url=f"https://finance.yahoo.com/quote/{stock.symbol}.NS"
            if source == "yahoo"
            else f"https://www.screener.in/company/{stock.symbol}/consolidated/",
        )
        session.add(row)
        created = True
    wrote = created
    if market_cap is not None and row.market_cap is None:
        row.market_cap = market_cap
        wrote = True
    if pe is not None and row.pe is None:
        row.pe = pe
        wrote = True
    if eps is not None and row.eps is None:
        row.eps = eps
        wrote = True
    if row.source is None:
        row.source = source
    return wrote


def apply_meta(session: Session, meta_by_symbol: dict[str, dict[str, Any]]) -> dict[str, int]:
    updated_sector = 0
    updated_fund = 0
    today = date.today()
    if not meta_by_symbol:
        return {"stocks_updated": 0, "fundamentals_updated": 0}
    stocks = {
        st.symbol: st
        for st in session.scalars(
            select(Stock).where(Stock.symbol.in_(list(meta_by_symbol.keys())))
        ).all()
    }
    for symbol, meta in meta_by_symbol.items():
        stock = stocks.get(symbol)
        if stock is None:
            continue
        changed = False
        if meta.get("broad_sector") and not (stock.broad_sector and str(stock.broad_sector).strip()):
            stock.broad_sector = meta["broad_sector"]
            changed = True
        if meta.get("sector") and not (stock.sector and str(stock.sector).strip()):
            stock.sector = meta["sector"]
            changed = True
        if meta.get("broad_industry") and not (
            stock.broad_industry and str(stock.broad_industry).strip()
        ):
            stock.broad_industry = meta["broad_industry"]
            changed = True
        if meta.get("industry") and not (stock.industry and str(stock.industry).strip()):
            stock.industry = meta["industry"]
            changed = True
        if meta.get("company_name") and (
            not stock.company_name or stock.company_name.upper() == stock.symbol.upper()
        ):
            stock.company_name = meta["company_name"]
            changed = True
        if changed:
            updated_sector += 1
        if _upsert_fundamental_meta(
            session,
            stock,
            market_cap=_f(meta.get("market_cap")),
            pe=_f(meta.get("pe")),
            eps=_f(meta.get("eps")),
            as_of=today,
            source=str(meta.get("source") or "yahoo"),
        ):
            updated_fund += 1
    session.commit()
    return {"stocks_updated": updated_sector, "fundamentals_updated": updated_fund}


def backfill_yahoo_meta(
    session: Session,
    *,
    symbols: list[str] | None = None,
    limit: int | None = None,
    chunk_size: int = 40,
    sleep_s: float = 0.35,
    screener_sectors: bool = True,
    screener_cache_only: bool = False,
    screener_delay_min: float = 2.0,
    screener_delay_max: float = 4.0,
) -> dict[str, Any]:
    init_db()
    targets = symbols or gap_symbols(session, limit=limit)
    if limit is not None and symbols:
        targets = targets[:limit]

    fetched = 0
    applied = {"stocks_updated": 0, "fundamentals_updated": 0}
    for start in range(0, len(targets), max(1, chunk_size)):
        chunk = targets[start : start + chunk_size]
        meta = fetch_yahoo_meta(chunk)
        fetched += len(meta)
        stats = apply_meta(session, meta)
        applied["stocks_updated"] += stats["stocks_updated"]
        applied["fundamentals_updated"] += stats["fundamentals_updated"]
        logger.info(
            "Yahoo meta chunk %s-%s: fetched=%s sector=%s fund=%s",
            start + 1,
            start + len(chunk),
            len(meta),
            stats["stocks_updated"],
            stats["fundamentals_updated"],
        )
        if sleep_s > 0 and start + chunk_size < len(targets):
            time.sleep(sleep_s)

    screener_stats = {"stocks_updated": 0, "fundamentals_updated": 0, "fetched": 0}
    if screener_sectors:
        still_missing = [
            s
            for s in (symbols or sector_gap_symbols(session))
            if s in set(targets) or symbols is None
        ]
        # Refresh sector gaps from DB after Yahoo pass
        still_missing = sector_gap_symbols(session)
        if symbols:
            want = {s.upper() for s in symbols}
            still_missing = [s for s in still_missing if s in want]
        if limit is not None:
            still_missing = still_missing[:limit]
        # Prefer cache hits first for speed
        cache_hits = [s for s in still_missing if (SCREENER_CACHE / f"{s}.html").exists()]
        need_live = [s for s in still_missing if s not in set(cache_hits)]
        for label, batch, cache_only in (
            ("cache", cache_hits, True),
            ("live", need_live if not screener_cache_only else [], False),
        ):
            if not batch:
                continue
            meta = fetch_screener_sectors(
                batch,
                delay_min=screener_delay_min,
                delay_max=screener_delay_max,
                cache_only=cache_only,
            )
            screener_stats["fetched"] += len(meta)
            stats = apply_meta(session, meta)
            screener_stats["stocks_updated"] += stats["stocks_updated"]
            screener_stats["fundamentals_updated"] += stats["fundamentals_updated"]
            logger.info(
                "Screener sectors (%s): targets=%s fetched=%s updated=%s",
                label,
                len(batch),
                len(meta),
                stats["stocks_updated"],
            )

    return {
        "targets": len(targets),
        "fetched": fetched,
        **applied,
        "screener": screener_stats,
    }
