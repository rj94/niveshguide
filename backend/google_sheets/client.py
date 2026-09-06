"""OAuth Google Sheets client — authenticates as the Gmail account that owns Drive."""

from google.oauth2.credentials import Credentials

from config.settings import get_settings
from google_sheets.sheets_client import SHEETS_SCOPES, SheetsReadError, gspread_client


def get_google_client():
    """Authorize as the personal Gmail account (token.json from setup_google_auth.py)."""
    settings = get_settings()
    if settings.token_path.exists():
        import gspread

        credentials = Credentials.from_authorized_user_file(str(settings.token_path), SHEETS_SCOPES)
        return gspread.authorize(credentials)
    return gspread_client()


def open_workbook(spreadsheet_id: str | None = None):
    settings = get_settings()
    return get_google_client().open_by_key(spreadsheet_id or settings.google_spreadsheet_id)


def open_source_tab(spreadsheet_id: str | None = None, gid: int | None = None, sheet_name: str | None = None):
    settings = get_settings()
    spreadsheet = open_workbook(spreadsheet_id)
    gid = settings.google_sheet_gid if gid is None else gid
    sheet_name = sheet_name or settings.google_sheet_name
    if gid is not None:
        for worksheet in spreadsheet.worksheets():
            if int(worksheet.id) == int(gid):
                return spreadsheet, worksheet
    if sheet_name:
        try:
            return spreadsheet, spreadsheet.worksheet(sheet_name)
        except Exception as exc:
            raise SheetsReadError(f"Tab {sheet_name!r} not found") from exc
    return spreadsheet, spreadsheet.sheet1
