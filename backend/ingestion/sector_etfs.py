"""Refresh the small curated ETF strip used by the home/markets UI."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from database.repository import get_stock_by_symbol, upsert_prices, upsert_snapshot, upsert_stock
from ingestion.ingest_stocks import fetch_yahoo_history

# Keep in sync with market_platform.services.markets INDEX_ETFS + SECTOR_ETFS.
KEY_ETFS: tuple[tuple[str, str, str, str | None], ...] = (
    ("NIFTYBEES", "Nifty 50 ETF", "index", None),
    ("BANKBEES", "Bank Nifty ETF", "index", None),
    ("JUNIORBEES", "Nifty Next 50 ETF", "index", None),
    ("MONIFTY500", "Nifty 500 ETF", "index", None),
    ("NIF100BEES", "Nifty 100 ETF", "index", None),
    ("ITBEES", "IT ETF", "sector", "Information Technology"),
    ("PHARMABEES", "Pharma ETF", "sector", "Healthcare"),
    ("PSUBNKBEES", "PSU Bank ETF", "sector", "Financials"),
    ("AUTOBEES", "Auto ETF", "sector", "Consumer"),
    ("INFRABEES", "Infra ETF", "sector", "Industrials"),
    ("CONSUMBEES", "Consumption ETF", "sector", "Consumer"),
    ("GOLDBEES", "Gold ETF", "commodity", None),
)


def key_etf_symbols() -> list[str]:
    return [symbol for symbol, *_ in KEY_ETFS]


def refresh_key_etf_quotes(session: Session, *, symbols: list[str] | None = None) -> dict[str, Any]:
    target_symbols = [s.strip().upper() for s in symbols or [] if s.strip()] or key_etf_symbols()
    history = fetch_yahoo_history(target_symbols, period="5d")
    today = date.today()
    stored = 0
    missing: list[str] = []

    for symbol in target_symbols:
        rows = history.get(symbol) or []
        if not rows:
            missing.append(symbol)
            continue
        latest = rows[-1]
        prev = rows[-2]["close"] if len(rows) >= 2 else None
        ltp = latest.get("close")
        stock = get_stock_by_symbol(session, symbol) or upsert_stock(session, symbol)
        upsert_prices(session, stock.id, rows)
        upsert_snapshot(
            session,
            stock.id,
            today,
            {
                "ltp": ltp,
                "prev_close": prev,
                "source": "yahoo",
            },
        )
        stored += 1

    session.commit()
    return {"requested": len(target_symbols), "stored": stored, "missing": missing}
