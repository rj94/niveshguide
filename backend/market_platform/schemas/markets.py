from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class MarketQuoteCard(BaseModel):
    id: str
    symbol: str
    name: str
    kind: str  # index | commodity | fx | sector
    exchange: str | None = None
    value: Decimal | None = None
    change: Decimal | None = None
    change_pct: float | None = None
    sparkline: list[float] = Field(default_factory=list)
    as_of: date | None = None
    # Sector-only extras
    score: Decimal | None = None
    score_change_1w: Decimal | None = None
    return_1m: Decimal | None = None
    rotation_state: str | None = None
    # Canonical sector for ETF → sector stocks click-through
    sector_name: str | None = None


class MarketsOverviewResponse(BaseModel):
    indices: list[MarketQuoteCard] = Field(default_factory=list)
    sector_etfs: list[MarketQuoteCard] = Field(default_factory=list)
    commodities: list[MarketQuoteCard] = Field(default_factory=list)
    sectors: list[MarketQuoteCard] = Field(default_factory=list)
    as_of: date | None = None


class MarketIndicesResponse(BaseModel):
    items: list[MarketQuoteCard] = Field(default_factory=list)
    as_of: date | None = None
