from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_session
from market_platform.engines.runner import list_strategies, run_strategy
from market_platform.schemas.strategies import StrategyListResponse, StrategyRunResponse

router = APIRouter()


@router.get("", response_model=StrategyListResponse)
def get_strategies() -> StrategyListResponse:
    return list_strategies()


@router.get("/{slug}", response_model=StrategyRunResponse)
def get_strategy_run(
    slug: str,
    exchange: str | None = Query(default="NSE"),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scan_limit: int = Query(default=5000, ge=50, le=5000),
    db: Session = Depends(get_session),
) -> StrategyRunResponse:
    try:
        return run_strategy(
            db,
            slug,
            exchange=exchange,
            q=q,
            limit=limit,
            offset=offset,
            scan_limit=scan_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
