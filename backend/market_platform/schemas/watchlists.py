from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class WatchlistItemOut(BaseModel):
    symbol: str
    name: str
    exchange: str
    position: int
    price: Decimal | None = None
    change: Decimal | None = None
    change_pct: float | None = None
    sparkline: list[float] = Field(default_factory=list)
    as_of: date | None = None


class WatchlistResponse(BaseModel):
    id: int
    name: str
    client_key: str
    items: list[WatchlistItemOut] = Field(default_factory=list)
    as_of: date | None = None


class WatchlistReplaceRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list, max_length=50)


class WatchlistAddRequest(BaseModel):
    symbol: str
    exchange: str | None = None
