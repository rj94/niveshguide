from indicators.moving_averages import moving_averages
from indicators.trend_score import classify_trend, distance_from_52w_high, trend_score


def test_moving_averages_windows():
    closes = list(range(1, 201))
    result = moving_averages(closes)
    assert result["ma_3"] == (198 + 199 + 200) / 3
    assert result["ma_7"] == sum(range(194, 201)) / 7
    assert result["ma_200"] == sum(range(1, 201)) / 200
    assert moving_averages([1, 2])["ma_3"] is None
    assert moving_averages([1, 2])["ma_200"] is None


def test_trend_score_all_bullish_is_strong_uptrend():
    result = trend_score(ma_3=12, ma_7=11, ma_21=10, ma_50=9, ma_200=8, ltp=13)
    assert result["trend_score"] == 5
    assert result["trend"] == "Strong Uptrend"
    assert result["crossover_3_7"] is True
    assert result["golden_cross"] is True


def test_trend_score_all_bearish_is_strong_downtrend():
    result = trend_score(ma_3=8, ma_7=9, ma_21=10, ma_50=11, ma_200=12, ltp=7)
    assert result["trend_score"] == 0
    assert classify_trend(result["trend_score"]) == "Strong Downtrend"


def test_distance_from_52w_high_matches_plan_examples():
    assert round(distance_from_52w_high(2270, 2301.4), 2) == -1.36
    assert round(distance_from_52w_high(1235, 1838.9), 2) == -32.84
    assert distance_from_52w_high(100, None) is None
