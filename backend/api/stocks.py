from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from api.serializers import serialize_row, serialize_signal
from database.models import Stock, StockIndicator, StockPrice, StockSignal, StockSnapshot
from database.repository import get_stock_by_symbol
from database.session import get_session

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("")
def list_stocks(
    q: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    filters = [Stock.is_active.is_(True)]
    if q:
        needle = q.strip()
        filters.append(or_(Stock.symbol.ilike(f"%{needle}%"), Stock.company_name.ilike(f"%{needle}%")))
    total = db.scalar(select(func.count()).select_from(Stock).where(*filters)) or 0
    rows = db.scalars(
        select(Stock).where(*filters).order_by(Stock.symbol).offset(offset).limit(limit)
    ).all()
    return {
        "count": len(rows),
        "total": total,
        "items": [{"symbol": stock.symbol, "company_name": stock.company_name, "exchange": stock.exchange} for stock in rows],
    }


@router.get("/{symbol}")
def stock_detail(symbol: str, db: Session = Depends(get_session)):
    stock = get_stock_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(404, f"Unknown symbol {symbol}")
    indicator = db.scalar(
        select(StockIndicator)
        .where(StockIndicator.stock_id == stock.id)
        .order_by(desc(StockIndicator.calculation_date))
        .limit(1)
    )
    snapshot = db.scalar(
        select(StockSnapshot)
        .where(StockSnapshot.stock_id == stock.id)
        .order_by(desc(StockSnapshot.snapshot_date))
        .limit(1)
    )
    prices = db.scalars(
        select(StockPrice)
        .where(StockPrice.stock_id == stock.id)
        .order_by(desc(StockPrice.price_date))
        .limit(520)
    ).all()
    signals = db.scalars(
        select(StockSignal)
        .where(StockSignal.stock_id == stock.id)
        .order_by(desc(StockSignal.signal_date), desc(StockSignal.id))
        .limit(50)
    ).all()
    payload = serialize_row(stock, indicator, snapshot)
    payload["prices"] = [
        {
            "date": price.price_date.isoformat(),
            "open": float(price.open) if price.open is not None else None,
            "high": float(price.high) if price.high is not None else None,
            "low": float(price.low) if price.low is not None else None,
            "close": float(price.close) if price.close is not None else None,
            "volume": price.volume,
        }
        for price in reversed(list(prices))
    ]
    payload["signals"] = [serialize_signal(stock, item) for item in signals]
    payload["trend_history"] = [
        {
            "date": item.calculation_date.isoformat(),
            "trend": item.trend,
            "trend_score": item.trend_score,
            "ma_3": float(item.ma_3) if item.ma_3 is not None else None,
            "ma_7": float(item.ma_7) if item.ma_7 is not None else None,
            "ma_21": float(item.ma_21) if item.ma_21 is not None else None,
            "ma_50": float(item.ma_50) if item.ma_50 is not None else None,
            "ma_200": float(item.ma_200) if item.ma_200 is not None else None,
        }
        for item in db.scalars(
            select(StockIndicator)
            .where(StockIndicator.stock_id == stock.id)
            .order_by(desc(StockIndicator.calculation_date))
            .limit(30)
        ).all()
    ]
    return payload
