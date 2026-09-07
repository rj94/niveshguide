from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cache.redis_cache import PREFIX_STRATEGY, get_json, set_json
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
    cache_key = (
        f"{PREFIX_STRATEGY}{slug.lower()}:{exchange or ''}:{q or ''}:"
        f"{scan_limit}:{offset}:{limit}"
    )
    cached = get_json(cache_key)
    if cached is not None:
        try:
            return StrategyRunResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            pass
    try:
        result = run_strategy(
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
    set_json(cache_key, result.model_dump(mode="json"), 120)
    return result
