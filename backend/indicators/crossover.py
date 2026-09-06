from __future__ import annotations


def bullish_3_7_crossover(prev_ma3, prev_ma7, ma3, ma7) -> bool:
    if None in (prev_ma3, prev_ma7, ma3, ma7):
        return False
    return prev_ma3 <= prev_ma7 and ma3 > ma7


def bearish_3_7_crossover(prev_ma3, prev_ma7, ma3, ma7) -> bool:
    if None in (prev_ma3, prev_ma7, ma3, ma7):
        return False
    return prev_ma3 >= prev_ma7 and ma3 < ma7


def golden_cross_fresh(prev_ma50, prev_ma200, ma50, ma200) -> bool:
    if None in (prev_ma50, prev_ma200, ma50, ma200):
        return False
    return prev_ma50 <= prev_ma200 and ma50 > ma200


def death_cross_fresh(prev_ma50, prev_ma200, ma50, ma200) -> bool:
    if None in (prev_ma50, prev_ma200, ma50, ma200):
        return False
    return prev_ma50 >= prev_ma200 and ma50 < ma200
