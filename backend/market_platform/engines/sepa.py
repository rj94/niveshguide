from __future__ import annotations

from market_platform.engines.base import (
    StrategyCriterion,
    StrategyResult,
    pct_state,
    rating_from_score,
    score_from_criteria,
)
from market_platform.engines.inputs import StrategyInput, rs_proxy
from market_platform.schemas.strategies import StrategyFilterDef, StrategyMeta


META = StrategyMeta(
    slug="sepa",
    name="SEPA (Minervini)",
    short_name="SEPA",
    description="Mark Minervini Specific Entry Point Analysis — Stage 2 trend template with VCP-style contraction.",
    filters=[
        StrategyFilterDef(key="T1", label="T1", detail="Price > 150 & 200 SMA"),
        StrategyFilterDef(key="T2", label="T2", detail="150 SMA > 200 SMA"),
        StrategyFilterDef(key="T3", label="T3", detail="200 SMA rising"),
        StrategyFilterDef(key="T4", label="T4", detail="50 SMA > 150 & 200"),
        StrategyFilterDef(key="T5", label="T5", detail="≥25% above 52W low"),
        StrategyFilterDef(key="T6", label="T6", detail="Within 25% of 52W high"),
        StrategyFilterDef(key="RS", label="RS", detail="RS Rating ≥ 70"),
        StrategyFilterDef(key="VCP", label="VCP", detail="Volatility contracting"),
    ],
)


def _vcp_proxy(row: StrategyInput) -> tuple[str, str, float | None]:
    bars = row.bars
    if len(bars) < 40:
        return "unknown", "Insufficient history for VCP", None

    recent = bars[-40:]
    first = recent[:20]
    second = recent[20:]

    def range_pct(window: list) -> float | None:
        hi = max(b.high for b in window)
        lo = min(b.low for b in window)
        mid = (hi + lo) / 2 if hi and lo else None
        if not mid:
            return None
        return (hi - lo) / mid * 100

    r1 = range_pct(first)
    r2 = range_pct(second)
    vols1 = [b.volume for b in first if b.volume]
    vols2 = [b.volume for b in second if b.volume]
    v1 = sum(vols1) / len(vols1) if vols1 else None
    v2 = sum(vols2) / len(vols2) if vols2 else None

    if r1 is None or r2 is None:
        return "unknown", "Unable to measure contraction", None

    contracting = r2 < r1 * 0.75
    vol_drying = v1 is not None and v2 is not None and v2 < v1 * 0.9
    value = round(r2, 2)

    if contracting and vol_drying:
        return "pass", f"Range {r1:.1f}% → {r2:.1f}% with volume dry-up", value
    if contracting or vol_drying:
        return "partial", f"Range {r1:.1f}% → {r2:.1f}%", value
    return "fail", f"Range still wide ({r2:.1f}%)", value


def score_sepa(row: StrategyInput) -> StrategyResult:
    price = row.ltp
    sma50 = row.sma_50
    sma150 = row.sma_150
    sma200 = row.sma_200
    sma200_prev = row.sma_200_20d_ago
    rs = rs_proxy(row)
    growth = row.pat_growth_yoy if row.pat_growth_yoy is not None else row.eps_cagr_3y
    roe = row.roe

    t1_ok = (
        price is not None
        and sma150 is not None
        and sma200 is not None
        and price > sma150
        and price > sma200
    )
    t1 = "pass" if t1_ok else ("unknown" if None in (price, sma150, sma200) else "fail")

    t2_ok = sma150 is not None and sma200 is not None and sma150 > sma200
    t2 = "pass" if t2_ok else ("unknown" if None in (sma150, sma200) else "fail")

    t3_ok = sma200 is not None and sma200_prev is not None and sma200 > sma200_prev
    t3 = "pass" if t3_ok else ("unknown" if None in (sma200, sma200_prev) else "fail")

    t4_ok = (
        sma50 is not None
        and sma150 is not None
        and sma200 is not None
        and sma50 > sma150
        and sma50 > sma200
    )
    t4 = "pass" if t4_ok else ("unknown" if None in (sma50, sma150, sma200) else "fail")

    # Also require price > 50 SMA (template rule 8) folded into T4 partial if only that fails
    if t4 == "pass" and price is not None and sma50 is not None and price <= sma50:
        t4 = "partial"

    dist_low = row.dist_from_52w_low_pct
    if dist_low is None:
        t5 = "unknown"
        t5_detail = "52W low distance unavailable"
    elif dist_low >= 25:
        t5 = "pass"
        t5_detail = f"{dist_low:.1f}% above 52W low"
    elif dist_low >= 15:
        t5 = "partial"
        t5_detail = f"{dist_low:.1f}% above 52W low"
    else:
        t5 = "fail"
        t5_detail = f"{dist_low:.1f}% above 52W low"

    dist_high = row.dist_from_52w_high_pct
    # Within 25% of high means dist_high >= -25
    if dist_high is None:
        t6 = "unknown"
        t6_detail = "52W high distance unavailable"
    elif dist_high >= -25:
        t6 = "pass"
        t6_detail = f"{dist_high:+.1f}% from 52W high"
    elif dist_high >= -35:
        t6 = "partial"
        t6_detail = f"{dist_high:+.1f}% from 52W high"
    else:
        t6 = "fail"
        t6_detail = f"{dist_high:+.1f}% from 52W high"

    rs_state = pct_state(rs, 70, 60)
    vcp_state, vcp_detail, vcp_val = _vcp_proxy(row)
    fund_state = pct_state(growth, 20, 12)
    roe_state = pct_state(roe, 15, 12)

    criteria = [
        StrategyCriterion("T1", "Price > 150/200", t1, detail=_ma_detail(price, sma150, sma200), weight=1.2),
        StrategyCriterion(
            "T2",
            "150 > 200 SMA",
            t2,
            detail=f"150={sma150:.1f} 200={sma200:.1f}" if sma150 and sma200 else "SMA unavailable",
            weight=1.1,
        ),
        StrategyCriterion(
            "T3",
            "200 SMA Rising",
            t3,
            detail="200 DMA trending up" if t3 == "pass" else "200 DMA not rising",
            weight=1.0,
        ),
        StrategyCriterion(
            "T4",
            "50 SMA Leadership",
            t4,
            detail=f"50={sma50:.1f}" if sma50 else "50 SMA unavailable",
            weight=1.2,
        ),
        StrategyCriterion("T5", "Above 52W Low", t5, detail=t5_detail, value=dist_low, weight=1.0),
        StrategyCriterion("T6", "Near 52W High", t6, detail=t6_detail, value=dist_high, weight=1.0),
        StrategyCriterion(
            "RS",
            "Relative Strength",
            rs_state,
            detail=f"RS {rs:.0f}" if rs is not None else "RS unavailable",
            value=rs,
            weight=1.3,
        ),
        StrategyCriterion("VCP", "VCP Contraction", vcp_state, detail=vcp_detail, value=vcp_val, weight=1.2),
        StrategyCriterion(
            "EPS",
            "Earnings Growth",
            fund_state,
            detail=f"Growth {growth:.1f}%" if growth is not None else "Growth unavailable",
            value=growth,
            weight=0.9,
        ),
        StrategyCriterion(
            "ROE",
            "ROE",
            roe_state,
            detail=f"ROE {roe:.1f}%" if roe is not None else "ROE unavailable",
            value=roe,
            weight=0.7,
        ),
    ]

    score = score_from_criteria(criteria)
    return StrategyResult(
        score=score,
        rating=rating_from_score(score),
        checklist=criteria,
        metrics={
            "sma_50": sma50,
            "sma_150": sma150,
            "sma_200": sma200,
            "rs_rating": rs,
            "dist_from_52w_high_pct": dist_high,
            "dist_from_52w_low_pct": dist_low,
            "eps_growth": growth,
            "roe": roe,
            "vcp_range_pct": vcp_val,
            "trend_template_pass": all(
                c.state == "pass" for c in criteria if c.key.startswith("T") or c.key == "RS"
            ),
        },
    )


def _ma_detail(price: float | None, sma150: float | None, sma200: float | None) -> str:
    parts = []
    if price is not None:
        parts.append(f"Px {price:.1f}")
    if sma150 is not None:
        parts.append(f"150={sma150:.1f}")
    if sma200 is not None:
        parts.append(f"200={sma200:.1f}")
    return " · ".join(parts) if parts else "MAs unavailable"
