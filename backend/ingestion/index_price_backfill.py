"""Backfill daily closes for NSE sectoral indices into market_index_prices.

Uses Yahoo Finance tickers where available so Sector Strength can show official
index 3M returns. Personal / research use.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import MarketIndex, MarketIndexPrice
from market_platform.services.sectors import SECTORAL_INDEX_KEYS

logger = logging.getLogger(__name__)

# MarketIndex.key → Yahoo Finance symbol
YAHOO_INDEX_TICKERS: dict[str, str] = {
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY CHEMICALS": "NIFTY_CHEMICALS.NS",
    "NIFTY CONSUMER DURABLES": "NIFTY_CONSR_DURBL.NS",
    "NIFTY FINANCIAL SERVICES": "NIFTY_FIN_SERVICE.NS",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY HEALTHCARE INDEX": "NIFTY_HEALTHCARE.NS",
    "NIFTY IT": "^CNXIT",
    "NIFTY MEDIA": "^CNXMEDIA",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY OIL & GAS": "NIFTY_OIL_AND_GAS.NS",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY PRIVATE BANK": "NIFTY_PVT_BANK.NS",
    "NIFTY PSU BANK": "^CNXPSUBANK",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY INFRA": "^CNXINFRA",
    "NIFTY CONSUMPTION": "^CNXCONSUM",
    "NIFTY 50": "^NSEI",
    "NIFTY NEXT 50": "NIFTYNXT50.NS",  # often unavailable; sparkline falls back to JUNIORBEES ETF
    "NIFTY 100": "^CNX100",
    "NIFTY 500": "^CRSLDX",
}


def _ensure_index(session: Session, key: str, name: str | None = None) -> MarketIndex:
    idx = session.scalar(select(MarketIndex).where(MarketIndex.key == key))
    if idx is None:
        idx = MarketIndex(key=key, name=name or key.title(), kind="sectoral", is_active=True)
        session.add(idx)
        session.flush()
    return idx


def backfill_index_prices(
    session: Session,
    *,
    period: str = "1y",
    keys: list[str] | None = None,
) -> dict[str, Any]:
    import yfinance as yf

    target_keys = keys or sorted(set(SECTORAL_INDEX_KEYS.values()) | set(YAHOO_INDEX_TICKERS.keys()))
    stored = 0
    ok: list[str] = []
    failed: list[dict[str, str]] = []

    for key in target_keys:
        ticker = YAHOO_INDEX_TICKERS.get(key)
        if not ticker:
            failed.append({"key": key, "error": "no yahoo ticker mapping"})
            continue
        try:
            data = yf.download(
                ticker,
                period=period,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001
            failed.append({"key": key, "error": str(exc)})
            continue
        if data is None or len(data) < 30:
            failed.append({"key": key, "error": f"insufficient rows ({0 if data is None else len(data)})"})
            continue

        idx = _ensure_index(session, key)
        close_col = data["Close"]
        if hasattr(close_col, "columns"):
            close_col = close_col.iloc[:, 0]
        count = 0
        for ts, close in close_col.dropna().items():
            try:
                if hasattr(ts, "date"):
                    day = ts.date()
                else:
                    day = datetime.strptime(str(ts)[:10], "%Y-%m-%d").date()
                val = float(close)
            except (TypeError, ValueError):
                continue
            row = session.scalar(
                select(MarketIndexPrice).where(
                    MarketIndexPrice.index_id == idx.id,
                    MarketIndexPrice.price_date == day,
                )
            )
            if row is None:
                row = MarketIndexPrice(index_id=idx.id, price_date=day)
                session.add(row)
            row.close = val
            count += 1
        session.commit()
        stored += count
        ok.append(key)
        logger.info("Backfilled %s (%s): %s bars", key, ticker, count)

    return {
        "ok": True,
        "indices_ok": len(ok),
        "indices_failed": len(failed),
        "price_rows": stored,
        "ok_keys": ok,
        "failures": failed[:20],
        "period": period,
    }


def backfill_sectoral_index_prices(session: Session, *, period: str = "1y") -> dict[str, Any]:
    keys = list(SECTORAL_INDEX_KEYS.values())
    return backfill_index_prices(session, period=period, keys=keys)
