"""Trade DB → MarketPlatform response shapes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from database.models import (
    Stock,
    StockFundamental,
    StockIndicator,
    StockIndexMembership,
    StockPrice,
    StockSnapshot,
)
from database.repository import get_stock_by_symbol, latest_screener_query
from ingestion.screener_in.fundamentals_api import (
    fundamentals_from_db,
    latest_fundamental,
    ownership_snapshot,
    period_history,
)
from market_platform.schemas.stocks import (
    FundamentalMetricsSnapshot,
    FundamentalsSnapshot,
    OwnershipSnapshot,
    PriceBar,
    Quote,
    ScoreCard,
    StockAnalysisResponse,
    StockAnalysisRow,
    StockDetail,
    StockListResponse,
    StockSummary,
    TechnicalsSnapshot,
)


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(float(value)))
    except (TypeError, ValueError):
        return None


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_change(ltp: float | None, prev: float | None) -> float | None:
    if ltp is None or prev is None or prev == 0:
        return None
    return round(((ltp - prev) / prev) * 100.0, 4)


def _ret_pct(fraction: Any) -> float | None:
    value = _f(fraction)
    if value is None:
        return None
    return round(value * 100.0, 4)


def _nullable_number(value: Any) -> tuple[bool, float]:
    parsed = _f(value)
    return (parsed is None, parsed if parsed is not None else 0.0)


def _sort_analysis_rows(
    items: list[StockAnalysisRow],
    *,
    sort_by: str,
    sort_dir: str,
) -> list[StockAnalysisRow]:
    reverse = sort_dir.lower() != "asc"
    sort_aliases = {
        "score": "trend_score",
        "distance": "distance_from_52w_high",
        "return_3m": "return_3m_pct",
        "return_6m": "return_6m_pct",
        "return_1m": "return_1m_pct",
        "momentum": "momentum_score",
        "acceleration": "momentum_acceleration",
        "avg_volume_1w": "avg_volume_1w",
    }
    sort_by = sort_aliases.get(sort_by, sort_by)
    key_map = {
        "symbol": lambda r: r.symbol,
        "ltp": lambda r: _nullable_number(r.ltp),
        "change_pct": lambda r: _nullable_number(r.change_pct),
        "sma_3": lambda r: _nullable_number(r.sma_3),
        "sma_7": lambda r: _nullable_number(r.sma_7),
        "sma_21": lambda r: _nullable_number(r.sma_21),
        "sma_50": lambda r: _nullable_number(r.sma_50),
        "sma_200": lambda r: _nullable_number(r.sma_200),
        "volume_ratio": lambda r: _nullable_number(r.volume_ratio),
        "avg_volume_1w": lambda r: _nullable_number(r.avg_volume_1w),
        "return_1m_pct": lambda r: _nullable_number(r.return_1m_pct),
        "return_3m_pct": lambda r: _nullable_number(r.return_3m_pct),
        "return_6m_pct": lambda r: _nullable_number(r.return_6m_pct),
        "distance_from_52w_high": lambda r: _nullable_number(r.distance_from_52w_high),
        "pe": lambda r: _nullable_number(r.pe),
        "eps": lambda r: _nullable_number(r.eps),
        "market_cap": lambda r: _nullable_number(r.market_cap),
        "trend_score": lambda r: _nullable_number(r.trend_score),
        "company_strength": lambda r: _nullable_number(r.company_strength),
        "overall": lambda r: _nullable_number(r.overall),
        "momentum_score": lambda r: _nullable_number(r.momentum_score),
        "momentum_acceleration": lambda r: _nullable_number(r.momentum_acceleration),
        "return_score": lambda r: _nullable_number(r.return_score),
        "dma_score": lambda r: _nullable_number(r.dma_score),
        "volume_score": lambda r: _nullable_number(r.volume_score),
        "result_score": lambda r: _nullable_number(r.result_score),
        "sector": lambda r: (r.sector or "").lower(),
        "industry": lambda r: (r.industry or "").lower(),
    }
    key_func = key_map.get(sort_by, key_map["symbol"])
    sorted_items = sorted(items, key=key_func, reverse=reverse)
    if sort_by in {"symbol", "sector", "industry"} or not reverse:
        return sorted_items

    present = [item for item in sorted_items if not key_func(item)[0]]
    missing = [item for item in sorted_items if key_func(item)[0]]
    return present + missing


def list_stocks(
    session: Session,
    *,
    q: str | None = None,
    exchange: str | None = None,
    symbols: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> StockListResponse:
    filters = [Stock.is_active.is_(True)]
    if exchange:
        filters.append(Stock.exchange == exchange.upper())
    if symbols:
        cleaned = [s.strip().upper() for s in symbols if s and s.strip()]
        if cleaned:
            filters.append(func.upper(Stock.symbol).in_(cleaned))
            # Prefer exact symbol set over fuzzy q when both provided
            limit = max(limit, len(cleaned))
            offset = 0
    if q and not symbols:
        needle = f"%{q.strip().upper()}%"
        filters.append(
            or_(func.upper(Stock.symbol).like(needle), func.upper(Stock.company_name).like(needle))
        )
    total = session.scalar(select(func.count()).select_from(Stock).where(*filters)) or 0
    stocks = session.scalars(
        select(Stock).where(*filters).order_by(Stock.symbol).offset(offset).limit(limit)
    ).all()
    if not stocks:
        return StockListResponse(items=[], total=total)

    stock_ids = [s.id for s in stocks]
    # Latest snapshot per stock (one query, take first row per stock_id)
    snap_rows = session.scalars(
        select(StockSnapshot)
        .where(StockSnapshot.stock_id.in_(stock_ids))
        .order_by(StockSnapshot.stock_id, desc(StockSnapshot.snapshot_date))
    ).all()
    snap_by_id: dict[int, StockSnapshot] = {}
    for snap in snap_rows:
        if snap.stock_id not in snap_by_id:
            snap_by_id[snap.stock_id] = snap

    priced_ids = {
        int(sid)
        for sid in session.scalars(
            select(StockPrice.stock_id).where(StockPrice.stock_id.in_(stock_ids)).distinct()
        ).all()
    }

    items: list[StockSummary] = []
    for stock in stocks:
        snap = snap_by_id.get(stock.id)
        ltp = _f(snap.ltp) if snap else None
        prev = _f(snap.prev_close) if snap else None
        items.append(
            StockSummary(
                id=stock.id,
                symbol=stock.symbol,
                company_name=stock.company_name or stock.symbol,
                exchange=stock.exchange or "NSE",
                sector=stock.sector,
                industry=stock.industry,
                market_cap=_dec(snap.market_cap) if snap else None,
                last_price=_dec(ltp),
                change_pct=_pct_change(ltp, prev),
                has_prices=stock.id in priced_ids,
            )
        )
    return StockListResponse(items=items, total=total)


def get_stock_detail(
    session: Session,
    symbol: str,
    *,
    exchange: str | None = None,
    price_limit: int = 730,
) -> StockDetail | None:
    stock = get_stock_by_symbol(session, symbol)
    if stock is None:
        return None
    if exchange and (stock.exchange or "NSE").upper() != exchange.upper():
        return None
    indicator = session.scalar(
        select(StockIndicator)
        .where(StockIndicator.stock_id == stock.id)
        .order_by(desc(StockIndicator.calculation_date))
        .limit(1)
    )
    snapshot = session.scalar(
        select(StockSnapshot)
        .where(StockSnapshot.stock_id == stock.id)
        .order_by(desc(StockSnapshot.snapshot_date))
        .limit(1)
    )
    prices = session.scalars(
        select(StockPrice)
        .where(StockPrice.stock_id == stock.id)
        .order_by(desc(StockPrice.price_date))
        .limit(max(50, min(price_limit, 1000)))
    ).all()
    price_bars: list[PriceBar] = []
    for price in reversed(list(prices)):
        if price.close is None:
            continue
        close = float(price.close)
        open_ = float(price.open) if price.open is not None else close
        high = float(price.high) if price.high is not None else close
        low = float(price.low) if price.low is not None else close
        price_bars.append(
            PriceBar(
                date=price.price_date,
                open=Decimal(str(open_)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=int(price.volume) if price.volume is not None else None,
            )
        )

    ltp = _f(snapshot.ltp) if snapshot else None
    prev = _f(snapshot.prev_close) if snapshot else None
    # Approx 1M / 1Y returns from stored closes when available.
    closes = [float(p.close) for p in price_bars if p.close is not None]
    return_1m = None
    return_1y = None
    if len(closes) > 21 and closes[-22]:
        return_1m = round(((closes[-1] / closes[-22]) - 1.0) * 100.0, 4)
    if len(closes) > 252 and closes[-253]:
        return_1y = round(((closes[-1] / closes[-253]) - 1.0) * 100.0, 4)

    if ltp is None and price_bars:
        ltp = float(price_bars[-1].close)
        if prev is None and len(price_bars) >= 2:
            prev = float(price_bars[-2].close)
    change = None
    if ltp is not None and prev is not None:
        change = ltp - prev
    ma3 = _f(indicator.ma_3) if indicator else None
    ma7 = _f(indicator.ma_7) if indicator else None
    ma21 = _f(indicator.ma_21) if indicator else None
    ma50 = _f(indicator.ma_50) if indicator else None
    ma200 = _f(indicator.ma_200) if indicator else None

    def ma_signal(price: float | None, ma: float | None) -> str | None:
        if price is None or ma is None:
            return None
        return "Bullish" if price >= ma else "Bearish"

    as_of = indicator.calculation_date if indicator else (snapshot.snapshot_date if snapshot else None)
    score = indicator.trend_score if indicator else None
    trend_strength = Decimal(str(round((score or 0) * 20, 1))) if score is not None else None
    mom_score = _dec(_f(indicator.momentum_score)) if indicator else None
    # Prefer V1 momentum score for overall / momentum pillars when available
    momentum = mom_score if mom_score is not None else trend_strength

    from market_platform.services.sectors import industry_strength_by_stock_id

    strength_map = industry_strength_by_stock_id(session)
    sector_s = _dec(strength_map.get(stock.id))

    fund_row = latest_fundamental(session, stock.id)
    fundamentals, fundamental_metrics = fundamentals_from_db(
        session,
        stock.id,
        sheet_eps=snapshot.eps if snapshot else None,
        sheet_pe=snapshot.pe if snapshot else None,
    )
    if fundamental_metrics.as_of is None:
        fundamental_metrics.as_of = as_of
    ownership = ownership_snapshot(session, stock.id)
    quarterly_history = period_history(session, stock.id, "quarters", limit=12)
    annual_history = period_history(session, stock.id, "profit-loss", limit=12)

    ma20 = _f(indicator.ma_20) if indicator else None
    market_cap = _f(snapshot.market_cap) if snapshot else None
    if market_cap is None and fund_row is not None:
        market_cap = _f(fund_row.market_cap)
    pe = _f(snapshot.pe) if snapshot else None
    if pe is None and fund_row is not None:
        pe = _f(fund_row.pe)
    eps = _f(snapshot.eps) if snapshot else None
    if eps is None and fund_row is not None:
        eps = _f(fund_row.eps)
    volume = int(snapshot.volume) if snapshot and snapshot.volume is not None else None
    if volume is None and prices:
        for price in prices:
            if price.volume is not None:
                volume = int(price.volume)
                break
    avg_vol_3m = _f(snapshot.avg_volume_3m) if snapshot else None
    avg_vol_6m = _f(snapshot.avg_volume_6m) if snapshot else None
    avg_vol_1y = _f(snapshot.avg_volume_1y) if snapshot else None
    avg_vol_20 = _f(indicator.volume_avg_20) if indicator else None
    if avg_vol_3m is None:
        avg_vol_3m = avg_vol_20

    memb_rows = session.scalars(
        select(StockIndexMembership)
        .where(StockIndexMembership.stock_id == stock.id)
        .order_by(StockIndexMembership.category, StockIndexMembership.index_name)
    ).all()
    index_memberships = [m.index_name for m in memb_rows]
    industries_set: set[str] = set()
    if stock.industry:
        industries_set.add(stock.industry.strip())
    for m in memb_rows:
        if m.industry and m.industry.strip():
            industries_set.add(m.industry.strip())
    industries = sorted(industries_set)

    return StockDetail(
        id=stock.id,
        symbol=stock.symbol,
        company_name=stock.company_name or stock.symbol,
        exchange=stock.exchange or "NSE",
        isin=stock.isin,
        sector=stock.sector,
        industry=stock.industry,
        industries=industries,
        index_memberships=index_memberships,
        market_cap=_dec(market_cap),
        listing_date=None,
        status="active" if stock.is_active else "inactive",
        quote=Quote(
            price=_dec(ltp),
            previous_close=_dec(prev),
            change=_dec(change),
            change_pct=_pct_change(ltp, prev),
            as_of=snapshot.snapshot_date if snapshot else (price_bars[-1].date if price_bars else None),
            open=_dec(prev),
            high=_dec(snapshot.day_high) if snapshot else None,
            low=None,
            volume=volume,
        ),
        scores=ScoreCard(
            as_of=as_of,
            overall=momentum,
            momentum=momentum,
            technical=trend_strength,
            sector_strength=sector_s,
            industry_strength=sector_s,
            return_score=_dec(_f(indicator.return_score)) if indicator else None,
            dma_score=_dec(_f(indicator.dma_score)) if indicator else None,
            volume_score=_dec(_f(indicator.volume_score)) if indicator else None,
            result_score=_dec(_f(indicator.result_score)) if indicator else None,
            momentum_acceleration=_dec(_f(indicator.momentum_acceleration)) if indicator else None,
            momentum_category=indicator.momentum_category if indicator else None,
            source="momentum_v1" if mom_score is not None else ("trade_trend_score" if score is not None else "unavailable"),
        ),
        fundamentals=fundamentals,
        annual_fundamentals=fundamentals,
        fundamental_metrics=fundamental_metrics,
        quarterly_history=quarterly_history,
        annual_history=annual_history,
        ownership=ownership,
        technicals=TechnicalsSnapshot(
            sma_3=_dec(ma3),
            sma_7=_dec(ma7),
            sma_20=_dec(ma20),
            sma_21=_dec(ma21),
            sma_50=_dec(ma50),
            sma_200=_dec(ma200),
            sma_21_signal=ma_signal(ltp, ma21),
            sma_50_signal=ma_signal(ltp, ma50),
            sma_200_signal=ma_signal(ltp, ma200),
            rsi_14=None,
            high_52w=_dec(snapshot.high_52_week) if snapshot else None,
            low_52w=_dec(snapshot.low_52_week) if snapshot else None,
            distance_from_52w_high_pct=_f(indicator.distance_from_52w_high) if indicator else None,
            return_1m_pct=_ret_pct(indicator.return_1m) if indicator and indicator.return_1m is not None else return_1m,
            return_3m_pct=_ret_pct(indicator.return_3m) if indicator else None,
            return_6m_pct=_ret_pct(indicator.return_6m) if indicator else None,
            return_1y_pct=_ret_pct(indicator.return_12m) if indicator and indicator.return_12m is not None else return_1y,
            trend=indicator.trend if indicator else None,
            trend_score=score,
            crossover_3_7=indicator.crossover_3_7 if indicator else None,
            above_ma_21=indicator.above_ma_21 if indicator else None,
            ma21_gt_ma50=indicator.ma21_gt_ma50 if indicator else None,
            above_ma_200=indicator.above_ma_200 if indicator else None,
            golden_cross=indicator.golden_cross if indicator else None,
            pe=_dec(pe),
            eps=_dec(eps),
            day_high=_dec(snapshot.day_high) if snapshot else None,
            prev_close=_dec(prev),
            avg_volume_20=avg_vol_20,
            avg_volume_3m=avg_vol_3m,
            avg_volume_6m=avg_vol_6m,
            avg_volume_1y=avg_vol_1y,
            volume_ratio=_f(indicator.volume_ratio) if indicator else None,
            distance_20_dma=_f(indicator.distance_20_dma) if indicator else None,
            distance_50_dma=_f(indicator.distance_50_dma) if indicator else None,
            distance_200_dma=_f(indicator.distance_200_dma) if indicator else None,
            momentum_score=_f(indicator.momentum_score) if indicator else None,
            momentum_acceleration=_f(indicator.momentum_acceleration) if indicator else None,
            momentum_category=indicator.momentum_category if indicator else None,
            return_score=_f(indicator.return_score) if indicator else None,
            dma_score=_f(indicator.dma_score) if indicator else None,
            volume_score=_f(indicator.volume_score) if indicator else None,
            result_score=_f(indicator.result_score) if indicator else None,
        ),
        prices=price_bars,
    )


def _analysis_row(
    stock: Stock,
    indicator: StockIndicator,
    snapshot: StockSnapshot | None,
    *,
    sector_strength: float | None = None,
    price_fallback: tuple[float | None, float | None] | None = None,
    fund_fallback: StockFundamental | None = None,
    volume_fallback: int | None = None,
) -> StockAnalysisRow:
    ltp = _f(snapshot.ltp) if snapshot else None
    prev = _f(snapshot.prev_close) if snapshot else None
    # Many small-caps have Yahoo OHLC (indicators) but no sheet snapshot — use last closes.
    if ltp is None and price_fallback:
        ltp = price_fallback[0]
        if prev is None:
            prev = price_fallback[1]
    ma3 = _f(indicator.ma_3)
    ma7 = _f(indicator.ma_7)
    ma20 = _f(indicator.ma_20)
    ma21 = _f(indicator.ma_21)
    ma50 = _f(indicator.ma_50)
    ma200 = _f(indicator.ma_200)
    volume = int(snapshot.volume) if snapshot and snapshot.volume is not None else None
    if volume is None and volume_fallback is not None:
        volume = volume_fallback
    avg_vol_20 = _f(indicator.volume_avg_20)
    avg_vol_1w = _f(getattr(indicator, "volume_avg_5", None))
    avg_vol_3m = _f(snapshot.avg_volume_3m) if snapshot else None
    avg_vol_6m = _f(snapshot.avg_volume_6m) if snapshot else None
    avg_vol_1y = _f(snapshot.avg_volume_1y) if snapshot else None
    if avg_vol_3m is None:
        avg_vol_3m = avg_vol_20
    if avg_vol_6m is None:
        avg_vol_6m = avg_vol_20
    if avg_vol_1y is None:
        avg_vol_1y = avg_vol_20
    volume_ratio = _f(indicator.volume_ratio)
    if volume_ratio is None and volume is not None and avg_vol_20 and avg_vol_20 > 0:
        volume_ratio = round(volume / avg_vol_20, 4)
    elif volume_ratio is None and volume is not None and avg_vol_3m and avg_vol_3m > 0:
        volume_ratio = round(volume / avg_vol_3m, 4)
    volume_gainer = None
    if (
        avg_vol_1w is not None
        and avg_vol_3m is not None
        and avg_vol_6m is not None
        and avg_vol_1y is not None
    ):
        volume_gainer = bool(
            avg_vol_1w > avg_vol_3m and avg_vol_1w > avg_vol_6m and avg_vol_1w > avg_vol_1y
        )
    pe = _f(snapshot.pe) if snapshot else None
    if pe is None and fund_fallback is not None:
        pe = _f(fund_fallback.pe)
    eps = _f(snapshot.eps) if snapshot else None
    if eps is None and fund_fallback is not None:
        eps = _f(fund_fallback.eps)
    market_cap = _f(snapshot.market_cap) if snapshot else None
    if market_cap is None and fund_fallback is not None:
        market_cap = _f(fund_fallback.market_cap)
    golden = indicator.golden_cross
    above_stack = None
    if ltp is not None and ma50 is not None and ma200 is not None:
        above_stack = bool(ltp > ma50 > ma200)
    score = indicator.trend_score
    strength = Decimal(str(round((score or 0) * 20, 1))) if score is not None else None
    mom = _dec(_f(indicator.momentum_score))
    sec_s = _dec(sector_strength)
    return StockAnalysisRow(
        id=stock.id,
        symbol=stock.symbol,
        company_name=stock.company_name or stock.symbol,
        exchange=stock.exchange or "NSE",
        sector=stock.sector,
        industry=stock.industry,
        ltp=_dec(ltp),
        change_pct=_pct_change(ltp, prev),
        sma_3=_dec(ma3),
        sma_7=_dec(ma7),
        sma_20=_dec(ma20),
        sma_21=_dec(ma21),
        sma_50=_dec(ma50),
        sma_200=_dec(ma200),
        price_above_50_above_200=above_stack,
        sma_50_above_200=golden if golden is not None else (bool(ma50 > ma200) if ma50 and ma200 else None),
        crossover_3_7=indicator.crossover_3_7,
        above_ma_21=indicator.above_ma_21,
        ma21_gt_ma50=indicator.ma21_gt_ma50,
        above_ma_200=indicator.above_ma_200,
        volume=volume,
        avg_volume_20=avg_vol_20 if avg_vol_20 is not None else avg_vol_3m,
        avg_volume_1w=avg_vol_1w,
        avg_volume_3m=avg_vol_3m,
        avg_volume_6m=avg_vol_6m,
        avg_volume_1y=avg_vol_1y,
        volume_ratio=volume_ratio,
        volume_mover=bool(volume_ratio is not None and volume_ratio >= 1.5),
        volume_gainer=volume_gainer,
        return_1m_pct=_ret_pct(indicator.return_1m),
        return_3m_pct=_ret_pct(indicator.return_3m),
        return_6m_pct=_ret_pct(indicator.return_6m),
        return_12m_pct=_ret_pct(indicator.return_12m),
        distance_from_52w_high=_f(indicator.distance_from_52w_high),
        pe=_dec(pe),
        eps=_dec(eps),
        market_cap=_dec(market_cap),
        trend=indicator.trend,
        trend_score=score,
        company_strength=strength,
        company_strength_source="trade_trend_score" if strength is not None else "unavailable",
        overall=mom if mom is not None else strength,
        sector_strength=sec_s,
        industry_strength=sec_s,
        return_score=_dec(_f(indicator.return_score)),
        dma_score=_dec(_f(indicator.dma_score)),
        volume_score=_dec(_f(indicator.volume_score)),
        result_score=_dec(_f(indicator.result_score)),
        momentum_score=mom,
        momentum_acceleration=_dec(_f(indicator.momentum_acceleration)),
        momentum_category=indicator.momentum_category,
        as_of=indicator.calculation_date,
    )


def _row_as_screen_dict(row: StockAnalysisRow) -> dict:
    """Shape compatible with Trade indicators.breakout SCREENERS."""
    return {
        "symbol": row.symbol,
        "ltp": float(row.ltp) if row.ltp is not None else None,
        "ma_21": float(row.sma_21) if row.sma_21 is not None else None,
        "ma_50": float(row.sma_50) if row.sma_50 is not None else None,
        "ma_200": float(row.sma_200) if row.sma_200 is not None else None,
        "crossover_3_7": row.crossover_3_7,
        "above_ma_21": row.above_ma_21,
        "ma21_gt_ma50": row.ma21_gt_ma50,
        "above_ma_200": row.above_ma_200,
        "golden_cross": row.sma_50_above_200,
        "distance_from_52w_high": row.distance_from_52w_high,
        "trend": row.trend,
        "trend_score": row.trend_score,
    }


def _avg_volume_1w_by_stock_id(session: Session, stock_ids: list[int]) -> dict[int, float]:
    """Mean volume over the last 5 trading sessions with volume > 0 (1 week)."""
    if not stock_ids:
        return {}

    # Window function works on SQLite 3.25+ and Postgres.
    ranked = (
        select(
            StockPrice.stock_id.label("stock_id"),
            StockPrice.volume.label("volume"),
            func.row_number()
            .over(partition_by=StockPrice.stock_id, order_by=StockPrice.price_date.desc())
            .label("rn"),
        )
        .where(
            StockPrice.stock_id.in_(stock_ids),
            StockPrice.volume.is_not(None),
            StockPrice.volume > 0,
        )
        .subquery()
    )
    rows = session.execute(
        select(ranked.c.stock_id, func.avg(ranked.c.volume))
        .where(ranked.c.rn <= 5)
        .group_by(ranked.c.stock_id)
    ).all()
    out: dict[int, float] = {}
    for stock_id, avg in rows:
        if avg is None:
            continue
        out[int(stock_id)] = float(avg)
    return out


def _latest_close_pair_by_stock_id(
    session: Session, stock_ids: list[int]
) -> dict[int, tuple[float | None, float | None]]:
    """stock_id → (latest close, previous close) from stock_prices."""
    if not stock_ids:
        return {}
    ranked = (
        select(
            StockPrice.stock_id.label("stock_id"),
            StockPrice.close.label("close"),
            func.row_number()
            .over(partition_by=StockPrice.stock_id, order_by=StockPrice.price_date.desc())
            .label("rn"),
        )
        .where(
            StockPrice.stock_id.in_(stock_ids),
            StockPrice.close.is_not(None),
        )
        .subquery()
    )
    rows = session.execute(
        select(ranked.c.stock_id, ranked.c.close, ranked.c.rn).where(ranked.c.rn <= 2)
    ).all()
    latest: dict[int, float | None] = {}
    prev: dict[int, float | None] = {}
    for stock_id, close, rn in rows:
        sid = int(stock_id)
        val = _f(close)
        if int(rn) == 1:
            latest[sid] = val
        elif int(rn) == 2:
            prev[sid] = val
    return {sid: (latest.get(sid), prev.get(sid)) for sid in latest}


def _latest_volume_by_stock_id(session: Session, stock_ids: list[int]) -> dict[int, int]:
    """stock_id → latest non-null volume from stock_prices."""
    if not stock_ids:
        return {}
    ranked = (
        select(
            StockPrice.stock_id.label("stock_id"),
            StockPrice.volume.label("volume"),
            func.row_number()
            .over(partition_by=StockPrice.stock_id, order_by=StockPrice.price_date.desc())
            .label("rn"),
        )
        .where(
            StockPrice.stock_id.in_(stock_ids),
            StockPrice.volume.is_not(None),
        )
        .subquery()
    )
    rows = session.execute(
        select(ranked.c.stock_id, ranked.c.volume).where(ranked.c.rn == 1)
    ).all()
    out: dict[int, int] = {}
    for stock_id, volume in rows:
        if volume is None:
            continue
        out[int(stock_id)] = int(volume)
    return out


def _fundamentals_by_stock_id(
    session: Session, stock_ids: list[int]
) -> dict[int, StockFundamental]:
    """Latest StockFundamental row per stock_id."""
    if not stock_ids:
        return {}
    fund_by_id: dict[int, StockFundamental] = {}
    for fund in session.scalars(
        select(StockFundamental).where(StockFundamental.stock_id.in_(stock_ids))
    ).all():
        prev = fund_by_id.get(fund.stock_id)
        if prev is None or (fund.as_of_date or date.min) >= (prev.as_of_date or date.min):
            fund_by_id[fund.stock_id] = fund
    return fund_by_id


def _with_volume_1w(row: StockAnalysisRow, avg_1w: float | None) -> StockAnalysisRow:
    data = row.model_dump()
    data["avg_volume_1w"] = avg_1w
    a3 = data.get("avg_volume_3m")
    a6 = data.get("avg_volume_6m")
    a1 = data.get("avg_volume_1y")
    if avg_1w is not None and a3 is not None and a6 is not None and a1 is not None:
        data["volume_gainer"] = bool(avg_1w > a3 and avg_1w > a6 and avg_1w > a1)
    else:
        data["volume_gainer"] = None
    return StockAnalysisRow(**data)


def list_stock_analysis(
    session: Session,
    *,
    q: str | None = None,
    exchange: str | None = None,
    price_above_50_above_200: bool | None = None,
    sma_50_above_200: bool | None = None,
    volume_mover: bool | None = None,
    volume_gainer: bool | None = None,
    min_return_1m: float | None = None,
    min_return_3m: float | None = None,
    min_return_6m: float | None = None,
    min_company_strength: float | None = None,
    min_momentum_score: float | None = None,
    min_momentum_acceleration: float | None = None,
    momentum_category: str | None = None,
    trend: str | None = None,
    min_score: int | None = None,
    sort_by: str = "symbol",
    sort_dir: str = "asc",
    limit: int = 50,
    offset: int = 0,
    scan_limit: int = 8000,
) -> tuple[list[StockAnalysisRow], int, int]:
    from indicators.breakout import SCREENERS
    from indicators.crossover import bullish_3_7_crossover
    from database.repository import get_previous_indicator

    rows = session.execute(latest_screener_query(session)).all()
    from market_platform.services.sectors import industry_strength_by_stock_id

    strength_map = industry_strength_by_stock_id(session)
    missing_ltp_ids = [
        int(stock.id)
        for stock, _indicator, snapshot in rows
        if snapshot is None or snapshot.ltp is None
    ]
    missing_vol_ids = [
        int(stock.id)
        for stock, _indicator, snapshot in rows
        if snapshot is None or snapshot.volume is None
    ]
    close_fallback = _latest_close_pair_by_stock_id(session, missing_ltp_ids)
    volume_fallback = _latest_volume_by_stock_id(session, missing_vol_ids)
    fund_by_id = _fundamentals_by_stock_id(session, [int(stock.id) for stock, _, _ in rows])

    items: list[StockAnalysisRow] = []
    fresh_flags: dict[str, bool] = {}
    for stock, indicator, snapshot in rows:
        if exchange and (stock.exchange or "NSE").upper() != exchange.upper():
            continue
        if q:
            needle = q.strip().upper()
            name = (stock.company_name or "").upper()
            if needle not in stock.symbol.upper() and needle not in name:
                continue
        row = _analysis_row(
            stock,
            indicator,
            snapshot,
            sector_strength=strength_map.get(stock.id),
            price_fallback=close_fallback.get(stock.id),
            fund_fallback=fund_by_id.get(stock.id),
            volume_fallback=volume_fallback.get(stock.id),
        )
        if price_above_50_above_200 is not None and row.price_above_50_above_200 is not price_above_50_above_200:
            if bool(row.price_above_50_above_200) != price_above_50_above_200:
                continue
        if sma_50_above_200 is not None and bool(row.sma_50_above_200) != sma_50_above_200:
            continue
        if volume_mover is not None and bool(row.volume_mover) != volume_mover:
            continue
        if min_return_1m is not None and (row.return_1m_pct is None or row.return_1m_pct < min_return_1m):
            continue
        if min_return_3m is not None and (row.return_3m_pct is None or row.return_3m_pct < min_return_3m):
            continue
        if min_return_6m is not None and (row.return_6m_pct is None or row.return_6m_pct < min_return_6m):
            continue
        strength = float(row.company_strength) if row.company_strength is not None else None
        if min_company_strength is not None and (strength is None or strength < min_company_strength):
            continue
        mom = float(row.momentum_score) if row.momentum_score is not None else None
        if min_momentum_score is not None and (mom is None or mom < min_momentum_score):
            continue
        accel = float(row.momentum_acceleration) if row.momentum_acceleration is not None else None
        if min_momentum_acceleration is not None and (accel is None or accel < min_momentum_acceleration):
            continue
        if momentum_category:
            cat = (row.momentum_category or "").strip().lower()
            want = momentum_category.strip().lower()
            if cat != want and cat.replace(" ", "-") != want.replace(" ", "-"):
                continue
        if min_score is not None and (row.trend_score or 0) < min_score:
            continue
        if trend == "fresh-uptrend":
            previous = get_previous_indicator(session, stock.id, indicator.calculation_date)
            fresh = bool(
                previous
                and bullish_3_7_crossover(previous.ma_3, previous.ma_7, indicator.ma_3, indicator.ma_7)
                and indicator.above_ma_21
            )
            fresh_flags[row.symbol] = fresh
            if not fresh:
                continue
        elif trend:
            screen = _row_as_screen_dict(row)
            if trend in SCREENERS:
                if not SCREENERS[trend](screen):
                    continue
            elif (row.trend or "").lower().replace(" ", "-") != trend:
                continue
        items.append(row)

    # Fill 1-week avg volume from price history when screening volume gainers.
    if volume_gainer is not None:
        avg_map = _avg_volume_1w_by_stock_id(session, [r.id for r in items])
        items = [
            _with_volume_1w(r, avg_map.get(r.id, r.avg_volume_1w)) for r in items
        ]
        items = [r for r in items if bool(r.volume_gainer) == volume_gainer]

    items = _sort_analysis_rows(items, sort_by=sort_by, sort_dir=sort_dir)
    scanned = min(len(items), scan_limit)
    items = items[:scan_limit]
    total = len(items)
    page = items[offset : offset + limit]
    return page, total, scanned
