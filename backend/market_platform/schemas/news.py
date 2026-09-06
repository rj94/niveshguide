from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class EventAttributeOut(BaseModel):
    key: str
    value_text: str | None = None
    value_number: Decimal | None = None
    unit: str | None = None
    source_text: str | None = None
    extraction_method: str
    confidence: Decimal | None = None


class NewsMetrics(BaseModel):
    revenue_yoy_pct: float | None = None
    revenue_qoq_pct: float | None = None
    ebitda_yoy_pct: float | None = None
    pat_yoy_pct: float | None = None
    pat_qoq_pct: float | None = None
    eps_yoy_pct: float | None = None
    ocf_yoy_pct: float | None = None
    revenue_cr: float | None = None
    ebitda_cr: float | None = None
    pat_cr: float | None = None
    order_value_cr: float | None = None
    order_to_revenue_pct: float | None = None
    materiality_band: str | None = None


class NewsEventCard(BaseModel):
    id: int
    event_type: str
    category: str
    category_label: str
    title: str
    what_happened: str
    summary_simple: str | None = None
    impact_score: Decimal | None = None
    confidence: Decimal | None = None
    sentiment: str | None = None
    published_at: datetime | None = None
    price_reaction_pct: Decimal | None = None
    extraction_method: str | None = None
    stock_id: int | None = None
    symbol: str | None = None
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    last_price: Decimal | None = None
    change_pct: float | None = None
    source_url: str | None = None
    announcement_id: int
    attributes: list[EventAttributeOut] = Field(default_factory=list)
    metrics: NewsMetrics = Field(default_factory=NewsMetrics)
    sector_profile: str = "general"
    sector_kpis: dict[str, float | None] = Field(default_factory=dict)


class NewsListResponse(BaseModel):
    items: list[NewsEventCard]
    total: int
    limit: int
    offset: int


class NewsCategoryCount(BaseModel):
    key: str
    label: str
    count: int


class NewsCategoriesResponse(BaseModel):
    categories: list[NewsCategoryCount]
    total: int


class TrendingStockOut(BaseModel):
    rank: int
    stock_id: int
    symbol: str
    company_name: str
    exchange: str
    event_count: int
    last_price: Decimal | None = None
    change_pct: float | None = None


class TrendingNewsResponse(BaseModel):
    items: list[TrendingStockOut]


class SummarizeResponse(BaseModel):
    id: int
    summary_simple: str | None
    extraction_method: str | None
    llm_used: bool


class NewsRefreshResponse(BaseModel):
    fetched: int
    created: int
    processed: int
    skipped: int
    days: int
    exchanges: list[str]
    used_seed: bool
    live_count: int
    purged_seed: int = 0
    limit: int = 0
