from fastapi import APIRouter

from market_platform.api import markets, news, portfolio, screener, sectors, stocks, strategies, watchlists

api_router = APIRouter()


@api_router.get("")
@api_router.get("/")
def api_v1_index() -> dict:
    return {
        "ok": True,
        "prefix": "/api/v1",
        "routes": [
            "/stocks",
            "/screener",
            "/strategies",
            "/markets/overview",
            "/markets/indices",
            "/markets/etfs",
            "/sectors",
            "/watchlists/me",
            "/portfolio/me",
            "/news",
        ],
        "docs": "/docs",
        "ui": "http://127.0.0.1:3000",
    }


api_router.include_router(stocks.router, prefix="/stocks", tags=["platform-stocks"])
api_router.include_router(screener.router, prefix="/screener", tags=["platform-screener"])
api_router.include_router(sectors.router, prefix="/sectors", tags=["platform-sectors"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["platform-strategies"])
api_router.include_router(markets.router, prefix="/markets", tags=["platform-markets"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["platform-watchlists"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["platform-portfolio"])
api_router.include_router(news.router, prefix="/news", tags=["platform-news"])
