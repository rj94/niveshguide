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
    slug="canslim",
    name="CANSLIM",
    short_name="CANSLIM",
    description="Identify growth stocks with strong earnings, relative strength, and institutional sponsorship during confirmed market uptrends.",
    filters=[
        StrategyFilterDef(key="C", label="C", detail="Current Earnings EPS QoQ > 25%"),
        StrategyFilterDef(key="A", label="A", detail="Annual Earnings EPS Annual > 25%"),
        StrategyFilterDef(key="N", label="N", detail="New Highs Near 52W High"),
        StrategyFilterDef(key="S", label="S", detail="Supply/Demand Rel Vol > 1.4x"),
        StrategyFilterDef(key="L", label="L", detail="Leader RS Rating ≥ 80"),
        StrategyFilterDef(key="I", label="I", detail="Institutions Accumulating"),
        StrategyFilterDef(key="M", label="M", detail="Market Confirmed Uptrend"),
    ],
)


def score_canslim(row: StrategyInput, *, market_uptrend: bool) -> StrategyResult:
    # C (Current): QoQ growth only — never silently substitute YoY
    eps_q = row.pat_growth_qoq
    rev_q = row.revenue_growth_qoq
    # A (Annual): real 3Y CAGR when present; else YoY as annual checklist proxy only
    eps_cagr = row.eps_cagr_3y
    eps_yoy = row.pat_growth_yoy
    a_growth = eps_cagr if eps_cagr is not None else eps_yoy
    a_growth_label = "EPS CAGR 3Y" if eps_cagr is not None else "EPS/PAT YoY"
    roe = row.roe
    rs = rs_proxy(row)
    vol = row.volume_ratio
    inst = row.institutional_pct
    near_high = row.dist_from_52w_high_pct

    c_eps = pct_state(eps_q, 25, 15)
    c_rev = pct_state(rev_q, 20, 10)
    if c_eps == "pass" and c_rev in ("pass", "partial", "unknown"):
        c_state = "pass"
    elif c_eps == "partial" or (c_eps == "pass" and c_rev == "fail"):
        c_state = "partial"
    elif c_eps == "unknown" and c_rev == "unknown":
        c_state = "unknown"
    else:
        c_state = "fail"

    a_eps = pct_state(a_growth, 25, 15)
    a_roe = pct_state(roe, 17, 12)
    if a_eps == "pass" and a_roe in ("pass", "partial", "unknown"):
        a_state = "pass"
    elif a_eps in ("pass", "partial") or a_roe == "pass":
        a_state = "partial"
    elif a_eps == "unknown" and a_roe == "unknown":
        a_state = "unknown"
    else:
        a_state = "fail"

    if near_high is None:
        n_state = "unknown"
        n_detail = "52-week high distance unavailable"
    elif near_high >= -10:
        n_state = "pass"
        n_detail = f"{near_high:+.1f}% from 52W high"
    elif near_high >= -20:
        n_state = "partial"
        n_detail = f"{near_high:+.1f}% from 52W high"
    else:
        n_state = "fail"
        n_detail = f"{near_high:+.1f}% from 52W high"

    price_ok = None
    if row.ltp is not None and row.sma_50 is not None:
        price_ok = row.ltp > row.sma_50
    if vol is not None and vol >= 1.4 and price_ok is not False:
        s_state = "pass"
    elif (vol is not None and vol >= 1.1) or price_ok:
        s_state = "partial"
    elif vol is None and price_ok is None:
        s_state = "unknown"
    else:
        s_state = "fail"

    l_state = pct_state(rs, 80, 70)

    if inst is None:
        i_state = "unknown"
        i_detail = "Ownership data unavailable"
        accum = "Unknown"
    elif 20 <= inst < 90:
        i_state = "pass"
        i_detail = f"Institutional {inst:.1f}%"
        accum = "Strong" if inst >= 40 else "Moderate"
    elif 10 <= inst < 20 or 90 <= inst < 95:
        i_state = "partial"
        i_detail = f"Institutional {inst:.1f}%"
        accum = "Moderate" if inst < 90 else "Crowded"
    else:
        i_state = "fail"
        i_detail = f"Institutional {inst:.1f}%"
        accum = "Weak"

    m_state = "pass" if market_uptrend else "fail"
    m_detail = "Confirmed uptrend" if market_uptrend else "Not in confirmed uptrend"

    criteria = [
        StrategyCriterion(
            "C",
            "Current Earnings",
            c_state,
            detail=_fmt_growth("EPS/PAT QoQ", eps_q, "Sales QoQ", rev_q),
            value=eps_q,
            weight=1.2,
        ),
        StrategyCriterion(
            "A",
            "Annual Earnings",
            a_state,
            detail=_fmt_growth(a_growth_label, a_growth, "ROE", roe),
            value=a_growth,
            weight=1.2,
        ),
        StrategyCriterion("N", "New Highs", n_state, detail=n_detail, value=near_high, weight=1.0),
        StrategyCriterion(
            "S",
            "Supply & Demand",
            s_state,
            detail=f"Rel vol {vol:.2f}x" if vol is not None else "Volume unavailable",
            value=vol,
            weight=1.0,
        ),
        StrategyCriterion(
            "L",
            "Leader (RS)",
            l_state,
            detail=f"RS {rs:.0f}" if rs is not None else "RS unavailable",
            value=rs,
            weight=1.3,
        ),
        StrategyCriterion("I", "Institutions", i_state, detail=i_detail, value=inst, weight=1.0),
        StrategyCriterion("M", "Market Direction", m_state, detail=m_detail, weight=1.3),
    ]

    score = score_from_criteria(criteria)
    # Soft-penalize when market is not uptrend even if other letters pass
    if not market_uptrend:
        score = round(score * 0.9, 1)

    return StrategyResult(
        score=score,
        rating=rating_from_score(score),
        checklist=criteria,
        metrics={
            "eps_qoq": eps_q,
            "eps_yoy": eps_yoy,
            "eps_cagr_3y": eps_cagr,
            "revenue_growth_qoq": rev_q,
            "revenue_growth_yoy": row.revenue_growth_yoy,
            "roe": roe,
            "rs_rating": rs,
            "relative_volume": vol,
            "institutional_accumulation": accum,
            "institutional_pct": inst,
            "dist_from_52w_high_pct": near_high,
        },
    )


def _fmt_growth(a_label: str, a: float | None, b_label: str, b: float | None) -> str:
    parts = []
    if a is not None:
        parts.append(f"{a_label} {a:.1f}%")
    if b is not None:
        parts.append(f"{b_label} {b:.1f}%")
    return " · ".join(parts) if parts else "Data unavailable"
