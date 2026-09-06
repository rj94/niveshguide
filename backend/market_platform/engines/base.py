from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CriterionState = Literal["pass", "partial", "fail", "unknown"]
RatingBand = Literal["strong_buy", "buy", "watch", "avoid"]


@dataclass
class StrategyCriterion:
    key: str
    label: str
    state: CriterionState
    detail: str | None = None
    value: float | None = None
    weight: float = 1.0


@dataclass
class StrategyResult:
    score: float
    rating: RatingBand
    checklist: list[StrategyCriterion] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def rating_from_score(score: float) -> RatingBand:
    if score >= 80:
        return "strong_buy"
    if score >= 65:
        return "buy"
    if score >= 45:
        return "watch"
    return "avoid"


def score_from_criteria(criteria: list[StrategyCriterion]) -> float:
    """Weighted score: pass=1, partial=0.5, fail/unknown=0."""
    if not criteria:
        return 0.0
    total_w = 0.0
    earned = 0.0
    for c in criteria:
        w = max(c.weight, 0.0)
        total_w += w
        if c.state == "pass":
            earned += w
        elif c.state == "partial":
            earned += 0.5 * w
    if total_w <= 0:
        return 0.0
    return round(100.0 * earned / total_w, 1)


def fnum(value: Any) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n


def pct_state(
    value: float | None,
    pass_at: float,
    partial_at: float | None = None,
    *,
    higher_is_better: bool = True,
) -> CriterionState:
    if value is None:
        return "unknown"
    if higher_is_better:
        if value >= pass_at:
            return "pass"
        if partial_at is not None and value >= partial_at:
            return "partial"
        return "fail"
    if value <= pass_at:
        return "pass"
    if partial_at is not None and value <= partial_at:
        return "partial"
    return "fail"
