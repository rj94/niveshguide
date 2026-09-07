from market_platform.schemas.stocks import StockAnalysisRow
from market_platform.services.stocks import _sort_analysis_rows


def _row(symbol: str, change_pct: float | None) -> StockAnalysisRow:
    return StockAnalysisRow(
        id=abs(hash(symbol)) % 100000,
        symbol=symbol,
        company_name=symbol,
        exchange="NSE",
        change_pct=change_pct,
    )


def test_change_pct_ascending_places_real_losers_before_blank_rows():
    rows = [_row("BLANK", None), _row("DOWN", -4.2), _row("FLAT", 0.0), _row("UP", 3.1)]

    sorted_rows = _sort_analysis_rows(rows, sort_by="change_pct", sort_dir="asc")

    assert [row.symbol for row in sorted_rows] == ["DOWN", "FLAT", "UP", "BLANK"]


def test_change_pct_descending_places_real_gainers_before_blank_rows():
    rows = [_row("BLANK", None), _row("DOWN", -4.2), _row("FLAT", 0.0), _row("UP", 3.1)]

    sorted_rows = _sort_analysis_rows(rows, sort_by="change_pct", sort_dir="desc")

    assert [row.symbol for row in sorted_rows] == ["UP", "FLAT", "DOWN", "BLANK"]
