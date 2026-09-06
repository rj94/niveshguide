"""Build import-ready NSE batch workbooks: ~500 symbols each, vertical layout.

The live StockTrade sheet puts one symbol per column, which is why GOOGLEFINANCE
cannot cover the full NSE list. These files use one symbol per row instead.

Outputs:
  backend/data/spreadsheets/NSE_STOCK_BATCH_01.csv ...
  backend/data/spreadsheets/CreateNseBatchSpreadsheets.gs
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from config.settings import BACKEND_ROOT, get_settings
from google_sheets.create_batches import MASTER_PATH, load_master_symbols
from google_sheets.formulas import (
    COLLECTION_HEADERS,
    apps_script_formula_row_fn,
    apps_script_momentum_fns,
    collection_row,
)

OUT_DIR = BACKEND_ROOT / "data" / "spreadsheets"

USER_WORKBOOKS = [
    {
        "batch_name": "NSE_0_500",
        "spreadsheet_id": "1xzT_B1vlCr_MlYN6a-CVfxDUbB8BhZiqfQUJkPGPBBk",
        "url": "https://docs.google.com/spreadsheets/d/1xzT_B1vlCr_MlYN6a-CVfxDUbB8BhZiqfQUJkPGPBBk/edit?gid=0#gid=0",
        "start": 0,
        "end": 500,
        "workbook_title": "NSE 0-500 Stocks",
        "momentum_sheet": "Momentum NSE 500",
    },
    {
        "batch_name": "NSE_500_1000",
        "spreadsheet_id": "1hc33TZaVWf9qRbsSH__07sn_XDkiBDliJF3zf2MAa-4",
        "url": "https://docs.google.com/spreadsheets/d/1hc33TZaVWf9qRbsSH__07sn_XDkiBDliJF3zf2MAa-4/edit?gid=0#gid=0",
        "start": 500,
        "end": 1000,
        "workbook_title": "NSE 500-1000 Stocks",
        "momentum_sheet": "Momentum NSE 500-1000",
    },
    {
        "batch_name": "NSE_1000_1500",
        "spreadsheet_id": "1obC866jNti_X7yvtugWdh_zhJe5gHPQQRKzRPi1JqyU",
        "url": "https://docs.google.com/spreadsheets/d/1obC866jNti_X7yvtugWdh_zhJe5gHPQQRKzRPi1JqyU/edit?gid=0#gid=0",
        "start": 1000,
        "end": 1500,
        "workbook_title": "NSE 1000-1500 Stocks",
        "momentum_sheet": "Momentum NSE 1000-1500",
    },
    {
        "batch_name": "NSE_1500_2000",
        "spreadsheet_id": "1Iv13XpfD1NMWLZYo1NXElJbZnVcqpNyyiNdFYZVN34s",
        "url": "https://docs.google.com/spreadsheets/d/1Iv13XpfD1NMWLZYo1NXElJbZnVcqpNyyiNdFYZVN34s/edit?gid=0#gid=0",
        "start": 1500,
        "end": 2000,
        "workbook_title": "NSE 1500-2000 Stocks",
        "momentum_sheet": "Momentum NSE 1500-2000",
    },
    {
        "batch_name": "NSE_2000_2500",
        "spreadsheet_id": "17I3gCKHas-2nf-crUw9br3rKAeNYCXdpSqVXVZsGQxw",
        "url": "https://docs.google.com/spreadsheets/d/17I3gCKHas-2nf-crUw9br3rKAeNYCXdpSqVXVZsGQxw/edit?gid=0#gid=0",
        "start": 2000,
        "end": 2500,
        "workbook_title": "NSE 2000-2500 Stocks",
        "momentum_sheet": "Momentum NSE 2000-2500",
    },
    {
        "batch_name": "NSE_2500_3000",
        "spreadsheet_id": "1UBLESBcoLqa65uUdlbk72YSlR9HhytoVbl18fKH_GKg",
        "url": "https://docs.google.com/spreadsheets/d/1UBLESBcoLqa65uUdlbk72YSlR9HhytoVbl18fKH_GKg/edit?gid=0#gid=0",
        "start": 2500,
        "end": 3000,
        "workbook_title": "NSE 2500-3000 Stocks",
        "momentum_sheet": "Momentum NSE 2500-3000",
    },
    {
        "batch_name": "NSE_3000_3500",
        "spreadsheet_id": "1v6PosqPBeARNHCLlJYRtTiwpcjB1okkvnyL-4k9QjKg",
        "url": "https://docs.google.com/spreadsheets/d/1v6PosqPBeARNHCLlJYRtTiwpcjB1okkvnyL-4k9QjKg/edit?gid=0#gid=0",
        "start": 3000,
        "end": 3500,
        "workbook_title": "NSE 3000-3500 Stocks",
        "momentum_sheet": "Momentum NSE 3000-3500",
    },
    {
        "batch_name": "NSE_3500_3625",
        "spreadsheet_id": "1S_73ZeQTIqnBU5Knk6NWmGYm450bz_-Gve3tyecG3ic",
        "url": "https://docs.google.com/spreadsheets/d/1S_73ZeQTIqnBU5Knk6NWmGYm450bz_-Gve3tyecG3ic/edit?gid=0#gid=0",
        "start": 3500,
        "end": 4000,
        "workbook_title": "NSE 3500-4000 Stocks",
        "momentum_sheet": "Momentum NSE 3500-4000",
    },
]
FILL_EXISTING_SCRIPT = r'''/**
 * Fills the eight Drive spreadsheets with a CLEANED StockFilter layout
 * plus Momentum tabs: one symbol per column, daily closes, 3m/6m returns, chart.
 *
 * StockFilter is already filled on NSE 0_500? Do NOT run fillNse0_500 again.
 * Run addMomentumAndFixTrendNse0_500 instead — it keeps existing quotes.
 *
 * How to run (no Google Cloud):
 *  1. Open https://docs.google.com/spreadsheets/d/1xzT_B1vlCr_MlYN6a-CVfxDUbB8BhZiqfQUJkPGPBBk/edit
 *  2. Extensions > Apps Script.
 *  3. Delete the default code, paste this entire file, Save.
 *  4. If StockFilter already has rows: select addMomentumAndFixTrendNse0_500, Run.
 *  5. If a workbook is still blank: run fillNse0_500 / fillNse500_1000 / ...
 *  6. Leave each spreadsheet open so GOOGLEFINANCE can calculate.
 *  7. python -m cli sync
 *  8. python -m cli calculate
 */
const WORKBOOKS = %%WORKBOOKS%%;
const HEADERS = %%HEADERS%%;

function fillExistingNseSpreadsheets() {
  const log = [];
  WORKBOOKS.forEach(function (book) {
    log.push(fillOne_(book));
  });
  Logger.log(log.join("\n"));
}

function fillNse0_500() { fillOne_(WORKBOOKS[0]); }
function fillNse500_1000() { fillOne_(WORKBOOKS[1]); }
function fillNse1000_1500() { fillOne_(WORKBOOKS[2]); }
function fillNse1500_2000() { fillOne_(WORKBOOKS[3]); }
function fillNse2000_2500() { fillOne_(WORKBOOKS[4]); }
function fillNse2500_3000() { fillOne_(WORKBOOKS[5]); }
function fillNse3000_3500() { fillOne_(WORKBOOKS[6]); }
function fillNse3500_3625() { fillOne_(WORKBOOKS[7]); }

function addMomentumAndFixTrendNse0_500() {
  Logger.log(addMomentumAndFixTrend_(WORKBOOKS[0]));
}

function removeMomentumChartsNse0_500() {
  Logger.log(removeMomentumCharts_(WORKBOOKS[0]));
}

function removeMomentumCharts_(book) {
  const ss = SpreadsheetApp.openById(book.spreadsheet_id);
  const name = book.momentum_sheet || "Momentum NSE 500";
  const sheet = ss.getSheetByName(name);
  if (!sheet) {
    return name + "\tmissing";
  }
  const charts = sheet.getCharts();
  charts.forEach(function (chart) { sheet.removeChart(chart); });
  return name + "\tremoved " + charts.length + " chart(s)";
}

function addMomentumAndFixTrendAll() {
  const log = [];
  WORKBOOKS.forEach(function (book) {
    log.push(addMomentumAndFixTrend_(book));
  });
  Logger.log(log.join("\n"));
}

%%FORMULA_ROW_FN%%
function ensureSheet_(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (sheet) {
    return sheet;
  }
  var all = ss.getSheets();
  for (var i = 0; i < all.length; i++) {
    if (all[i].getName().indexOf("Momentum") === 0) {
      all[i].setName(name);
      return all[i];
    }
  }
  return ss.insertSheet(name);
}

function renameWorkbook_(ss, book) {
  if (book.workbook_title) {
    ss.rename(book.workbook_title);
  }
}

function orderTabs_(ss, momentumName) {
  var momentum = ss.getSheetByName(momentumName);
  var filter = ss.getSheetByName("StockFilter");
  if (momentum) {
    ss.setActiveSheet(momentum);
    ss.moveActiveSheet(1);
  }
  if (filter) {
    ss.setActiveSheet(filter);
    ss.moveActiveSheet(2);
  }
}
%%MOMENTUM_FNS%%

function fixTrend_(ss) {
  const sheet = ss.getSheetByName("StockFilter");
  if (!sheet) {
    return "StockFilter missing";
  }
  const last = sheet.getLastRow();
  if (last < 2) {
    return "StockFilter empty";
  }
  const formulas = [];
  for (var row = 2; row <= last; row++) {
    formulas.push(['=IF(AND(N' + row + '="Yes",O' + row + '="Yes",P' + row + '="Yes"),"Up","Down")']);
  }
  sheet.getRange(2, 17, formulas.length, 1).setFormulas(formulas);
  return last - 1;
}

function addMomentumAndFixTrend_(book) {
  const ss = SpreadsheetApp.openById(book.spreadsheet_id);
  renameWorkbook_(ss, book);
  const trend = fixTrend_(ss);
  const momentum = fillMomentum_(ss, book);
  orderTabs_(ss, book.momentum_sheet || "Momentum NSE 500");
  SpreadsheetApp.flush();
  return book.batch_name + "\ttrend " + trend + "\t" + momentum + "\t" + ss.getUrl();
}

function fillOne_(book) {
  if (!book.spreadsheet_id) {
    return book.batch_name + "\tSKIP no spreadsheet_id — run CreateNseBatchSpreadsheets.gs then paste ID into batches.yaml";
  }
  const ss = SpreadsheetApp.openById(book.spreadsheet_id);
  renameWorkbook_(ss, book);
  let sheet = ss.getSheetByName("StockFilter") || ss.getSheets()[0];
  if (sheet.getName() !== "StockFilter") {
    sheet.setName("StockFilter");
  }
  sheet.clear();
  const symbols = book.symbols || [];
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  if (!symbols.length) {
    return book.batch_name + "\t0 symbols\t" + ss.getUrl();
  }
  sheet.getRange(2, 1, symbols.length, 1).setValues(symbols.map(function (symbol) {
    return [symbol];
  }));
  const formulas = symbols.map(function (_, index) {
    return formulaRow_(index + 2);
  });
  sheet.getRange(2, 2, formulas.length, formulas[0].length).setFormulas(formulas);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumn(1);
  fillMomentum_(ss, book);
  orderTabs_(ss, book.momentum_sheet || "Momentum NSE 500");
  SpreadsheetApp.flush();
  return book.batch_name + "\t" + symbols.length + " symbols\t" + ss.getUrl();
}
'''

APPS_SCRIPT = r'''/**
 * Creates one Google Spreadsheet per ~500 NSE symbols, with GOOGLEFINANCE formulas.
 * No Google Cloud project required.
 *
 * How to run:
 *  1. Open https://docs.google.com/spreadsheets/ and create a blank sheet (any name).
 *  2. Extensions → Apps Script.
 *  3. Delete the default code, paste this entire file, Save.
 *  4. Select createAllNseBatches, click Run, authorize with your Gmail.
 *  5. View → Logs for the new spreadsheet URLs.
 *  6. Share each new file: Anyone with the link → Viewer, then paste the IDs into
 *     backend/config/batches.yaml and run: python -m cli sync
 */
const BATCHES = %%BATCHES%%;

const HEADERS = %%HEADERS%%;

function createAllNseBatches() {
  const urls = [];
  BATCHES.forEach(function (batch) {
    urls.push(createOneBatch_(batch.name, batch.symbols));
  });
  Logger.log("Created " + urls.length + " spreadsheets:\\n" + urls.join("\\n"));
}

%%FORMULA_ROW_FN%%
function createOneBatch_(title, symbols) {
  const ss = SpreadsheetApp.create(title);
  const sheet = ss.getActiveSheet();
  sheet.setName("StockFilter");
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  const symbolCells = symbols.map(function (symbol) { return [symbol]; });
  sheet.getRange(2, 1, symbolCells.length, 1).setValues(symbolCells);
  const formulas = symbols.map(function (_, index) {
    return formulaRow_(index + 2);
  });
  sheet.getRange(2, 2, formulas.length, formulas[0].length).setFormulas(formulas);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumn(1);
  return title + "\\t" + ss.getUrl() + "\\t" + ss.getId();
}
'''


def export_formula_csvs(batch_size: int | None = None) -> list[Path]:
    size = batch_size or get_settings().batch_size
    symbols = load_master_symbols()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, start in enumerate(range(0, len(symbols), size), start=1):
        chunk = symbols[start : start + size]
        path = OUT_DIR / f"NSE_STOCK_BATCH_{index:02d}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLLECTION_HEADERS)
            for offset, item in enumerate(chunk):
                row_number = offset + 2
                writer.writerow([item["symbol"], *collection_row(row_number)])
        written.append(path)
    return written


def export_apps_script(batch_size: int | None = None) -> Path:
    size = batch_size or get_settings().batch_size
    symbols = load_master_symbols()
    batches = []
    for index, start in enumerate(range(0, len(symbols), size), start=1):
        chunk = [item["symbol"] for item in symbols[start : start + size]]
        batches.append({"name": f"NSE_STOCK_BATCH_{index:02d}", "symbols": chunk})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "CreateNseBatchSpreadsheets.gs"
    path.write_text(
        APPS_SCRIPT.replace("%%BATCHES%%", json.dumps(batches))
        .replace("%%HEADERS%%", json.dumps(COLLECTION_HEADERS))
        .replace("%%FORMULA_ROW_FN%%", apps_script_formula_row_fn()),
        encoding="utf-8",
    )
    return path


def export_fill_existing_script(batch_size: int | None = None) -> Path:
    """Embed symbols into FillExisting Apps Script.

    Prefer keeping the previous master order for books that are already filled
    (avoid reshuffling Drive StockFilter for 0–2500). Overflow books (2500+)
    use contiguous slices of the live master so they match fill-batch-sheets --only.
    """
    size = batch_size or get_settings().batch_size
    current = []
    seen: set[str] = set()
    for item in load_master_symbols():
        if item["symbol"] in seen:
            continue
        seen.add(item["symbol"])
        current.append(item["symbol"])

    previous_path = MASTER_PATH.with_suffix(MASTER_PATH.suffix + ".bak")
    previous: list[str] = []
    if previous_path.exists():
        prev_seen: set[str] = set()
        for item in load_master_symbols(previous_path):
            if item["symbol"] in prev_seen:
                continue
            prev_seen.add(item["symbol"])
            previous.append(item["symbol"])

    # Stable assignment for already-filled equity books (0–2500).
    assigned_base = previous if previous else current

    payload = []
    for book in USER_WORKBOOKS:
        start, end = book["start"], book["end"]
        if start >= 2500:
            chunk = current[start:end]
        else:
            chunk = assigned_base[start:end]
        payload.append(
            {
                "batch_name": book["batch_name"],
                "spreadsheet_id": book["spreadsheet_id"],
                "workbook_title": book.get("workbook_title") or book["batch_name"],
                "momentum_sheet": book.get("momentum_sheet") or "Momentum NSE 500",
                "symbols": chunk,
            }
        )

    # Any symbols past the last configured end (should be rare).
    last_end = max((b["end"] for b in USER_WORKBOOKS), default=0)
    leftover = current[last_end:]
    overflow_index = 0
    while leftover:
        chunk = leftover[:size]
        leftover = leftover[size:]
        overflow_index += 1
        lo = last_end + (overflow_index - 1) * size
        hi = lo + len(chunk)
        payload.append(
            {
                "batch_name": f"NSE_{lo}_{hi}",
                "spreadsheet_id": "",
                "workbook_title": f"NSE {lo}-{hi} Stocks",
                "momentum_sheet": f"Momentum NSE {lo}-{hi}",
                "symbols": chunk,
                "needs_create": True,
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "FillExistingNseSpreadsheets.gs"
    path.write_text(
        FILL_EXISTING_SCRIPT.replace("%%WORKBOOKS%%", json.dumps(payload))
        .replace("%%HEADERS%%", json.dumps(COLLECTION_HEADERS))
        .replace("%%FORMULA_ROW_FN%%", apps_script_formula_row_fn())
        .replace("%%MOMENTUM_FNS%%", apps_script_momentum_fns()),
        encoding="utf-8",
    )
    return path


def export_all(batch_size: int | None = None) -> dict:
    csvs = export_formula_csvs(batch_size)
    script = export_apps_script(batch_size)
    fill_script = export_fill_existing_script(batch_size)
    symbols = list(load_master_symbols())
    return {
        "symbol_count": len(symbols),
        "batch_files": [str(path) for path in csvs],
        "apps_script": str(script),
        "fill_existing_script": str(fill_script),
        "batches": len(csvs),
    }
