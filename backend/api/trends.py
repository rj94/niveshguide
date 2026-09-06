from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from api.serializers import serialize_signal
from database.models import Stock, StockSignal
from database.session import get_session

router = APIRouter(tags=["signals"])


@router.get("/signals/today")
def signals_today(db: Session = Depends(get_session)):
    latest = db.scalar(select(StockSignal.signal_date).order_by(desc(StockSignal.signal_date)).limit(1))
    if latest is None:
        return {"as_of": None, "count": 0, "items": []}
    return _signals(db, latest)


@router.get("/signals/fresh-crossover")
def fresh_crossover(db: Session = Depends(get_session)):
    latest = db.scalar(select(StockSignal.signal_date).order_by(desc(StockSignal.signal_date)).limit(1))
    return _signals(db, latest, types=["BULLISH_3_7_CROSSOVER", "BEARISH_3_7_CROSSOVER"])


@router.get("/signals/golden-cross")
def golden_cross(db: Session = Depends(get_session)):
    latest = db.scalar(select(StockSignal.signal_date).order_by(desc(StockSignal.signal_date)).limit(1))
    return _signals(db, latest, types=["GOLDEN_CROSS", "DEATH_CROSS"])


@router.get("/breakout-watchlist")
def breakout_watchlist(
    db: Session = Depends(get_session),
    limit: int = Query(100, ge=1, le=500),
):
    from api.screener import screener

    return screener(trend="breakout-watchlist", min_score=None, max_score=None, q=None, sort="distance", limit=limit, db=db)


def _signals(db: Session, as_of: date | None, types: list[str] | None = None):
    if as_of is None:
        return {"as_of": None, "count": 0, "items": []}
    query = (
        select(Stock, StockSignal)
        .join(StockSignal, StockSignal.stock_id == Stock.id)
        .where(StockSignal.signal_date == as_of)
        .order_by(Stock.symbol)
    )
    if types:
        query = query.where(StockSignal.signal_type.in_(types))
    rows = db.execute(query).all()
    items = [serialize_signal(stock, signal) for stock, signal in rows]
    return {"as_of": as_of.isoformat(), "count": len(items), "items": items}
