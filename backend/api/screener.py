from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from api.serializers import serialize_row
from database.repository import get_previous_indicator, latest_screener_query
from database.session import get_session
from indicators.breakout import SCREENERS
from indicators.crossover import bullish_3_7_crossover

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("")
def screener(
    trend: str | None = Query(None, description="strong-momentum | fresh-uptrend | long-term-uptrend | breakout-watchlist | weak-avoid"),
    min_score: int | None = Query(None, ge=0, le=5),
    max_score: int | None = Query(None, ge=0, le=5),
    q: str | None = None,
    sort: str = Query("score", description="score | distance | ltp | symbol | market_cap | return_3m | return_6m"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_session),
):
    rows = db.execute(latest_screener_query(db)).all()
    items = []
    for stock, indicator, snapshot in rows:
        payload = serialize_row(stock, indicator, snapshot)
        previous = get_previous_indicator(db, stock.id, indicator.calculation_date)
        payload["_fresh_uptrend"] = bool(
            previous
            and bullish_3_7_crossover(previous.ma_3, previous.ma_7, indicator.ma_3, indicator.ma_7)
            and indicator.above_ma_21
        )
        items.append(payload)

    if q:
        needle = q.strip().upper()
        items = [
            item
            for item in items
            if needle in item["symbol"] or needle in (item.get("company_name") or "").upper()
        ]
    if min_score is not None:
        items = [item for item in items if (item.get("trend_score") or 0) >= min_score]
    if max_score is not None:
        items = [item for item in items if (item.get("trend_score") or 0) <= max_score]
    if trend:
        if trend == "fresh-uptrend":
            items = [item for item in items if item.get("_fresh_uptrend")]
        elif trend in SCREENERS:
            items = [item for item in items if SCREENERS[trend](item)]
        else:
            items = [item for item in items if (item.get("trend") or "").lower().replace(" ", "-") == trend]

    reverse = sort != "symbol"
    key_map = {
        "score": lambda item: item.get("trend_score") or -1,
        "distance": lambda item: item.get("distance_from_52w_high") if item.get("distance_from_52w_high") is not None else -999,
        "ltp": lambda item: item.get("ltp") or -1,
        "symbol": lambda item: item.get("symbol") or "",
        "market_cap": lambda item: item.get("market_cap") or -1,
        "return_3m": lambda item: item.get("return_3m") if item.get("return_3m") is not None else -999,
        "return_6m": lambda item: item.get("return_6m") if item.get("return_6m") is not None else -999,
    }
    items.sort(key=key_map.get(sort, key_map["score"]), reverse=reverse)
    for item in items:
        item.pop("_fresh_uptrend", None)
    return {"count": len(items[:limit]), "total": len(items), "screen": trend, "items": items[:limit]}
