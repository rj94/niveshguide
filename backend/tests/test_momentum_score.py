"""Unit tests for V1 momentum score helpers."""

from indicators.momentum_score import (
    blend_momentum_score,
    compute_dma_score,
    compute_result_score,
    compute_return_score,
    compute_volume_score,
    finalize_momentum_fields,
    growth_bucket_score,
    momentum_category,
    percentile_rank,
    percentile_to_bucket_score,
    volume_ratio_score,
)


def test_percentile_buckets():
    assert percentile_to_bucket_score(0.95) == 100
    assert percentile_to_bucket_score(0.85) == 90
    assert percentile_to_bucket_score(0.70) == 70
    assert percentile_to_bucket_score(0.50) == 50
    assert percentile_to_bucket_score(0.30) == 30
    assert percentile_to_bucket_score(0.10) == 10


def test_percentile_rank_ordering():
    universe = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert percentile_rank(0.5, universe) == 0.9  # 4 below + 0.5 tie / 5
    assert percentile_rank(0.1, universe) == 0.1


def test_dma_score_full_stack():
    score = compute_dma_score(
        price=110,
        ma_20=105,
        ma_50=100,
        ma_200=90,
        distance_from_52w_high=-0.05,
    )
    # 15+20+25+15+15+10 = 100
    assert score == 100


def test_dma_score_partial():
    score = compute_dma_score(
        price=80,
        ma_20=100,
        ma_50=90,
        ma_200=70,
        distance_from_52w_high=-0.30,
    )
    # price > 200 (25) + 20>50 (15) + 50>200 (15) = 55
    assert score == 55


def test_volume_ratio_and_blend():
    assert volume_ratio_score(3.5) == 100
    assert volume_ratio_score(0.5) == 20
    score = compute_volume_score(volume_ratio=2.0, positive_volume_days_20=0.5, return_5d=0.02)
    # 60%*85 + 40%*50 = 51+20 = 71, +5 confirmation = 76
    assert score == 76.0


def test_result_score_renormalize_when_partial():
    score = compute_result_score(
        revenue_growth_yoy=0.25,
        pat_growth_yoy=0.35,
        revenue_growth_qoq=None,
        pat_growth_qoq=None,
        margin_change=None,
        earnings_acceleration=None,
    )
    # Only rev 80 (25%) and pat 100 (30%) → renormalize to 25/55 and 30/55
    assert score is not None
    assert 85 < score < 95


def test_growth_bucket():
    assert growth_bucket_score(0.35) == 100
    assert growth_bucket_score(-0.05) == 10


def test_blend_and_category():
    final = blend_momentum_score(90, 85, 70, 80)
    assert final is not None
    assert abs(final - 82.25) < 0.01
    assert momentum_category(82.25) == "Positive Momentum"
    assert momentum_category(90) == "Strong Momentum"
    assert momentum_category(10) == "Negative"


def test_finalize_momentum_fields():
    raw = {
        "ltp": 100,
        "ma_20": 95,
        "ma_50": 90,
        "ma_200": 80,
        "distance_from_52w_high": -0.05,
        "return_1m": 0.1,
        "return_3m": 0.2,
        "return_6m": 0.15,
        "return_12m": 0.3,
        "volume_ratio": 1.8,
        "positive_volume_days_20": 0.4,
        "return_5d": 0.01,
        "revenue_growth_yoy": 0.2,
        "pat_growth_yoy": 0.25,
        "revenue_growth_qoq": 0.05,
        "pat_growth_qoq": 0.08,
        "margin_change": 1.0,
        "earnings_acceleration": 0.02,
    }
    universes = {
        "return_1m": [0.0, 0.05, 0.1, 0.15],
        "return_3m": [0.0, 0.1, 0.2, 0.3],
        "return_6m": [0.0, 0.1, 0.15, 0.2],
        "return_12m": [0.0, 0.1, 0.2, 0.3],
    }
    out = finalize_momentum_fields(raw, universes)
    assert out["momentum_score"] is not None
    assert out["momentum_category"] is not None
    assert out["return_score"] is not None
    assert out["dma_score"] == 100
