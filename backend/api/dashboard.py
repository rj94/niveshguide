from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import DataSourceBatch
from database.repository import overview_counts
from database.session import get_session

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_session)):
    overview = overview_counts(db)
    batches = db.scalars(select(DataSourceBatch).order_by(DataSourceBatch.batch_name)).all()
    by_trend = overview.get("by_trend") or {}
    signals = overview.get("signals_today") or {}
    return {
        "as_of": overview.get("as_of"),
        "total_active": overview.get("total_active") or 0,
        "strong_uptrend": by_trend.get("Strong Uptrend", 0),
        "uptrend": by_trend.get("Uptrend", 0) + by_trend.get("Mild Uptrend", 0),
        "neutral": by_trend.get("Neutral", 0),
        "downtrend": by_trend.get("Downtrend", 0),
        "strong_downtrend": by_trend.get("Strong Downtrend", 0),
        "fresh_bullish_crossovers": signals.get("BULLISH_3_7_CROSSOVER", 0),
        "fresh_bearish_crossovers": signals.get("BEARISH_3_7_CROSSOVER", 0),
        "new_52_week_highs": signals.get("NEW_52_WEEK_HIGH", 0),
        "golden_crosses": signals.get("GOLDEN_CROSS", 0),
        "by_trend": by_trend,
        "signals_today": signals,
        "batches": [
            {
                "batch_name": batch.batch_name,
                "spreadsheet_id": batch.spreadsheet_id,
                "gid": batch.gid,
                "sheet_name": batch.sheet_name,
                "status": batch.status,
                "last_successful_sync": batch.last_successful_sync.isoformat() if batch.last_successful_sync else None,
                "last_attempted_sync": batch.last_attempted_sync.isoformat() if batch.last_attempted_sync else None,
                "error_message": batch.error_message,
                "retry_count": batch.retry_count,
                "url": (
                    f"https://docs.google.com/spreadsheets/d/{batch.spreadsheet_id}/edit"
                    + (f"?gid={batch.gid}#gid={batch.gid}" if batch.gid is not None else "")
                ),
            }
            for batch in batches
        ],
        "source_workbook": next(
            (
                f"https://docs.google.com/spreadsheets/d/{batch.spreadsheet_id}/edit"
                + (f"?gid={batch.gid}#gid={batch.gid}" if batch.gid is not None else "")
                for batch in batches
                if batch.status == "ACTIVE"
            ),
            "https://docs.google.com/spreadsheets/d/1xzT_B1vlCr_MlYN6a-CVfxDUbB8BhZiqfQUJkPGPBBk/edit?gid=0#gid=0",
        ),
    }
