"""Parse the wide Momentum NSE tab into daily close rows for stock_prices."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from google_sheets.formulas import MOMENTUM_INGEST_DAYS
from ingestion.normalize import parse_number

_SKIP_HEADERS = {"", "NSE DATA", "SYMBOL", "DATE", "NIFTY", "SELECTED", "CLOSE", "MARKETCAP", "PRICE"}
_SHEETS_EPOCH = date(1899, 12, 30)


def parse_sheet_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        serial = float(text)
        if serial > 20000:
            return _SHEETS_EPOCH + timedelta(days=int(serial))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text[:19] if ":" in text else text[:10], fmt).date()
        except ValueError:
            continue
    return None


def momentum_symbols(rows: list[list[Any]]) -> list[str]:
    if not rows:
        return []
    seen: set[str] = set()
    symbols: list[str] = []
    for cell in rows[0]:
        name = str(cell or "").strip().upper()
        if name in _SKIP_HEADERS or name.startswith("RETURN") or name in seen:
            continue
        seen.add(name)
        symbols.append(name)
    return symbols


def parse_momentum_grid(rows: list[list[Any]], ingest_days: int = MOMENTUM_INGEST_DAYS) -> list[dict[str, Any]]:
    """Turn one-symbol-per-column history into {symbol, price_date, close}."""
    if not rows:
        return []
    header = rows[0]
    symbols: list[tuple[int, str]] = []
    seen: set[str] = set()
    for index, cell in enumerate(header):
        name = str(cell or "").strip().upper()
        if name in _SKIP_HEADERS or name.startswith("RETURN"):
            continue
        if name in seen:
            continue
        seen.add(name)
        symbols.append((index, name))
    if not symbols:
        return []

    hist_start = None
    for offset, row in enumerate(rows):
        if row and parse_sheet_date(row[0]):
            hist_start = offset
            break
    if hist_start is None:
        return []

    cutoff = date.today() - timedelta(days=ingest_days)
    points: list[dict[str, Any]] = []
    for col, symbol in symbols:
        for row in rows[hist_start:]:
            if not row:
                continue
            price_date = parse_sheet_date(row[0])
            if price_date is None or price_date < cutoff:
                continue
            if col >= len(row):
                continue
            close = parse_number(row[col])
            if close is None:
                continue
            points.append({"symbol": symbol, "price_date": price_date, "close": close})
    return points
