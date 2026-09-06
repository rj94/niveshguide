from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from database.models import Stock
from database.repository import upsert_indicator, upsert_prices, upsert_snapshot, upsert_stock
from indicators.trend_score import distance_from_52w_high, trend_score
from ingestion.normalize import parse_number


def _num(row: dict[str, Any], key: str):
    return parse_number(row.get(key))


def _int(row: dict[str, Any], key: str) -> int | None:
    value = parse_number(row.get(key))
    if value is None:
        return None
    return int(round(value))


def ingest_snapshots(session: Session, rows: list[dict[str, Any]], source: str, snapshot_date: date | None = None) -> int:
    snapshot_date = snapshot_date or date.today()
    count = 0
    for row in rows:
        stock = upsert_stock(session, row["symbol"], row.get("company_name"))
        fields = {
            "market_cap": _num(row, "market_cap"),
            "ltp": _num(row, "ltp"),
            "day_high": _num(row, "day_high"),
            "prev_close": _num(row, "prev_close"),
            "high_52_week": _num(row, "high_52_week"),
            "low_52_week": _num(row, "low_52_week"),
            "pe": _num(row, "pe"),
            "eps": _num(row, "eps"),
            "volume": _int(row, "volume"),
            "avg_volume_3m": _num(row, "avg_volume_3m"),
            "avg_volume_6m": _num(row, "avg_volume_6m"),
            "avg_volume_1y": _num(row, "avg_volume_1y"),
            "source": source,
        }
        ltp = fields["ltp"]
        if ltp is None:
            continue
        upsert_snapshot(session, stock.id, snapshot_date, fields)
        if ltp:
            upsert_prices(
                session,
                stock.id,
                [
                    {
                        "price_date": snapshot_date,
                        "close": ltp,
                        "high": fields["day_high"],
                        "open": fields["prev_close"],
                        "volume": fields["volume"],
                    }
                ],
            )
        ma_fields = {
            "ma_3": _num(row, "ma_3"),
            "ma_7": _num(row, "ma_7"),
            "ma_21": _num(row, "ma_21"),
            "ma_50": _num(row, "ma_50"),
            "ma_200": _num(row, "ma_200"),
        }
        if any(value is not None for value in ma_fields.values()) or ltp:
            scored = trend_score(
                ma_fields["ma_3"],
                ma_fields["ma_7"],
                ma_fields["ma_21"],
                ma_fields["ma_50"],
                ma_fields["ma_200"],
                ltp,
            )
            distance = _num(row, "distance_from_52w_high")
            if distance is None:
                distance = distance_from_52w_high(ltp, fields["high_52_week"])
            upsert_indicator(
                session,
                stock.id,
                snapshot_date,
                {**ma_fields, **scored, "distance_from_52w_high": distance},
            )
        count += 1
    return count


def ingest_momentum_history(session: Session, rows: list[list[Any]], ingest_days: int | None = None) -> int:
    """Load 2 years of daily closes from a Momentum tab into stock_prices."""
    from google_sheets.formulas import MOMENTUM_INGEST_DAYS
    from ingestion.momentum_history import parse_momentum_grid

    window = ingest_days if ingest_days is not None else MOMENTUM_INGEST_DAYS
    points = parse_momentum_grid(rows, window)
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for point in points:
        by_symbol.setdefault(point["symbol"], []).append(
            {"price_date": point["price_date"], "close": point["close"]}
        )
    stored = 0
    for symbol, prices in by_symbol.items():
        stock = upsert_stock(session, symbol)
        stored += upsert_prices(session, stock.id, prices)
    return stored


def fetch_yahoo_history(symbols: list[str], period: str = "1y") -> dict[str, list[dict[str, Any]]]:
    """Backfill OHLCV from Yahoo Finance (NSE suffix .NS)."""
    import yfinance as yf

    if not symbols:
        return {}
    tickers = " ".join(f"{symbol}.NS" for symbol in symbols)
    frame = yf.download(
        tickers,
        period=period,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    result: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    if frame.empty:
        return result

    if len(symbols) == 1:
        symbol = symbols[0]
        for idx, row in frame.iterrows():
            close = parse_number(row.get("Close"))
            if close is None:
                continue
            result[symbol].append(
                {
                    "price_date": idx.date() if hasattr(idx, "date") else idx,
                    "open": parse_number(row.get("Open")),
                    "high": parse_number(row.get("High")),
                    "low": parse_number(row.get("Low")),
                    "close": close,
                    "volume": int(row["Volume"]) if parse_number(row.get("Volume")) is not None else None,
                }
            )
        return result

    for symbol in symbols:
        key = f"{symbol}.NS"
        if key not in frame.columns.get_level_values(0) and symbol not in frame.columns.get_level_values(0):
            continue
        subset_key = key if key in frame.columns.get_level_values(0) else symbol
        subset = frame[subset_key]
        for idx, row in subset.iterrows():
            close = parse_number(row.get("Close"))
            if close is None:
                continue
            result[symbol].append(
                {
                    "price_date": idx.date() if hasattr(idx, "date") else idx,
                    "open": parse_number(row.get("Open")),
                    "high": parse_number(row.get("High")),
                    "low": parse_number(row.get("Low")),
                    "close": close,
                    "volume": int(row["Volume"]) if parse_number(row.get("Volume")) is not None else None,
                }
            )
    return result


def backfill_prices(session: Session, symbols: list[str] | None = None, period: str = "1y") -> int:
    if symbols is None:
        symbols = [row[0] for row in session.query(Stock.symbol).filter(Stock.is_active.is_(True)).all()]
    stored = 0
    chunk_size = 40
    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[start : start + chunk_size]
        history = fetch_yahoo_history(chunk, period=period)
        for symbol, rows in history.items():
            stock = upsert_stock(session, symbol)
            stored += upsert_prices(session, stock.id, rows)
        session.commit()
    return stored
