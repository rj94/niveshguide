"""Sector / industry listings from Stock.sector and Stock.industry."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database.models import (
    MarketIndex,
    MarketIndexPrice,
    Stock,
    StockIndicator,
    StockIndexMembership,
    StockSnapshot,
)
from database.repository import latest_screener_query
from indicators.momentum_score import percentile_rank, percentile_to_bucket_score
from market_platform.schemas.sectors import IndustryScoreRow, SectorListResponse, SectorScoreRow
from market_platform.schemas.stocks import StockAnalysisResponse, StockAnalysisRow
from market_platform.services.stocks import _analysis_row


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(round(float(value), 4)))
    except (TypeError, ValueError):
        return None


def _norm_name(name: str) -> str:
    return unquote(name or "").strip()


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _cap_weighted_avg(pairs: list[tuple[float, float]]) -> float | None:
    """pairs: (value, weight). Returns None if no positive weight."""
    num = 0.0
    den = 0.0
    for value, weight in pairs:
        if weight is None or weight <= 0:
            continue
        num += value * weight
        den += weight
    if den <= 0:
        return None
    return num / den


def _frac_to_pct(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) * 100.0


# Sectoral UI label → NSE MarketIndex.key
SECTORAL_INDEX_KEYS: dict[str, str] = {
    "Auto": "NIFTY AUTO",
    "Bank": "NIFTY BANK",
    "Chemicals": "NIFTY CHEMICALS",
    "Consumer Durables": "NIFTY CONSUMER DURABLES",
    "Financial Services": "NIFTY FINANCIAL SERVICES",
    "Financial Services Ex-Bank": "NIFTY FINANCIAL SERVICES EX-BANK",
    "FMCG": "NIFTY FMCG",
    "Healthcare": "NIFTY HEALTHCARE INDEX",
    "IT": "NIFTY IT",
    "Media": "NIFTY MEDIA",
    "Metal": "NIFTY METAL",
    "Oil & Gas": "NIFTY OIL & GAS",
    "Pharma": "NIFTY PHARMA",
    "Private Bank": "NIFTY PRIVATE BANK",
    "PSU Bank": "NIFTY PSU BANK",
    "Realty": "NIFTY REALTY",
}


def _load_mcaps_by_stock(session: Session) -> dict[int, float]:
    latest = (
        select(
            StockSnapshot.stock_id,
            func.max(StockSnapshot.snapshot_date).label("max_date"),
        )
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
        if mcap is None:
            continue
        try:
            val = float(mcap)
        except (TypeError, ValueError):
            continue
        if val > 0:
            out[stock_id] = val
    return out


def _index_return_pct(session: Session, index_key: str, *, lookback: int = 63) -> float | None:
    """Official index ~N-session return % from market_index_prices."""
    idx = session.scalar(select(MarketIndex).where(MarketIndex.key == index_key))
    if idx is None:
        return None
    closes = session.scalars(
        select(MarketIndexPrice.close)
        .where(MarketIndexPrice.index_id == idx.id, MarketIndexPrice.close.is_not(None))
        .order_by(MarketIndexPrice.price_date.desc())
        .limit(lookback + 1)
    ).all()
    if len(closes) < lookback + 1:
        return None
    latest = float(closes[0])
    past = float(closes[lookback])
    if past == 0:
        return None
    return round(((latest / past) - 1.0) * 100.0, 4)


class _MemberMetrics:
    __slots__ = (
        "return_1m_pct",
        "return_3m_pct",
        "return_6m_pct",
        "momentum_score",
        "momentum_acceleration",
        "above_ma_50",
    )

    def __init__(
        self,
        *,
        return_1m_pct: float | None,
        return_3m_pct: float | None,
        return_6m_pct: float | None,
        momentum_score: float | None,
        momentum_acceleration: float | None,
        above_ma_50: bool | None,
    ) -> None:
        self.return_1m_pct = return_1m_pct
        self.return_3m_pct = return_3m_pct
        self.return_6m_pct = return_6m_pct
        self.momentum_score = momentum_score
        self.momentum_acceleration = momentum_acceleration
        self.above_ma_50 = above_ma_50


def _load_metrics_by_stock(session: Session) -> dict[int, _MemberMetrics]:
    """Latest indicator per stock that has usable momentum/returns (skip empty calc rows)."""
    usable = (
        select(
            StockIndicator.stock_id,
            func.max(StockIndicator.calculation_date).label("max_date"),
        )
        .where(
            (StockIndicator.momentum_score.is_not(None))
            | (StockIndicator.return_3m.is_not(None))
            | (StockIndicator.return_1m.is_not(None))
        )
        .group_by(StockIndicator.stock_id)
        .subquery()
    )
    ind_rows = session.execute(
        select(
            StockIndicator.stock_id,
            StockIndicator.return_1m,
            StockIndicator.return_3m,
            StockIndicator.return_6m,
            StockIndicator.momentum_score,
            StockIndicator.momentum_acceleration,
            StockIndicator.distance_50_dma,
            StockIndicator.above_ma_21,
            StockIndicator.golden_cross,
        ).join(
            usable,
            (StockIndicator.stock_id == usable.c.stock_id)
            & (StockIndicator.calculation_date == usable.c.max_date),
        )
    ).all()
    out: dict[int, _MemberMetrics] = {}
    for row in ind_rows:
        above_50 = None
        if row.distance_50_dma is not None:
            above_50 = float(row.distance_50_dma) > 0
        elif row.golden_cross is not None:
            above_50 = bool(row.golden_cross)
        elif row.above_ma_21 is not None:
            above_50 = bool(row.above_ma_21)
        out[row.stock_id] = _MemberMetrics(
            return_1m_pct=_frac_to_pct(float(row.return_1m) if row.return_1m is not None else None),
            return_3m_pct=_frac_to_pct(float(row.return_3m) if row.return_3m is not None else None),
            return_6m_pct=_frac_to_pct(float(row.return_6m) if row.return_6m is not None else None),
            momentum_score=float(row.momentum_score) if row.momentum_score is not None else None,
            momentum_acceleration=(
                float(row.momentum_acceleration) if row.momentum_acceleration is not None else None
            ),
            above_ma_50=above_50,
        )
    return out


def _group_stats(
    members: list[Stock],
    metrics: dict[int, _MemberMetrics],
    mcaps: dict[int, float] | None = None,
) -> dict[str, float | None | str]:
    mcaps = mcaps or {}
    m1: list[float] = []
    m3: list[float] = []
    m6: list[float] = []
    cw1: list[tuple[float, float]] = []
    cw3: list[tuple[float, float]] = []
    moms: list[float] = []
    accels: list[float] = []
    advancing = 0
    with_ret = 0
    above_dma = 0
    with_dma = 0
    for stock in members:
        met = metrics.get(stock.id)
        if met is None:
            continue
        mcap = mcaps.get(stock.id)
        if met.return_1m_pct is not None:
            m1.append(met.return_1m_pct)
            if mcap:
                cw1.append((met.return_1m_pct, mcap))
        if met.return_3m_pct is not None:
            m3.append(met.return_3m_pct)
            with_ret += 1
            if met.return_3m_pct > 0:
                advancing += 1
            if mcap:
                cw3.append((met.return_3m_pct, mcap))
        if met.return_6m_pct is not None:
            m6.append(met.return_6m_pct)
        if met.momentum_score is not None:
            moms.append(met.momentum_score)
        if met.momentum_acceleration is not None:
            accels.append(met.momentum_acceleration)
        if met.above_ma_50 is not None:
            with_dma += 1
            if met.above_ma_50:
                above_dma += 1

    breadth = (100.0 * advancing / with_ret) if with_ret else None
    above_50dma_pct = (100.0 * above_dma / with_dma) if with_dma else None
    avg_accel = _avg(accels)
    ew_3m = _avg(m3)
    ew_1m = _avg(m1)
    # Prefer cap-weight when ≥50% of returning members have mcap
    cw_3m = None
    if m3 and len(cw3) >= max(1, int(0.5 * len(m3))):
        cw_3m = _cap_weighted_avg(cw3)
    cw_1m = None
    if m1 and len(cw1) >= max(1, int(0.5 * len(m1))):
        cw_1m = _cap_weighted_avg(cw1)

    if cw_3m is not None:
        primary_3m = cw_3m
        source = "cap_weight"
    elif ew_3m is not None:
        primary_3m = ew_3m
        source = "equal_weight"
    else:
        primary_3m = None
        source = None

    primary_1m = cw_1m if cw_1m is not None else ew_1m

    gaining = False
    if avg_accel is not None:
        gaining = avg_accel > 0
    elif primary_3m is not None:
        gaining = primary_3m > 0

    return {
        "return_1m": primary_1m,
        "return_3m": primary_3m,  # used in strength blend (CW preferred)
        "return_3m_cw": cw_3m,
        "return_3m_ew": ew_3m,
        "return_3m_source": source,
        "return_6m": _avg(m6),
        "momentum_score": _avg(moms),
        "breadth_score": breadth,
        "above_50dma_pct": above_50dma_pct,
        "avg_accel": avg_accel,
        "is_gaining": gaining,
    }


def _blend_strength(
    *,
    momentum_avg: float | None,
    return_3m_pct: float | None,
    breadth: float | None,
    universe_3m: list[float],
) -> float | None:
    """60% momentum + 25% cross-group return percentile bucket + 15% breadth."""
    parts: list[tuple[float, float]] = []
    if momentum_avg is not None:
        parts.append((max(0.0, min(100.0, momentum_avg)), 0.60))
    if return_3m_pct is not None and universe_3m:
        pct = percentile_rank(return_3m_pct, universe_3m)
        bucket = percentile_to_bucket_score(pct)
        if bucket is not None:
            parts.append((bucket, 0.25))
    if breadth is not None:
        parts.append((max(0.0, min(100.0, breadth)), 0.15))
    if not parts:
        return None
    total_w = sum(w for _, w in parts)
    return round(sum(score * (w / total_w) for score, w in parts), 4)


def industry_strength_by_stock_id(
    session: Session,
    *,
    min_constituents: int = 1,
    metrics: dict[int, _MemberMetrics] | None = None,
    mcaps: dict[int, float] | None = None,
) -> dict[int, float]:
    """Map stock_id → industry/sector strength (0–100); multi-tag stocks use primary tag strength."""
    metrics = metrics if metrics is not None else _load_metrics_by_stock(session)
    mcaps = mcaps if mcaps is not None else _load_mcaps_by_stock(session)
    stocks = session.scalars(select(Stock).where(Stock.is_active.is_(True))).all()
    groups: dict[str, list[Stock]] = defaultdict(list)
    seen: dict[str, set[int]] = defaultdict(set)
    for stock in stocks:
        for label in _stock_industry_tags(stock):
            if stock.id in seen[label]:
                continue
            groups[label].append(stock)
            seen[label].add(stock.id)

    stats: dict[str, dict[str, float | None | str]] = {}
    for name, members in groups.items():
        if len(members) < min_constituents:
            continue
        stats[name] = _group_stats(members, metrics, mcaps)

    universe = [float(st["return_3m"]) for st in stats.values() if st.get("return_3m") is not None]
    strength_by_label: dict[str, float] = {}
    for name, st in stats.items():
        strength = _blend_strength(
            momentum_avg=st.get("momentum_score") if isinstance(st.get("momentum_score"), (int, float)) else None,
            return_3m_pct=st.get("return_3m") if isinstance(st.get("return_3m"), (int, float)) else None,
            breadth=st.get("breadth_score") if isinstance(st.get("breadth_score"), (int, float)) else None,
            universe_3m=universe,
        )
        if strength is not None:
            strength_by_label[name] = float(strength)

    out: dict[int, float] = {}
    for stock in stocks:
        tags = _stock_industry_tags(stock)
        if not tags:
            continue
        # Primary tag first; else max across tags
        primary = tags[0]
        if primary in strength_by_label:
            out[stock.id] = strength_by_label[primary]
            continue
        vals = [strength_by_label[t] for t in tags if t in strength_by_label]
        if vals:
            out[stock.id] = max(vals)
    return out


def _attach_return_fields(
    session: Session,
    *,
    name: str,
    st: dict[str, float | None | str],
    is_sectoral: bool,
) -> dict[str, Any]:
    """Merge CW/EW with official index 3M; pick display primary."""
    cw = st.get("return_3m_cw")
    ew = st.get("return_3m_ew")
    blend_3m = st.get("return_3m")  # CW preferred inside stats
    idx_3m = None
    if is_sectoral:
        key = SECTORAL_INDEX_KEYS.get(name)
        if key:
            idx_3m = _index_return_pct(session, key)
    if idx_3m is not None:
        display = idx_3m
        source = "index"
    elif isinstance(blend_3m, (int, float)):
        display = float(blend_3m)
        source = str(st.get("return_3m_source") or "cap_weight")
    else:
        display = None
        source = None
    return {
        "return_3m": display,
        "return_3m_cw": float(cw) if isinstance(cw, (int, float)) else None,
        "return_3m_ew": float(ew) if isinstance(ew, (int, float)) else None,
        "return_3m_index": idx_3m,
        "return_3m_source": source,
        "blend_return_3m": float(blend_3m) if isinstance(blend_3m, (int, float)) else None,
    }


def _row_return_kwargs(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "return_3m": _dec(fields.get("return_3m")),
        "return_3m_cw": _dec(fields.get("return_3m_cw")),
        "return_3m_ew": _dec(fields.get("return_3m_ew")),
        "return_3m_index": _dec(fields.get("return_3m_index")),
        "return_3m_source": fields.get("return_3m_source"),
    }


def _rotation_state(
    *,
    strength: float | None,
    is_gaining: bool,
    avg_accel: float | None = None,
) -> str:
    """
    Classic 4-box rotation label from strength level + momentum direction.

    Leading / Improving when gaining; Weakening / Lagging when not.
    Acceleration magnitude can refine Improving ↔ Leading thresholds.
    """
    strong = (strength or 0.0) >= 50.0
    if avg_accel is not None:
        if avg_accel > 5:
            is_gaining = True
        elif avg_accel < -5:
            is_gaining = False
    if strong and is_gaining:
        return "Leading"
    if not strong and is_gaining:
        return "Improving"
    if strong and not is_gaining:
        return "Weakening"
    return "Lagging"


def _stock_industry_tags(stock: Stock) -> list[str]:
    """Explode broad_industry (| or comma) into membership tags; fallback sector/industry."""
    from ingestion.niftyindices_constituents import split_industry_labels

    raw = (stock.broad_industry or stock.industry or stock.sector or "").strip()
    tags = split_industry_labels(raw)
    if tags:
        return tags
    primary = (stock.sector or stock.industry or "").strip()
    return [primary] if primary else []


def list_sectors(
    session: Session,
    *,
    limit: int = 100,
    min_constituents: int = 0,
    gaining_only: bool = False,
) -> SectorListResponse:
    as_of = date.today()
    metrics = _load_metrics_by_stock(session)
    mcaps = _load_mcaps_by_stock(session)

    stocks = session.scalars(select(Stock).where(Stock.is_active.is_(True))).all()
    sector_groups: dict[str, list[Stock]] = defaultdict(list)
    sector_seen: dict[str, set[int]] = defaultdict(set)
    industry_groups: dict[str, list[Stock]] = defaultdict(list)
    industry_parent: dict[str, str | None] = {}
    industry_seen: dict[str, set[int]] = defaultdict(set)

    # Explode broad_industry tags → multi-membership sector/industry buckets
    for stock in stocks:
        tags = _stock_industry_tags(stock)
        primary = tags[0] if tags else None
        for label in tags:
            if stock.id not in sector_seen[label]:
                sector_groups[label].append(stock)
                sector_seen[label].add(stock.id)
            if stock.id not in industry_seen[label]:
                industry_groups[label].append(stock)
                industry_seen[label].add(stock.id)
            industry_parent.setdefault(label, primary)

    # Precompute group stats for percentile universe (sectors first, then industries)
    sector_stats: dict[str, dict[str, float | None | str]] = {}
    for name, members in sector_groups.items():
        if len(members) < min_constituents:
            continue
        sector_stats[name] = _group_stats(members, metrics, mcaps)

    industry_stats: dict[str, dict[str, float | None | str]] = {}
    for name, members in industry_groups.items():
        if len(members) < min_constituents:
            continue
        industry_stats[name] = _group_stats(members, metrics, mcaps)

    sector_3m_universe = [
        float(st["return_3m"]) for st in sector_stats.values() if st.get("return_3m") is not None
    ]
    industry_3m_universe = [
        float(st["return_3m"]) for st in industry_stats.values() if st.get("return_3m") is not None
    ]

    sector_rows: list[SectorScoreRow] = []
    for name, members in sector_groups.items():
        if name not in sector_stats:
            continue
        st = sector_stats[name]
        # Industry labels have no 1:1 official sectoral index → CW/EW display
        ret_fields = _attach_return_fields(session, name=name, st=st, is_sectoral=False)
        blend_ret = ret_fields.get("blend_return_3m")
        strength = _blend_strength(
            momentum_avg=st.get("momentum_score") if isinstance(st.get("momentum_score"), (int, float)) else None,
            return_3m_pct=blend_ret,
            breadth=st.get("breadth_score") if isinstance(st.get("breadth_score"), (int, float)) else None,
            universe_3m=sector_3m_universe,
        )
        rs_bucket = None
        if blend_ret is not None and sector_3m_universe:
            rs_bucket = percentile_to_bucket_score(
                percentile_rank(float(blend_ret), sector_3m_universe)
            )
        gaining = bool(st.get("is_gaining"))
        sector_rows.append(
            SectorScoreRow(
                name=name,
                parent_sector=None,
                as_of=as_of,
                strength_score=_dec(strength),
                momentum_score=_dec(st.get("momentum_score")),
                relative_strength_score=_dec(rs_bucket),
                breadth_score=_dec(st.get("breadth_score")),
                constituent_count=len(members),
                return_1m=_dec(st.get("return_1m")),
                above_50dma_pct=_dec(st.get("above_50dma_pct")),
                is_gaining_strength=gaining,
                rotation_state=_rotation_state(
                    strength=strength,
                    is_gaining=gaining,
                    avg_accel=st.get("avg_accel") if isinstance(st.get("avg_accel"), (int, float)) else None,
                ),
                sector_name=name,
                sector_strength_score=_dec(strength),
                **_row_return_kwargs(ret_fields),
            )
        )

    industry_rows: list[IndustryScoreRow] = []
    for name, members in industry_groups.items():
        if name not in industry_stats:
            continue
        st = industry_stats[name]
        ret_fields = _attach_return_fields(session, name=name, st=st, is_sectoral=False)
        blend_ret = ret_fields.get("blend_return_3m")
        strength = _blend_strength(
            momentum_avg=st.get("momentum_score") if isinstance(st.get("momentum_score"), (int, float)) else None,
            return_3m_pct=blend_ret,
            breadth=st.get("breadth_score") if isinstance(st.get("breadth_score"), (int, float)) else None,
            universe_3m=industry_3m_universe,
        )
        rs_bucket = None
        if blend_ret is not None and industry_3m_universe:
            rs_bucket = percentile_to_bucket_score(
                percentile_rank(float(blend_ret), industry_3m_universe)
            )
        gaining = bool(st.get("is_gaining"))
        industry_rows.append(
            IndustryScoreRow(
                name=name,
                parent_sector=industry_parent.get(name),
                as_of=as_of,
                strength_score=_dec(strength),
                momentum_score=_dec(st.get("momentum_score")),
                relative_strength_score=_dec(rs_bucket),
                breadth_score=_dec(st.get("breadth_score")),
                constituent_count=len(members),
                return_1m=_dec(st.get("return_1m")),
                above_50dma_pct=_dec(st.get("above_50dma_pct")),
                is_gaining_strength=gaining,
                rotation_state=_rotation_state(
                    strength=strength,
                    is_gaining=gaining,
                    avg_accel=st.get("avg_accel") if isinstance(st.get("avg_accel"), (int, float)) else None,
                ),
                industry_name=name,
                industry_strength_score=_dec(strength),
                **_row_return_kwargs(ret_fields),
            )
        )

    # Rank by strength descending
    sector_rows.sort(
        key=lambda r: (
            float(r.strength_score) if r.strength_score is not None else -1.0,
            r.constituent_count or 0,
        ),
        reverse=True,
    )
    industry_rows.sort(
        key=lambda r: (
            float(r.strength_score) if r.strength_score is not None else -1.0,
            r.constituent_count or 0,
        ),
        reverse=True,
    )
    for idx, row in enumerate(sector_rows, start=1):
        row.rank = idx
    for idx, row in enumerate(industry_rows, start=1):
        row.rank = idx

    items = sector_rows
    industries = industry_rows
    if gaining_only:
        items = [row for row in items if row.is_gaining_strength]
        industries = [row for row in industries if row.is_gaining_strength]
    gaining = [row for row in items if row.is_gaining_strength][:20]
    return SectorListResponse(
        items=items[: max(1, limit)],
        industries=industries[:500],
        gaining=gaining,
        as_of=as_of,
    )


def get_sector(session: Session, name: str) -> SectorScoreRow:
    name = _norm_name(name)
    payload = list_sectors(session, limit=500, min_constituents=0)
    for row in payload.items:
        if row.name.lower() == name.lower():
            return row
    count = session.scalar(
        select(func.count()).select_from(Stock).where(Stock.sector == name, Stock.is_active.is_(True))
    ) or 0
    return SectorScoreRow(
        name=name,
        as_of=date.today(),
        constituent_count=int(count),
        sector_name=name,
    )


def get_industry(session: Session, name: str) -> IndustryScoreRow:
    name = _norm_name(name)
    payload = list_sectors(session, limit=2000, min_constituents=0)
    for row in payload.industries:
        if row.name.lower() == name.lower():
            return row
    stock = session.scalar(select(Stock).where(Stock.industry == name).limit(1))
    count_stock = session.scalar(
        select(func.count()).select_from(Stock).where(
            func.lower(Stock.industry) == name.lower(),
            Stock.is_active.is_(True),
        )
    ) or 0
    count_memb = session.scalar(
        select(func.count(func.distinct(StockIndexMembership.stock_id))).where(
            func.lower(StockIndexMembership.industry) == name.lower()
        )
    ) or 0
    return IndustryScoreRow(
        name=name,
        parent_sector=stock.sector if stock else None,
        as_of=date.today(),
        constituent_count=max(int(count_stock), int(count_memb)),
        industry_name=name,
    )


def _minimal_analysis_row(stock: Stock) -> StockAnalysisRow:
    """Constituent row when price indicators are not yet calculated."""
    return StockAnalysisRow(
        id=stock.id,
        symbol=stock.symbol,
        company_name=stock.company_name or stock.symbol,
        exchange=stock.exchange or "NSE",
        sector=stock.sector,
        industry=stock.industry,
        company_strength_source="unavailable",
    )


def _stocks_matching_tag(session: Session, tag: str) -> set[int]:
    """Match stocks whose primary sector/industry OR exploded broad_industry tags equal tag."""
    tag_norm = tag.strip().lower()
    if not tag_norm:
        return set()
    ids: set[int] = set(
        session.scalars(
            select(Stock.id).where(
                Stock.is_active.is_(True),
                or_(
                    func.lower(Stock.sector) == tag_norm,
                    func.lower(Stock.industry) == tag_norm,
                ),
            )
        ).all()
    )
    # broad_industry may store pipe-joined tags — scan active stocks with tags
    for stock in session.scalars(
        select(Stock).where(
            Stock.is_active.is_(True),
            Stock.broad_industry.is_not(None),
            Stock.broad_industry != "",
        )
    ).all():
        for t in _stock_industry_tags(stock):
            if t.lower() == tag_norm:
                ids.add(stock.id)
                break
    return ids


def _constituent_stocks(
    session: Session,
    *,
    sector: str | None = None,
    industry: str | None = None,
    exchange: str | None = None,
    sort_by: str = "symbol",
    sort_dir: str = "asc",
    limit: int = 150,
) -> StockAnalysisResponse:
    industry_stock_ids: set[int] | None = None
    if industry:
        industry_stock_ids = _stocks_matching_tag(session, industry)
        industry_norm = industry.strip().lower()
        membership_ids = set(
            session.scalars(
                select(StockIndexMembership.stock_id).where(
                    func.lower(StockIndexMembership.industry) == industry_norm
                )
            ).all()
        )
        industry_stock_ids |= membership_ids

    sector_stock_ids: set[int] | None = None
    if sector:
        sector_stock_ids = _stocks_matching_tag(session, sector)

    rows = session.execute(latest_screener_query(session)).all()
    strength_map = industry_strength_by_stock_id(session)
    items = []
    for stock, indicator, snapshot in rows:
        if sector_stock_ids is not None and stock.id not in sector_stock_ids:
            continue
        if industry_stock_ids is not None and stock.id not in industry_stock_ids:
            continue
        if exchange and (stock.exchange or "NSE").upper() != exchange.upper():
            continue
        if indicator is None:
            items.append(_minimal_analysis_row(stock))
        else:
            items.append(
                _analysis_row(
                    stock,
                    indicator,
                    snapshot,
                    sector_strength=strength_map.get(stock.id),
                )
            )

    if sector or industry:
        q = select(Stock).where(Stock.is_active.is_(True))
        if sector_stock_ids is not None:
            if not sector_stock_ids:
                q = q.where(Stock.id == -1)
            else:
                q = q.where(Stock.id.in_(sector_stock_ids))
        if industry_stock_ids is not None:
            if not industry_stock_ids:
                q = q.where(Stock.id == -1)
            else:
                q = q.where(Stock.id.in_(industry_stock_ids))
        if exchange:
            q = q.where(func.upper(Stock.exchange) == exchange.upper())
        have = {row.symbol for row in items}
        for stock in session.scalars(q).all():
            if stock.symbol in have:
                continue
            items.append(_minimal_analysis_row(stock))

    reverse = sort_dir.lower() != "asc"
    key_map = {
        "symbol": lambda r: r.symbol,
        "ltp": lambda r: float(r.ltp) if r.ltp is not None else -1e18,
        "overall": lambda r: float(r.overall) if r.overall is not None else -1e18,
        "momentum_score": lambda r: float(r.momentum_score) if r.momentum_score is not None else -1e18,
        "return_1m_pct": lambda r: r.return_1m_pct if r.return_1m_pct is not None else -1e18,
        "return_3m_pct": lambda r: r.return_3m_pct if r.return_3m_pct is not None else -1e18,
        "company_strength": lambda r: float(r.company_strength) if r.company_strength is not None else -1e18,
        "industry_strength": lambda r: float(r.industry_strength) if r.industry_strength is not None else -1e18,
    }
    key_fn = key_map.get(sort_by, key_map["symbol"])
    items.sort(key=key_fn, reverse=reverse)
    total = len(items)
    return StockAnalysisResponse(items=items[:limit], total=total, scanned=total)


def sector_stocks(
    session: Session,
    name: str,
    *,
    exchange: str | None = None,
    sort_by: str = "symbol",
    sort_dir: str = "asc",
    limit: int = 150,
) -> StockAnalysisResponse:
    return _constituent_stocks(
        session,
        sector=_norm_name(name),
        exchange=exchange,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
    )


def industry_stocks(
    session: Session,
    name: str,
    *,
    exchange: str | None = None,
    sort_by: str = "symbol",
    sort_dir: str = "asc",
    limit: int = 150,
) -> StockAnalysisResponse:
    return _constituent_stocks(
        session,
        industry=_norm_name(name),
        exchange=exchange,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
    )
