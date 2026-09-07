"""CANSLIM metrics must expose distinct QoQ vs YoY growth."""

from market_platform.engines.canslim import score_canslim, _fmt_growth
from market_platform.engines.inputs import StrategyInput


def _row(**overrides) -> StrategyInput:
    base = dict(
        id=1,
        symbol="TEST",
        company_name="Test Co",
        exchange="NSE",
        sector="IT",
        industry="Software",
        ltp=100.0,
        change_pct=1.0,
        sma_21=98.0,
        sma_50=95.0,
        sma_200=90.0,
        price_above_50_above_200=True,
        sma_50_above_200=True,
        volume=1_000_000,
        avg_volume_20=500_000.0,
        volume_ratio=2.0,
        volume_mover=True,
        return_1m_pct=5.0,
        return_3m_pct=12.0,
        return_6m_pct=20.0,
        as_of=None,
        revenue_growth_yoy=40.0,
        pat_growth_yoy=50.0,
        revenue_growth_qoq=22.0,
        pat_growth_qoq=30.0,
        eps_cagr_3y=20.0,
        revenue_cagr_3y=18.0,
        roe=20.0,
        institutional_pct=35.0,
        momentum=85.0,
        dist_from_52w_high_pct=-5.0,
    )
    base.update(overrides)
    return StrategyInput(**base)


def test_eps_qoq_and_yoy_are_distinct():
    result = score_canslim(_row(pat_growth_qoq=30, pat_growth_yoy=50, eps_cagr_3y=20), market_uptrend=True)
    assert result.metrics["eps_qoq"] == 30
    assert result.metrics["eps_yoy"] == 50
    assert result.metrics["eps_qoq"] != result.metrics["eps_yoy"]
    assert result.metrics["eps_cagr_3y"] == 20


def test_metrics_differ_even_if_cagr_was_yoy_proxy():
    """Old bug: eps_cagr_3y=pat_yoy proxy made eps_yoy equal YoY and hid QoQ.

    Even if someone still sets cagr equal to yoy, UI metrics must use QoQ vs YoY.
    """
    yoy = 50.0
    qoq = 30.0
    result = score_canslim(
        _row(pat_growth_qoq=qoq, pat_growth_yoy=yoy, eps_cagr_3y=yoy),
        market_uptrend=True,
    )
    assert result.metrics["eps_qoq"] == qoq
    assert result.metrics["eps_yoy"] == yoy
    assert result.metrics["eps_qoq"] != result.metrics["eps_yoy"]


def test_c_uses_qoq_not_yoy_for_scoring():
    # QoQ fails (<15), YoY would pass — C must fail from QoQ
    result = score_canslim(
        _row(pat_growth_qoq=10, revenue_growth_qoq=5, pat_growth_yoy=80, eps_cagr_3y=80),
        market_uptrend=True,
    )
    c = next(item for item in result.checklist if item.key == "C")
    assert c.state == "fail"
    assert "QoQ" in (c.detail or "")


def test_a_falls_back_to_yoy_when_cagr_missing():
    result = score_canslim(
        _row(pat_growth_qoq=30, pat_growth_yoy=50, eps_cagr_3y=None),
        market_uptrend=True,
    )
    a = next(item for item in result.checklist if item.key == "A")
    assert "YoY" in (a.detail or "")
    assert result.metrics["eps_yoy"] == 50
    assert result.metrics["eps_cagr_3y"] is None
    assert result.metrics["eps_qoq"] == 30


def test_fmt_growth_uses_middle_dot():
    s = _fmt_growth("EPS/PAT QoQ", 30.0, "Sales QoQ", 22.0)
    assert " · " in s
    assert s == "EPS/PAT QoQ 30.0% · Sales QoQ 22.0%"
