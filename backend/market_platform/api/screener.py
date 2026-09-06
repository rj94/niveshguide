from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_session
from market_platform.schemas.stocks import StockAnalysisResponse
from market_platform.services import stocks as stock_service

router = APIRouter()


@router.get("", response_model=StockAnalysisResponse)
def screen_stocks(
    q: str | None = Query(default=None),
    exchange: str | None = Query(default=None),
    price_above_50_above_200: bool | None = Query(default=None),
    sma_50_above_200: bool | None = Query(default=None),
    volume_mover: bool | None = Query(default=None),
    volume_gainer: bool | None = Query(
        default=None,
        description="avg 1-week volume greater than 3m, 6m, and 1y averages",
    ),
    min_return_1m: float | None = Query(default=None),
    min_return_3m: float | None = Query(default=None),
    min_return_6m: float | None = Query(default=None),
    min_company_strength: float | None = Query(default=None, ge=0, le=100),
    min_momentum_score: float | None = Query(default=None, ge=0, le=100),
    min_momentum_acceleration: float | None = Query(default=None),
    momentum_category: str | None = Query(default=None),
    trend: str | None = Query(
        default=None,
        description="strong-momentum | fresh-uptrend | long-term-uptrend | breakout-watchlist | weak-avoid",
    ),
    min_score: int | None = Query(default=None, ge=0, le=5),
    sort_by: str = Query(default="momentum_score"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    scan_limit: int = Query(default=8000, ge=50, le=10000),
    db: Session = Depends(get_session),
) -> StockAnalysisResponse:
    items, total, scanned = stock_service.list_stock_analysis(
        db,
        q=q,
        exchange=exchange,
        price_above_50_above_200=price_above_50_above_200,
        sma_50_above_200=sma_50_above_200,
        volume_mover=volume_mover,
        volume_gainer=volume_gainer,
        min_return_1m=min_return_1m,
        min_return_3m=min_return_3m,
        min_return_6m=min_return_6m,
        min_company_strength=min_company_strength,
        min_momentum_score=min_momentum_score,
        min_momentum_acceleration=min_momentum_acceleration,
        momentum_category=momentum_category,
        trend=trend,
        min_score=min_score,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        scan_limit=scan_limit,
    )
    return StockAnalysisResponse(items=items, total=total, scanned=scanned)
