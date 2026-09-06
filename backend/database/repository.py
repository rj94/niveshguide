from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, aliased

from database.models import (
    DataSourceBatch,
    Stock,
    StockIndicator,
    StockPrice,
    StockSignal,
    StockSnapshot,
)


def _insert(table, session: Session):
    dialect = session.get_bind().dialect.name
    return sqlite_insert(table) if dialect == "sqlite" else pg_insert(table)


def upsert_stock(
    session: Session, symbol: str, company_name: str | None = None, isin: str | None = None
) -> Stock:
    symbol = symbol.strip().upper()
    stock = session.scalar(select(Stock).where(Stock.symbol == symbol))
    if stock is None:
        stock = Stock(symbol=symbol, company_name=company_name, isin=isin, exchange="NSE", is_active=True)
        session.add(stock)
        session.flush()
        return stock
    if company_name and not stock.company_name:
        stock.company_name = company_name
    if isin and not stock.isin:
        stock.isin = isin
    stock.is_active = True
    return stock


def get_stock_by_symbol(session: Session, symbol: str) -> Stock | None:
    return session.scalar(select(Stock).where(Stock.symbol == symbol.strip().upper()))


def upsert_snapshot(session: Session, stock_id: int, snapshot_date: date, fields: dict[str, Any]) -> None:
    stmt = _insert(StockSnapshot, session).values(stock_id=stock_id, snapshot_date=snapshot_date, **fields)
    update_cols = {key: getattr(stmt.excluded, key) for key in fields}
    stmt = stmt.on_conflict_do_update(index_elements=["stock_id", "snapshot_date"], set_=update_cols)
    session.execute(stmt)


def upsert_prices(session: Session, stock_id: int, rows: list[dict[str, Any]]) -> int:
    """Upsert OHLCV. Null incoming open/high/low/volume do not wipe existing values."""
    if not rows:
        return 0
    count = 0
    chunk_size = 400
    for start in range(0, len(rows), chunk_size):
        chunk = [{"stock_id": stock_id, **row} for row in rows[start : start + chunk_size]]
        stmt = _insert(StockPrice, session).values(chunk)
        excluded = stmt.excluded
        update_cols = {
            "close": excluded.close,
            "open": func.coalesce(excluded.open, StockPrice.open),
            "high": func.coalesce(excluded.high, StockPrice.high),
            "low": func.coalesce(excluded.low, StockPrice.low),
            "volume": func.coalesce(excluded.volume, StockPrice.volume),
        }
        stmt = stmt.on_conflict_do_update(index_elements=["stock_id", "price_date"], set_=update_cols)
        session.execute(stmt)
        count += len(chunk)
    return count


def upsert_indicator(session: Session, stock_id: int, calculation_date: date, fields: dict[str, Any]) -> None:
    stmt = _insert(StockIndicator, session).values(stock_id=stock_id, calculation_date=calculation_date, **fields)
    update_cols = {key: getattr(stmt.excluded, key) for key in fields}
    stmt = stmt.on_conflict_do_update(index_elements=["stock_id", "calculation_date"], set_=update_cols)
    session.execute(stmt)


def get_previous_indicator(session: Session, stock_id: int, before: date) -> StockIndicator | None:
    return session.scalar(
        select(StockIndicator)
        .where(StockIndicator.stock_id == stock_id, StockIndicator.calculation_date < before)
        .order_by(desc(StockIndicator.calculation_date))
        .limit(1)
    )


def latest_closes(session: Session, stock_id: int, limit: int = 220) -> list[float]:
    rows = session.scalars(
        select(StockPrice.close)
        .where(StockPrice.stock_id == stock_id, StockPrice.close.is_not(None))
        .order_by(desc(StockPrice.price_date))
        .limit(limit)
    ).all()
    return [float(value) for value in reversed(rows)]


def latest_close_volume_series(
    session: Session, stock_id: int, limit: int = 530
) -> tuple[list[float], list[float | None]]:
    """Oldest→newest closes and aligned volumes (None when missing)."""
    rows = session.execute(
        select(StockPrice.close, StockPrice.volume)
        .where(StockPrice.stock_id == stock_id, StockPrice.close.is_not(None))
        .order_by(desc(StockPrice.price_date))
        .limit(limit)
    ).all()
    rows = list(reversed(rows))
    closes = [float(r[0]) for r in rows]
    volumes: list[float | None] = [float(r[1]) if r[1] is not None else None for r in rows]
    return closes, volumes


def add_signal(
    session: Session,
    stock_id: int,
    signal_date: date,
    signal_type: str,
    direction: str | None,
    metadata: dict | None = None,
) -> None:
    existing = session.scalar(
        select(StockSignal).where(
            StockSignal.stock_id == stock_id,
            StockSignal.signal_date == signal_date,
            StockSignal.signal_type == signal_type,
        )
    )
    if existing:
        return
    session.add(
        StockSignal(
            stock_id=stock_id,
            signal_date=signal_date,
            signal_type=signal_type,
            direction=direction,
            metadata_json=metadata,
        )
    )


def latest_screener_query(session: Session) -> Select:
    """Join each active stock to its latest indicator row + latest snapshot."""
    snap = aliased(StockSnapshot)
    latest_ind = (
        select(
            StockIndicator.stock_id.label("stock_id"),
            func.max(StockIndicator.calculation_date).label("max_date"),
        )
        .group_by(StockIndicator.stock_id)
        .subquery()
    )
    latest_snap = (
        select(func.max(StockSnapshot.snapshot_date))
        .where(StockSnapshot.stock_id == Stock.id)
        .scalar_subquery()
    )
    return (
        select(Stock, StockIndicator, snap)
        .join(latest_ind, latest_ind.c.stock_id == Stock.id)
        .join(
            StockIndicator,
            (StockIndicator.stock_id == Stock.id)
            & (StockIndicator.calculation_date == latest_ind.c.max_date),
        )
        .outerjoin(snap, (snap.stock_id == Stock.id) & (snap.snapshot_date == latest_snap))
        .where(Stock.is_active.is_(True))
    )


def overview_counts(session: Session) -> dict[str, Any]:
    latest_date = session.scalar(select(func.max(StockIndicator.calculation_date)))
    if latest_date is None:
        return {"as_of": None, "total_active": 0, "by_trend": {}, "signals_today": {}}
    rows = session.execute(
        select(StockIndicator.trend, func.count())
        .where(StockIndicator.calculation_date == latest_date)
        .group_by(StockIndicator.trend)
    ).all()
    today_signals = session.execute(
        select(StockSignal.signal_type, func.count())
        .where(StockSignal.signal_date == latest_date)
        .group_by(StockSignal.signal_type)
    ).all()
    total = session.scalar(
        select(func.count()).select_from(StockIndicator).where(StockIndicator.calculation_date == latest_date)
    )
    return {
        "as_of": latest_date.isoformat(),
        "total_active": total or 0,
        "by_trend": {trend or "Unknown": count for trend, count in rows},
        "signals_today": {sig: count for sig, count in today_signals},
    }


def upsert_batch(session: Session, payload: dict[str, Any]) -> DataSourceBatch:
    batch = session.scalar(select(DataSourceBatch).where(DataSourceBatch.batch_name == payload["batch_name"]))
    if batch is None:
        batch = DataSourceBatch(**payload)
        session.add(batch)
        session.flush()
        return batch
    for key, value in payload.items():
        setattr(batch, key, value)
    return batch


def mark_batch_attempt(session: Session, batch: DataSourceBatch, error: str | None = None) -> None:
    batch.last_attempted_sync = datetime.utcnow()
    if error:
        batch.error_message = error[:1000]
        batch.retry_count = (batch.retry_count or 0) + 1
        batch.status = "FAILED"
    else:
        batch.last_successful_sync = datetime.utcnow()
        batch.error_message = None
        batch.retry_count = 0
        batch.status = "ACTIVE"
