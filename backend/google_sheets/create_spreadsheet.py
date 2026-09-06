"""Write GOOGLEFINANCE collection tabs into the Drive-hosted workbook."""

from __future__ import annotations

import csv
from typing import Any

from config.settings import get_settings
from google_sheets.create_batches import load_master_symbols, split_batches
from google_sheets.formulas import (
    COLLECTION_HEADERS,
    MOMENTUM_HISTORY_ROWS,
    collection_row,
    col_letter,
    config_rows,
    momentum_date_formula,
    momentum_history_formula,
    momentum_marketcap_formula,
    momentum_nifty_formula,
    momentum_price_formula,
    momentum_return_formula,
)
from google_sheets.sheets_client import gspread_client, save_batch_config


def _ensure_worksheet(spreadsheet, title: str, rows: int, cols: int):
    try:
        worksheet = spreadsheet.worksheet(title)
        if worksheet.row_count < rows or worksheet.col_count < cols:
            worksheet.resize(rows=max(worksheet.row_count, rows), cols=max(worksheet.col_count, cols))
        return worksheet
    except Exception:
        return spreadsheet.add_worksheet(title, rows=rows, cols=cols)


def populate_collection_tab(worksheet, symbols: list[str]) -> None:
    worksheet.clear()
    last = col_letter(len(COLLECTION_HEADERS))
    worksheet.update(f"A1:{last}1", [COLLECTION_HEADERS], value_input_option="RAW")
    if not symbols:
        return
    worksheet.update(f"A2:A{1 + len(symbols)}", [[symbol] for symbol in symbols], value_input_option="RAW")
    formulas = [collection_row(row) for row in range(2, 2 + len(symbols))]
    worksheet.update(f"B2:{last}{1 + len(symbols)}", formulas, value_input_option="USER_ENTERED")


def populate_momentum_tab(worksheet, symbols: list[str]) -> None:
    """Wide Momentum layout: one symbol per column, 2 years of daily closes."""
    worksheet.clear()
    if not symbols:
        return
    cols = 2 + len(symbols)
    rows = MOMENTUM_HISTORY_ROWS
    if worksheet.row_count < rows or worksheet.col_count < cols:
        worksheet.resize(rows=max(worksheet.row_count, rows), cols=max(worksheet.col_count, cols))
    last = col_letter(cols)
    header = ["NSE Data", "Symbol", *symbols]
    worksheet.update(f"A1:{last}1", [header], value_input_option="RAW")
    worksheet.update(
        "A2:B5",
        [
            ["", "MarketCap"],
            ["", "Price"],
            ["", "Return in 6 month"],
            ["", "Return in 3 month"],
        ],
        value_input_option="RAW",
    )
    worksheet.update("A6:B6", [["Date", "NIFTY"]], value_input_option="RAW")
    worksheet.update(f"C6:{last}6", [["Close"] * len(symbols)], value_input_option="RAW")
    letters = [col_letter(3 + index) for index in range(len(symbols))]
    worksheet.update(
        f"C2:{last}5",
        [
            [momentum_marketcap_formula(col) for col in letters],
            [momentum_price_formula(col) for col in letters],
            [momentum_return_formula(col, 126) for col in letters],
            [momentum_return_formula(col, 63) for col in letters],
        ],
        value_input_option="USER_ENTERED",
    )
    worksheet.update(
        f"A7:{last}7",
        [[
            momentum_date_formula(),
            momentum_nifty_formula(),
            *[momentum_history_formula(col) for col in letters],
        ]],
        value_input_option="USER_ENTERED",
    )


def setup_drive_workbook(
    spreadsheet_id: str | None = None,
    batch_size: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Split NSE symbols across tabs of ~500 and plant GOOGLEFINANCE formulas."""
    settings = get_settings()
    spreadsheet_id = spreadsheet_id or settings.google_spreadsheet_id
    size = batch_size or settings.batch_size
    client = gspread_client()
    spreadsheet = client.open_by_key(spreadsheet_id)

    symbols = [row["symbol"] for row in load_master_symbols()]
    if limit:
        symbols = symbols[:limit]
    chunks = [symbols[index : index + size] for index in range(0, len(symbols), size)] or [[]]

    config = _ensure_worksheet(spreadsheet, "CONFIG", rows=30, cols=4)
    config.clear()
    config.update("A1:B1", [["Setting", "Value"]], value_input_option="RAW")

    batches: list[dict[str, Any]] = []
    config_body: list[list[str]] = []
    for index, chunk in enumerate(chunks, start=1):
        tab_name = f"NSE_{index:02d}"
        worksheet = _ensure_worksheet(spreadsheet, tab_name, rows=max(len(chunk) + 20, 100), cols=12)
        populate_collection_tab(worksheet, chunk)
        batches.append(
            {
                "batch_name": tab_name,
                "spreadsheet_id": spreadsheet_id,
                "gid": int(worksheet.id),
                "sheet_name": tab_name,
                "status": "ACTIVE",
                "symbol_start": chunk[0] if chunk else None,
                "symbol_end": chunk[-1] if chunk else None,
                "notes": f"{len(chunk)} symbols with GOOGLEFINANCE formulas",
            }
        )
        config_body.extend(config_rows(tab_name, tab_name, spreadsheet_id))
        config_body.append(["", ""])

    config.update(f"A2:B{1 + len(config_body)}", config_body, value_input_option="USER_ENTERED")
    save_batch_config(batches, spreadsheet_id)
    return {
        "title": spreadsheet.title,
        "url": spreadsheet.url,
        "tabs": len(batches),
        "symbols": len(symbols),
        "batches": batches,
    }


def create_spreadsheets_for_batches() -> list[dict]:
    """Legacy: one workbook per batch. Prefer setup_drive_workbook for a single Drive file."""
    client = gspread_client()
    created = []
    for path in split_batches():
        with path.open(encoding="utf-8", newline="") as handle:
            symbols = [row["symbol"] for row in csv.DictReader(handle)]
        title = f"NSE Trend Batch {path.stem.replace('_', ' ').title()}"
        spreadsheet = client.create(title)
        worksheet = _ensure_worksheet(spreadsheet, "STOCK_DATA", rows=max(len(symbols) + 20, 100), cols=12)
        populate_collection_tab(worksheet, symbols)
        created.append(
            {
                "batch_name": path.stem.upper(),
                "spreadsheet_id": spreadsheet.id,
                "gid": int(worksheet.id),
                "url": spreadsheet.url,
                "symbol_count": len(symbols),
            }
        )
    return created


def populate_existing(spreadsheet_id: str, symbols: list[str] | None = None) -> None:
    setup_drive_workbook(spreadsheet_id=spreadsheet_id, limit=len(symbols) if symbols else None)
