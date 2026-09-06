from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StrengthRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    parent_sector: str | None = None
    as_of: date | None = None
    strength_score: Decimal | None = None
    momentum_score: Decimal | None = None
    relative_strength_score: Decimal | None = None
    breadth_score: Decimal | None = None
    risk_score: Decimal | None = None
    rank: int | None = None
    rank_change: int | None = None
    score_change_1w: Decimal | None = None
    score_change_1m: Decimal | None = None
    score_change_3m: Decimal | None = None
    score_1w_ago: Decimal | None = None
    score_1m_ago: Decimal | None = None
    score_3m_ago: Decimal | None = None
    rotation_state: str | None = None
    is_gaining_strength: bool | None = None
    constituent_count: int | None = None
    return_1m: Decimal | None = None
    return_3m: Decimal | None = None
    return_3m_cw: Decimal | None = None
    return_3m_ew: Decimal | None = None
    return_3m_index: Decimal | None = None
    return_3m_source: str | None = None  # index | cap_weight | equal_weight
    above_50dma_pct: Decimal | None = None


class SectorScoreRow(StrengthRow):
    """Backward-compatible alias fields used by existing frontend."""

    sector_name: str | None = None
    sector_strength_score: Decimal | None = None


class IndustryScoreRow(StrengthRow):
    industry_name: str | None = None
    industry_strength_score: Decimal | None = None


class SectorListResponse(BaseModel):
    items: list[SectorScoreRow]
    industries: list[IndustryScoreRow] = Field(default_factory=list)
    gaining: list[SectorScoreRow] = Field(default_factory=list)
    as_of: date | None = None
