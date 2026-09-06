from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from database.models import StockIndicator
from database.repository import add_signal
from indicators.crossover import (
    bearish_3_7_crossover,
    bullish_3_7_crossover,
    death_cross_fresh,
    golden_cross_fresh,
)
from indicators.breakout import is_breakout_watchlist, is_strong_momentum


def generate_signals(
    session: Session,
    stock_id: int,
    calc_date: date,
    current: dict,
    previous: StockIndicator | None,
    row_for_screens: dict,
) -> list[str]:
    created: list[str] = []

    def emit(signal_type: str, direction: str, metadata: dict | None = None) -> None:
        add_signal(session, stock_id, calc_date, signal_type, direction, metadata)
        created.append(signal_type)

    if previous:
        if bullish_3_7_crossover(previous.ma_3, previous.ma_7, current.get("ma_3"), current.get("ma_7")):
            emit("BULLISH_3_7_CROSSOVER", "BULLISH")
        if bearish_3_7_crossover(previous.ma_3, previous.ma_7, current.get("ma_3"), current.get("ma_7")):
            emit("BEARISH_3_7_CROSSOVER", "BEARISH")
        if golden_cross_fresh(previous.ma_50, previous.ma_200, current.get("ma_50"), current.get("ma_200")):
            emit("GOLDEN_CROSS", "BULLISH")
        if death_cross_fresh(previous.ma_50, previous.ma_200, current.get("ma_50"), current.get("ma_200")):
            emit("DEATH_CROSS", "BEARISH")
        if previous.trend != "Strong Uptrend" and current.get("trend") == "Strong Uptrend":
            emit("ENTERED_STRONG_UPTREND", "BULLISH")
        if previous.trend == "Strong Uptrend" and current.get("trend") != "Strong Uptrend":
            emit("EXITED_STRONG_UPTREND", "BEARISH")

    distance = current.get("distance_from_52w_high")
    if distance is not None and distance >= 0:
        emit("NEW_52_WEEK_HIGH", "BULLISH", {"distance": distance})

    if is_breakout_watchlist(row_for_screens):
        emit("BREAKOUT_WATCHLIST", "BULLISH")
    if is_strong_momentum(row_for_screens):
        emit("STRONG_MOMENTUM", "BULLISH")

    return created
