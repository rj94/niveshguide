from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from market_platform.engines import canslim, darvas, garp, sepa
from market_platform.engines.base import StrategyResult
from market_platform.engines.inputs import (
    StrategyInput,
    enrich_from_bars,
    load_bars_for_stocks,
    load_market_context,
    load_strategy_universe,
)
from market_platform.schemas.strategies import (
    CriterionStatus,
    DataCoverage,
    DistributionSlice,
    InsightItem,
    MarketTrend,
    RatingCounts,
    StrategyListResponse,
    StrategyMeta,
    StrategyRunResponse,
    StrategyStockRow,
    StrategySummary,
    TrendPoint,
)

STRATEGY_META: dict[str, StrategyMeta] = {
    "canslim": canslim.META,
    "garp": garp.META,
    "darvas": darvas.META,
    "sepa": sepa.META,
}

NEEDS_BARS = frozenset({"canslim", "darvas", "sepa"})
BAR_CANDIDATE_CAP = {
    "canslim": 400,
    "darvas": 250,
    "sepa": 350,
    "garp": 0,
}


def list_strategies() -> StrategyListResponse:
    return StrategyListResponse(items=list(STRATEGY_META.values()))


def run_strategy(
    session: Session,
    slug: str,
    *,
    exchange: str | None = "NSE",
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    scan_limit: int = 5000,
) -> StrategyRunResponse:
    slug = slug.lower().strip()
    if slug not in STRATEGY_META:
        raise ValueError(f"Unknown strategy: {slug}")

    meta = STRATEGY_META[slug]
    universe = load_strategy_universe(
        session, exchange=exchange, q=q, limit=scan_limit
    )

    # Enrich a capped candidate set with OHLC-derived fields when needed
    if slug in NEEDS_BARS and universe:
        cap = BAR_CANDIDATE_CAP.get(slug, 300)
        candidates = universe[:cap]
        if slug == "canslim":
            # Indicators usually already have SMAs/returns — skip ~100k-row load when complete
            need_bars = [
                r
                for r in candidates
                if r.sma_50 is None or r.sma_200 is None or r.return_3m_pct is None
            ]
            if need_bars:
                bars_map = load_bars_for_stocks(session, [r.id for r in need_bars])
                for row in need_bars:
                    enrich_from_bars(row, bars_map.get(row.id, []))
        else:
            bars_map = load_bars_for_stocks(session, [r.id for r in candidates])
            for row in candidates:
                enrich_from_bars(row, bars_map.get(row.id, []))

    market = load_market_context(session, universe)

    scored: list[tuple[StrategyInput, StrategyResult]] = []
    for row in universe:
        if slug == "canslim":
            result = canslim.score_canslim(row, market_uptrend=market.uptrend)
        elif slug == "garp":
            result = garp.score_garp(row)
        elif slug == "darvas":
            result = darvas.score_darvas(row)
        else:
            result = sepa.score_sepa(row)
        scored.append((row, result))

    scored.sort(key=lambda pair: (-pair[1].score, pair[0].symbol))

    counts = RatingCounts()
    for _, result in scored:
        counts.total += 1
        if result.rating == "strong_buy":
            counts.strong_buy += 1
        elif result.rating == "buy":
            counts.buy += 1
        elif result.rating == "watch":
            counts.watch += 1
        else:
            counts.avoid += 1

    page = scored[offset : offset + limit]
    items: list[StrategyStockRow] = []
    for rank_offset, (row, result) in enumerate(page, start=offset + 1):
        items.append(
            StrategyStockRow(
                id=row.id,
                symbol=row.symbol,
                company_name=row.company_name,
                exchange=row.exchange,
                sector=row.sector,
                industry=row.industry,
                ltp=Decimal(str(row.ltp)) if row.ltp is not None else None,
                change_pct=row.change_pct,
                score=result.score,
                rating=result.rating,
                rank=rank_offset,
                metrics=result.metrics,
                checklist=[
                    CriterionStatus(
                        key=c.key,
                        label=c.label,
                        state=c.state,
                        detail=c.detail,
                        value=c.value,
                    )
                    for c in result.checklist
                ],
                as_of=row.as_of,
            )
        )

    distribution = _distribution(counts)
    trend = _synthetic_trend(counts)
    insights = _insights(slug, market, counts, scored[:20])
    coverage = _data_coverage(universe)

    trend_label = market.label if market.label in ("Bullish", "Neutral", "Bearish") else "Neutral"
    summary = StrategySummary(
        market_trend=MarketTrend(
            label=trend_label,  # type: ignore[arg-type]
            detail=market.detail,
            proxy_symbol=market.proxy_symbol,
            price=market.price,
            change_pct=market.change_pct,
            advances=market.advances,
            declines=market.declines,
            new_highs=market.new_highs,
            new_lows=market.new_lows,
        ),
        counts=counts,
        distribution=distribution,
        trend=trend,
        insights=insights,
        data_coverage=coverage,
    )

    selected = items[0].symbol if items else None
    return StrategyRunResponse(
        strategy=meta,
        summary=summary,
        items=items,
        total=len(scored),
        scanned=len(universe),
        selected_symbol=selected,
    )


def _data_coverage(universe: list[StrategyInput]) -> DataCoverage:
    scanned = len(universe)
    with_fund = sum(
        1
        for r in universe
        if any(
            v is not None
            for v in (r.pat_growth_yoy, r.eps_cagr_3y, r.roe, r.pe_ttm, r.revenue_growth_yoy)
        )
    )
    with_own = sum(1 for r in universe if r.institutional_pct is not None)
    with_mom = sum(1 for r in universe if r.momentum is not None)
    with_peg = sum(1 for r in universe if r.peg is not None)
    with_eps = sum(1 for r in universe if r.eps_cagr_3y is not None)
    notes: list[str] = []
    if scanned and with_own == 0:
        notes.append(
            "Institutional ownership missing - CANSLIM I stays unknown until shareholding ingest."
        )
    elif scanned and with_own / scanned < 0.3:
        notes.append(f"Ownership coverage low ({with_own}/{scanned}).")
    if scanned and with_fund / scanned < 0.7:
        notes.append(f"Fundamentals incomplete ({with_fund}/{scanned}).")
    if scanned and with_peg / scanned < 0.15:
        notes.append("Native PEG sparse - GARP falls back to PE / growth when possible.")
    if scanned and with_eps / scanned < 0.5:
        notes.append("3Y EPS CAGR sparse - annual growth letter often partial.")
    return DataCoverage(
        scanned=scanned,
        with_fundamentals=with_fund,
        with_ownership=with_own,
        with_momentum=with_mom,
        with_peg=with_peg,
        with_eps_cagr=with_eps,
        notes=notes,
    )


def _distribution(counts: RatingCounts) -> list[DistributionSlice]:
    total = max(counts.total, 1)
    return [
        DistributionSlice(
            key="strong_buy",
            label="Strong Buy",
            count=counts.strong_buy,
            pct=round(100 * counts.strong_buy / total, 1),
        ),
        DistributionSlice(
            key="buy",
            label="Buy",
            count=counts.buy,
            pct=round(100 * counts.buy / total, 1),
        ),
        DistributionSlice(
            key="watch",
            label="Watch",
            count=counts.watch,
            pct=round(100 * counts.watch / total, 1),
        ),
        DistributionSlice(
            key="avoid",
            label="Avoid",
            count=counts.avoid,
            pct=round(100 * counts.avoid / total, 1),
        ),
    ]


def _synthetic_trend(counts: RatingCounts) -> list[TrendPoint]:
    """Placeholder multi-week trend until strategy runs are persisted."""
    labels = ["4W", "3W", "2W", "1W", "Now"]
    sb, b, w, a = counts.strong_buy, counts.buy, counts.watch, counts.avoid
    points = []
    for i, label in enumerate(labels):
        # Ease toward current counts
        t = i / (len(labels) - 1)
        points.append(
            TrendPoint(
                label=label,
                strong_buy=max(0, int(sb * (0.7 + 0.3 * t))),
                buy=max(0, int(b * (0.75 + 0.25 * t))),
                watch=max(0, int(w * (1.1 - 0.1 * t))),
                avoid=max(0, int(a * (1.15 - 0.15 * t))),
            )
        )
    return points


def _insights(
    slug: str,
    market: Any,
    counts: RatingCounts,
    top: list[tuple[StrategyInput, StrategyResult]],
) -> list[InsightItem]:
    items: list[InsightItem] = []
    if market.uptrend:
        items.append(
            InsightItem(text="Market in confirmed uptrend — favorable for growth breakouts.", tone="positive")
        )
    else:
        items.append(
            InsightItem(text="Market not in confirmed uptrend — keep risk tight.", tone="warning")
        )

    if counts.strong_buy:
        items.append(
            InsightItem(
                text=f"{counts.strong_buy} stocks rate Strong Buy on {slug.upper()}.",
                tone="positive",
            )
        )

    sectors: dict[str, int] = {}
    for row, result in top:
        if result.score < 65 or not row.sector:
            continue
        sectors[row.sector] = sectors.get(row.sector, 0) + 1
    if sectors:
        leader = max(sectors.items(), key=lambda kv: kv[1])
        items.append(
            InsightItem(
                text=f"{leader[0]} showing the most high-scoring names ({leader[1]}).",
                tone="positive",
            )
        )

    if market.advances and market.declines:
        breadth = market.advances / max(market.advances + market.declines, 1)
        items.append(
            InsightItem(
                text=f"Universe breadth: {market.advances} advances vs {market.declines} declines ({breadth:.0%}).",
                tone="positive" if breadth >= 0.55 else "neutral",
            )
        )

    return items[:5]
