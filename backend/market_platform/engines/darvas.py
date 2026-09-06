from __future__ import annotations

from market_platform.engines.base import (
    StrategyCriterion,
    StrategyResult,
    pct_state,
    rating_from_score,
    score_from_criteria,
)
from market_platform.engines.inputs import BarPoint, StrategyInput
from market_platform.schemas.strategies import StrategyFilterDef, StrategyMeta


META = StrategyMeta(
    slug="darvas",
    name="Darvas Box",
    short_name="DARVAS",
    description="Nicolas Darvas trend-following boxes — buy breakouts from consolidating ranges on expanding volume.",
    filters=[
        StrategyFilterDef(key="HIGH", label="HIGH", detail="Near multi-month / 52W high"),
        StrategyFilterDef(key="BOX", label="BOX", detail="Valid Darvas box formed"),
        StrategyFilterDef(key="BRK", label="BRK", detail="Breakout above box top"),
        StrategyFilterDef(key="VOL", label="VOL", detail="Volume > 20D average"),
        StrategyFilterDef(key="EPS", label="EPS", detail="Earnings growth filter"),
        StrategyFilterDef(key="IND", label="IND", detail="Industry momentum"),
    ],
)


def detect_latest_box(bars: list[BarPoint]) -> tuple[float | None, float | None, int | None]:
    """Return (box_top, box_bottom, top_index) for the most recent Darvas-like box."""
    if len(bars) < 20:
        return None, None, None

    # Scan from newer peaks backward for a 3-day confirmed high
    for i in range(len(bars) - 4, 8, -1):
        h = bars[i].high
        if not (
            h > bars[i - 1].high
            and h > bars[i - 2].high
            and h > bars[i - 3].high
            and h > bars[i + 1].high
            and h > bars[i + 2].high
            and h > bars[i + 3].high
        ):
            continue
        # Floor: lowest low in next 3–8 sessions after the peak
        end = min(len(bars), i + 9)
        window = bars[i:end]
        if len(window) < 3:
            continue
        box_bottom = min(b.low for b in window)
        if box_bottom >= h or box_bottom <= 0:
            continue
        # Reasonable box height (2%–25%)
        height_pct = (h - box_bottom) / h * 100
        if height_pct < 1.5 or height_pct > 30:
            continue
        return round(h, 4), round(box_bottom, 4), i
    return None, None, None


def score_darvas(row: StrategyInput) -> StrategyResult:
    near_high = row.dist_from_52w_high_pct
    vol = row.volume_ratio
    growth = row.pat_growth_yoy if row.pat_growth_yoy is not None else row.eps_cagr_3y
    industry = row.industry_strength if row.industry_strength is not None else row.sector_strength

    box_top, box_bottom, _idx = detect_latest_box(row.bars)
    price = row.ltp
    breakout = False
    inside = False
    if box_top is not None and price is not None:
        # Darvas: buy slightly above box top
        breakout = price >= box_top * 1.001
        inside = box_bottom is not None and box_bottom <= price < box_top

    if near_high is None:
        high_state = "unknown"
        high_detail = "52W high unavailable"
    elif near_high >= -8:
        high_state = "pass"
        high_detail = f"{near_high:+.1f}% from 52W high"
    elif near_high >= -18:
        high_state = "partial"
        high_detail = f"{near_high:+.1f}% from 52W high"
    else:
        high_state = "fail"
        high_detail = f"{near_high:+.1f}% from 52W high"

    if box_top is None:
        box_state = "fail" if row.bars else "unknown"
        box_detail = "No Darvas box detected" if row.bars else "Price history unavailable"
    else:
        box_state = "pass"
        box_detail = f"Box {box_bottom:.2f} – {box_top:.2f}" if box_bottom else f"Top {box_top:.2f}"

    if box_top is None or price is None:
        brk_state = "unknown"
        brk_detail = "Breakout status unknown"
    elif breakout:
        brk_state = "pass"
        brk_detail = f"Breakout @ {price:.2f}"
    elif inside:
        brk_state = "partial"
        brk_detail = "Consolidating inside box"
    else:
        brk_state = "fail"
        brk_detail = "Below / outside active box"

    if vol is None:
        vol_state = "unknown"
        vol_detail = "Volume unavailable"
    elif vol >= 1.5:
        vol_state = "pass"
        vol_detail = f"Rel vol {vol:.2f}x"
    elif vol >= 1.1:
        vol_state = "partial"
        vol_detail = f"Rel vol {vol:.2f}x"
    else:
        vol_state = "fail"
        vol_detail = f"Rel vol {vol:.2f}x"

    eps_state = pct_state(growth, 15, 8)
    ind_state = pct_state(industry, 60, 45)

    criteria = [
        StrategyCriterion("HIGH", "Near Highs", high_state, detail=high_detail, value=near_high, weight=1.2),
        StrategyCriterion("BOX", "Darvas Box", box_state, detail=box_detail, value=box_top, weight=1.4),
        StrategyCriterion("BRK", "Breakout", brk_state, detail=brk_detail, value=price, weight=1.4),
        StrategyCriterion("VOL", "Volume", vol_state, detail=vol_detail, value=vol, weight=1.2),
        StrategyCriterion(
            "EPS",
            "Earnings",
            eps_state,
            detail=f"Growth {growth:.1f}%" if growth is not None else "Growth unavailable",
            value=growth,
            weight=1.0,
        ),
        StrategyCriterion(
            "IND",
            "Industry",
            ind_state,
            detail=f"Strength {industry:.0f}" if industry is not None else "Industry strength unavailable",
            value=industry,
            weight=0.8,
        ),
    ]

    score = score_from_criteria(criteria)
    return StrategyResult(
        score=score,
        rating=rating_from_score(score),
        checklist=criteria,
        metrics={
            "box_top": box_top,
            "box_bottom": box_bottom,
            "breakout": breakout,
            "inside_box": inside,
            "relative_volume": vol,
            "eps_growth": growth,
            "industry_strength": industry,
            "dist_from_52w_high_pct": near_high,
            "stop_loss": box_bottom,
        },
    )
