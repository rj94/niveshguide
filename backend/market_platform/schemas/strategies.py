from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

StrategySlug = Literal["canslim", "garp", "darvas", "sepa"]
RatingBand = Literal["strong_buy", "buy", "watch", "avoid"]
CriterionState = Literal["pass", "partial", "fail", "unknown"]


class StrategyMeta(BaseModel):
    slug: StrategySlug
    name: str
    short_name: str
    description: str
    filters: list["StrategyFilterDef"] = Field(default_factory=list)


class StrategyFilterDef(BaseModel):
    key: str
    label: str
    detail: str


class CriterionStatus(BaseModel):
    key: str
    label: str
    state: CriterionState
    detail: str | None = None
    value: float | None = None


class StrategyStockRow(BaseModel):
    id: int
    symbol: str
    company_name: str
    exchange: str
    sector: str | None = None
    industry: str | None = None
    ltp: Decimal | None = None
    change_pct: float | None = None
    score: float
    rating: RatingBand
    rank: int
    metrics: dict[str, Any] = Field(default_factory=dict)
    checklist: list[CriterionStatus] = Field(default_factory=list)
    as_of: date | None = None


class RatingCounts(BaseModel):
    strong_buy: int = 0
    buy: int = 0
    watch: int = 0
    avoid: int = 0
    total: int = 0


class MarketTrend(BaseModel):
    label: Literal["Bullish", "Neutral", "Bearish"]
    detail: str
    proxy_symbol: str | None = None
    price: Decimal | None = None
    change_pct: float | None = None
    advances: int | None = None
    declines: int | None = None
    new_highs: int | None = None
    new_lows: int | None = None


class DistributionSlice(BaseModel):
    key: RatingBand
    label: str
    count: int
    pct: float


class TrendPoint(BaseModel):
    label: str
    strong_buy: int
    buy: int
    watch: int
    avoid: int


class InsightItem(BaseModel):
    text: str
    tone: Literal["positive", "neutral", "warning"] = "neutral"


class DataCoverage(BaseModel):
    scanned: int = 0
    with_fundamentals: int = 0
    with_ownership: int = 0
    with_momentum: int = 0
    with_peg: int = 0
    with_eps_cagr: int = 0
    notes: list[str] = Field(default_factory=list)


class StrategySummary(BaseModel):
    market_trend: MarketTrend
    counts: RatingCounts
    distribution: list[DistributionSlice] = Field(default_factory=list)
    trend: list[TrendPoint] = Field(default_factory=list)
    insights: list[InsightItem] = Field(default_factory=list)
    data_coverage: DataCoverage | None = None


class StrategyRunResponse(BaseModel):
    strategy: StrategyMeta
    summary: StrategySummary
    items: list[StrategyStockRow]
    total: int
    scanned: int
    selected_symbol: str | None = None


class StrategyListResponse(BaseModel):
    items: list[StrategyMeta]
