from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_session
from market_platform.schemas.stocks import StockDetail, StockListResponse
from market_platform.services import stocks as stock_service

router = APIRouter()


@router.get("", response_model=StockListResponse)
def list_stocks(
    q: str | None = None,
    exchange: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
) -> StockListResponse:
    return stock_service.list_stocks(db, q=q, exchange=exchange, limit=limit, offset=offset)


@router.get("/{symbol}", response_model=StockDetail)
def get_stock(
    symbol: str,
    exchange: str | None = Query(default=None),
    price_limit: int = Query(default=730, ge=50, le=1000),
    db: Session = Depends(get_session),
) -> StockDetail:
    detail = stock_service.get_stock_detail(db, symbol, exchange=exchange, price_limit=price_limit)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol {symbol}")
    return detail
