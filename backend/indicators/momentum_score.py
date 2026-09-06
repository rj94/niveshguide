"""V1 Momentum Score: Returns 30% + DMA 25% + Volume 20% + Results 25%."""

from __future__ import annotations

from typing import Any, Sequence


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _renormalize(weighted: list[tuple[float, float]]) -> float | None:
    """weighted = [(raw_score_0_100, weight), ...]; skip None scores by omitting them."""
    parts = [(score, w) for score, w in weighted if score is not None and w > 0]
    if not parts:
        return None
    total_w = sum(w for _, w in parts)
    if total_w <= 0:
        return None
    return round(sum(score * (w / total_w) for score, w in parts), 4)


def percentile_rank(value: float, universe: Sequence[float]) -> float | None:
    """Rank in [0, 1]: fraction of universe values strictly below `value` (+ half ties)."""
    if not universe:
        return None
    n = len(universe)
    below = sum(1 for x in universe if x < value)
    equal = sum(1 for x in universe if x == value)
    return (below + 0.5 * equal) / n


def percentile_to_bucket_score(pct: float | None) -> float | None:
    """Map percentile rank (0–1) to doc bucket scores."""
    if pct is None:
        return None
    p = pct * 100.0
    if p >= 90:
        return 100.0
    if p >= 80:
        return 90.0
    if p >= 60:
        return 70.0
    if p >= 40:
        return 50.0
    if p >= 20:
        return 30.0
    return 10.0


def growth_bucket_score(growth: float | None) -> float | None:
    """Revenue/PAT growth as fraction (0.30 = 30%)."""
    if growth is None:
        return None
    pct = growth * 100.0
    if pct > 30:
        return 100.0
    if pct >= 20:
        return 80.0
    if pct >= 10:
        return 60.0
    if pct >= 0:
        return 40.0
    return 10.0


def volume_ratio_score(ratio: float | None) -> float | None:
    if ratio is None:
        return None
    if ratio > 3:
        return 100.0
    if ratio >= 2:
        return 85.0
    if ratio >= 1.5:
        return 70.0
    if ratio >= 1:
        return 50.0
    return 20.0


def dma_distance_pct(price: float | None, dma: float | None) -> float | None:
    if price is None or dma is None or dma == 0:
        return None
    return ((price / dma) - 1.0) * 100.0


def compute_dma_score(
    *,
    price: float | None,
    ma_20: float | None,
    ma_50: float | None,
    ma_200: float | None,
    distance_from_52w_high: float | None,
) -> float:
    """Raw DMA / trend score out of 100 (sum of condition points)."""
    points = 0.0
    if price is not None and ma_20 is not None and price > ma_20:
        points += 15
    if price is not None and ma_50 is not None and price > ma_50:
        points += 20
    if price is not None and ma_200 is not None and price > ma_200:
        points += 25
    if ma_20 is not None and ma_50 is not None and ma_20 > ma_50:
        points += 15
    if ma_50 is not None and ma_200 is not None and ma_50 > ma_200:
        points += 15
    # distance_from_52w_high stored as fraction below high (e.g. -0.05 = 5% below)
    if distance_from_52w_high is not None and distance_from_52w_high >= -0.10:
        points += 10
    return _clip(points)


def compute_return_score(
    *,
    return_1m: float | None,
    return_3m: float | None,
    return_6m: float | None,
    return_12m: float | None,
    universe_1m: Sequence[float],
    universe_3m: Sequence[float],
    universe_6m: Sequence[float],
    universe_12m: Sequence[float],
) -> float | None:
    scores: list[tuple[float | None, float]] = [
        (percentile_to_bucket_score(percentile_rank(return_1m, universe_1m) if return_1m is not None else None), 0.20),
        (percentile_to_bucket_score(percentile_rank(return_3m, universe_3m) if return_3m is not None else None), 0.30),
        (percentile_to_bucket_score(percentile_rank(return_6m, universe_6m) if return_6m is not None else None), 0.30),
        (percentile_to_bucket_score(percentile_rank(return_12m, universe_12m) if return_12m is not None else None), 0.20),
    ]
    return _renormalize([(s, w) for s, w in scores if s is not None])


def compute_volume_score(
    *,
    volume_ratio: float | None,
    positive_volume_days_20: float | None,
    return_5d: float | None = None,
) -> float | None:
    """
    Volume Score = 60% × volume ratio score + 40% × positive volume trend (0–100).
    positive_volume_days_20 is fraction of last 20 sessions that were up-days with vol ratio > 1.
    Light confirmation: if 5d return < 0 and ratio > 1.5, shave 10 points (distribution).
    """
    ratio_s = volume_ratio_score(volume_ratio)
    trend_s = None
    if positive_volume_days_20 is not None:
        trend_s = _clip(positive_volume_days_20 * 100.0)
    base = _renormalize(
        [
            (ratio_s, 0.60),
            (trend_s, 0.40),
        ]
    )
    if base is None:
        return None
    if return_5d is not None and volume_ratio is not None and return_5d < 0 and volume_ratio > 1.5:
        base = _clip(base - 10.0)
    elif return_5d is not None and volume_ratio is not None and return_5d > 0 and volume_ratio > 1.5:
        base = _clip(base + 5.0)
    return round(base, 4)


def compute_result_score(
    *,
    revenue_growth_yoy: float | None,
    pat_growth_yoy: float | None,
    revenue_growth_qoq: float | None,
    pat_growth_qoq: float | None,
    margin_change: float | None,
    earnings_acceleration: float | None,
) -> float | None:
    """
    Result Score =
      25% Rev YoY + 30% PAT YoY + 20% Margin Trend + 15% QoQ + 10% Earnings Acceleration
    """
    rev_yoy = growth_bucket_score(revenue_growth_yoy)
    pat_yoy = growth_bucket_score(pat_growth_yoy)
    # QoQ: average of rev/pat qoq bucket scores when available
    qoq_parts = [growth_bucket_score(revenue_growth_qoq), growth_bucket_score(pat_growth_qoq)]
    qoq_vals = [v for v in qoq_parts if v is not None]
    qoq = sum(qoq_vals) / len(qoq_vals) if qoq_vals else None

    # Margin change in percentage points (e.g. +2.0 = +2pp) → map to 0–100
    margin_s = None
    if margin_change is not None:
        if margin_change > 2:
            margin_s = 100.0
        elif margin_change > 0:
            margin_s = 70.0
        elif margin_change > -2:
            margin_s = 40.0
        else:
            margin_s = 10.0

    accel_s = None
    if earnings_acceleration is not None:
        accel_s = 100.0 if earnings_acceleration > 0 else (50.0 if earnings_acceleration == 0 else 10.0)

    return _renormalize(
        [
            (rev_yoy, 0.25),
            (pat_yoy, 0.30),
            (margin_s, 0.20),
            (qoq, 0.15),
            (accel_s, 0.10),
        ]
    )


def blend_momentum_score(
    return_score: float | None,
    dma_score: float | None,
    volume_score: float | None,
    result_score: float | None,
    sector_strength: float | None = None,
) -> float | None:
    """Returns 25% · DMA 20% · Volume 15% · Results 20% · Sector strength 20%."""
    return _renormalize(
        [
            (return_score, 0.25),
            (dma_score, 0.20),
            (volume_score, 0.15),
            (result_score, 0.20),
            (sector_strength, 0.20),
        ]
    )


def momentum_category(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 85:
        return "Strong Momentum"
    if score >= 70:
        return "Positive Momentum"
    if score >= 55:
        return "Emerging Momentum"
    if score >= 40:
        return "Neutral"
    if score >= 20:
        return "Weak"
    return "Negative"


def growth_ratio(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return (current / previous) - 1.0


def operating_margin(revenue: float | None, op_profit: float | None) -> float | None:
    if revenue is None or op_profit is None or revenue == 0:
        return None
    return (op_profit / revenue) * 100.0


def extract_quarter_series(by_period: dict[str, dict[str, float | None]], period_order: list[str]) -> dict[str, Any]:
    """
    From quarterly metric maps (oldest→newest period_order), derive YoY/QoQ growth fields.
    Expects keys like sales/revenue, net profit/pat, operating profit.
    """
    def rev(m: dict[str, float | None]) -> float | None:
        for k in ("sales", "revenue"):
            if m.get(k) is not None:
                return m[k]
        return None

    def pat(m: dict[str, float | None]) -> float | None:
        for k in ("net profit", "pat", "profit after tax"):
            if m.get(k) is not None:
                return m[k]
        return None

    def op(m: dict[str, float | None]) -> float | None:
        for k in ("operating profit", "ebitda", "opm"):
            if k == "opm":
                continue
            if m.get(k) is not None:
                return m[k]
        return None

    if len(period_order) < 2:
        return {
            "revenue_growth_yoy": None,
            "pat_growth_yoy": None,
            "revenue_growth_qoq": None,
            "pat_growth_qoq": None,
            "margin_change": None,
            "earnings_acceleration": None,
        }

    latest = by_period.get(period_order[-1]) or {}
    prev_q = by_period.get(period_order[-2]) or {}
    yoy = by_period.get(period_order[-5]) or {} if len(period_order) >= 5 else {}
    prev_yoy_pat_growth = None
    if len(period_order) >= 6:
        # Previous quarter's YoY: period[-2] vs period[-6]
        prev_q_yoy_base = by_period.get(period_order[-6]) or {}
        prev_yoy_pat_growth = growth_ratio(pat(prev_q), pat(prev_q_yoy_base))

    rev_yoy = growth_ratio(rev(latest), rev(yoy)) if yoy else None
    pat_yoy = growth_ratio(pat(latest), pat(yoy)) if yoy else None
    rev_qoq = growth_ratio(rev(latest), rev(prev_q))
    pat_qoq = growth_ratio(pat(latest), pat(prev_q))

    m_now = operating_margin(rev(latest), op(latest))
    m_prev = operating_margin(rev(prev_q), op(prev_q))
    margin_change = None
    if m_now is not None and m_prev is not None:
        margin_change = m_now - m_prev

    earnings_acceleration = None
    if pat_yoy is not None and prev_yoy_pat_growth is not None:
        earnings_acceleration = pat_yoy - prev_yoy_pat_growth
    elif pat_yoy is not None and pat_qoq is not None:
        # Fallback: positive if QoQ PAT growth positive while YoY positive
        earnings_acceleration = pat_qoq if pat_yoy is not None else None

    return {
        "revenue_growth_yoy": rev_yoy,
        "pat_growth_yoy": pat_yoy,
        "revenue_growth_qoq": rev_qoq,
        "pat_growth_qoq": pat_qoq,
        "margin_change": margin_change,
        "earnings_acceleration": earnings_acceleration,
    }


def volume_metrics(
    closes: Sequence[float],
    volumes: Sequence[float | None],
    *,
    lookback: int = 20,
) -> dict[str, float | None]:
    """Compute volume_avg_5 (1w), volume_avg_20, volume_ratio, positive_volume_days_20, return_5d."""
    n = min(len(closes), len(volumes))
    if n < 2:
        return {
            "volume_avg_5": None,
            "volume_avg_20": None,
            "volume_ratio": None,
            "positive_volume_days_20": None,
            "return_5d": None,
        }
    closes = list(closes[-n:])
    volumes = list(volumes[-n:])
    today_vol = volumes[-1]
    window = [v for v in volumes[-lookback:] if v is not None and v > 0]
    # Prefer prior days for average when today is included
    prior = [v for v in volumes[-(lookback + 1) : -1] if v is not None and v > 0]
    avg = (sum(prior) / len(prior)) if prior else ((sum(window) / len(window)) if window else None)
    week = [v for v in volumes[-5:] if v is not None and v > 0]
    avg_1w = (sum(week) / len(week)) if week else None
    ratio = None
    if today_vol is not None and avg and avg > 0:
        ratio = float(today_vol) / avg

    # Positive volume trend: up-days in last 20 with volume > prior 20d avg
    pos = 0
    counted = 0
    start = max(1, n - lookback)
    for i in range(start, n):
        if closes[i] is None or closes[i - 1] is None:
            continue
        counted += 1
        vol_i = volumes[i]
        hist = [v for v in volumes[max(0, i - lookback) : i] if v is not None and v > 0]
        avg_i = (sum(hist) / len(hist)) if hist else None
        if closes[i] > closes[i - 1] and vol_i is not None and avg_i and vol_i > avg_i:
            pos += 1
    pos_frac = (pos / counted) if counted else None

    ret_5d = None
    if n >= 6 and closes[-6]:
        ret_5d = (closes[-1] / closes[-6]) - 1.0

    return {
        "volume_avg_5": avg_1w,
        "volume_avg_20": avg,
        "volume_ratio": ratio,
        "positive_volume_days_20": pos_frac,
        "return_5d": ret_5d,
    }


def finalize_momentum_fields(
    raw: dict[str, Any],
    universes: dict[str, list[float]],
    *,
    sector_strength: float | None = None,
) -> dict[str, Any]:
    """Attach component scores + final momentum from raw metrics + universe return lists."""
    return_score = compute_return_score(
        return_1m=raw.get("return_1m"),
        return_3m=raw.get("return_3m"),
        return_6m=raw.get("return_6m"),
        return_12m=raw.get("return_12m"),
        universe_1m=universes.get("return_1m") or [],
        universe_3m=universes.get("return_3m") or [],
        universe_6m=universes.get("return_6m") or [],
        universe_12m=universes.get("return_12m") or [],
    )
    dma_score = compute_dma_score(
        price=raw.get("ltp"),
        ma_20=raw.get("ma_20"),
        ma_50=raw.get("ma_50"),
        ma_200=raw.get("ma_200"),
        distance_from_52w_high=raw.get("distance_from_52w_high"),
    )
    volume_score = compute_volume_score(
        volume_ratio=raw.get("volume_ratio"),
        positive_volume_days_20=raw.get("positive_volume_days_20"),
        return_5d=raw.get("return_5d"),
    )
    result_score = compute_result_score(
        revenue_growth_yoy=raw.get("revenue_growth_yoy"),
        pat_growth_yoy=raw.get("pat_growth_yoy"),
        revenue_growth_qoq=raw.get("revenue_growth_qoq"),
        pat_growth_qoq=raw.get("pat_growth_qoq"),
        margin_change=raw.get("margin_change"),
        earnings_acceleration=raw.get("earnings_acceleration"),
    )
    momentum = blend_momentum_score(
        return_score, dma_score, volume_score, result_score, sector_strength
    )
    out = {
        "return_score": return_score,
        "dma_score": dma_score,
        "volume_score": volume_score,
        "result_score": result_score,
        "momentum_score": momentum,
        "momentum_category": momentum_category(momentum),
    }
    return out
