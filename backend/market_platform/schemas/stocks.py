from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    company_name: str
    exchange: str
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    last_price: Decimal | None = None
    change_pct: float | None = None
    has_prices: bool = False


class StockListResponse(BaseModel):
    items: list[StockSummary]
    total: int


class Quote(BaseModel):
    price: Decimal | None = None
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_pct: float | None = None
    as_of: date | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    volume: int | None = None


class ScoreCard(BaseModel):
    as_of: date | None = None
    overall: Decimal | None = None
    quality: Decimal | None = None
    growth: Decimal | None = None
    value: Decimal | None = None
    momentum: Decimal | None = None
    financial_health: Decimal | None = None
    management: Decimal | None = None
    ownership: Decimal | None = None
    risk: Decimal | None = None
    canslim: Decimal | None = None
    technical: Decimal | None = None
    sector_strength: Decimal | None = None
    industry_strength: Decimal | None = None
    # V1 momentum breakdown
    return_score: Decimal | None = None
    dma_score: Decimal | None = None
    volume_score: Decimal | None = None
    result_score: Decimal | None = None
    momentum_acceleration: Decimal | None = None
    momentum_category: str | None = None
    source: str = "unavailable"


class FundamentalsSnapshot(BaseModel):
    period: date | None = None
    period_label: str | None = None
    period_type: str | None = None  # quarterly | annual
    revenue: Decimal | None = None
    ebitda: Decimal | None = None
    ebit: Decimal | None = None
    pat: Decimal | None = None
    eps: Decimal | None = None
    operating_cashflow: Decimal | None = None
    free_cashflow: Decimal | None = None
    total_assets: Decimal | None = None
    total_debt: Decimal | None = None
    cash: Decimal | None = None
    equity: Decimal | None = None
    roe: Decimal | None = None
    roce: Decimal | None = None
    roa: Decimal | None = None
    debt_equity: Decimal | None = None
    ebitda_margin: Decimal | None = None
    pat_margin: Decimal | None = None
    current_ratio: Decimal | None = None


class FundamentalMetricsSnapshot(BaseModel):
    as_of: date | None = None
    latest_annual_period: date | None = None
    latest_quarter_period: date | None = None
    revenue_cagr_3y: Decimal | None = None
    revenue_cagr_5y: Decimal | None = None
    ebitda_cagr_3y: Decimal | None = None
    pat_cagr_3y: Decimal | None = None
    eps_cagr_3y: Decimal | None = None
    fcf_cagr_3y: Decimal | None = None
    revenue_growth_yoy: Decimal | None = None
    pat_growth_yoy: Decimal | None = None
    roe: Decimal | None = None
    roce: Decimal | None = None
    roa: Decimal | None = None
    ebitda_margin: Decimal | None = None
    pat_margin: Decimal | None = None
    debt_equity: Decimal | None = None
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None
    peg: Decimal | None = None
    ev_ebitda: Decimal | None = None
    source: str | None = None


class PeriodFinancialRow(BaseModel):
    period: date
    period_label: str | None = None
    revenue: Decimal | None = None
    ebitda: Decimal | None = None
    pat: Decimal | None = None
    eps: Decimal | None = None
    free_cashflow: Decimal | None = None
    total_debt: Decimal | None = None
    equity: Decimal | None = None


class OwnershipSnapshot(BaseModel):
    period: str | None = None
    promoter_pct: Decimal | None = None
    fii_pct: Decimal | None = None
    dii_pct: Decimal | None = None
    public_pct: Decimal | None = None
    promoter_pledge_pct: Decimal | None = None


class TechnicalsSnapshot(BaseModel):
    sma_3: Decimal | None = None
    sma_7: Decimal | None = None
    sma_20: Decimal | None = None
    sma_21: Decimal | None = None
    sma_50: Decimal | None = None
    sma_200: Decimal | None = None
    sma_21_signal: str | None = None
    sma_50_signal: str | None = None
    sma_200_signal: str | None = None
    rsi_14: float | None = None
    high_52w: Decimal | None = None
    low_52w: Decimal | None = None
    distance_from_52w_high_pct: float | None = None
    return_1m_pct: float | None = None
    return_3m_pct: float | None = None
    return_6m_pct: float | None = None
    return_1y_pct: float | None = None
    trend: str | None = None
    trend_score: int | None = None
    crossover_3_7: bool | None = None
    above_ma_21: bool | None = None
    ma21_gt_ma50: bool | None = None
    above_ma_200: bool | None = None
    golden_cross: bool | None = None
    pe: Decimal | None = None
    eps: Decimal | None = None
    day_high: Decimal | None = None
    prev_close: Decimal | None = None
    avg_volume_20: float | None = None
    avg_volume_3m: float | None = None
    avg_volume_6m: float | None = None
    avg_volume_1y: float | None = None
    volume_ratio: float | None = None
    distance_20_dma: float | None = None
    distance_50_dma: float | None = None
    distance_200_dma: float | None = None
    momentum_score: float | None = None
    momentum_acceleration: float | None = None
    momentum_category: str | None = None
    return_score: float | None = None
    dma_score: float | None = None
    volume_score: float | None = None
    result_score: float | None = None


class StockAnalysisRow(BaseModel):
    id: int
    symbol: str
    company_name: str
    exchange: str
    sector: str | None = None
    industry: str | None = None
    ltp: Decimal | None = None
    change_pct: float | None = None
    sma_3: Decimal | None = None
    sma_7: Decimal | None = None
    sma_20: Decimal | None = None
    sma_21: Decimal | None = None
    sma_50: Decimal | None = None
    sma_200: Decimal | None = None
    price_above_50_above_200: bool | None = None
    sma_50_above_200: bool | None = None
    crossover_3_7: bool | None = None
    above_ma_21: bool | None = None
    ma21_gt_ma50: bool | None = None
    above_ma_200: bool | None = None
    volume: int | None = None
    avg_volume_20: float | None = None
    avg_volume_1w: float | None = None
    avg_volume_3m: float | None = None
    avg_volume_6m: float | None = None
    avg_volume_1y: float | None = None
    volume_ratio: float | None = None
    volume_mover: bool | None = None
    volume_gainer: bool | None = None
    return_1m_pct: float | None = None
    return_3m_pct: float | None = None
    return_6m_pct: float | None = None
    return_12m_pct: float | None = None
    distance_from_52w_high: float | None = None
    pe: Decimal | None = None
    eps: Decimal | None = None
    market_cap: Decimal | None = None
    trend: str | None = None
    trend_score: int | None = None
    company_strength: Decimal | None = None
    company_strength_source: str = "unavailable"
    overall: Decimal | None = None
    sector_strength: Decimal | None = None
    industry_strength: Decimal | None = None
    return_score: Decimal | None = None
    dma_score: Decimal | None = None
    volume_score: Decimal | None = None
    result_score: Decimal | None = None
    momentum_score: Decimal | None = None
    momentum_acceleration: Decimal | None = None
    momentum_category: str | None = None
    as_of: date | None = None


class StockAnalysisResponse(BaseModel):
    items: list[StockAnalysisRow]
    total: int
    scanned: int = 0


class PriceBar(BaseModel):
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None


class StockDetail(BaseModel):
    id: int
    symbol: str
    company_name: str
    exchange: str
    isin: str | None = None
    sector: str | None = None
    industry: str | None = None
    industries: list[str] = Field(default_factory=list)
    index_memberships: list[str] = Field(default_factory=list)
    market_cap: Decimal | None = None
    listing_date: date | None = None
    status: str
    quote: Quote
    scores: ScoreCard
    fundamentals: FundamentalsSnapshot
    annual_fundamentals: FundamentalsSnapshot
    fundamental_metrics: FundamentalMetricsSnapshot
    quarterly_history: list[PeriodFinancialRow] = Field(default_factory=list)
    annual_history: list[PeriodFinancialRow] = Field(default_factory=list)
    ownership: OwnershipSnapshot
    technicals: TechnicalsSnapshot
    prices: list[PriceBar] = Field(default_factory=list)
