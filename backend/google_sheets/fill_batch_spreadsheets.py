"""Fill the shared NSE batch workbooks with a cleaned StockFilter layout.

Does not copy StockFilter rows. That tab has 78 duplicate symbols and 24
dead/renamed tickers (#N/A). These workbooks get unique current NSE symbols
and the same 19-column GOOGLEFINANCE formulas.

Write path:
  python -m cli fill-batch-sheets
  python -m cli fill-batch-sheets --only NSE_2500_3000,NSE_3000_3500,NSE_3500_3625
    1. Google Sheets API if you have signed in (python -m cli google-login)
    2. Otherwise writes FillExistingNseSpreadsheets.gs — paste into Apps Script
"""

from __future__ import annotations

from typing import Any

from google_sheets.create_batches import load_master_symbols
from google_sheets.create_spreadsheet import _ensure_worksheet, populate_collection_tab, populate_momentum_tab
from google_sheets.export_batch_workbooks import USER_WORKBOOKS, export_fill_existing_script
from google_sheets.formulas import COLLECTION_HEADERS, col_letter, collection_row
from google_sheets.sheets_client import SheetsReadError, gspread_client, load_batch_config


def unique_nse_symbols() -> list[str]:
    seen: set[str] = set()
    symbols: list[str] = []
    for item in load_master_symbols():
        symbol = item["symbol"]
        if symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)
    return symbols


def workbook_chunks() -> list[dict[str, Any]]:
    symbols = unique_nse_symbols()
    books = []
    for book in USER_WORKBOOKS:
        chunk = symbols[book["start"] : book["end"]]
        books.append({**book, "symbols": chunk})
    return books


def parse_only_batches(only: str | None) -> set[str] | None:
    if not only or not str(only).strip():
        return None
    names = {part.strip().upper() for part in str(only).split(",") if part.strip()}
    return names or None


def filter_workbook_chunks(only: str | None = None) -> list[dict[str, Any]]:
    books = workbook_chunks()
    selected = parse_only_batches(only)
    if not selected:
        return books
    known = {book["batch_name"] for book in books}
    missing = sorted(selected - known)
    if missing:
        raise ValueError(f"Unknown batch name(s): {', '.join(missing)}. Known: {', '.join(sorted(known))}")
    return [book for book in books if book["batch_name"] in selected]


def fill_one_via_api(client, book: dict[str, Any]) -> dict[str, Any]:
    symbols: list[str] = book["symbols"]
    spreadsheet = client.open_by_key(book["spreadsheet_id"])
    try:
        worksheet = spreadsheet.worksheet("StockFilter")
    except Exception:
        worksheet = spreadsheet.sheet1
        if worksheet.title != "StockFilter":
            worksheet.update_title("StockFilter")
    need_rows = max(len(symbols) + 20, 100)
    if worksheet.row_count < need_rows or worksheet.col_count < 24:
        worksheet.resize(rows=max(worksheet.row_count, need_rows), cols=max(worksheet.col_count, 24))
    populate_collection_tab(worksheet, symbols)
    title = book.get("workbook_title")
    if title:
        spreadsheet.update_title(title)
    momentum_name = book.get("momentum_sheet") or "Momentum NSE 500"
    momentum = _ensure_worksheet(
        spreadsheet, momentum_name, rows=560, cols=max(14, 2 + len(symbols))
    )
    populate_momentum_tab(momentum, symbols)
    return {
        "batch_name": book["batch_name"],
        "spreadsheet_id": book["spreadsheet_id"],
        "gid": int(worksheet.id),
        "symbol_count": len(symbols),
        "url": spreadsheet.url,
        "first": symbols[0] if symbols else None,
        "last": symbols[-1] if symbols else None,
        "momentum_sheet": momentum_name,
    }


def fill_via_api(only: str | None = None) -> dict[str, Any]:
    client = gspread_client()
    books = filter_workbook_chunks(only)
    filled = [fill_one_via_api(client, book) for book in books]
    return {
        "mode": "api",
        "filled": filled,
        "symbol_count": sum(item["symbol_count"] for item in filled),
        "only": list(parse_only_batches(only) or []),
    }


def fill_batch_spreadsheets(only: str | None = None) -> dict[str, Any]:
    """Write selected Drive workbooks. Falls back to Apps Script if API login is missing."""
    script = export_fill_existing_script()
    books = filter_workbook_chunks(only)
    try:
        result = fill_via_api(only=only)
        result["apps_script"] = str(script)
        return result
    except SheetsReadError as exc:
        run_hints = [f"fillNse{book['batch_name'].removeprefix('NSE_')}" for book in books]
        return {
            "mode": "apps_script",
            "apps_script": str(script),
            "symbol_count": sum(len(book["symbols"]) for book in books),
            "only": list(parse_only_batches(only) or []),
            "workbooks": [
                {
                    "batch_name": book["batch_name"],
                    "spreadsheet_id": book["spreadsheet_id"],
                    "url": book["url"],
                    "symbol_count": len(book["symbols"]),
                    "run": f"fillNse{book['batch_name'].removeprefix('NSE_')}",
                }
                for book in books
            ],
            "error": str(exc),
            "next": (
                "Open any overflow sheet > Extensions > Apps Script > "
                "paste FillExistingNseSpreadsheets.gs > Save. "
                f"Run only: {', '.join(run_hints)}. "
                "Leave sheets open for GOOGLEFINANCE, then: python -m cli sync"
            ),
        }


def active_workbook_chunks() -> list[dict[str, Any]]:
    active = {
        item["batch_name"]
        for item in load_batch_config()
        if str(item.get("status") or "ACTIVE").upper() == "ACTIVE"
    }
    return [book for book in workbook_chunks() if book["batch_name"] in active]


def _stockfilter_worksheet(spreadsheet):
    try:
        return spreadsheet.worksheet("StockFilter")
    except Exception:
        worksheet = spreadsheet.sheet1
        if worksheet.title != "StockFilter":
            worksheet.update_title("StockFilter")
        return worksheet


def existing_stockfilter_symbols(worksheet) -> list[str]:
    values = worksheet.col_values(1)
    return [str(value).strip() for value in values[1:] if str(value).strip()]


def refresh_one_stockfilter(client, book: dict[str, Any]) -> dict[str, Any]:
    """Rewrite GOOGLEFINANCE formulas on StockFilter. Never clears existing rows."""
    spreadsheet = client.open_by_key(book["spreadsheet_id"])
    worksheet = _stockfilter_worksheet(spreadsheet)
    symbols = existing_stockfilter_symbols(worksheet)
    action = "rewrote"
    if not symbols:
        symbols = list(book.get("symbols") or [])
        if not symbols:
            return {
                "batch_name": book["batch_name"],
                "spreadsheet_id": book["spreadsheet_id"],
                "action": "skipped",
                "symbol_count": 0,
                "url": spreadsheet.url,
            }
        need_rows = max(len(symbols) + 20, 100)
        if worksheet.row_count < need_rows or worksheet.col_count < 24:
            worksheet.resize(rows=max(worksheet.row_count, need_rows), cols=max(worksheet.col_count, 24))
        populate_collection_tab(worksheet, symbols)
        action = "filled"
    else:
        last = col_letter(len(COLLECTION_HEADERS))
        formulas = [collection_row(row) for row in range(2, 2 + len(symbols))]
        worksheet.update(f"B2:{last}{1 + len(symbols)}", formulas, value_input_option="USER_ENTERED")
    return {
        "batch_name": book["batch_name"],
        "spreadsheet_id": book["spreadsheet_id"],
        "action": action,
        "symbol_count": len(symbols),
        "url": spreadsheet.url,
        "first": symbols[0],
        "last": symbols[-1],
    }


def refresh_stockfilter_formulas() -> dict[str, Any]:
    """Re-apply StockFilter GOOGLEFINANCE formulas on active workbooks."""
    script = export_fill_existing_script()
    try:
        client = gspread_client()
        refreshed = [refresh_one_stockfilter(client, book) for book in active_workbook_chunks()]
        return {
            "mode": "api",
            "refreshed": refreshed,
            "symbol_count": sum(item["symbol_count"] for item in refreshed),
        }
    except SheetsReadError as exc:
        return {
            "mode": "apps_script",
            "apps_script": str(script),
            "error": str(exc),
            "next": (
                "Not signed in to Google. Run: python -m cli google-login\n"
                "Or open each sheet so GOOGLEFINANCE can calculate, then: "
                "python -m cli refresh --skip-formulas"
            ),
        }
