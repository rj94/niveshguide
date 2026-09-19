from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.settings import get_settings
from database.session import get_session
from market_platform.schemas.ai import AiQueryRequest, AiQueryResponse, AiStatusResponse
from market_platform.services.ai_query import run_ai_query

router = APIRouter()

DISABLED_DETAIL = {
    "code": "ai_disabled",
    "message": "AI Search is not enabled on this server yet. It will appear here once the operator turns it on.",
}


@router.get("/status", response_model=AiStatusResponse)
def ai_status() -> AiStatusResponse:
    settings = get_settings()
    if not settings.ai_enabled:
        return AiStatusResponse(enabled=False)
    return AiStatusResponse(
        enabled=True,
        provider=settings.ai_provider,
        model=settings.ai_model,
    )


@router.post("/query", response_model=AiQueryResponse)
def query_ai(
    payload: AiQueryRequest,
    db: Session = Depends(get_session),
) -> AiQueryResponse:
    settings = get_settings()
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail=DISABLED_DETAIL)
    return run_ai_query(db, payload, settings=settings)
