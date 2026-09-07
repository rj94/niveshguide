"""v1 stubs for MarketPlatform modules not backed by Trade data yet."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy.orm import Session

from database.session import get_session
from market_platform.schemas.markets import MarketEtfsResponse, MarketIndicesResponse, MarketsOverviewResponse
from market_platform.schemas.news import (
    NewsCategoriesResponse,
    NewsListResponse,
    NewsRefreshResponse,
    SummarizeResponse,
    TrendingNewsResponse,
)
from market_platform.schemas.portfolio import PortfolioResponse, PortfolioSummary
from market_platform.schemas.sectors import IndustryScoreRow, SectorListResponse, SectorScoreRow
from market_platform.schemas.stocks import StockAnalysisResponse
from market_platform.schemas.watchlists import WatchlistResponse
from market_platform.services import markets as markets_service

router_markets = APIRouter()
router_sectors = APIRouter()
router_news = APIRouter()
router_watchlists = APIRouter()
router_portfolio = APIRouter()


@router_markets.get("/overview", response_model=MarketsOverviewResponse)
def markets_overview(db: Session = Depends(get_session)) -> MarketsOverviewResponse:
    return markets_service.markets_overview(db)


@router_markets.get("/indices", response_model=MarketIndicesResponse)
def list_market_indices(db: Session = Depends(get_session)) -> MarketIndicesResponse:
    return markets_service.list_market_indices(db)


@router_markets.get("/etfs", response_model=MarketEtfsResponse)
def list_market_etfs(db: Session = Depends(get_session)) -> MarketEtfsResponse:
    return markets_service.list_market_etfs(db)


@router_sectors.get("", response_model=SectorListResponse)
def list_sectors(
    limit: int = Query(default=100),
    min_constituents: int = Query(default=0),
    gaining_only: bool = Query(default=False),
    db: Session = Depends(get_session),
) -> SectorListResponse:
    from market_platform.services import sectors as sectors_service

    return sectors_service.list_sectors(
        db, limit=limit, min_constituents=min_constituents, gaining_only=gaining_only
    )


@router_sectors.get("/by-name/{name}", response_model=SectorScoreRow)
def get_sector(name: str, db: Session = Depends(get_session)) -> SectorScoreRow:
    from market_platform.services import sectors as sectors_service

    return sectors_service.get_sector(db, name)


@router_sectors.get("/by-name/{name}/stocks", response_model=StockAnalysisResponse)
def sector_stocks(
    name: str,
    exchange: str | None = Query(default="NSE"),
    sort_by: str = Query(default="overall"),
    sort_dir: str = Query(default="desc"),
    limit: int = Query(default=150),
    db: Session = Depends(get_session),
) -> StockAnalysisResponse:
    from market_platform.services import sectors as sectors_service

    return sectors_service.sector_stocks(
        db, name, exchange=exchange, sort_by=sort_by, sort_dir=sort_dir, limit=limit
    )


@router_sectors.get("/industries/by-name/{name}", response_model=IndustryScoreRow)
def get_industry(name: str, db: Session = Depends(get_session)) -> IndustryScoreRow:
    from market_platform.services import sectors as sectors_service

    return sectors_service.get_industry(db, name)


@router_sectors.get("/industries/by-name/{name}/stocks", response_model=StockAnalysisResponse)
def industry_stocks(
    name: str,
    exchange: str | None = Query(default="NSE"),
    sort_by: str = Query(default="overall"),
    sort_dir: str = Query(default="desc"),
    limit: int = Query(default=150),
    db: Session = Depends(get_session),
) -> StockAnalysisResponse:
    from market_platform.services import sectors as sectors_service

    return sectors_service.industry_stocks(
        db, name, exchange=exchange, sort_by=sort_by, sort_dir=sort_dir, limit=limit
    )


@router_news.get("", response_model=NewsListResponse)
def list_news() -> NewsListResponse:
    return NewsListResponse(items=[], total=0, limit=50, offset=0)


@router_news.get("/categories", response_model=NewsCategoriesResponse)
def news_categories() -> NewsCategoriesResponse:
    return NewsCategoriesResponse(categories=[], total=0)


@router_news.get("/trending", response_model=TrendingNewsResponse)
def news_trending() -> TrendingNewsResponse:
    return TrendingNewsResponse(items=[])


@router_news.post("/refresh", response_model=NewsRefreshResponse)
def news_refresh() -> NewsRefreshResponse:
    return NewsRefreshResponse(
        fetched=0,
        created=0,
        processed=0,
        skipped=0,
        days=0,
        exchanges=[],
        used_seed=False,
        live_count=0,
    )


@router_news.get("/{event_id}")
def news_event(event_id: int):
    return {
        "id": event_id,
        "event_type": "info",
        "category": "general",
        "category_label": "General",
        "title": "Unavailable",
        "what_happened": "News not configured in Trade v1.",
        "announcement_id": 0,
    }


@router_news.post("/{event_id}/summarize", response_model=SummarizeResponse)
def news_summarize(event_id: int) -> SummarizeResponse:
    return SummarizeResponse(
        id=event_id,
        summary_simple="News summarization is not available in this Trade build.",
        extraction_method=None,
        llm_used=False,
    )


def _empty_watchlist(client_key: str) -> WatchlistResponse:
    return WatchlistResponse(id=0, name="Watchlist", client_key=client_key, items=[], as_of=date.today())


@router_watchlists.get("/me", response_model=WatchlistResponse)
def my_watchlist(x_client_key: str | None = Header(default="anon")) -> WatchlistResponse:
    return _empty_watchlist(x_client_key or "anon")


@router_watchlists.put("/me/items", response_model=WatchlistResponse)
def replace_watchlist(x_client_key: str | None = Header(default="anon")) -> WatchlistResponse:
    return _empty_watchlist(x_client_key or "anon")


@router_watchlists.post("/me/items", response_model=WatchlistResponse)
def add_watchlist(x_client_key: str | None = Header(default="anon")) -> WatchlistResponse:
    return _empty_watchlist(x_client_key or "anon")


@router_watchlists.delete("/me/items/{symbol}", response_model=WatchlistResponse)
def remove_watchlist(symbol: str, x_client_key: str | None = Header(default="anon")) -> WatchlistResponse:
    return _empty_watchlist(x_client_key or "anon")


def _empty_portfolio(client_key: str) -> PortfolioResponse:
    zero = Decimal("0")
    return PortfolioResponse(
        id=0,
        name="Portfolio",
        client_key=client_key,
        holdings=[],
        summary=PortfolioSummary(
            invested_value=zero,
            current_value=zero,
            total_pnl=zero,
            total_pnl_pct=0.0,
            day_pnl=zero,
            holdings_count=0,
        ),
        as_of=date.today(),
    )


@router_portfolio.get("/me", response_model=PortfolioResponse)
def my_portfolio(x_client_key: str | None = Header(default="anon")) -> PortfolioResponse:
    return _empty_portfolio(x_client_key or "anon")


@router_portfolio.post("/me/import", response_model=PortfolioResponse)
async def import_portfolio(
    file: UploadFile = File(...),
    x_client_key: str | None = Header(default="anon"),
) -> PortfolioResponse:
    _ = file
    return _empty_portfolio(x_client_key or "anon")


@router_portfolio.delete("/me/holdings", response_model=PortfolioResponse)
def clear_portfolio(x_client_key: str | None = Header(default="anon")) -> PortfolioResponse:
    return _empty_portfolio(x_client_key or "anon")
