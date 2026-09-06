from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PortfolioHoldingOut(BaseModel):
    symbol: str
    name: str
    exchange: str
    quantity: Decimal
    avg_price: Decimal
    last_price: Decimal | None = None
    day_change: Decimal | None = None
    day_change_pct: float | None = None
    invested_value: Decimal
    current_value: Decimal | None = None
    pnl: Decimal | None = None
    pnl_pct: float | None = None
    weight_pct: float | None = None
    sector: str | None = None
    isin: str | None = None
    broker_symbol: str | None = None
    as_of: date | None = None


class PortfolioImportOut(BaseModel):
    id: int
    broker: str
    filename: str
    row_count: int
    matched_count: int
    unmatched_symbols: list[str] = Field(default_factory=list)
    imported_at: str | None = None


class PortfolioSummary(BaseModel):
    invested_value: Decimal
    current_value: Decimal
    total_pnl: Decimal
    total_pnl_pct: float | None = None
    day_pnl: Decimal
    holdings_count: int


class PortfolioResponse(BaseModel):
    id: int
    name: str
    client_key: str
    broker: str | None = None
    last_import_at: str | None = None
    summary: PortfolioSummary
    holdings: list[PortfolioHoldingOut]
    recent_imports: list[PortfolioImportOut] = Field(default_factory=list)
    as_of: date | None = None
    refreshed_at: str | None = None
