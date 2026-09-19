"""Unit tests for the sector strength engine."""

from market_platform.engines.sector_rotation import (
    INDUSTRY_WEIGHTS,
    SECTOR_WEIGHTS,
    StockFeature,
    aggregate_features,
    classify_rotation,
    emerging_score,
    extension_penalty,
    percentile_score,
    strength_score,
    volume_component,
    weighted_blend,
)


def test_component_weights_sum_to_one():
    assert round(sum(SECTOR_WEIGHTS.values()), 6) == 1.0
    assert round(sum(INDUSTRY_WEIGHTS.values()), 6) == 1.0
    assert "trend" not in INDUSTRY_WEIGHTS


def test_percentile_normalize():
    universe = [0.1, 0.2, 0.3, 0.4]
    assert percentile_score(0.4, universe) == 87.5  # (3 + 0.5) / 4 * 100
    assert percentile_score(0.1, universe) == 12.5


def test_extension_penalty():
    assert extension_penalty(1.10) == 0.0
    assert extension_penalty(1.16) == 10.0
    assert extension_penalty(1.21) == 20.0
    assert extension_penalty(None) == 0.0


def test_weighted_blend_renormalizes_missing():
    # Only RS 25% and momentum 20% present → 25/45 and 20/45
    score = weighted_blend([(100.0, 0.25), (50.0, 0.20), (None, 0.20)])
    assert score is not None
    expected = 100 * (0.25 / 0.45) + 50 * (0.20 / 0.45)
    assert abs(score - expected) < 0.01


def test_sector_vs_industry_strength_weights():
    kwargs = dict(
        rs_score=100.0,
        momentum_score=0.0,
        breadth_score=0.0,
        volume_score=0.0,
        breakout_score=0.0,
        trend_score=0.0,
    )
    sector = strength_score(kind="sector", **kwargs)
    industry = strength_score(kind="industry", **kwargs)
    assert sector == 25.0
    assert industry == 30.0


def test_volume_drops_delivery_and_redistributes():
    agg = aggregate_features(
        "Banks",
        [
            StockFeature(
                stock_id=1,
                price_up_volume_up=True,
                volume_ratio=2.0,
                turnover_5d=150,
                turnover_20d=100,
            ),
            StockFeature(
                stock_id=2,
                price_up_volume_up=True,
                volume_ratio=1.6,
                turnover_5d=150,
                turnover_20d=100,
            ),
        ],
    )
    score = volume_component(agg)
    assert score is not None
    # 100% price-up+vol, turnover 1.5x → 75, 100% vol>1.5x
    # 0.44*100 + 0.31*75 + 0.25*100 = 44+23.25+25 = 92.25
    assert 90 < score < 95


def test_rotation_leading():
    assert (
        classify_rotation(
            rs_score=70,
            momentum_score=70,
            breadth_score=70,
            strength_score=70,
            score_change_5d=2,
            momentum_change_5d=1,
            breadth_change_5d=1,
        )
        == "Leading"
    )


def test_rotation_weakening_overrides_leading_when_declining():
    assert (
        classify_rotation(
            rs_score=70,
            momentum_score=70,
            breadth_score=70,
            strength_score=70,
            momentum_change_5d=-3,
            breadth_change_5d=1,
        )
        == "Weakening"
    )


def test_rotation_improving():
    assert (
        classify_rotation(
            rs_score=50,
            momentum_score=60,
            breadth_score=50,
            strength_score=58,
            score_change_5d=4,
            rs_change_5d=3,
            breadth_change_5d=2,
        )
        == "Improving"
    )


def test_rotation_lagging():
    assert (
        classify_rotation(
            rs_score=30,
            momentum_score=25,
            breadth_score=20,
            strength_score=28,
            score_change_5d=-1,
        )
        == "Lagging"
    )


def test_rotation_nearest_bucket_fallback():
    assert (
        classify_rotation(
            rs_score=50,
            momentum_score=50,
            breadth_score=50,
            strength_score=60,
            score_change_5d=-2,
        )
        == "Weakening"
    )
    assert (
        classify_rotation(
            rs_score=50,
            momentum_score=50,
            breadth_score=50,
            strength_score=42,
            score_change_5d=3,
        )
        == "Improving"
    )


def test_emerging_score_rewards_positive_acceleration():
    rising = emerging_score(
        rs_change_5d=10,
        breadth_change_5d=8,
        volume_score=70,
        volume_change_5d=6,
        breakout_change_5d=4,
        trend_change_5d=3,
    )
    flat = emerging_score(
        rs_change_5d=0,
        breadth_change_5d=0,
        volume_score=50,
        volume_change_5d=0,
        breakout_change_5d=0,
        trend_change_5d=0,
    )
    assert rising is not None and flat is not None
    assert rising > flat
    assert rising > 60
    assert 45 < flat < 55
