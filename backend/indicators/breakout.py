from __future__ import annotations

from typing import Any


def is_strong_momentum(row: dict[str, Any], near_high: bool = False) -> bool:
    flags = [
        row.get("crossover_3_7"),
        row.get("above_ma_21"),
        row.get("ma21_gt_ma50"),
        row.get("above_ma_200"),
        row.get("golden_cross"),
    ]
    if not all(flags):
        return False
    if near_high:
        distance = row.get("distance_from_52w_high")
        return distance is not None and distance > -10
    return True


def is_long_term_uptrend(row: dict[str, Any]) -> bool:
    return bool(row.get("above_ma_200") and row.get("golden_cross"))


def is_breakout_watchlist(row: dict[str, Any]) -> bool:
    distance = row.get("distance_from_52w_high")
    return (
        distance is not None
        and distance >= -5
        and bool(row.get("above_ma_21"))
        and bool(row.get("golden_cross"))
    )


def is_weak_avoid(row: dict[str, Any]) -> bool:
    ltp = row.get("ltp")
    ma_21 = row.get("ma_21")
    ma_50 = row.get("ma_50")
    ma_200 = row.get("ma_200")
    if None in (ltp, ma_21, ma_50, ma_200):
        return False
    return ltp < ma_21 and ltp < ma_50 and ltp < ma_200 and ma_50 < ma_200


SCREENERS = {
    "strong-momentum": lambda row: is_strong_momentum(row, near_high=False),
    "strong-momentum-near-high": lambda row: is_strong_momentum(row, near_high=True),
    "long-term-uptrend": is_long_term_uptrend,
    "breakout-watchlist": is_breakout_watchlist,
    "weak-avoid": is_weak_avoid,
}
