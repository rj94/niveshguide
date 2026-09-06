"""Read Google Sheets in bulk — one request per batch, never per symbol."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import yaml

from config.settings import BACKEND_ROOT, get_settings

BATCHES_PATH = BACKEND_ROOT / "config" / "batches.yaml"

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsReadError(RuntimeError):
    pass


def load_batch_config() -> list[dict[str, Any]]:
    with BATCHES_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    defaults = payload.get("defaults") or {}
    batches = []
    for item in payload.get("batches") or []:
        merged = {**defaults, **item}
        if not merged.get("sheet_name"):
            merged["sheet_name"] = None
        batches.append(merged)
    return batches


def save_batch_config(batches: list[dict[str, Any]], spreadsheet_id: str) -> None:
    payload = {
        "defaults": {"sheet_name": "STOCK_DATA", "range": "A1:J", "exchange": "NSE"},
        "batches": batches,
        "workbook": {
            "spreadsheet_id": spreadsheet_id,
            "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
        },
    }
    BATCHES_PATH.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _oauth_credentials(interactive: bool = False):
    settings = get_settings()
    token_path = settings.token_path
    client_path = settings.oauth_client_path
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SHEETS_SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds
    if not interactive or client_path is None:
        return None
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SHEETS_SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def google_login() -> str:
    """Open a browser so the owner of the Drive spreadsheet can grant access."""
    settings = get_settings()
    if settings.oauth_client_path is None:
        raise SheetsReadError(
            "Missing OAuth client file. Create a Google Cloud Desktop OAuth client, "
            "download the JSON, and save it as credentials.json in the project root "
            "(or set GOOGLE_OAUTH_CLIENT_FILE)."
        )
    creds = _oauth_credentials(interactive=True)
    if creds is None:
        raise SheetsReadError("Google login did not produce credentials.")
    return str(settings.token_path)


def gspread_client():
    """Authorize gspread via service account, else the user's Google login."""
    import gspread
    from google.oauth2.service_account import Credentials as ServiceCredentials

    settings = get_settings()
    if settings.service_account_path:
        creds = ServiceCredentials.from_service_account_file(
            str(settings.service_account_path), scopes=SHEETS_SCOPES
        )
        return gspread.authorize(creds)

    oauth = _oauth_credentials(interactive=False)
    if oauth is not None:
        return gspread.authorize(oauth)

    raise SheetsReadError(
        "Not signed in to Google. Run: python -m cli google-login\n"
        "Or set GOOGLE_SERVICE_ACCOUNT_FILE and share the Drive spreadsheet "
        "with that service-account email."
    )


def _worksheet_by_gid(spreadsheet, gid: int | None, sheet_name: str | None):
    if gid is not None:
        for worksheet in spreadsheet.worksheets():
            if int(worksheet.id) == int(gid):
                return worksheet
    if sheet_name:
        try:
            return spreadsheet.worksheet(sheet_name)
        except Exception:
            pass
    return spreadsheet.sheet1


def inspect_spreadsheet(spreadsheet_id: str) -> dict[str, Any]:
    client = gspread_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    return {
        "title": spreadsheet.title,
        "id": spreadsheet.id,
        "url": spreadsheet.url,
        "tabs": [{"title": ws.title, "gid": ws.id, "rows": ws.row_count} for ws in spreadsheet.worksheets()],
    }


def read_via_api(spreadsheet_id: str, gid: int | None, sheet_name: str | None) -> list[list[str]]:
    try:
        client = gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = _worksheet_by_gid(spreadsheet, gid, sheet_name)
        return worksheet.get_all_values()
    except SheetsReadError:
        raise
    except Exception as exc:
        raise SheetsReadError(f"Google Sheets API read failed: {exc}") from exc


def _looks_like_html(text: str) -> bool:
    start = text.lstrip()[:120].lower()
    return start.startswith("<!doctype") or start.startswith("<html") or "<title>google accounts</title>" in start


def public_csv_url(spreadsheet_id: str, gid: int | None) -> str:
    gid_value = gid if gid is not None else 0
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid_value}"


def gviz_csv_url(spreadsheet_id: str, gid: int | None = None, sheet_name: str | None = None) -> str:
    if sheet_name:
        return (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?"
            f"tqx=out:csv&sheet={quote(sheet_name)}"
        )
    gid_value = gid if gid is not None else 0
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&gid={gid_value}"


def read_via_csv(url: str) -> list[list[str]]:
    headers = {"User-Agent": "Mozilla/5.0 NSE-Stock-Trend-Screener"}
    with httpx.Client(follow_redirects=True, timeout=60.0, headers=headers) as client:
        response = client.get(url)
        if response.status_code in {401, 403}:
            raise SheetsReadError(_private_sheet_help())
        response.raise_for_status()
        text = response.text
    if _looks_like_html(text):
        raise SheetsReadError(_private_sheet_help())
    return [row for row in csv.reader(io.StringIO(text))]


def _private_sheet_help() -> str:
    return (
        "The Google Sheet is private, so it cannot be downloaded without Google Cloud login.\n"
        "Share it without Cloud:\n"
        "  1. Open the spreadsheet.\n"
        "  2. Share → General access → Anyone with the link → Viewer.\n"
        "  3. Run: python -m cli sync\n"
        "Or File → Download → Comma Separated Values (.csv) and save as backend/data/sheet_export.csv, "
        "then: python -m cli sync --local-csv"
    )


def read_local_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.reader(handle)]


def _has_google_api_creds() -> bool:
    settings = get_settings()
    return settings.service_account_path is not None or settings.token_path.exists()


def read_batch(batch: dict[str, Any], allow_local_csv: bool = False) -> list[list[str]]:
    """Read one tab in bulk. Default: public CSV export (no Google Cloud)."""
    settings = get_settings()
    spreadsheet_id = batch.get("spreadsheet_id") or settings.google_spreadsheet_id
    gid = batch.get("gid") if batch.get("gid") is not None else settings.google_sheet_gid
    sheet_name = batch.get("sheet_name") or settings.google_sheet_name
    errors: list[str] = []

    csv_urls = []
    if settings.google_sheets_csv_url:
        csv_urls.append(settings.google_sheets_csv_url)
    csv_urls.append(public_csv_url(spreadsheet_id, gid))
    csv_urls.append(gviz_csv_url(spreadsheet_id, gid))

    accessible_empty = False
    for url in csv_urls:
        try:
            rows = read_via_csv(url)
            if rows:
                return rows
            accessible_empty = True
        except Exception as exc:
            errors.append(str(exc))

    if _has_google_api_creds():
        try:
            return read_via_api(spreadsheet_id, gid, sheet_name)
        except SheetsReadError as exc:
            errors.append(str(exc))

    local = BACKEND_ROOT / "data" / "sheet_export.csv"
    if local.exists() and allow_local_csv:
        return read_local_csv(local)

    if accessible_empty:
        return []

    raise SheetsReadError(errors[-1] if errors else _private_sheet_help())


def read_named_tab(spreadsheet_id: str, sheet_name: str, allow_local_csv: bool = False) -> list[list[str]]:
    """Read a tab by name (Momentum NSE 500), not by gid 0."""
    errors: list[str] = []
    try:
        rows = read_via_csv(gviz_csv_url(spreadsheet_id, sheet_name=sheet_name))
        if rows:
            return rows
    except Exception as exc:
        errors.append(str(exc))
    if _has_google_api_creds():
        try:
            return read_via_api(spreadsheet_id, None, sheet_name)
        except SheetsReadError as exc:
            errors.append(str(exc))
    if allow_local_csv:
        local = BACKEND_ROOT / "data" / f"{sheet_name.replace(' ', '_').lower()}.csv"
        if local.exists():
            return read_local_csv(local)
    raise SheetsReadError(errors[-1] if errors else f"Could not read tab {sheet_name!r}")
