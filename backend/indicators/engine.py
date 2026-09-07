from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Stock, StockFinancialPeriod, StockIndicator, StockPrice, StockSnapshot
from database.repository import (
    get_previous_indicator,
    latest_close_volume_series,
    latest_closes,
    upsert_indicator,
)
from indicators.momentum_score import (
    dma_distance_pct,
    extract_quarter_series,
    finalize_momentum_fields,
    volume_metrics,
)
from indicators.moving_averages import moving_averages
from indicators.signal_generator import generate_signals
from indicators.trend_score import distance_from_52w_high, trend_score

# Columns persisted on StockIndicator (exclude ephemeral keys like ltp / return_5d)
_INDICATOR_KEYS = {
    "ma_3",
    "ma_7",
    "ma_20",
    "ma_21",
    "ma_50",
    "ma_200",
    "crossover_3_7",
    "above_ma_21",
    "ma21_gt_ma50",
    "above_ma_200",
    "golden_cross",
    "trend_score",
    "trend",
    "distance_from_52w_high",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_12m",
    "distance_20_dma",
    "distance_50_dma",
    "distance_200_dma",
    "volume_avg_5",
    "volume_avg_20",
    "volume_ratio",
    "positive_volume_days_20",
    "revenue_growth_yoy",
    "pat_growth_yoy",
    "revenue_growth_qoq",
    "pat_growth_qoq",
    "margin_change",
    "earnings_acceleration",
    "return_score",
    "dma_score",
    "volume_score",
    "result_score",
    "momentum_score",
    "momentum_score_20d_ago",
    "momentum_acceleration",
    "momentum_category",
}


def _latest_snapshot(session: Session, stock_id: int) -> StockSnapshot | None:
    return session.scalar(
        select(StockSnapshot)
        .where(StockSnapshot.stock_id == stock_id)
        .order_by(StockSnapshot.snapshot_date.desc())
        .limit(1)
    )


def period_return(closes: list[float], trading_days: int) -> float | None:
    if len(closes) < 2:
        return None
    start = max(0, len(closes) - 1 - trading_days)
    old = closes[start]
    last = closes[-1]
    if not old:
        return None
    return (last / old) - 1


def _quarter_metrics(session: Session, stock_id: int) -> dict[str, Any]:
    rows = session.scalars(
        select(StockFinancialPeriod).where(
            StockFinancialPeriod.stock_id == stock_id,
            StockFinancialPeriod.section == "quarters",
        )
    ).all()
    if not rows:
        return extract_quarter_series({}, [])
    by_period: dict[str, dict[str, float | None]] = defaultdict(dict)
    period_order: list[str] = []
    seen: set[str] = set()
    for row in rows:
        key = (row.metric or "").strip().lower().rstrip("+").strip()
        by_period[row.period_label][key] = float(row.value_num) if row.value_num is not None else None
        if row.period_label not in seen:
            seen.add(row.period_label)
            period_order.append(row.period_label)
    return extract_quarter_series(by_period, period_order)


def _raw_momentum_from_series(
    closes: list[float],
    volumes: list[float | None],
    *,
    ltp: float | None,
    high_52: float | None,
    fundamentals: dict[str, Any],
    existing: StockIndicator | None = None,
) -> dict[str, Any] | None:
    if not closes and ltp is None:
        return None
    if not closes and ltp is not None:
        closes = [float(ltp)]
        volumes = [None]

    mas = moving_averages(closes)
    if existing:
        for key in ("ma_3", "ma_7", "ma_20", "ma_21", "ma_50", "ma_200"):
            if mas.get(key) is None and getattr(existing, key, None) is not None:
                mas[key] = float(getattr(existing, key))

    price = float(ltp) if ltp is not None else (closes[-1] if closes else None)
    scored = trend_score(mas["ma_3"], mas["ma_7"], mas["ma_21"], mas["ma_50"], mas["ma_200"], price)
    distance = distance_from_52w_high(price, high_52)
    vol = volume_metrics(closes, volumes)

    return {
        **mas,
        **scored,
        "ltp": price,
        "distance_from_52w_high": distance,
        "return_1m": period_return(closes, 21),
        "return_3m": period_return(closes, 63),
        "return_6m": period_return(closes, 126),
        "return_12m": period_return(closes, 252),
        "distance_20_dma": dma_distance_pct(price, mas.get("ma_20")),
        "distance_50_dma": dma_distance_pct(price, mas.get("ma_50")),
        "distance_200_dma": dma_distance_pct(price, mas.get("ma_200")),
        **vol,
        **fundamentals,
    }


def collect_raw_for_stock(session: Session, stock: Stock, calc_date: date | None = None) -> dict[str, Any] | None:
    snapshot = _latest_snapshot(session, stock.id)
    calc_date = calc_date or (snapshot.snapshot_date if snapshot else date.today())
    closes, volumes = latest_close_volume_series(session, stock.id, limit=530)
    if not closes and snapshot and snapshot.ltp:
        closes = [float(snapshot.ltp)]
        volumes = [float(snapshot.volume) if snapshot.volume is not None else None]
    if not snapshot and not closes:
        return None

    existing = session.scalar(
        select(StockIndicator).where(
            StockIndicator.stock_id == stock.id,
            StockIndicator.calculation_date == calc_date,
        )
    )
    ltp = float(snapshot.ltp) if snapshot and snapshot.ltp is not None else None
    high_52 = float(snapshot.high_52_week) if snapshot and snapshot.high_52_week is not None else None
    fundamentals = _quarter_metrics(session, stock.id)

    raw = _raw_momentum_from_series(
        closes,
        volumes,
        ltp=ltp,
        high_52=high_52,
        fundamentals=fundamentals,
        existing=existing,
    )
    if raw is None:
        return None

    # Acceleration window: same metrics as of 20 sessions ago
    raw_20: dict[str, Any] | None = None
    if len(closes) > 25:
        closes_20 = closes[:-20]
        volumes_20 = volumes[:-20] if len(volumes) >= len(closes) else volumes[: len(closes_20)]
        high_52_20 = max(closes_20[-252:]) if len(closes_20) >= 50 else (max(closes_20) if closes_20 else None)
        # Approximate 52w distance at T-20 using closes window high
        dist_20 = distance_from_52w_high(closes_20[-1] if closes_20 else None, high_52_20)
        raw_20 = _raw_momentum_from_series(
            closes_20,
            volumes_20,
            ltp=closes_20[-1] if closes_20 else None,
            high_52=high_52_20,
            fundamentals=fundamentals,
            existing=None,
        )
        if raw_20 is not None:
            raw_20["distance_from_52w_high"] = dist_20

    return {
        "stock_id": stock.id,
        "calc_date": calc_date,
        "raw": raw,
        "raw_20": raw_20,
        "snapshot": snapshot,
    }


def _persist_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: fields[k] for k in _INDICATOR_KEYS if k in fields}


def calculate_for_stock(session: Session, stock: Stock, calc_date: date | None = None) -> dict[str, Any] | None:
    """Single-stock path (no universe percentiles — used for ad-hoc calls)."""
    bundle = collect_raw_for_stock(session, stock, calc_date)
    if not bundle:
        return None
    raw = bundle["raw"]
    universes = {
        "return_1m": [raw["return_1m"]] if raw.get("return_1m") is not None else [],
        "return_3m": [raw["return_3m"]] if raw.get("return_3m") is not None else [],
        "return_6m": [raw["return_6m"]] if raw.get("return_6m") is not None else [],
        "return_12m": [raw["return_12m"]] if raw.get("return_12m") is not None else [],
    }
    scored = finalize_momentum_fields(raw, universes)
    fields = {**raw, **scored}
    if bundle.get("raw_20"):
        scored_20 = finalize_momentum_fields(bundle["raw_20"], universes)
        fields["momentum_score_20d_ago"] = scored_20.get("momentum_score")
        if fields.get("momentum_score") is not None and fields["momentum_score_20d_ago"] is not None:
            fields["momentum_acceleration"] = round(
                float(fields["momentum_score"]) - float(fields["momentum_score_20d_ago"]), 4
            )
    calc_date = bundle["calc_date"]
    previous = get_previous_indicator(session, stock.id, calc_date)
    upsert_indicator(session, stock.id, calc_date, _persist_fields(fields))
    screen_row = {**fields, "ltp": raw.get("ltp")}
    generate_signals(session, stock.id, calc_date, {**fields, "ltp": raw.get("ltp")}, previous, screen_row)
    return fields


def calculate_all(session: Session, calc_date: date | None = None) -> int:
    # One shared as-of date so latest_screener_query does not prefer a thin
    # price-only cohort that used date.today() while sheet stocks used snapshot_date.
    stocks = session.scalars(
        select(Stock)
        .where(Stock.is_active.is_(True))
        .where(Stock.id.in_(select(StockSnapshot.stock_id).union(select(StockPrice.stock_id))))
    ).all()
    if calc_date is None:
        snap_max = session.scalar(select(func.max(StockSnapshot.snapshot_date)))
        calc_date = snap_max or date.today()

    bundles: list[dict[str, Any]] = []
    for stock in stocks:
        bundle = collect_raw_for_stock(session, stock, calc_date)
        if bundle:
            bundles.append(bundle)

    universes: dict[str, list[float]] = {
        "return_1m": [],
        "return_3m": [],
        "return_6m": [],
        "return_12m": [],
    }
    for bundle in bundles:
        raw = bundle["raw"]
        for key in universes:
            val = raw.get(key)
            if val is not None:
                universes[key].append(float(val))

    # Also include T-20 returns in universe? Plan says percentile vs complete universe at same as-of.
    # For acceleration, recompute return score with same current universe (stable ranking scale).
    from market_platform.services.sectors import (
        _MemberMetrics,
        _frac_to_pct,
        _load_mcaps_by_stock,
        industry_strength_by_stock_id,
    )

    # Pass 1: component scores without sector strength (avoids circular dependency)
    provisional: dict[int, _MemberMetrics] = {}
    prepared: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for bundle in bundles:
        raw = bundle["raw"]
        scored = finalize_momentum_fields(raw, universes)
        scored_20 = None
        if bundle.get("raw_20"):
            scored_20 = finalize_momentum_fields(bundle["raw_20"], universes)
        provisional[bundle["stock_id"]] = _MemberMetrics(
            return_1m_pct=_frac_to_pct(float(raw["return_1m"]) if raw.get("return_1m") is not None else None),
            return_3m_pct=_frac_to_pct(float(raw["return_3m"]) if raw.get("return_3m") is not None else None),
            return_6m_pct=_frac_to_pct(float(raw["return_6m"]) if raw.get("return_6m") is not None else None),
            momentum_score=float(scored["momentum_score"]) if scored.get("momentum_score") is not None else None,
            momentum_acceleration=None,
            above_ma_50=(
                float(raw["distance_50_dma"]) > 0
                if raw.get("distance_50_dma") is not None
                else (bool(raw["golden_cross"]) if raw.get("golden_cross") is not None else None)
            ),
        )
        prepared.append((bundle, scored_20))

    strength_map = industry_strength_by_stock_id(
        session,
        metrics=provisional,
        mcaps=_load_mcaps_by_stock(session),
    )

    count = 0
    for bundle, scored_20 in prepared:
        raw = bundle["raw"]
        sector_s = strength_map.get(bundle["stock_id"])
        scored = finalize_momentum_fields(raw, universes, sector_strength=sector_s)
        fields = {**raw, **scored}
        if scored_20 is not None or bundle.get("raw_20"):
            scored_20b = finalize_momentum_fields(
                bundle["raw_20"], universes, sector_strength=sector_s
            )
            fields["momentum_score_20d_ago"] = scored_20b.get("momentum_score")
            if fields.get("momentum_score") is not None and fields["momentum_score_20d_ago"] is not None:
                fields["momentum_acceleration"] = round(
                    float(fields["momentum_score"]) - float(fields["momentum_score_20d_ago"]), 4
                )
            else:
                fields["momentum_acceleration"] = None
        else:
            fields["momentum_score_20d_ago"] = None
            fields["momentum_acceleration"] = None

        stock_id = bundle["stock_id"]
        cdate = bundle["calc_date"]
        previous = get_previous_indicator(session, stock_id, cdate)
        upsert_indicator(session, stock_id, cdate, _persist_fields(fields))
        screen_row = {**fields, "ltp": raw.get("ltp")}
        generate_signals(
            session,
            stock_id,
            cdate,
            {**fields, "ltp": raw.get("ltp")},
            previous,
            screen_row,
        )
        count += 1

    session.commit()
    try:
        from cache.redis_cache import invalidate_market_caches

        invalidate_market_caches()
    except Exception:  # noqa: BLE001
        pass
    return count
