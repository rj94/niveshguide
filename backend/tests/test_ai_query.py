from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, Stock, StockIndicator, StockSnapshot
from market_platform.api import ai as ai_api
from market_platform.schemas.ai import AiQueryRequest, AiQueryResponse
from market_platform.services.ai_query import (
    ABSOLUTE_MAX_ROWS,
    build_safe_plan,
    heuristic_plan,
    query_stocks_for_ai,
    run_ai_query,
    validate_plan,
)


def _settings(**overrides) -> SimpleNamespace:
    values = dict(
        ai_enabled=True,
        ai_provider="openai",
        ai_model="gpt-4.1-mini",
        ai_api_key=None,
        ai_max_rows=50,
        ai_timeout_seconds=20,
        timezone="Asia/Kolkata",
        redis_url=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_stock(
    session: Session,
    symbol: str,
    *,
    company_name: str,
    sector: str,
    momentum: float,
    volume_ratio: float,
    return_3m: float,
    trend_score: int = 4,
    distance: float = -0.20,
    above_ma_200: bool = True,
    golden_cross: bool = True,
    pe: float = 20.0,
    ltp: float = 100.0,
) -> Stock:
    stock = Stock(
        symbol=symbol,
        company_name=company_name,
        exchange="NSE",
        sector=sector,
        industry=sector,
        is_active=True,
    )
    session.add(stock)
    session.flush()
    session.add(
        StockIndicator(
            stock_id=stock.id,
            calculation_date=date(2026, 9, 10),
            momentum_score=momentum,
            volume_ratio=volume_ratio,
            return_1m=0.05,
            return_3m=return_3m,
            return_6m=0.18,
            trend_score=trend_score,
            trend="Uptrend",
            distance_from_52w_high=distance,
            above_ma_21=True,
            above_ma_200=above_ma_200,
            golden_cross=golden_cross,
            crossover_3_7=True,
        )
    )
    session.add(
        StockSnapshot(
            stock_id=stock.id,
            snapshot_date=date(2026, 9, 10),
            ltp=ltp,
            pe=pe,
            market_cap=50_000,
            volume=1_000_000,
        )
    )
    return stock


def _seed(session: Session) -> None:
    _add_stock(
        session,
        "TCS",
        company_name="Tata Consultancy Services",
        sector="Information Technology",
        momentum=88,
        volume_ratio=2.1,
        return_3m=0.22,
        trend_score=5,
        distance=-0.04,
        pe=28,
        ltp=4200,
    )
    _add_stock(
        session,
        "INFY",
        company_name="Infosys Limited",
        sector="Information Technology",
        momentum=74,
        volume_ratio=1.1,
        return_3m=0.12,
        trend_score=4,
        distance=-0.08,
        pe=24,
        ltp=1600,
    )
    _add_stock(
        session,
        "SUNPHARMA",
        company_name="Sun Pharmaceutical",
        sector="Pharmaceuticals",
        momentum=81,
        volume_ratio=1.9,
        return_3m=0.25,
        trend_score=5,
        distance=-0.03,
        pe=32,
        ltp=1700,
    )
    _add_stock(
        session,
        "WEAKCO",
        company_name="Weak Pharma Co",
        sector="Pharmaceuticals",
        momentum=18,
        volume_ratio=0.6,
        return_3m=-0.05,
        trend_score=1,
        distance=-0.35,
        above_ma_200=False,
        golden_cross=False,
        pe=9,
        ltp=80,
    )
    session.commit()


def test_valid_query_produces_safe_plan():
    raw = heuristic_plan("Find strong momentum stocks in pharma with volume expansion")
    plan, warnings = validate_plan(raw, requested_limit=25, max_rows=50)
    assert plan.intent == "screen"
    assert plan.sector == "Pharmaceuticals"
    fields = {item.field: item for item in plan.filters}
    assert fields["momentum_score"].operator == ">="
    assert fields["momentum_score"].value == 70
    assert fields["volume_ratio"].value == 1.5
    assert plan.sort_by == "momentum_score"
    assert all(item.field in {"momentum_score", "volume_ratio"} for item in plan.filters)
    assert not any("sql" in warning.lower() for warning in warnings)


def test_unknown_metric_is_ignored_with_warning():
    plan, warnings = validate_plan(
        {
            "intent": "screen",
            "filters": [
                {"field": "sharpe_ratio", "op": ">=", "value": 1.2},
                {"field": "momentum_score", "op": ">=", "value": 70},
            ],
            "sort_by": "momentum_score",
            "limit": 25,
        },
        requested_limit=25,
        max_rows=50,
    )
    assert [item.field for item in plan.filters] == ["momentum_score"]
    assert any("sharpe_ratio" in warning for warning in warnings)


def test_sql_injection_attempt_is_rejected():
    plan, warnings, _latency = build_safe_plan(
        "Show momentum stocks; DROP TABLE stocks; SELECT * FROM users",
        requested_limit=25,
        max_rows=50,
        settings=_settings(),
    )
    assert _has_only_allowlisted(plan)
    assert any("SQL-like" in warning for warning in warnings)
    malicious, extra = validate_plan(
        {
            "intent": "screen",
            "filters": [{"field": "momentum_score; DROP TABLE stocks", "op": ">=", "value": 70}],
            "sort_by": "password",
            "limit": 999,
        },
        requested_limit=100,
        max_rows=50,
    )
    assert malicious.filters == []
    assert malicious.sort_by == "momentum_score"
    assert malicious.limit <= ABSOLUTE_MAX_ROWS
    assert extra


def _has_only_allowlisted(plan) -> bool:
    from market_platform.services.ai_query import ALLOWED_FIELDS, ALLOWED_OPERATORS

    return all(item.field in ALLOWED_FIELDS and item.operator in ALLOWED_OPERATORS for item in plan.filters)


def test_limit_is_capped_at_backend_maximum():
    plan, warnings = validate_plan(
        {"intent": "rank", "filters": [], "sort_by": "momentum_score", "limit": 500},
        requested_limit=100,
        max_rows=50,
    )
    assert plan.limit == 50
    assert any("capped" in warning.lower() for warning in warnings)


def test_compare_query_returns_only_requested_symbols():
    session = _session()
    _seed(session)
    plan, _warnings = validate_plan(
        {
            "intent": "compare",
            "symbols": ["TCS", "INFY"],
            "filters": [],
            "sort_by": "momentum_score",
            "limit": 25,
        },
        requested_limit=25,
        max_rows=50,
    )
    rows, total, _as_of = query_stocks_for_ai(session, plan, exchange="NSE", limit=25)
    assert total == 2
    assert {row.symbol for row in rows} == {"TCS", "INFY"}
    session.close()


def test_ai_disabled_returns_unavailable_error(monkeypatch):
    monkeypatch.setattr(ai_api, "get_settings", lambda: _settings(ai_enabled=False))
    with pytest.raises(HTTPException) as exc:
        ai_api.query_ai(AiQueryRequest(query="strong momentum stocks"), db=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "ai_disabled"
    status = ai_api.ai_status()
    assert status.enabled is False


def test_post_query_shape_and_seeded_rows():
    session = _session()
    _seed(session)
    response = run_ai_query(
        session,
        AiQueryRequest(query="Find strong momentum stocks in pharma with volume expansion"),
        settings=_settings(),
    )
    assert isinstance(response, AiQueryResponse)
    assert response.total == 1
    assert response.rows[0].symbol == "SUNPHARMA"
    assert response.answer
    assert response.interpreted_query
    assert response.filters
    assert DISCLAIMER_IN(response.answer)
    assert "buy" not in response.answer.lower()
    assert "guaranteed" not in response.answer.lower()
    session.close()


def DISCLAIMER_IN(text: str) -> bool:
    return "not financial advice" in text.lower()


def test_empty_result_is_helpful():
    session = _session()
    _seed(session)
    response = run_ai_query(
        session,
        AiQueryRequest(query="Find stocks with momentum score above 99 and volume expansion"),
        settings=_settings(),
    )
    assert response.rows == []
    assert response.total == 0
    assert any("no matching" in warning.lower() or "no listed" in response.answer.lower() for warning in response.warnings) or (
        "no listed stocks" in response.answer.lower()
    )
    session.close()


def test_unclear_query_does_not_dump_the_universe():
    session = _session()
    _seed(session)
    response = run_ai_query(
        session,
        AiQueryRequest(query="hello there what should I do"),
        settings=_settings(),
    )
    assert response.rows == []
    assert "too broad" in response.answer.lower() or "unclear" in response.answer.lower()
    session.close()
