"""Helpers to load screener.in tables into MarketPlatform snapshots."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from database.models import StockFinancialPeriod, StockFundamental, StockOwnership
from market_platform.schemas.stocks import (
    FundamentalMetricsSnapshot,
    FundamentalsSnapshot,
    OwnershipSnapshot,
    PeriodFinancialRow,
)


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(float(value)))
    except (TypeError, ValueError):
        return None


def latest_fundamental(session: Session, stock_id: int) -> StockFundamental | None:
    return session.scalar(
        select(StockFundamental)
        .where(StockFundamental.stock_id == stock_id)
        .order_by(desc(StockFundamental.as_of_date))
        .limit(1)
    )


def latest_ownership(session: Session, stock_id: int) -> StockOwnership | None:
    return session.scalar(
        select(StockOwnership)
        .where(StockOwnership.stock_id == stock_id)
        .order_by(desc(StockOwnership.id))
        .limit(1)
    )


def ownership_snapshot(session: Session, stock_id: int) -> OwnershipSnapshot:
    row = latest_ownership(session, stock_id)
    if not row:
        return OwnershipSnapshot()
    return OwnershipSnapshot(
        period=row.period_label,
        promoter_pct=_dec(row.promoter_pct),
        fii_pct=_dec(row.fii_pct),
        dii_pct=_dec(row.dii_pct),
        public_pct=_dec(row.public_pct),
        promoter_pledge_pct=_dec(row.promoter_pledge_pct),
    )


def fundamentals_from_db(
    session: Session, stock_id: int, *, sheet_eps: Any = None, sheet_pe: Any = None
) -> tuple[FundamentalsSnapshot, FundamentalMetricsSnapshot]:
    row = latest_fundamental(session, stock_id)
    if not row:
        return (
            FundamentalsSnapshot(eps=_dec(sheet_eps)),
            FundamentalMetricsSnapshot(
                pe_ttm=_dec(sheet_pe),
                source="sheets" if sheet_pe is not None else None,
            ),
        )
    fundamentals = FundamentalsSnapshot(
        period=row.as_of_date,
        period_label=row.as_of_date.isoformat(),
        period_type="annual",
        revenue=_dec(row.sales),
        pat=_dec(row.pat),
        eps=_dec(row.eps) if row.eps is not None else _dec(sheet_eps),
        roe=_dec(row.roe),
        roce=_dec(row.roce),
        debt_equity=_dec(row.debt_equity),
    )
    metrics = FundamentalMetricsSnapshot(
        as_of=row.as_of_date,
        latest_annual_period=row.as_of_date,
        roe=_dec(row.roe),
        roce=_dec(row.roce),
        debt_equity=_dec(row.debt_equity),
        pe_ttm=_dec(row.pe) if row.pe is not None else _dec(sheet_pe),
        pb=_dec(row.book_value),
        source="screener.in",
    )
    return fundamentals, metrics


def _metric_map(rows: list[StockFinancialPeriod]) -> dict[str, dict[str, float | None]]:
    """period -> metric_norm -> value"""
    out: dict[str, dict[str, float | None]] = defaultdict(dict)
    for row in rows:
        key = (row.metric or "").strip().lower().rstrip("+").strip()
        out[row.period_label][key] = float(row.value_num) if row.value_num is not None else None
    return out


def period_history(session: Session, stock_id: int, section: str, *, limit: int = 12) -> list[PeriodFinancialRow]:
    rows = session.scalars(
        select(StockFinancialPeriod).where(
            StockFinancialPeriod.stock_id == stock_id,
            StockFinancialPeriod.section == section,
        )
    ).all()
    if not rows:
        return []
    by_period = _metric_map(rows)
    # Keep periods in appearance order from DB (approx chronological by label sort is weak; use insert order)
    periods: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row.period_label not in seen:
            seen.add(row.period_label)
            periods.append(row.period_label)
    periods = periods[-limit:]
    history: list[PeriodFinancialRow] = []
    for label in periods:
        metrics = by_period.get(label) or {}
        history.append(
            PeriodFinancialRow(
                period=date.today(),
                period_label=label,
                revenue=_dec(metrics.get("sales") or metrics.get("revenue")),
                ebitda=_dec(metrics.get("operating profit") or metrics.get("ebitda")),
                pat=_dec(metrics.get("net profit") or metrics.get("pat") or metrics.get("profit after tax")),
                eps=_dec(metrics.get("eps in rs") or metrics.get("eps")),
                free_cashflow=_dec(metrics.get("free cash flow") or metrics.get("cash from operating activity")),
                total_debt=_dec(metrics.get("borrowings") or metrics.get("total debt")),
                equity=_dec(metrics.get("equity capital") or metrics.get("reserves")),
            )
        )
    return history
