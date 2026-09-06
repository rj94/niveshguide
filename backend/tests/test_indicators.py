from indicators.breakout import is_breakout_watchlist, is_strong_momentum, is_weak_avoid
from indicators.crossover import bearish_3_7_crossover, bullish_3_7_crossover


def test_fresh_crossover_requires_state_change():
    assert bullish_3_7_crossover(10, 11, 12, 11) is True
    assert bullish_3_7_crossover(12, 11, 13, 11) is False
    assert bearish_3_7_crossover(12, 11, 10, 11) is True


def test_screener_predicates():
    strong = {
        "crossover_3_7": True,
        "above_ma_21": True,
        "ma21_gt_ma50": True,
        "above_ma_200": True,
        "golden_cross": True,
        "distance_from_52w_high": -1.3,
        "ltp": 2270,
        "ma_21": 2111,
        "ma_50": 1966,
        "ma_200": 1959,
    }
    assert is_strong_momentum(strong) is True
    assert is_breakout_watchlist(strong) is True
    weak = {
        "ltp": 100,
        "ma_21": 110,
        "ma_50": 120,
        "ma_200": 130,
        "above_ma_21": False,
        "golden_cross": False,
        "distance_from_52w_high": -40,
    }
    assert is_weak_avoid(weak) is True
    assert is_strong_momentum(weak) is False
