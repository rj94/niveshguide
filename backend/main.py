from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dashboard import router as dashboard_router
from api.screener import router as screener_router
from api.stocks import router as stocks_router
from api.trends import router as trends_router
from config.settings import get_settings
from database.session import init_db
from monitoring.healthcheck import router as health_router
from market_platform.api.router import api_router as platform_api_router

settings = get_settings()

app = FastAPI(
    title="NiveshGuide API",
    description=(
        "NiveshGuide market platform API for NSE stocks. Live snapshots are ingested from "
        "the six NSE batch Google Spreadsheets configured in backend/config/batches.yaml. "
        "MarketPlatform-compatible routes live under /api/v1."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # LAN / Expo web previews (native React Native fetch does not enforce CORS)
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(stocks_router)
app.include_router(screener_router)
app.include_router(trends_router)
app.include_router(platform_api_router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {
        "service": "NiveshGuide API",
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
        "ui": "https://niveshguide.com",
    }


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if settings.scheduler_enabled:
        from scheduler.daily_update import start_scheduler

        start_scheduler()
