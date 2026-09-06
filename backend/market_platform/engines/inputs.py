"""Strategy engine inputs loaded from Trade SQLite tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    MarketIndex,
    MarketIndexSnapshot,
    Stock,
    StockFundamental,
    StockIndicator,
    StockOwnership,
    StockPrice,
    StockSnapshot,
)
from database.repository import latest_closes, latest_screener_query
from market_platform.engines.base import fnum

# ETF fallbacks only if official index snapshots are missing.
MARKET_PROXY_SYMBOLS = ("NIFTYBEES", "MONIFTY500", "BANKBEES", "RELIANCE", "TCS", "HDFCBANK")
MARKET_INDEX_KEYS = ("NIFTY 50", "NIFTY BANK", "NIFTY 500")
PRICE_LOOKBACK_DAYS = 420


@dataclass
class BarPoint:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None


@dataclass
class StrategyInput:
    id: int
    symbol: str
    company_name: str
    exchange: str
    sector: str | None
    industry: str | None
    ltp: float | None
    change_pct: float | None
    sma_21: float | None
    sma_50: float | None
    sma_200: float | None
    price_above_50_above_200: bool | None
    sma_50_above_200: bool | None
    volume: int | None
    avg_volume_20: float | None
    volume_ratio: float | None
    volume_mover: bool | None
    return_1m_pct: float | None
    return_3m_pct: float | None
    return_6m_pct: float | None
    as_of: date | None
    revenue_growth_yoy: float | None = None
    pat_growth_yoy: float | None = None
    eps_cagr_3y: float | None = None
    revenue_cagr_3y: float | None = None
    roe: float | None = None
    debt_equity: float | None = None
    pe_ttm: float | None = None
    peg: float | None = None
    institutional_pct: float | None = None
    fii_pct: float | None = None
    dii_pct: float | None = None
    momentum: float | None = None
    overall: float | None = None
    growth: float | None = None
    sector_strength: float | None = None
    industry_strength: float | None = None
    sma_150: float | None = None
    sma_200_20d_ago: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    dist_from_52w_high_pct: float | None = None
    dist_from_52w_low_pct: float | None = None
    bars: list[BarPoint] = field(default_factory=list)


@dataclass
class MarketContext:
    label: str
    detail: str
    proxy_symbol: str | None
    price: Decimal | None
    change_pct: float | None
    advances: int
    declines: int
    new_highs: int
    new_lows: int
    uptrend: bool


def _f(value: Any) -> float | None:
    return fnum(value)


def _pct_change(ltp: float | None, prev: float | None) -> float | None:
    if ltp is None or prev is None or prev == 0:
        return None
    return round(((ltp - prev) / prev) * 100.0, 4)


def _frac_to_pct(value: float | None) -> float | None:
    """Convert stored fraction (0.25) to percent points (25) for strategy engines."""
    if value is None:
        return None
    # Values already in percent-point form (e.g. 25) pass through
    if abs(value) > 1.5:
        return float(value)
    return round(float(value) * 100.0, 4)


def _row_from_trade(
    stock: Stock,
    indicator: StockIndicator | None,
    snapshot: StockSnapshot | None,
    *,
    fundamental: StockFundamental | None = None,
    ownership: StockOwnership | None = None,
) -> StrategyInput:
    ltp = _f(snapshot.ltp) if snapshot else None
    prev = _f(snapshot.prev_close) if snapshot else None
    # Fallback LTP from closes when snapshot missing (price-only symbols)
    if ltp is None and indicator is not None:
        # Prefer last close via caller enrichment; leave None here if unknown
        pass
    ma21 = _f(indicator.ma_21) if indicator else None
    ma50 = _f(indicator.ma_50) if indicator else None
    ma200 = _f(indicator.ma_200) if indicator else None
    volume = int(snapshot.volume) if snapshot and snapshot.volume is not None else None
    avg_vol_20 = _f(indicator.volume_avg_20) if indicator else None
    avg_vol_3m = _f(snapshot.avg_volume_3m) if snapshot else None
    avg_vol = avg_vol_20 if avg_vol_20 is not None else avg_vol_3m
    volume_ratio = _f(indicator.volume_ratio) if indicator else None
    if volume_ratio is None and volume is not None and avg_vol and avg_vol > 0:
        volume_ratio = round(volume / avg_vol, 4)

    ret1 = _f(indicator.return_1m) if indicator else None
    ret3 = _f(indicator.return_3m) if indicator else None
    ret6 = _f(indicator.return_6m) if indicator else None
    ret1_pct = round(ret1 * 100.0, 4) if ret1 is not None else None
    ret3_pct = round(ret3 * 100.0, 4) if ret3 is not None else None
    ret6_pct = round(ret6 * 100.0, 4) if ret6 is not None else None

    golden = indicator.golden_cross if indicator else None
    above_50_200 = None
    if ltp is not None and ma50 is not None and ma200 is not None:
        above_50_200 = bool(ltp > ma50 > ma200)
    elif golden is not None and ltp is not None and ma50 is not None:
        above_50_200 = bool(golden and ltp > ma50)

    high_52 = _f(snapshot.high_52_week) if snapshot else None
    low_52 = _f(snapshot.low_52_week) if snapshot else None
    dist_high = _f(indicator.distance_from_52w_high) if indicator else None
    # Strategy engines treat distance as percent points (e.g. -5.0)
    if dist_high is not None and abs(dist_high) <= 1.5:
        dist_high = round(dist_high * 100.0, 2)
    dist_low = None
    if ltp is not None and low_52 and low_52 > 0:
        dist_low = round(((ltp - low_52) / low_52) * 100.0, 2)

    pe = _f(snapshot.pe) if snapshot else None
    if pe is None and fundamental is not None:
        pe = _f(fundamental.pe)

    mom = _f(indicator.momentum_score) if indicator else None
    if mom is None:
        score = indicator.trend_score if indicator else None
        mom = round((score or 0) * 20.0, 1) if score is not None else None

    roe = _f(fundamental.roe) if fundamental else None
    de = _f(fundamental.debt_equity) if fundamental else None
    # Prefer growth from indicator (fractions) → percent for engines
    rev_yoy = _frac_to_pct(_f(indicator.revenue_growth_yoy) if indicator else None)
    pat_yoy = _frac_to_pct(_f(indicator.pat_growth_yoy) if indicator else None)

    fii = _f(ownership.fii_pct) if ownership else None
    dii = _f(ownership.dii_pct) if ownership else None
    inst = None
    if fii is not None or dii is not None:
        inst = round((fii or 0.0) + (dii or 0.0), 2)

    return StrategyInput(
        id=stock.id,
        symbol=stock.symbol,
        company_name=stock.company_name or stock.symbol,
        exchange=stock.exchange or "NSE",
        sector=stock.sector,
        industry=stock.industry,
        ltp=ltp,
        change_pct=_pct_change(ltp, prev),
        sma_21=ma21,
        sma_50=ma50,
        sma_200=ma200,
        price_above_50_above_200=above_50_200,
        sma_50_above_200=golden if golden is not None else (bool(ma50 > ma200) if ma50 and ma200 else None),
        volume=volume,
        avg_volume_20=avg_vol,
        volume_ratio=volume_ratio,
        volume_mover=bool(volume_ratio is not None and volume_ratio >= 1.5),
        return_1m_pct=ret1_pct,
        return_3m_pct=ret3_pct,
        return_6m_pct=ret6_pct,
        as_of=indicator.calculation_date if indicator else (snapshot.snapshot_date if snapshot else None),
        revenue_growth_yoy=rev_yoy,
        pat_growth_yoy=pat_yoy,
        eps_cagr_3y=pat_yoy,  # proxy until dedicated CAGR is stored
        revenue_cagr_3y=rev_yoy,
        roe=roe,
        debt_equity=de,
        pe_ttm=pe,
        peg=None,
        institutional_pct=inst,
        fii_pct=fii,
        dii_pct=dii,
        momentum=mom,
        overall=mom,
        growth=pat_yoy,
        high_52w=high_52,
        low_52w=low_52,
        dist_from_52w_high_pct=dist_high,
        dist_from_52w_low_pct=dist_low,
    )


def load_strategy_universe(
    session: Session,
    *,
    exchange: str | None = "NSE",
    q: str | None = None,
    limit: int = 5000,
) -> list[StrategyInput]:
    limit = max(50, min(limit, 5000))
    rows = session.execute(latest_screener_query(session)).all()

    # Batch-load fundamentals & ownership for the candidate set
    stock_ids = [stock.id for stock, _, _ in rows]
    fund_by_id: dict[int, StockFundamental] = {}
    if stock_ids:
        for fund in session.scalars(
            select(StockFundamental).where(StockFundamental.stock_id.in_(stock_ids))
        ).all():
            prev = fund_by_id.get(fund.stock_id)
            if prev is None or (fund.as_of_date or date.min) >= (prev.as_of_date or date.min):
                fund_by_id[fund.stock_id] = fund
    own_by_id: dict[int, StockOwnership] = {}
    if stock_ids:
        for own in session.scalars(
            select(StockOwnership).where(StockOwnership.stock_id.in_(stock_ids))
        ).all():
            # keep last seen (highest id roughly latest import)
            own_by_id[own.stock_id] = own

    out: list[StrategyInput] = []
    for stock, indicator, snapshot in rows:
        if exchange and (stock.exchange or "NSE").upper() != exchange.upper():
            continue
        if q:
            needle = q.strip().upper()
            name = (stock.company_name or "").upper()
            if needle not in stock.symbol.upper() and needle not in name:
                continue
        row = _row_from_trade(
            stock,
            indicator,
            snapshot,
            fundamental=fund_by_id.get(stock.id),
            ownership=own_by_id.get(stock.id),
        )
        # Fill LTP from latest close when snapshot missing
        if row.ltp is None:
            closes = latest_closes(session, stock.id, limit=5)
            if closes:
                row.ltp = closes[-1]
        if row.ltp is None:
            continue
        out.append(row)
    out.sort(key=lambda r: (r.momentum is None, -(r.momentum or 0), r.symbol))
    return out[:limit]


def enrich_from_bars(row: StrategyInput, bars: list[StockPrice]) -> StrategyInput:
    if not bars:
        return row
    closes = [float(b.close) for b in bars if b.close is not None]
    highs = [float(b.high if b.high is not None else b.close) for b in bars if b.close is not None]
    lows = [float(b.low if b.low is not None else b.close) for b in bars if b.close is not None]
    n = len(closes)
    if n == 0:
        return row
    price = closes[-1]

    def sma(window: int) -> float | None:
        if n < window:
            return None
        return sum(closes[-window:]) / window

    sma_150 = sma(150)
    if row.sma_200 is None:
        row.sma_200 = sma(200)
    if row.sma_50 is None:
        row.sma_50 = sma(50)
    sma_200_20d_ago = None
    if n >= 220:
        sma_200_20d_ago = sum(closes[-220:-20]) / 200
    if row.ltp is None:
        row.ltp = price
    if row.high_52w is None and highs:
        row.high_52w = max(highs[-252:]) if len(highs) >= 20 else max(highs)
    if row.low_52w is None and lows:
        row.low_52w = min(lows[-252:]) if len(lows) >= 20 else min(lows)
    if row.dist_from_52w_high_pct is None and row.ltp is not None and row.high_52w:
        row.dist_from_52w_high_pct = round(((row.ltp / row.high_52w) - 1.0) * 100.0, 2)
    if row.dist_from_52w_low_pct is None and row.ltp is not None and row.low_52w and row.low_52w > 0:
        row.dist_from_52w_low_pct = round(((row.ltp - row.low_52w) / row.low_52w) * 100.0, 2)
    if row.price_above_50_above_200 is None and row.ltp is not None and row.sma_50 is not None and row.sma_200 is not None:
        row.price_above_50_above_200 = bool(row.ltp > row.sma_50 > row.sma_200)
    if row.sma_50_above_200 is None and row.sma_50 is not None and row.sma_200 is not None:
        row.sma_50_above_200 = bool(row.sma_50 > row.sma_200)
    if row.return_1m_pct is None and n > 21 and closes[-22]:
        row.return_1m_pct = round(((closes[-1] / closes[-22]) - 1.0) * 100.0, 4)
    if row.return_3m_pct is None and n > 63 and closes[-64]:
        row.return_3m_pct = round(((closes[-1] / closes[-64]) - 1.0) * 100.0, 4)
    if row.return_6m_pct is None and n > 126 and closes[-127]:
        row.return_6m_pct = round(((closes[-1] / closes[-127]) - 1.0) * 100.0, 4)

    row.sma_150 = sma_150
    row.sma_200_20d_ago = sma_200_20d_ago
    row.bars = [
        BarPoint(
            date=b.price_date,
            open=float(b.open if b.open is not None else b.close),
            high=float(b.high if b.high is not None else b.close),
            low=float(b.low if b.low is not None else b.close),
            close=float(b.close),
            volume=float(b.volume) if b.volume is not None else None,
        )
        for b in bars
        if b.close is not None
    ]
    return row


def load_bars_for_stocks(session: Session, stock_ids: list[int]) -> dict[int, list[StockPrice]]:
    if not stock_ids:
        return {}
    cutoff = date.today() - timedelta(days=PRICE_LOOKBACK_DAYS)
    rows = session.scalars(
        select(StockPrice)
        .where(StockPrice.stock_id.in_(stock_ids), StockPrice.price_date >= cutoff)
        .order_by(StockPrice.stock_id, StockPrice.price_date)
    ).all()
    out: dict[int, list[StockPrice]] = {sid: [] for sid in stock_ids}
    for row in rows:
        out.setdefault(row.stock_id, []).append(row)
    return out


def load_market_context(session: Session, universe: list[StrategyInput]) -> MarketContext:
    advances = sum(1 for r in universe if (r.return_3m_pct or 0) > 0)
    declines = sum(1 for r in universe if (r.return_3m_pct or 0) < 0)
    new_highs = sum(1 for r in universe if r.dist_from_52w_high_pct is not None and r.dist_from_52w_high_pct >= -5)
    new_lows = sum(1 for r in universe if r.dist_from_52w_low_pct is not None and r.dist_from_52w_low_pct <= 10)
    uptrend = advances > declines and new_highs >= new_lows

    proxy_symbol = None
    price = None
    change_pct = None

    # Prefer official NSE index levels (Nifty 50 ~24k), not ETF unit prices (NIFTYBEES ~273).
    for key in MARKET_INDEX_KEYS:
        idx = session.scalar(select(MarketIndex).where(MarketIndex.key == key).limit(1))
        if not idx:
            continue
        snap = session.scalar(
            select(MarketIndexSnapshot)
            .where(MarketIndexSnapshot.index_id == idx.id)
            .order_by(MarketIndexSnapshot.as_of.desc())
            .limit(1)
        )
        if snap and snap.last is not None:
            proxy_symbol = idx.name or key
            price = Decimal(str(snap.last))
            change_pct = _f(snap.change_pct)
            if change_pct is None:
                change_pct = _pct_change(_f(snap.last), _f(snap.prev_close))
            break

    if price is None:
        for sym in MARKET_PROXY_SYMBOLS:
            stock = session.scalar(select(Stock).where(Stock.symbol == sym).limit(1))
            if not stock:
                continue
            snap = session.scalar(
                select(StockSnapshot)
                .where(StockSnapshot.stock_id == stock.id)
                .order_by(StockSnapshot.snapshot_date.desc())
                .limit(1)
            )
            if snap and snap.ltp is not None:
                proxy_symbol = f"{sym} ETF"
                price = Decimal(str(snap.ltp))
                change_pct = _pct_change(_f(snap.ltp), _f(snap.prev_close))
                break

    if uptrend:
        label = "Bullish"
    elif advances < declines:
        label = "Bearish"
    else:
        label = "Neutral"
    detail = f"{advances} advancing / {declines} declining · {new_highs} near highs"
    return MarketContext(
        label=label,
        detail=detail,
        proxy_symbol=proxy_symbol,
        price=price,
        change_pct=change_pct,
        advances=advances,
        declines=declines,
        new_highs=new_highs,
        new_lows=new_lows,
        uptrend=uptrend,
    )


def rs_proxy(row: StrategyInput) -> float | None:
    """Relative-strength proxy 0–100 from momentum / returns."""
    if row.momentum is not None:
        return max(0.0, min(100.0, float(row.momentum)))
    if row.return_3m_pct is None:
        return None
    # Map rough 3M return percent to 0–100 band
    return max(0.0, min(100.0, 50.0 + float(row.return_3m_pct)))
