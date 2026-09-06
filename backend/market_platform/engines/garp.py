from __future__ import annotations

from market_platform.engines.base import (
    StrategyCriterion,
    StrategyResult,
    pct_state,
    rating_from_score,
    score_from_criteria,
)
from market_platform.engines.inputs import StrategyInput
from market_platform.schemas.strategies import StrategyFilterDef, StrategyMeta


META = StrategyMeta(
    slug="garp",
    name="GARP",
    short_name="GARP",
    description="Growth at a Reasonable Price — find consistent growers trading at fair PEG multiples (Peter Lynch style).",
    filters=[
        StrategyFilterDef(key="PEG", label="PEG", detail="PEG Ratio ≤ 1.0"),
        StrategyFilterDef(key="EPS", label="EPS", detail="EPS Growth 12–25%"),
        StrategyFilterDef(key="ROE", label="ROE", detail="ROE ≥ 15%"),
        StrategyFilterDef(key="DE", label="D/E", detail="Debt/Equity ≤ 0.50"),
        StrategyFilterDef(key="PE", label="P/E", detail="TTM P/E ≤ 30"),
        StrategyFilterDef(key="FCF", label="FCF", detail="Positive growth quality"),
    ],
)


def score_garp(row: StrategyInput) -> StrategyResult:
    growth = row.eps_cagr_3y if row.eps_cagr_3y is not None else row.pat_growth_yoy
    peg = row.peg
    if peg is None and row.pe_ttm is not None and growth is not None and growth > 0:
        peg = row.pe_ttm / growth

    pe = row.pe_ttm
    roe = row.roe
    de = row.debt_equity

    # PEG
    if peg is None:
        peg_state = "unknown"
        peg_detail = "PEG unavailable"
    elif 0 < peg <= 1.0:
        peg_state = "pass"
        peg_detail = f"PEG {peg:.2f}"
    elif peg <= 1.2:
        peg_state = "partial"
        peg_detail = f"PEG {peg:.2f}"
    else:
        peg_state = "fail"
        peg_detail = f"PEG {peg:.2f}"

    # Growth band 12-25 preferred; up to 30 partial
    if growth is None:
        g_state = "unknown"
        g_detail = "EPS growth unavailable"
    elif 12 <= growth <= 25:
        g_state = "pass"
        g_detail = f"EPS growth {growth:.1f}%"
    elif 10 <= growth < 12 or 25 < growth <= 30:
        g_state = "partial"
        g_detail = f"EPS growth {growth:.1f}%"
    else:
        g_state = "fail"
        g_detail = f"EPS growth {growth:.1f}%"

    roe_state = pct_state(roe, 15, 12)

    if de is None:
        de_state = "unknown"
        de_detail = "D/E unavailable"
    elif de <= 0.5:
        de_state = "pass"
        de_detail = f"D/E {de:.2f}"
    elif de <= 0.75:
        de_state = "partial"
        de_detail = f"D/E {de:.2f}"
    else:
        de_state = "fail"
        de_detail = f"D/E {de:.2f}"

    if pe is None:
        pe_state = "unknown"
        pe_detail = "P/E unavailable"
    elif 0 < pe <= 30:
        pe_state = "pass"
        pe_detail = f"P/E {pe:.1f}"
    elif pe <= 35:
        pe_state = "partial"
        pe_detail = f"P/E {pe:.1f}"
    else:
        pe_state = "fail"
        pe_detail = f"P/E {pe:.1f}"

    # Proxy for FCF quality: revenue CAGR or growth score
    fcf_proxy = row.revenue_cagr_3y if row.revenue_cagr_3y is not None else row.growth
    if fcf_proxy is None:
        fcf_state = "unknown"
        fcf_detail = "Quality proxy unavailable"
    elif fcf_proxy >= 12:
        fcf_state = "pass"
        fcf_detail = f"Growth quality {fcf_proxy:.1f}"
    elif fcf_proxy >= 5:
        fcf_state = "partial"
        fcf_detail = f"Growth quality {fcf_proxy:.1f}"
    else:
        fcf_state = "fail"
        fcf_detail = f"Growth quality {fcf_proxy:.1f}"

    criteria = [
        StrategyCriterion("PEG", "PEG Ratio", peg_state, detail=peg_detail, value=peg, weight=1.5),
        StrategyCriterion("EPS", "EPS Growth", g_state, detail=g_detail, value=growth, weight=1.3),
        StrategyCriterion(
            "ROE",
            "Return on Equity",
            roe_state,
            detail=f"ROE {roe:.1f}%" if roe is not None else "ROE unavailable",
            value=roe,
            weight=1.1,
        ),
        StrategyCriterion("DE", "Debt / Equity", de_state, detail=de_detail, value=de, weight=1.0),
        StrategyCriterion("PE", "P/E Ratio", pe_state, detail=pe_detail, value=pe, weight=1.0),
        StrategyCriterion("FCF", "Growth Quality", fcf_state, detail=fcf_detail, value=fcf_proxy, weight=0.8),
    ]

    score = score_from_criteria(criteria)
    return StrategyResult(
        score=score,
        rating=rating_from_score(score),
        checklist=criteria,
        metrics={
            "peg": peg,
            "eps_growth": growth,
            "roe": roe,
            "debt_equity": de,
            "pe_ttm": pe,
            "revenue_cagr_3y": row.revenue_cagr_3y,
        },
    )
