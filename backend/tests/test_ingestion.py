from ingestion.normalize import normalize_rows, parse_number
from ingestion.validate import validate_rows


def test_normalize_maps_plan_headers():
    raw = [
        [
            "Symbol",
            "Market Cap",
            "LTP",
            "High",
            "Prev Close",
            "52 Week High",
            "52 Week Low",
            "3 Days MA",
            "7 Days MA",
            "21 Days MA",
            "50 Days MA",
            "200 Days MA",
            "Crossover 3D > 7D",
            "LTP > 21D",
            "LTP > 200D",
            "Crossover 50D > 200D",
            "Trend",
            "PE",
            "EPS",
        ],
        [
            "EPIGRAL",
            "5327.95",
            "1235",
            "1241",
            "1206.4",
            "1838.9",
            "807",
            "1233",
            "1226",
            "1146",
            "1125",
            "1085",
            "Yes",
            "Yes",
            "Yes",
            "Yes",
            "Up",
            "19.66",
            "62.82",
        ],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["BAD", "x", "0", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]
    rows = normalize_rows(raw)
    assert rows[0]["symbol"] == "EPIGRAL"
    assert rows[0]["ltp"] == 1235
    assert rows[0]["crossover_3_7"] is True
    assert rows[0]["pe"] == 19.66


def test_parse_number_rejects_errors_and_zero_trap():
    assert parse_number("#N/A") is None
    assert parse_number("") is None
    assert parse_number("1,235.50") == 1235.5
    assert parse_number(0) == 0.0


def test_validate_rejects_blank_duplicate_and_nonpositive_ltp():
    valid, invalid = validate_rows(
        [
            {"symbol": "AAA", "ltp": 10},
            {"symbol": "AAA", "ltp": 11},
            {"symbol": "", "ltp": 10},
            {"symbol": "BBB", "ltp": 0},
            {"symbol": "CCC", "ltp": 12},
            {"symbol": "DDD", "ltp": None},
        ]
    )
    assert [row["symbol"] for row in valid] == ["AAA", "CCC"]
    assert len(invalid) == 4


def test_normalize_wide_layout_one_symbol_per_column():
    raw = [
        ["NSE Data", "Symbol", "Symbol", "EPIGRAL", "APLAPOLLO", "ABBOTINDIA"],
        ["EPIGRAL", "MarketCap", "5327.95", "5327.95", "62700.62", "55620.05"],
        ["3MINDIA", "Price", "1235", "1235", "2270", "26200"],
    ]
    rows = {item["symbol"]: item for item in normalize_rows(raw)}
    assert rows["EPIGRAL"]["ltp"] == 1235
    assert rows["APLAPOLLO"]["market_cap"] == 62700.62
    assert rows["ABBOTINDIA"]["ltp"] == 26200


def test_normalize_stockfilter_headers():
    raw = [
        [
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
        ],
        [
            "EPIGRAL",
            "5327.95",
            "1235",
            "1241",
            "1206.4",
            "1838.9",
            "807",
            "1233",
            "1226",
            "1146",
            "1125",
            "1085",
            "Yes",
            "Yes",
            "Yes",
            "Yes",
            "Up",
            "19.66",
            "62.82",
        ],
    ]
    rows = normalize_rows(raw)
    assert rows[0]["symbol"] == "EPIGRAL"
    assert rows[0]["ltp"] == 1235
    assert rows[0]["ma_3"] == 1233
    assert rows[0]["ma_200"] == 1085
    assert rows[0]["crossover_3_7"] is True
    assert rows[0]["above_ma_21"] is True
    assert rows[0]["golden_cross"] is True
    assert rows[0]["trend"] == "Up"
    assert rows[0]["pe"] == 19.66


def test_stockfilter_headers_are_canonical():
    from google_sheets.formulas import STOCKFILTER_HEADERS, formula_for_column

    assert STOCKFILTER_HEADERS == [
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
    ]
    trend = formula_for_column("Trend", 2)
    assert 'N2="Yes"' in trend
    assert 'O2="Yes"' in trend
    assert 'P2="Yes"' in trend
    assert "Q2" not in trend


def test_momentum_wide_history_and_returns():
    from google_sheets.formulas import (
        MOMENTUM_HISTORY_DAYS,
        MOMENTUM_INGEST_DAYS,
        MOMENTUM_LABELS,
        momentum_date_formula,
        momentum_history_formula,
        momentum_return_formula,
    )

    assert MOMENTUM_HISTORY_DAYS == 730
    assert MOMENTUM_INGEST_DAYS == 730
    assert "Return in 6 month" in MOMENTUM_LABELS
    hist = momentum_history_formula("C")
    assert "TODAY()-730" in hist
    assert "select Col2" in hist
    assert "C$1" in momentum_date_formula()
    ret6 = momentum_return_formula("C", 126)
    ret3 = momentum_return_formula("C", 63)
    assert "COUNTA" in ret6 and "COUNTA" in ret3
    assert "-126" in ret6
    assert "-63" in ret3


def test_period_return_uses_trading_day_lookback():
    from indicators.engine import period_return

    closes = [100.0] + [100.0] * 62 + [110.0]
    assert abs((period_return(closes, 63) or 0) - 0.10) < 1e-9
    assert period_return([100.0], 63) is None


def test_parse_momentum_grid_skips_duplicate_header_and_serial_dates():
    from ingestion.momentum_history import parse_momentum_grid, parse_sheet_date

    serial = parse_sheet_date("46066.64583")
    assert serial is not None and serial.year in {2025, 2026}
    rows = [
        ["NSE Data", "Symbol", "20MICRONS", "20MICRONS", "3MINDIA"],
        ["", "MarketCap", "100", "100", "200"],
        ["Date", "NIFTY", "Close", "Close", "Close"],
        ["2026-08-01", "25000", "10.5", "10.5", "100"],
        ["2026-08-04", "25100", "11", "11", "101"],
    ]
    points = parse_momentum_grid(rows, ingest_days=730)
    symbols = {item["symbol"] for item in points}
    assert symbols == {"20MICRONS", "3MINDIA"}
    assert len([item for item in points if item["symbol"] == "20MICRONS"]) == 2


def test_batch_workbook_split_covers_unique_nse_list():
    from google_sheets.fill_batch_spreadsheets import unique_nse_symbols, workbook_chunks

    symbols = unique_nse_symbols()
    assert len(symbols) == 2389
    assert len(symbols) == len(set(symbols))
    books = workbook_chunks()
    combined = [symbol for book in books for symbol in book["symbols"]]
    assert combined == symbols
    assert [len(book["symbols"]) for book in books] == [500, 500, 500, 500, 389, 0]
    assert books[0]["momentum_sheet"] == "Momentum NSE 500"
    assert books[0]["workbook_title"] == "NSE 0-500 Stocks"
    assert books[1]["momentum_sheet"] == "Momentum NSE 500-1000"
