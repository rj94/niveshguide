"""Persist daily sector/industry strength snapshots from prices + indicators."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    IndustryDailyMetrics,
    MarketIndex,
    MarketIndexPrice,
    SectorDailyMetrics,
    Stock,
    StockIndicator,
    StockPrice,
    StockSnapshot,
)
from market_platform.engines.sector_rotation import (
    BenchmarkReturns,
    PriorScores,
    ScoredGroup,
    StockFeature,
    aggregate_features,
    score_groups,
)

logger = logging.getLogger(__name__)

NIFTY_500_KEY = "NIFTY 500"
DEFAULT_MIN_CONSTITUENTS = 5
BACKFILL_DATES = 63
PRICE_LOOKBACK_CALENDAR_DAYS = 400


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:
        return None
    return n


def _period_return(closes: Sequence[float], days: int) -> float | None:
    if len(closes) < days + 1:
        return None
    old = closes[-(days + 1)]
    last = closes[-1]
    if not old:
        return None
    return (last / old) - 1.0


def _sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    chunk = values[-window:]
    return sum(chunk) / window


def sector_label(stock: Stock) -> str | None:
    name = (stock.sector or stock.broad_sector or "").strip()
    return name or None


def industry_labels(stock: Stock) -> list[str]:
    from ingestion.niftyindices_constituents import split_industry_labels

    out: list[str] = []
    seen: set[str] = set()
    primary = (stock.industry or "").strip()
    if primary:
        out.append(primary)
        seen.add(primary.lower())
    for label in split_industry_labels(stock.broad_industry):
        key = label.lower()
        if not label or key in seen:
            continue
        out.append(label)
        seen.add(key)
    return out


def _trading_dates_before(session: Session, as_of: date, *, model, date_col, n: int) -> list[date]:
    rows = session.scalars(
        select(date_col).where(date_col < as_of).distinct().order_by(date_col.desc()).limit(n)
    ).all()
    return list(rows)


def load_benchmark_returns(session: Session, as_of: date) -> BenchmarkReturns:
    idx = session.scalar(select(MarketIndex).where(MarketIndex.key == NIFTY_500_KEY))
    if idx is None:
        return BenchmarkReturns()
    closes = [
        float(c)
        for c in session.scalars(
            select(MarketIndexPrice.close)
            .where(
                MarketIndexPrice.index_id == idx.id,
                MarketIndexPrice.price_date <= as_of,
                MarketIndexPrice.close.is_not(None),
            )
            .order_by(MarketIndexPrice.price_date.asc())
        ).all()
        if c is not None
    ]
    return BenchmarkReturns(
        return_5d=_period_return(closes, 5),
        return_21d=_period_return(closes, 21),
        return_63d=_period_return(closes, 63),
        return_126d=_period_return(closes, 126),
    )


def _load_mcaps(session: Session, as_of: date) -> dict[int, float]:
    latest = (
        select(
            StockSnapshot.stock_id,
            func.max(StockSnapshot.snapshot_date).label("max_date"),
        )
        .where(StockSnapshot.snapshot_date <= as_of)
        .group_by(StockSnapshot.stock_id)
        .subquery()
    )
    rows = session.execute(
        select(StockSnapshot.stock_id, StockSnapshot.market_cap).join(
            latest,
            (StockSnapshot.stock_id == latest.c.stock_id)
            & (StockSnapshot.snapshot_date == latest.c.max_date),
        )
    ).all()
    out: dict[int, float] = {}
    for stock_id, mcap in rows:
        val = _f(mcap)
        if val and val > 0:
            out[int(stock_id)] = val
    return out


def _load_indicators(session: Session, as_of: date) -> dict[int, StockIndicator]:
    latest = (
        select(
            StockIndicator.stock_id,
            func.max(StockIndicator.calculation_date).label("max_date"),
        )
        .where(StockIndicator.calculation_date <= as_of)
        .group_by(StockIndicator.stock_id)
        .subquery()
    )
    rows = session.scalars(
        select(StockIndicator).join(
            latest,
            (StockIndicator.stock_id == latest.c.stock_id)
            & (StockIndicator.calculation_date == latest.c.max_date),
        )
    ).all()
    return {int(row.stock_id): row for row in rows}


def _load_price_series(
    session: Session, as_of: date
) -> dict[int, list[tuple[date, float, float | None, float | None]]]:
    """stock_id → chronological (date, close, high, volume)."""
    cutoff = as_of - timedelta(days=PRICE_LOOKBACK_CALENDAR_DAYS)
    rows = session.execute(
        select(
            StockPrice.stock_id,
            StockPrice.price_date,
            StockPrice.close,
            StockPrice.high,
            StockPrice.volume,
        )
        .where(StockPrice.price_date <= as_of, StockPrice.price_date >= cutoff)
        .order_by(StockPrice.stock_id, StockPrice.price_date.asc())
    ).all()
    series: dict[int, list[tuple[date, float, float | None, float | None]]] = defaultdict(list)
    for stock_id, price_date, close, high, volume in rows:
        c = _f(close)
        if c is None:
            continue
        series[int(stock_id)].append((price_date, c, _f(high), _f(volume)))
    return series


def _features_from_series(
    stock: Stock,
    indicator: StockIndicator | None,
    bars: Sequence[tuple[date, float, float | None, float | None]],
    mcap: float | None,
) -> StockFeature | None:
    if not bars:
        return None
    closes = [row[1] for row in bars]
    highs = [row[2] if row[2] is not None else row[1] for row in bars]
    volumes = [row[3] for row in bars]
    close = closes[-1]
    ma_21 = _f(indicator.ma_21) if indicator is not None else _sma(closes, 21)
    ma_50 = _f(indicator.ma_50) if indicator is not None else _sma(closes, 50)
    ma_200 = _f(indicator.ma_200) if indicator is not None else _sma(closes, 200)
    ma21_prev = _sma(closes[:-5], 21) if len(closes) >= 26 else None
    ma50_prev = _sma(closes[:-5], 50) if len(closes) >= 55 else None
    ma21_now = ma_21 if ma_21 is not None else _sma(closes, 21)
    ma50_now = ma_50 if ma_50 is not None else _sma(closes, 50)

    above_21 = None
    above_50 = None
    above_200 = None
    if indicator is not None:
        above_21 = indicator.above_ma_21
        if indicator.distance_50_dma is not None:
            above_50 = float(indicator.distance_50_dma) > 0
        elif indicator.golden_cross is not None:
            above_50 = bool(indicator.golden_cross)
        above_200 = indicator.above_ma_200
    if above_21 is None and ma21_now:
        above_21 = close > ma21_now
    if above_50 is None and ma50_now:
        above_50 = close > ma50_now
    if above_200 is None and ma_200:
        above_200 = close > ma_200

    ma21_gt = indicator.ma21_gt_ma50 if indicator is not None else None
    if ma21_gt is None and ma21_now and ma50_now:
        ma21_gt = ma21_now > ma50_now
    ma50_gt = None
    if ma50_now and ma_200:
        ma50_gt = ma50_now > ma_200

    vol_ratio = _f(indicator.volume_ratio) if indicator is not None else None
    avg_vol_20 = None
    known_vol = [v for v in volumes[-20:] if v is not None]
    if len(known_vol) >= 5:
        avg_vol_20 = sum(known_vol) / len(known_vol)
        last_vol = volumes[-1]
        if vol_ratio is None and last_vol is not None and avg_vol_20 > 0:
            vol_ratio = last_vol / avg_vol_20

    price_up = len(closes) >= 2 and closes[-1] > closes[-2]
    vol_up = False
    if volumes[-1] is not None and avg_vol_20:
        vol_up = volumes[-1] > avg_vol_20
    elif len(volumes) >= 2 and volumes[-1] is not None and volumes[-2] is not None:
        vol_up = volumes[-1] > volumes[-2]

    def turnover(window: int) -> float | None:
        chunk = bars[-window:]
        vals = []
        for _d, c, _h, v in chunk:
            if v is None:
                continue
            vals.append(c * v)
        if not vals:
            return None
        return sum(vals) / len(vals)

    high_20 = max(highs[-20:]) if len(highs) >= 10 else None
    high_50 = max(highs[-50:]) if len(highs) >= 20 else None
    at_20 = None if high_20 is None else close >= 0.995 * high_20
    at_50 = None if high_50 is None else close >= 0.995 * high_50
    dist_52 = _f(indicator.distance_from_52w_high) if indicator is not None else None
    at_52 = None if dist_52 is None else dist_52 >= -0.005

    ret_21 = _period_return(closes, 21)
    if ret_21 is None and indicator is not None and indicator.return_1m is not None:
        ret_21 = float(indicator.return_1m)
    ret_63 = _period_return(closes, 63)
    if ret_63 is None and indicator is not None and indicator.return_3m is not None:
        ret_63 = float(indicator.return_3m)
    ret_126 = _period_return(closes, 126)
    if ret_126 is None and indicator is not None and indicator.return_6m is not None:
        ret_126 = float(indicator.return_6m)

    return StockFeature(
        stock_id=stock.id,
        sector=sector_label(stock),
        industries=tuple(industry_labels(stock)),
        parent_sector=sector_label(stock),
        market_cap=mcap,
        return_5d=_period_return(closes, 5),
        return_10d=_period_return(closes, 10),
        return_21d=ret_21,
        return_63d=ret_63,
        return_126d=ret_126,
        close=close,
        ma_21=ma_21,
        ma_50=ma_50,
        ma_200=ma_200,
        above_ma_21=above_21,
        above_ma_50=above_50,
        above_ma_200=above_200,
        ma21_gt_ma50=ma21_gt,
        ma50_gt_ma200=ma50_gt,
        ma21_slope_up=None if ma21_now is None or ma21_prev is None else ma21_now > ma21_prev,
        ma50_slope_up=None if ma50_now is None or ma50_prev is None else ma50_now > ma50_prev,
        distance_from_52w_high=dist_52,
        at_20d_high=at_20,
        at_50d_high=at_50,
        at_52w_high=at_52,
        volume_ratio=vol_ratio,
        price_up_volume_up=price_up and vol_up,
        turnover_5d=turnover(5),
        turnover_20d=turnover(20),
    )


def load_stock_features(session: Session, as_of: date) -> list[StockFeature]:
    stocks = session.scalars(select(Stock).where(Stock.is_active.is_(True))).all()
    indicators = _load_indicators(session, as_of)
    prices = _load_price_series(session, as_of)
    mcaps = _load_mcaps(session, as_of)
    features: list[StockFeature] = []
    for stock in stocks:
        feat = _features_from_series(
            stock,
            indicators.get(stock.id),
            prices.get(stock.id, []),
            mcaps.get(stock.id),
        )
        if feat is None:
            continue
        features.append(feat)
    return features


def _group_features(
    features: Sequence[StockFeature],
    *,
    min_constituents: int,
) -> tuple[dict[str, list[StockFeature]], dict[str, list[StockFeature]], dict[str, str | None]]:
    sectors: dict[str, list[StockFeature]] = defaultdict(list)
    industries: dict[str, list[StockFeature]] = defaultdict(list)
    parents: dict[str, list[str]] = defaultdict(list)
    for feat in features:
        if feat.sector:
            sectors[feat.sector].append(feat)
        for name in feat.industries:
            industries[name].append(feat)
            if feat.parent_sector:
                parents[name].append(feat.parent_sector)

    sector_groups = {k: v for k, v in sectors.items() if len(v) >= min_constituents}
    industry_groups = {k: v for k, v in industries.items() if len(v) >= min_constituents}
    parent_map: dict[str, str | None] = {}
    for name, votes in parents.items():
        parent_map[name] = Counter(votes).most_common(1)[0][0] if votes else None
    return sector_groups, industry_groups, parent_map


def _prior_map(
    session: Session,
    *,
    as_of: date,
    model,
    name_attr: str,
    offset: int,
) -> dict[str, PriorScores]:
    date_col = model.metric_date
    dates = _trading_dates_before(session, as_of, model=model, date_col=date_col, n=offset)
    if len(dates) < offset:
        return {}
    target = dates[offset - 1]
    rows = session.scalars(select(model).where(date_col == target)).all()
    out: dict[str, PriorScores] = {}
    for row in rows:
        name = getattr(row, name_attr)
        strength = _f(row.sector_score) if hasattr(row, "sector_score") else _f(row.industry_score)
        out[name] = PriorScores(
            strength_score=strength,
            rs_score=_f(row.rs_score),
            momentum_score=_f(row.momentum_score),
            breadth_score=_f(row.breadth_score),
            volume_score=_f(row.volume_score),
            breakout_score=_f(row.breakout_score),
            trend_score=_f(getattr(row, "trend_score", None)),
        )
    return out


def _upsert_sector(session: Session, as_of: date, row: ScoredGroup) -> None:
    existing = session.scalar(
        select(SectorDailyMetrics).where(
            SectorDailyMetrics.sector_name == row.name,
            SectorDailyMetrics.metric_date == as_of,
        )
    )
    payload = dict(
        rs_score=row.rs_score,
        momentum_score=row.momentum_score,
        breadth_score=row.breadth_score,
        volume_score=row.volume_score,
        breakout_score=row.breakout_score,
        trend_score=row.trend_score,
        sector_score=row.strength_score,
        emerging_score=row.emerging_score,
        pct_above_21dma=row.pct_above_21,
        pct_above_50dma=row.pct_above_50,
        pct_above_200dma=row.pct_above_200,
        pct_positive_5d=row.pct_positive_5d,
        pct_positive_21d=row.pct_positive_21d,
        pct_breakout_20d=row.pct_breakout_20d,
        pct_breakout_50d=row.pct_breakout_50d,
        pct_breakout_52w=row.pct_breakout_52w,
        pct_price_up_volume_up=row.pct_price_up_volume_up,
        pct_volume_gt_1_5x=row.pct_volume_gt_1_5x,
        volume_expansion=row.volume_expansion,
        return_1m=row.return_1m,
        return_3m=row.return_3m,
        return_3m_cw=row.return_3m_cw,
        return_3m_ew=row.return_3m_ew,
        score_change_1d=row.score_change_1d,
        score_change_5d=row.score_change_5d,
        score_change_21d=row.score_change_21d,
        rs_change_5d=row.rs_change_5d,
        momentum_change_5d=row.momentum_change_5d,
        breadth_change_5d=row.breadth_change_5d,
        rotation_state=row.rotation_state,
        constituent_count=row.constituent_count,
        alerts=row.alerts or None,
    )
    if existing is None:
        session.add(SectorDailyMetrics(sector_name=row.name, metric_date=as_of, **payload))
        return
    for key, value in payload.items():
        setattr(existing, key, value)


def _upsert_industry(session: Session, as_of: date, row: ScoredGroup) -> None:
    existing = session.scalar(
        select(IndustryDailyMetrics).where(
            IndustryDailyMetrics.industry_name == row.name,
            IndustryDailyMetrics.metric_date == as_of,
        )
    )
    payload = dict(
        parent_sector=row.parent_sector,
        rs_score=row.rs_score,
        momentum_score=row.momentum_score,
        breadth_score=row.breadth_score,
        volume_score=row.volume_score,
        breakout_score=row.breakout_score,
        industry_score=row.strength_score,
        emerging_score=row.emerging_score,
        pct_above_21dma=row.pct_above_21,
        pct_above_50dma=row.pct_above_50,
        pct_above_200dma=row.pct_above_200,
        pct_positive_5d=row.pct_positive_5d,
        pct_positive_21d=row.pct_positive_21d,
        pct_breakout_20d=row.pct_breakout_20d,
        pct_breakout_50d=row.pct_breakout_50d,
        pct_breakout_52w=row.pct_breakout_52w,
        pct_price_up_volume_up=row.pct_price_up_volume_up,
        pct_volume_gt_1_5x=row.pct_volume_gt_1_5x,
        volume_expansion=row.volume_expansion,
        return_1m=row.return_1m,
        return_3m=row.return_3m,
        return_3m_cw=row.return_3m_cw,
        return_3m_ew=row.return_3m_ew,
        score_change_1d=row.score_change_1d,
        score_change_5d=row.score_change_5d,
        score_change_21d=row.score_change_21d,
        rs_change_5d=row.rs_change_5d,
        momentum_change_5d=row.momentum_change_5d,
        breadth_change_5d=row.breadth_change_5d,
        rotation_state=row.rotation_state,
        constituent_count=row.constituent_count,
        alerts=row.alerts or None,
    )
    if existing is None:
        session.add(IndustryDailyMetrics(industry_name=row.name, metric_date=as_of, **payload))
        return
    for key, value in payload.items():
        setattr(existing, key, value)


def persist_daily_metrics(
    session: Session,
    as_of: date,
    *,
    min_constituents: int = DEFAULT_MIN_CONSTITUENTS,
    commit: bool = True,
) -> dict[str, Any]:
    features = load_stock_features(session, as_of)
    sector_groups, industry_groups, parent_map = _group_features(
        features, min_constituents=min_constituents
    )
    bench = load_benchmark_returns(session, as_of)

    sector_aggs = [
        aggregate_features(name, members, kind="sector")
        for name, members in sector_groups.items()
    ]
    industry_aggs = [
        aggregate_features(name, members, kind="industry", parent_sector=parent_map.get(name))
        for name, members in industry_groups.items()
    ]

    sectors = score_groups(
        sector_aggs,
        kind="sector",
        benchmark=bench,
        prior_1d=_prior_map(session, as_of=as_of, model=SectorDailyMetrics, name_attr="sector_name", offset=1),
        prior_5d=_prior_map(session, as_of=as_of, model=SectorDailyMetrics, name_attr="sector_name", offset=5),
        prior_21d=_prior_map(session, as_of=as_of, model=SectorDailyMetrics, name_attr="sector_name", offset=21),
    )
    industries = score_groups(
        industry_aggs,
        kind="industry",
        benchmark=bench,
        prior_1d=_prior_map(session, as_of=as_of, model=IndustryDailyMetrics, name_attr="industry_name", offset=1),
        prior_5d=_prior_map(session, as_of=as_of, model=IndustryDailyMetrics, name_attr="industry_name", offset=5),
        prior_21d=_prior_map(session, as_of=as_of, model=IndustryDailyMetrics, name_attr="industry_name", offset=21),
    )
    for row in sectors:
        _upsert_sector(session, as_of, row)
    for row in industries:
        _upsert_industry(session, as_of, row)
    if commit:
        session.commit()
    return {"sectors": len(sectors), "industries": len(industries), "as_of": as_of}


def indicator_dates(session: Session, *, limit: int = BACKFILL_DATES) -> list[date]:
    rows = session.scalars(
        select(StockIndicator.calculation_date)
        .distinct()
        .order_by(StockIndicator.calculation_date.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


def backfill_daily_metrics(
    session: Session,
    *,
    lookback_dates: int = BACKFILL_DATES,
    min_constituents: int = DEFAULT_MIN_CONSTITUENTS,
) -> dict[str, Any]:
    dates = indicator_dates(session, limit=lookback_dates)
    written = 0
    for as_of in dates:
        persist_daily_metrics(session, as_of, min_constituents=min_constituents, commit=True)
        written += 1
    return {"dates": written, "first": dates[0] if dates else None, "last": dates[-1] if dates else None}


def latest_metrics_date(session: Session) -> date | None:
    return session.scalar(select(func.max(SectorDailyMetrics.metric_date)))


def distinct_metric_dates(session: Session) -> int:
    return int(session.scalar(select(func.count(func.distinct(SectorDailyMetrics.metric_date)))) or 0)


def persist_after_indicators(session: Session, as_of: date | None = None) -> dict[str, Any] | None:
    """Hook from calculate_all: backfill if history is thin, else write today's row."""
    as_of = as_of or session.scalar(select(func.max(StockIndicator.calculation_date))) or date.today()
    try:
        if distinct_metric_dates(session) < 6:
            return backfill_daily_metrics(session)
        return persist_daily_metrics(session, as_of)
    except Exception:  # noqa: BLE001 — never fail the indicator job
        logger.exception("sector daily metrics persist failed for %s", as_of)
        session.rollback()
        return None


def ensure_latest_metrics(session: Session, *, min_constituents: int = DEFAULT_MIN_CONSTITUENTS) -> date | None:
    latest = latest_metrics_date(session)
    if latest is not None:
        return latest
    as_of = session.scalar(select(func.max(StockIndicator.calculation_date)))
    if as_of is None:
        return None
    persist_daily_metrics(session, as_of, min_constituents=min_constituents)
    return as_of
