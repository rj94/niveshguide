from typing import Any, Literal

from pydantic import BaseModel, Field

AiIntent = Literal["screen", "compare", "explain_stock", "rank", "unknown"]
AiSortDir = Literal["asc", "desc"]


class AiQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    exchange: str = "NSE"
    limit: int = Field(default=25, ge=1, le=100)
    include_explanation: bool = True


class AiQueryFilter(BaseModel):
    field: str
    operator: str
    value: str | int | float | bool | list[Any] | None = None


class AiQueryRow(BaseModel):
    symbol: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    ltp: float | None = None
    market_cap: float | None = None
    pe: float | None = None
    trend_score: int | None = None
    trend: str | None = None
    momentum_score: float | None = None
    momentum_acceleration: float | None = None
    return_1m: float | None = None
    return_3m: float | None = None
    return_6m: float | None = None
    volume_ratio: float | None = None
    distance_from_52w_high: float | None = None


class AiQueryResponse(BaseModel):
    answer: str
    interpreted_query: str
    filters: list[AiQueryFilter]
    rows: list[AiQueryRow]
    total: int
    warnings: list[str] = Field(default_factory=list)


class AiStatusResponse(BaseModel):
    enabled: bool
    provider: str | None = None
    model: str | None = None


class SafeAiQueryPlan(BaseModel):
    intent: AiIntent = "screen"
    symbols: list[str] = Field(default_factory=list)
    sector: str | None = None
    industry: str | None = None
    filters: list[AiQueryFilter] = Field(default_factory=list)
    sort_by: str = "momentum_score"
    sort_dir: AiSortDir = "desc"
    limit: int = Field(default=25, ge=1, le=100)
