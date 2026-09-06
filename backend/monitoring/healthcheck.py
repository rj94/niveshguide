from fastapi import APIRouter

from config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "spreadsheet_id": settings.google_spreadsheet_id,
        "gid": settings.google_sheet_gid,
        "has_service_account": settings.service_account_path is not None,
        "has_oauth_client": settings.oauth_client_path is not None,
        "has_oauth_token": settings.token_path.exists(),
        "workbook": f"https://docs.google.com/spreadsheets/d/{settings.google_spreadsheet_id}/edit?gid={settings.google_sheet_gid}",
    }
