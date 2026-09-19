"""Sector / industry strength engine (no SQL).

Six-component Sector Strength Score vs NIFTY 500, industry variant, rotation
state, emerging score, and derived alert flags. All public helpers are pure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

from indicators.momentum_score import percentile_rank

Kind = Literal["sector", "industry"]
RotationState = Literal["Leading", "Improving", "Weakening", "Lagging"]

SECTOR_WEIGHTS: dict[str, float] = {
    "rs": 0.25,
    "momentum": 0.20,
    "breadth": 0.20,
    "volume": 0.15,
    "breakout": 0.10,
    "trend": 0.10,
}

INDUSTRY_WEIGHTS: dict[str, float] = {
    "rs": 0.30,
    "momentum": 0.25,
    "breadth": 0.20,
    "volume": 0.15,
    "breakout": 0.10,
}

# Spec volume weights drop delivery and renormalize 35/25/20 → 44/31/25.
VOLUME_PRICE_UP_WEIGHT = 0.44
VOLUME_TURNOVER_WEIGHT = 0.31
VOLUME_HIGH_VOL_WEIGHT = 0.25

RS_HORIZON_WEIGHTS = (0.35, 0.30, 0.20, 0.15)  # 5D / 21D / 63D / 126D
MOMENTUM_HORIZON_WEIGHTS = (0.25, 0.25, 0.20, 0.15, 0.15)  # 5/10, 21, 63, MA, slope
BREADTH_WEIGHTS = (0.25, 0.20, 0.15, 0.15, 0.10, 0.15)
EMERGING_WEIGHTS = (0.30, 0.25, 0.20, 0.15, 0.10)

NEAR_52W_THRESHOLD = -0.10  # within 10% of 52-week high
AT_HIGH_THRESHOLD = -0.005  # within 0.5% counts as "at high"
EXTENSION_SOFT = 1.15
EXTENSION_HARD = 1.20
EXTENSION_SOFT_PENALTY = 10.0
EXTENSION_HARD_PENALTY = 20.0


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def weighted_blend(parts: Sequence[tuple[float | None, float]]) -> float | None:
    """Renormalize over present components. parts = [(score_0_100, weight), ...]."""
    present = [(float(score), w) for score, w in parts if score is not None and w > 0]
    if not present:
        return None
    total_w = sum(w for _, w in present)
    if total_w <= 0:
        return None
    return round(sum(score * (w / total_w) for score, w in present), 4)


def percentile_score(value: float | None, universe: Sequence[float]) -> float | None:
    if value is None or not universe:
        return None
    rank = percentile_rank(float(value), list(universe))
    if rank is None:
        return None
    return round(float(rank) * 100.0, 4)


def extension_penalty(close_over_ma21: float | None) -> float:
    """Subtract from trend quality when price is extended vs 21DMA."""
    ratio = _f(close_over_ma21)
    if ratio is None:
        return 0.0
    if ratio > EXTENSION_HARD:
        return EXTENSION_HARD_PENALTY
    if ratio > EXTENSION_SOFT:
        return EXTENSION_SOFT_PENALTY
    return 0.0


def map_turnover_expansion(ratio: float | None) -> float | None:
    """Map 5D/20D turnover ratio to 0–100. 0.5→20, 1.0→50, 1.5→75, 2.0→100."""
    r = _f(ratio)
    if r is None:
        return None
    return round(_clamp((r - 0.5) / 1.5 * 80.0 + 20.0), 4)


def _mean(values: Sequence[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _frac_true(flags: Sequence[bool | None]) -> float | None:
    known = [bool(v) for v in flags if v is not None]
    if not known:
        return None
    return 100.0 * sum(1 for v in known if v) / len(known)


def _cap_weighted(pairs: Sequence[tuple[float, float]]) -> float | None:
    num = 0.0
    den = 0.0
    for value, weight in pairs:
        if weight is None or weight <= 0:
            continue
        num += value * weight
        den += weight
    if den <= 0:
        return None
    return num / den


@dataclass
class StockFeature:
    stock_id: int
    sector: str | None = None
    industries: tuple[str, ...] = ()
    parent_sector: str | None = None
    market_cap: float | None = None
    return_5d: float | None = None
    return_10d: float | None = None
    return_21d: float | None = None
    return_63d: float | None = None
    return_126d: float | None = None
    close: float | None = None
    ma_21: float | None = None
    ma_50: float | None = None
    ma_200: float | None = None
    above_ma_21: bool | None = None
    above_ma_50: bool | None = None
    above_ma_200: bool | None = None
    ma21_gt_ma50: bool | None = None
    ma50_gt_ma200: bool | None = None
    ma21_slope_up: bool | None = None
    ma50_slope_up: bool | None = None
    distance_from_52w_high: float | None = None
    at_20d_high: bool | None = None
    at_50d_high: bool | None = None
    at_52w_high: bool | None = None
    volume_ratio: float | None = None
    price_up_volume_up: bool | None = None
    turnover_5d: float | None = None
    turnover_20d: float | None = None


@dataclass
class BenchmarkReturns:
    return_5d: float | None = None
    return_21d: float | None = None
    return_63d: float | None = None
    return_126d: float | None = None


@dataclass
class GroupAggregate:
    name: str
    kind: Kind
    parent_sector: str | None
    constituent_count: int
    return_5d: float | None = None
    return_10d: float | None = None
    return_21d: float | None = None
    return_63d: float | None = None
    return_126d: float | None = None
    return_21d_cw: float | None = None
    return_63d_cw: float | None = None
    pct_above_21: float | None = None
    pct_above_50: float | None = None
    pct_above_200: float | None = None
    pct_positive_5d: float | None = None
    pct_positive_21d: float | None = None
    pct_breakout_20d: float | None = None
    pct_breakout_50d: float | None = None
    pct_breakout_52w: float | None = None
    pct_price_up_volume_up: float | None = None
    pct_volume_gt_1_5x: float | None = None
    turnover_expansion: float | None = None
    pct_ma21_gt_ma50: float | None = None
    pct_ma50_gt_ma200: float | None = None
    pct_ma21_slope_up: float | None = None
    pct_ma50_slope_up: float | None = None
    pct_near_52w: float | None = None
    close_over_ma21: float | None = None
    avg_volume_ratio: float | None = None


@dataclass
class PriorScores:
    strength_score: float | None = None
    rs_score: float | None = None
    momentum_score: float | None = None
    breadth_score: float | None = None
    volume_score: float | None = None
    breakout_score: float | None = None
    trend_score: float | None = None


@dataclass
class ScoredGroup:
    name: str
    kind: Kind
    parent_sector: str | None
    constituent_count: int
    rs_score: float | None = None
    momentum_score: float | None = None
    breadth_score: float | None = None
    volume_score: float | None = None
    breakout_score: float | None = None
    trend_score: float | None = None
    strength_score: float | None = None
    emerging_score: float | None = None
    rotation_state: RotationState | None = None
    alerts: list[str] = field(default_factory=list)
    is_gaining_strength: bool = False
    score_change_1d: float | None = None
    score_change_5d: float | None = None
    score_change_21d: float | None = None
    rs_change_5d: float | None = None
    momentum_change_5d: float | None = None
    breadth_change_5d: float | None = None
    pct_above_21: float | None = None
    pct_above_50: float | None = None
    pct_above_200: float | None = None
    pct_positive_5d: float | None = None
    pct_positive_21d: float | None = None
    pct_breakout_20d: float | None = None
    pct_breakout_50d: float | None = None
    pct_breakout_52w: float | None = None
    pct_price_up_volume_up: float | None = None
    pct_volume_gt_1_5x: float | None = None
    volume_expansion: float | None = None
    return_1m: float | None = None
    return_3m: float | None = None
    return_3m_cw: float | None = None
    return_3m_ew: float | None = None


def aggregate_features(
    name: str,
    features: Sequence[StockFeature],
    *,
    kind: Kind = "sector",
    parent_sector: str | None = None,
) -> GroupAggregate:
    if not features:
        return GroupAggregate(name=name, kind=kind, parent_sector=parent_sector, constituent_count=0)

    def col(attr: str) -> list[float | None]:
        return [_f(getattr(row, attr)) for row in features]

    def flags(attr: str) -> list[bool | None]:
        return [getattr(row, attr) for row in features]

    rets_21 = col("return_21d")
    rets_63 = col("return_63d")
    cw_21: list[tuple[float, float]] = []
    cw_63: list[tuple[float, float]] = []
    for row in features:
        mcap = _f(row.market_cap)
        r21 = _f(row.return_21d)
        r63 = _f(row.return_63d)
        if mcap and r21 is not None:
            cw_21.append((r21, mcap))
        if mcap and r63 is not None:
            cw_63.append((r63, mcap))

    turn_5 = _mean(col("turnover_5d"))
    turn_20 = _mean(col("turnover_20d"))
    expansion = None
    if turn_5 is not None and turn_20 and turn_20 > 0:
        expansion = turn_5 / turn_20

    close_over: list[float] = []
    for row in features:
        close = _f(row.close)
        ma21 = _f(row.ma_21)
        if close is not None and ma21 and ma21 > 0:
            close_over.append(close / ma21)

    near_52w = []
    at_52w = []
    for row in features:
        dist = _f(row.distance_from_52w_high)
        if dist is None:
            near_52w.append(None)
            at_52w.append(row.at_52w_high)
            continue
        near_52w.append(dist >= NEAR_52W_THRESHOLD)
        if row.at_52w_high is None:
            at_52w.append(dist >= AT_HIGH_THRESHOLD)
        else:
            at_52w.append(row.at_52w_high)

    vol_flags = []
    for row in features:
        vr = _f(row.volume_ratio)
        if vr is None:
            vol_flags.append(None)
        else:
            vol_flags.append(vr >= 1.5)

    pos_5 = []
    pos_21 = []
    for row in features:
        r5 = _f(row.return_5d)
        r21 = _f(row.return_21d)
        pos_5.append(None if r5 is None else r5 > 0)
        pos_21.append(None if r21 is None else r21 > 0)

    return GroupAggregate(
        name=name,
        kind=kind,
        parent_sector=parent_sector,
        constituent_count=len(features),
        return_5d=_mean(col("return_5d")),
        return_10d=_mean(col("return_10d")),
        return_21d=_mean(rets_21),
        return_63d=_mean(rets_63),
        return_126d=_mean(col("return_126d")),
        return_21d_cw=_cap_weighted(cw_21),
        return_63d_cw=_cap_weighted(cw_63),
        pct_above_21=_frac_true(flags("above_ma_21")),
        pct_above_50=_frac_true(flags("above_ma_50")),
        pct_above_200=_frac_true(flags("above_ma_200")),
        pct_positive_5d=_frac_true(pos_5),
        pct_positive_21d=_frac_true(pos_21),
        pct_breakout_20d=_frac_true(flags("at_20d_high")),
        pct_breakout_50d=_frac_true(flags("at_50d_high")),
        pct_breakout_52w=_frac_true(at_52w),
        pct_price_up_volume_up=_frac_true(flags("price_up_volume_up")),
        pct_volume_gt_1_5x=_frac_true(vol_flags),
        turnover_expansion=expansion,
        pct_ma21_gt_ma50=_frac_true(flags("ma21_gt_ma50")),
        pct_ma50_gt_ma200=_frac_true(flags("ma50_gt_ma200")),
        pct_ma21_slope_up=_frac_true(flags("ma21_slope_up")),
        pct_ma50_slope_up=_frac_true(flags("ma50_slope_up")),
        pct_near_52w=_frac_true(near_52w),
        close_over_ma21=_mean(close_over),
        avg_volume_ratio=_mean(col("volume_ratio")),
    )


def _rs_raw(group_ret: float | None, bench_ret: float | None) -> float | None:
    if group_ret is None:
        return None
    if bench_ret is None:
        return group_ret
    return group_ret - bench_ret


def relative_strength_raw(agg: GroupAggregate, bench: BenchmarkReturns | None) -> float | None:
    bench = bench or BenchmarkReturns()
    return weighted_blend(
        [
            (_rs_raw(agg.return_5d, bench.return_5d), RS_HORIZON_WEIGHTS[0]),
            (_rs_raw(agg.return_21d, bench.return_21d), RS_HORIZON_WEIGHTS[1]),
            (_rs_raw(agg.return_63d, bench.return_63d), RS_HORIZON_WEIGHTS[2]),
            (_rs_raw(agg.return_126d, bench.return_126d), RS_HORIZON_WEIGHTS[3]),
        ]
    )


def momentum_structure_score(agg: GroupAggregate) -> float | None:
    """MA stack as 0–100 from equal-weighted boolean breadths."""
    return weighted_blend(
        [
            (agg.pct_above_21, 1.0),
            (agg.pct_above_50, 1.0),
            (agg.pct_above_200, 1.0),
            (agg.pct_ma21_gt_ma50, 1.0),
            (agg.pct_ma50_gt_ma200, 1.0),
            (agg.pct_ma21_slope_up, 1.0),
            (agg.pct_ma50_slope_up, 1.0),
        ]
    )


def momentum_slope_score(agg: GroupAggregate) -> float | None:
    return weighted_blend(
        [
            (agg.pct_ma21_slope_up, 0.6),
            (agg.pct_ma50_slope_up, 0.4),
        ]
    )


def breadth_component(agg: GroupAggregate) -> float | None:
    breakout_breadth = weighted_blend(
        [
            (agg.pct_breakout_20d, 1.0),
            (agg.pct_breakout_50d, 1.0),
            (agg.pct_breakout_52w, 1.0),
        ]
    )
    return weighted_blend(
        [
            (agg.pct_above_21, BREADTH_WEIGHTS[0]),
            (agg.pct_above_50, BREADTH_WEIGHTS[1]),
            (agg.pct_above_200, BREADTH_WEIGHTS[2]),
            (agg.pct_positive_5d, BREADTH_WEIGHTS[3]),
            (agg.pct_positive_21d, BREADTH_WEIGHTS[4]),
            (breakout_breadth, BREADTH_WEIGHTS[5]),
        ]
    )


def volume_component(agg: GroupAggregate) -> float | None:
    return weighted_blend(
        [
            (agg.pct_price_up_volume_up, VOLUME_PRICE_UP_WEIGHT),
            (map_turnover_expansion(agg.turnover_expansion), VOLUME_TURNOVER_WEIGHT),
            (agg.pct_volume_gt_1_5x, VOLUME_HIGH_VOL_WEIGHT),
        ]
    )


def breakout_component(agg: GroupAggregate) -> float | None:
    return weighted_blend(
        [
            (agg.pct_breakout_20d, 1.0),
            (agg.pct_breakout_50d, 1.0),
            (agg.pct_breakout_52w, 1.0),
        ]
    )


def trend_component(agg: GroupAggregate) -> float | None:
    raw = weighted_blend(
        [
            (agg.pct_above_21, 1.0),
            (agg.pct_ma21_gt_ma50, 1.0),
            (agg.pct_ma50_gt_ma200, 1.0),
            (agg.pct_ma21_slope_up, 1.0),
            (agg.pct_ma50_slope_up, 1.0),
            (agg.pct_near_52w, 1.0),
        ]
    )
    if raw is None:
        return None
    return round(_clamp(raw - extension_penalty(agg.close_over_ma21)), 4)


def strength_score(
    *,
    kind: Kind,
    rs_score: float | None,
    momentum_score: float | None,
    breadth_score: float | None,
    volume_score: float | None,
    breakout_score: float | None,
    trend_score: float | None,
) -> float | None:
    weights = SECTOR_WEIGHTS if kind == "sector" else INDUSTRY_WEIGHTS
    parts = [
        (rs_score, weights["rs"]),
        (momentum_score, weights["momentum"]),
        (breadth_score, weights["breadth"]),
        (volume_score, weights["volume"]),
        (breakout_score, weights["breakout"]),
    ]
    if kind == "sector":
        parts.append((trend_score, weights["trend"]))
    return weighted_blend(parts)


def _delta(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None:
        return None
    return round(float(current) - float(prior), 4)


def _rising(delta: float | None, *, epsilon: float = 0.0) -> bool:
    return delta is not None and delta > epsilon


def _falling(delta: float | None, *, epsilon: float = 0.0) -> bool:
    return delta is not None and delta < -epsilon


def _change_to_score(delta: float | None, *, scale: float = 20.0) -> float | None:
    """Map a score delta to 0–100. 0 → 50, +scale → 100, −scale → 0."""
    if delta is None:
        return None
    return round(_clamp(50.0 + (float(delta) / scale) * 50.0), 4)


def emerging_score(
    *,
    rs_change_5d: float | None,
    breadth_change_5d: float | None,
    volume_score: float | None,
    volume_change_5d: float | None,
    breakout_change_5d: float | None,
    trend_change_5d: float | None,
) -> float | None:
    volume_leg = _change_to_score(volume_change_5d)
    if volume_leg is None:
        volume_leg = volume_score
    return weighted_blend(
        [
            (_change_to_score(rs_change_5d), EMERGING_WEIGHTS[0]),
            (_change_to_score(breadth_change_5d), EMERGING_WEIGHTS[1]),
            (volume_leg, EMERGING_WEIGHTS[2]),
            (_change_to_score(breakout_change_5d), EMERGING_WEIGHTS[3]),
            (_change_to_score(trend_change_5d), EMERGING_WEIGHTS[4]),
        ]
    )


def classify_rotation(
    *,
    rs_score: float | None,
    momentum_score: float | None,
    breadth_score: float | None,
    strength_score: float | None,
    score_change_5d: float | None = None,
    rs_change_5d: float | None = None,
    momentum_change_5d: float | None = None,
    breadth_change_5d: float | None = None,
) -> RotationState:
    rs = rs_score if rs_score is not None else -1.0
    mom = momentum_score if momentum_score is not None else -1.0
    br = breadth_score if breadth_score is not None else -1.0
    score = strength_score if strength_score is not None else -1.0
    mom_down = _falling(momentum_change_5d)
    br_down = _falling(breadth_change_5d)
    score_up = _rising(score_change_5d)
    rs_up = _rising(rs_change_5d)
    br_up = _rising(breadth_change_5d)

    leading = rs > 60 and mom > 60 and br > 60 and score > 65
    if leading and (mom_down or br_down):
        return "Weakening"
    if leading:
        return "Leading"
    if rs > 60 and (mom_down or br_down):
        return "Weakening"
    if score_up and rs_up and br_up and mom > 55:
        return "Improving"
    if rs < 40 and mom < 40 and (br < 40 or br < 0):
        return "Lagging"

    # Nearest bucket by score + 5D change
    ch = score_change_5d if score_change_5d is not None else 0.0
    if score >= 55:
        return "Leading" if ch >= 0 else "Weakening"
    if score >= 40:
        return "Improving" if ch > 0 else "Weakening"
    return "Improving" if ch > 0 else "Lagging"


def derive_alerts(
    *,
    strength_score: float | None,
    rs_score: float | None,
    momentum_score: float | None,
    breadth_score: float | None,
    score_change_5d: float | None,
    rs_change_5d: float | None,
    momentum_change_5d: float | None,
    breadth_change_5d: float | None,
    pct_above_21: float | None,
    pct_above_50: float | None,
    volume_expansion: float | None,
    rotation_state: str | None,
) -> list[str]:
    alerts: list[str] = []
    score = strength_score or 0.0
    rs = rs_score or 0.0
    mom = momentum_score or 0.0
    br = breadth_score or 0.0
    ch5 = score_change_5d or 0.0
    rs_up = _rising(rs_change_5d)
    vol_ratio = volume_expansion or 0.0
    above21 = pct_above_21 or 0.0
    above50 = pct_above_50 or 0.0

    if score > 55 and ch5 > 8 and rs_up and br > 55 and vol_ratio > 1.20:
        alerts.append("EARLY_ROTATION")
    if (
        score > 65
        and ch5 > 10
        and above21 > 65
        and above50 > 55
        and rs_up
        and (volume_expansion is None or vol_ratio >= 1.0)
    ):
        alerts.append("EMERGING_LEADER")
    if score > 80 and rs > 70 and br > 70 and mom > 65:
        alerts.append("LEADING_SECTOR")
    if score > 65 and ch5 < -5 and _falling(breadth_change_5d) and _falling(momentum_change_5d):
        alerts.append("LEADER_WEAKENING")
    if rotation_state == "Leading" and "LEADING_SECTOR" not in alerts and score > 80:
        alerts.append("LEADING_SECTOR")
    return alerts


def score_groups(
    aggregates: Sequence[GroupAggregate],
    *,
    kind: Kind,
    benchmark: BenchmarkReturns | None = None,
    prior_1d: dict[str, PriorScores] | None = None,
    prior_5d: dict[str, PriorScores] | None = None,
    prior_21d: dict[str, PriorScores] | None = None,
) -> list[ScoredGroup]:
    """Cross-section percentile RS/momentum, then blend, accelerate, classify."""
    prior_1d = prior_1d or {}
    prior_5d = prior_5d or {}
    prior_21d = prior_21d or {}

    rs_raws = [relative_strength_raw(agg, benchmark) for agg in aggregates]
    rs_universe = [v for v in rs_raws if v is not None]
    r5 = [agg.return_5d for agg in aggregates if agg.return_5d is not None]
    r10 = [agg.return_10d for agg in aggregates if agg.return_10d is not None]
    r21 = [agg.return_21d for agg in aggregates if agg.return_21d is not None]
    r63 = [agg.return_63d for agg in aggregates if agg.return_63d is not None]

    scored: list[ScoredGroup] = []
    for agg, raw_rs in zip(aggregates, rs_raws):
        rs = percentile_score(raw_rs, rs_universe)
        mom_5 = percentile_score(agg.return_5d, r5)
        mom_10 = percentile_score(agg.return_10d, r10)
        short_horizon = weighted_blend([(mom_5, 0.5), (mom_10, 0.5)])
        mom = weighted_blend(
            [
                (short_horizon, MOMENTUM_HORIZON_WEIGHTS[0]),
                (percentile_score(agg.return_21d, r21), MOMENTUM_HORIZON_WEIGHTS[1]),
                (percentile_score(agg.return_63d, r63), MOMENTUM_HORIZON_WEIGHTS[2]),
                (momentum_structure_score(agg), MOMENTUM_HORIZON_WEIGHTS[3]),
                (momentum_slope_score(agg), MOMENTUM_HORIZON_WEIGHTS[4]),
            ]
        )
        br = breadth_component(agg)
        vol = volume_component(agg)
        brk = breakout_component(agg)
        trend = trend_component(agg) if kind == "sector" else None
        strength = strength_score(
            kind=kind,
            rs_score=rs,
            momentum_score=mom,
            breadth_score=br,
            volume_score=vol,
            breakout_score=brk,
            trend_score=trend,
        )
        p1 = prior_1d.get(agg.name) or PriorScores()
        p5 = prior_5d.get(agg.name) or PriorScores()
        p21 = prior_21d.get(agg.name) or PriorScores()
        ch1 = _delta(strength, p1.strength_score)
        ch5 = _delta(strength, p5.strength_score)
        ch21 = _delta(strength, p21.strength_score)
        rs_ch5 = _delta(rs, p5.rs_score)
        mom_ch5 = _delta(mom, p5.momentum_score)
        br_ch5 = _delta(br, p5.breadth_score)
        vol_ch5 = _delta(vol, p5.volume_score)
        brk_ch5 = _delta(brk, p5.breakout_score)
        trend_ch5 = _delta(trend, p5.trend_score)
        emerge = emerging_score(
            rs_change_5d=rs_ch5,
            breadth_change_5d=br_ch5,
            volume_score=vol,
            volume_change_5d=vol_ch5,
            breakout_change_5d=brk_ch5,
            trend_change_5d=trend_ch5,
        )
        state = classify_rotation(
            rs_score=rs,
            momentum_score=mom,
            breadth_score=br,
            strength_score=strength,
            score_change_5d=ch5,
            rs_change_5d=rs_ch5,
            momentum_change_5d=mom_ch5,
            breadth_change_5d=br_ch5,
        )
        alerts = derive_alerts(
            strength_score=strength,
            rs_score=rs,
            momentum_score=mom,
            breadth_score=br,
            score_change_5d=ch5,
            rs_change_5d=rs_ch5,
            momentum_change_5d=mom_ch5,
            breadth_change_5d=br_ch5,
            pct_above_21=agg.pct_above_21,
            pct_above_50=agg.pct_above_50,
            volume_expansion=agg.turnover_expansion,
            rotation_state=state,
        )
        ret_1m = None if agg.return_21d is None else round(agg.return_21d * 100.0, 4)
        ret_3m_ew = None if agg.return_63d is None else round(agg.return_63d * 100.0, 4)
        ret_3m_cw = None if agg.return_63d_cw is None else round(agg.return_63d_cw * 100.0, 4)
        scored.append(
            ScoredGroup(
                name=agg.name,
                kind=kind,
                parent_sector=agg.parent_sector,
                constituent_count=agg.constituent_count,
                rs_score=rs,
                momentum_score=mom,
                breadth_score=br,
                volume_score=vol,
                breakout_score=brk,
                trend_score=trend,
                strength_score=strength,
                emerging_score=emerge,
                rotation_state=state,
                alerts=alerts,
                is_gaining_strength=state in {"Leading", "Improving"} or (ch5 is not None and ch5 > 0),
                score_change_1d=ch1,
                score_change_5d=ch5,
                score_change_21d=ch21,
                rs_change_5d=rs_ch5,
                momentum_change_5d=mom_ch5,
                breadth_change_5d=br_ch5,
                pct_above_21=agg.pct_above_21,
                pct_above_50=agg.pct_above_50,
                pct_above_200=agg.pct_above_200,
                pct_positive_5d=agg.pct_positive_5d,
                pct_positive_21d=agg.pct_positive_21d,
                pct_breakout_20d=agg.pct_breakout_20d,
                pct_breakout_50d=agg.pct_breakout_50d,
                pct_breakout_52w=agg.pct_breakout_52w,
                pct_price_up_volume_up=agg.pct_price_up_volume_up,
                pct_volume_gt_1_5x=agg.pct_volume_gt_1_5x,
                volume_expansion=agg.turnover_expansion,
                return_1m=ret_1m,
                return_3m=ret_3m_cw if ret_3m_cw is not None else ret_3m_ew,
                return_3m_cw=ret_3m_cw,
                return_3m_ew=ret_3m_ew,
            )
        )
    scored.sort(
        key=lambda row: (
            float(row.strength_score) if row.strength_score is not None else -1.0,
            row.constituent_count,
        ),
        reverse=True,
    )
    return scored
