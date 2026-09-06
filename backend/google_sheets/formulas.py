"""GOOGLEFINANCE formulas matching the StockFilter tab layout.

Live quote / fundamental fields come from GOOGLEFINANCE.
3/7/21/50/200-day averages use a dated GOOGLEFINANCE close window.
Crossover and Trend columns are cheap IF formulas on those values.
"""

from __future__ import annotations

# Exact header row from StockFilter (gid=1375108259)
STOCKFILTER_HEADERS = [
    "Symbol",
    "marketcap",
    "LTP",
    "High",
    "Prev Close",
    "52 week high",
    "52 week low",
    "3Days MA",
    "7Days MA",
    "21Days MA",
    "50Days MA",
    "200Days MA",
    "Crossover(3D>7D)",
    "LTP > 21 D",
    "LTP > 200 D",
    "Crossover(50D>200D)",
    "Trend",
    "PE",
    "EPS",
    "Volume",
    "3M Avg Vol",
    "6M Avg Vol",
    "1Year Avg Vol",
]

COLLECTION_HEADERS = STOCKFILTER_HEADERS
STOCK_DATA_HEADERS = STOCKFILTER_HEADERS
TAB_NAME = "StockFilter"
MOMENTUM_TAB_NAME = "Momentum NSE 500"

# Same layout as StockTrade "Momentum NSE 500" (gid 1863479878):
# one symbol per column, daily closes down the sheet, 3m/6m returns from that series.
MOMENTUM_HISTORY_DAYS = 730
MOMENTUM_INGEST_DAYS = 730
MOMENTUM_HISTORY_START_ROW = 7
MOMENTUM_FIRST_SYMBOL_COL = 3
MOMENTUM_HISTORY_ROWS = 560
MOMENTUM_LABELS = ["MarketCap", "Price", "Return in 6 month", "Return in 3 month"]

_SMA_LOOKBACK = {3: 7, 7: 14, 21: 35, 50: 80, 200: 320}


def _sma(row: int, days: int) -> str:
    lookback = _SMA_LOOKBACK[days]
    return (
        f'=IFERROR(AVERAGE(QUERY(GOOGLEFINANCE("NSE:"&A{row},"close",TODAY()-{lookback},TODAY()),'
        f'"select Col2 offset 1 label Col2 \'\'")),)'
    )


def formula_for_column(column: str, row: int) -> str:
    symbol = f"A{row}"
    mapping = {
        "marketcap": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"marketcap")/10000000,)',
        "Market Cap": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"marketcap")/10000000,)',
        "LTP": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"price"),)',
        "High": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"high"),)',
        "Day High": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"high"),)',
        "Prev Close": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"closeyest"),)',
        "Previous Close": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"closeyest"),)',
        "52 week high": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"high52"),)',
        "52 Week High": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"high52"),)',
        "52 week low": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"low52"),)',
        "52 Week Low": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"low52"),)',
        "3Days MA": _sma(row, 3),
        "7Days MA": _sma(row, 7),
        "21Days MA": _sma(row, 21),
        "50Days MA": _sma(row, 50),
        "200Days MA": _sma(row, 200),
        "Crossover(3D>7D)": f'=IF(AND(ISNUMBER(H{row}),ISNUMBER(I{row})),IF(H{row}>I{row},"Yes","No"),)',
        "LTP > 21 D": f'=IF(AND(ISNUMBER(C{row}),ISNUMBER(J{row})),IF(C{row}>J{row},"Yes","No"),)',
        "LTP > 200 D": f'=IF(AND(ISNUMBER(C{row}),ISNUMBER(L{row})),IF(C{row}>L{row},"Yes","No"),)',
        "Crossover(50D>200D)": f'=IF(AND(ISNUMBER(K{row}),ISNUMBER(L{row})),IF(K{row}>L{row},"Yes","No"),)',
        # A=Symbol ... N=LTP>21, O=LTP>200, P=50D>200, Q=Trend. Q must not read Q.
        "Trend": f'=IF(AND(N{row}="Yes",O{row}="Yes",P{row}="Yes"),"Up","Down")',
        "PE": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"pe"),)',
        "EPS": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"eps"),)',
        "Volume": f'=IFERROR(GOOGLEFINANCE("NSE:"&{symbol},"volume"),)',
        "3M Avg Vol": (
            f'=IFERROR(AVERAGE(INDEX(GOOGLEFINANCE("NSE:"&{symbol},"volume",TODAY()-90,TODAY()),0,2)),)'
        ),
        "6M Avg Vol": (
            f'=IFERROR(AVERAGE(INDEX(GOOGLEFINANCE("NSE:"&{symbol},"volume",TODAY()-180,TODAY()),0,2)),)'
        ),
        "1Year Avg Vol": (
            f'=IFERROR(AVERAGE(INDEX(GOOGLEFINANCE("NSE:"&{symbol},"volume",TODAY()-360,TODAY()),0,2)),)'
        ),
        "Last Updated": "=IFERROR(NOW(),)",
    }
    return mapping.get(column, "")


def collection_row(row: int) -> list[str]:
    return [formula_for_column(header, row) for header in STOCKFILTER_HEADERS[1:]]


def col_letter(index: int) -> str:
    """1-based column index to A, B, ... AA."""
    letter = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letter = chr(65 + rem) + letter
    return letter


def momentum_marketcap_formula(col: str) -> str:
    return f'=IFERROR(GOOGLEFINANCE("NSE:"&{col}$1,"marketcap")/10000000,)'


def momentum_price_formula(col: str) -> str:
    return f'=IFERROR(GOOGLEFINANCE("NSE:"&{col}$1,"price"),)'


def momentum_history_formula(col: str, days: int = MOMENTUM_HISTORY_DAYS) -> str:
    """Daily closes only (Col2) so each symbol stays one column for charting."""
    return (
        f'=IFERROR(QUERY(GOOGLEFINANCE("NSE:"&{col}$1,"close",TODAY()-{days},TODAY()),'
        f'"select Col2 offset 1 label Col2 \'\'"),)'
    )


def momentum_return_formula(col: str, trading_days: int) -> str:
    """Latest close / close N trading days earlier - 1. Uses COUNTA, not date MATCH."""
    start = MOMENTUM_HISTORY_START_ROW
    series = f"{col}${start}:{col}"
    return (
        f"=IFERROR(INDEX({series},COUNTA({series}))"
        f"/INDEX({series},MAX(1,COUNTA({series})-{trading_days}))-1,)"
    )


def momentum_date_formula(days: int = MOMENTUM_HISTORY_DAYS) -> str:
    return (
        f'=IFERROR(QUERY(GOOGLEFINANCE("NSE:"&C$1,"close",TODAY()-{days},TODAY()),'
        f'"select Col1 offset 1 label Col1 \'\'"),)'
    )


def momentum_nifty_formula(days: int = MOMENTUM_HISTORY_DAYS) -> str:
    return (
        f'=IFERROR(QUERY(GOOGLEFINANCE("INDEXNSE:NIFTY_50","close",TODAY()-{days},TODAY()),'
        f'"select Col2 offset 1 label Col2 \'\'"),)'
    )


def apps_script_momentum_fns() -> str:
    return r'''
function columnLetter_(n) {
  var s = "";
  while (n > 0) {
    var m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function momentumReturn_(col, tradingDays) {
  return '=IFERROR(INDEX(' + col + '$7:' + col + ',COUNTA(' + col + '$7:' + col + '))/INDEX(' + col + '$7:' + col + ',MAX(1,COUNTA(' + col + '$7:' + col + ')-' + tradingDays + '))-1,)';
}

function momentumHistory_(col) {
  return '=IFERROR(QUERY(GOOGLEFINANCE("NSE:"&' + col + '$1,"close",TODAY()-730,TODAY()),"select Col2 offset 1 label Col2 \'\'"),)';
}

function fillMomentum_(ss, book) {
  const name = book.momentum_sheet || "Momentum NSE 500";
  const sheet = ensureSheet_(ss, name);
  sheet.getCharts().forEach(function (chart) { sheet.removeChart(chart); });
  sheet.clear();
  var symbols = book.symbols || [];
  if (!symbols.length) {
    var filter = ss.getSheetByName("StockFilter");
    if (filter) {
      symbols = filter.getRange("A2:A").getValues().map(function (row) {
        return row[0];
      }).filter(function (value) { return value; });
    }
  }
  if (!symbols.length) {
    return name + "\t0";
  }
  const cols = 2 + symbols.length;
  const histRows = 560;
  if (sheet.getMaxColumns() < cols) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), cols - sheet.getMaxColumns());
  }
  if (sheet.getMaxRows() < histRows) {
    sheet.insertRowsAfter(sheet.getMaxRows(), histRows - sheet.getMaxRows());
  }
  const header = ["NSE Data", "Symbol"].concat(symbols);
  sheet.getRange(1, 1, 1, header.length).setValues([header]);
  sheet.getRange("A2:B5").setValues([
    ["", "MarketCap"],
    ["", "Price"],
    ["", "Return in 6 month"],
    ["", "Return in 3 month"]
  ]);
  sheet.getRange("A6:B6").setValues([["Date", "NIFTY"]]);
  sheet.getRange(6, 3, 1, symbols.length).setValue("Close");

  const mcap = [];
  const price = [];
  const ret6 = [];
  const ret3 = [];
  const hist = [];
  for (var i = 0; i < symbols.length; i++) {
    const col = columnLetter_(3 + i);
    mcap.push('=IFERROR(GOOGLEFINANCE("NSE:"&' + col + '$1,"marketcap")/10000000,)');
    price.push('=IFERROR(GOOGLEFINANCE("NSE:"&' + col + '$1,"price"),)');
    ret6.push(momentumReturn_(col, 126));
    ret3.push(momentumReturn_(col, 63));
    hist.push(momentumHistory_(col));
  }
  sheet.getRange(2, 3, 1, symbols.length).setFormulas([mcap]);
  sheet.getRange(3, 3, 1, symbols.length).setFormulas([price]);
  sheet.getRange(4, 3, 1, symbols.length).setFormulas([ret6]);
  sheet.getRange(5, 3, 1, symbols.length).setFormulas([ret3]);
  sheet.getRange(7, 3, 1, symbols.length).setFormulas([hist]);
  sheet.getRange("A7").setFormula('=IFERROR(QUERY(GOOGLEFINANCE("NSE:"&C$1,"close",TODAY()-730,TODAY()),"select Col1 offset 1 label Col1 \'\'"),)');
  sheet.getRange("B7").setFormula('=IFERROR(QUERY(GOOGLEFINANCE("INDEXNSE:NIFTY_50","close",TODAY()-730,TODAY()),"select Col2 offset 1 label Col2 \'\'"),)');
  sheet.getRange("A7:A" + histRows).setNumberFormat("yyyy-mm-dd");
  sheet.getRange(4, 3, 2, symbols.length).setNumberFormat("0.00%");
  sheet.setFrozenRows(6);
  sheet.setFrozenColumns(2);
  sheet.autoResizeColumn(1);
  sheet.autoResizeColumn(2);
  return name + "\t" + symbols.length + " x 2y history";
}
'''


def apps_script_formula_row_fn() -> str:
    """JS helper used by the fill/create Apps Script files."""
    return r'''
function formulaRow_(row) {
  return [
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"marketcap")/10000000,)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"price"),)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"high"),)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"closeyest"),)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"high52"),)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"low52"),)',
    '=IFERROR(AVERAGE(QUERY(GOOGLEFINANCE("NSE:"&A' + row + ',"close",TODAY()-7,TODAY()),"select Col2 offset 1 label Col2 \'\'")),)',
    '=IFERROR(AVERAGE(QUERY(GOOGLEFINANCE("NSE:"&A' + row + ',"close",TODAY()-14,TODAY()),"select Col2 offset 1 label Col2 \'\'")),)',
    '=IFERROR(AVERAGE(QUERY(GOOGLEFINANCE("NSE:"&A' + row + ',"close",TODAY()-35,TODAY()),"select Col2 offset 1 label Col2 \'\'")),)',
    '=IFERROR(AVERAGE(QUERY(GOOGLEFINANCE("NSE:"&A' + row + ',"close",TODAY()-80,TODAY()),"select Col2 offset 1 label Col2 \'\'")),)',
    '=IFERROR(AVERAGE(QUERY(GOOGLEFINANCE("NSE:"&A' + row + ',"close",TODAY()-320,TODAY()),"select Col2 offset 1 label Col2 \'\'")),)',
    '=IF(AND(ISNUMBER(H' + row + '),ISNUMBER(I' + row + ')),IF(H' + row + '>I' + row + ',"Yes","No"),)',
    '=IF(AND(ISNUMBER(C' + row + '),ISNUMBER(J' + row + ')),IF(C' + row + '>J' + row + ',"Yes","No"),)',
    '=IF(AND(ISNUMBER(C' + row + '),ISNUMBER(L' + row + ')),IF(C' + row + '>L' + row + ',"Yes","No"),)',
    '=IF(AND(ISNUMBER(K' + row + '),ISNUMBER(L' + row + ')),IF(K' + row + '>L' + row + ',"Yes","No"),)',
    '=IF(AND(N' + row + '="Yes",O' + row + '="Yes",P' + row + '="Yes"),"Up","Down")',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"pe"),)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"eps"),)',
    '=IFERROR(GOOGLEFINANCE("NSE:"&A' + row + ',"volume"),)',
    '=IFERROR(AVERAGE(INDEX(GOOGLEFINANCE("NSE:"&A' + row + ',"volume",TODAY()-90,TODAY()),0,2)),)',
    '=IFERROR(AVERAGE(INDEX(GOOGLEFINANCE("NSE:"&A' + row + ',"volume",TODAY()-180,TODAY()),0,2)),)',
    '=IFERROR(AVERAGE(INDEX(GOOGLEFINANCE("NSE:"&A' + row + ',"volume",TODAY()-360,TODAY()),0,2)),)'
  ];
}
'''


def config_rows(batch_id: str, tab_name: str, spreadsheet_id: str) -> list[list[str]]:
    return [
        ["Batch ID", batch_id],
        ["Exchange", "NSE"],
        ["Tab", tab_name],
        ["Symbol Count", f"=COUNTA('{tab_name}'!A2:A)"],
        ["Refresh Date", "=NOW()"],
        ["Status", "Active"],
        ["Workbook", spreadsheet_id],
        ["Layout", "StockFilter: one symbol per row"],
    ]
