"""CLI for the NSE trend screener.

    python -m cli google-login
    python -m cli setup-sheet --limit 50
    python -m cli load-symbols
    python -m cli sync
    python -m cli refresh
    python -m cli calculate
    python -m cli serve
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DEMO_SYMBOLS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "BAJFINANCE",
    "KOTAKBANK",
    "LT",
    "HCLTECH",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "SUNPHARMA",
    "TITAN",
    "NESTLEIND",
    "WIPRO",
    "M&M",
    "NTPC",
    "ONGC",
    "TATAMOTORS",
    "JSWSTEEL",
    "ADANIENT",
    "COALINDIA",
    "EPIGRAL",
    "APLAPOLLO",
    "ABBOTINDIA",
]


def _session():
    from database.session import SessionLocal, init_db

    init_db()
    return SessionLocal()


def cmd_load_symbols(_args) -> None:
    from database.repository import upsert_stock
    from google_sheets.create_batches import load_master_symbols

    session = _session()
    rows = load_master_symbols()
    for row in rows:
        upsert_stock(session, row["symbol"], row["company_name"], row.get("isin"))
    session.commit()
    print(f"Loaded {len(rows)} NSE symbols")


def cmd_split_batches(_args) -> None:
    from google_sheets.create_batches import split_batches

    paths = split_batches()
    print(f"Wrote {len(paths)} batch files:")
    for path in paths:
        print(f"  {path}")


def cmd_sync(args) -> None:
    from ingestion.read_batches import sync_all_batches

    session = _session()
    result = sync_all_batches(session, allow_local_csv=args.local_csv)
    print(json.dumps(result, indent=2))
    empty = result.get("empty") or []
    if empty:
        print(
            f"Warning: {len(empty)} batch(es) produced 0 snapshots "
            "(blank sheet or missing LTP). Fill/open those workbooks, then re-run sync."
        )
    for detail in result.get("batches") or []:
        invalid = detail.get("invalid") or 0
        if invalid:
            print(
                f"  {detail.get('batch')}: {detail.get('rows', 0)} rows ok, "
                f"{invalid} invalid skipped ({detail.get('status')})"
            )


def cmd_refresh(args) -> None:
    from google_sheets.fill_batch_spreadsheets import refresh_stockfilter_formulas
    from ingestion.nse_indices import scrape_and_store
    from scheduler.daily_update import sync_and_calculate

    if not args.skip_formulas:
        formulas = refresh_stockfilter_formulas()
        print(json.dumps({"formulas": formulas}, indent=2, default=str))
        if formulas.get("mode") == "apps_script":
            print(formulas.get("next", ""))
    session = _session()
    try:
        indices = scrape_and_store(session)
        print(json.dumps({"indices": indices}, indent=2, default=str))
    except Exception as exc:  # noqa: BLE001 — refresh must continue if NSE blocks
        print(json.dumps({"indices": {"ok": False, "error": str(exc)}}, indent=2))
    result = sync_and_calculate(session, allow_local_csv=args.local_csv)
    print(json.dumps(result, indent=2, default=str))
    print(
        "If LTP columns are still blank, open the five Drive workbooks, "
        "wait for GOOGLEFINANCE, then: python -m cli refresh --skip-formulas"
    )


def cmd_scrape_indices(_args) -> None:
    from ingestion.nse_indices import scrape_and_store

    session = _session()
    result = scrape_and_store(session)
    print(json.dumps(result, indent=2, default=str))


def cmd_scrape_etfs(args) -> None:
    from ingestion.sector_etfs import refresh_key_etf_quotes

    session = _session()
    symbols = [part.strip().upper() for part in (args.symbols or "").split(",") if part.strip()] or None
    result = refresh_key_etf_quotes(session, symbols=symbols)
    print(json.dumps(result, indent=2, default=str))


def cmd_backfill_index_prices(args) -> None:
    from ingestion.index_price_backfill import backfill_index_prices
    from ingestion.nse_indices import FEATURED_INDICES

    session = _session()
    # Include FEATURED_INDICES so home sparklines have real history (not 2-point slopes).
    featured = [key for key, _ in FEATURED_INDICES]
    result = backfill_index_prices(session, period=args.period, keys=None)
    result["featured_requested"] = featured
    print(json.dumps(result, indent=2, default=str))


def cmd_scrape_nifty_constituents(_args) -> None:
    from ingestion.niftyindices_constituents import download_all

    result = download_all()
    print(json.dumps(result, indent=2, default=str))


def cmd_import_nifty_constituents(_args) -> None:
    from ingestion.niftyindices_constituents import import_constituents

    session = _session()
    result = import_constituents(session)
    print(json.dumps(result, indent=2, default=str))


def cmd_club_nifty_symbols(_args) -> None:
    from ingestion.niftyindices_constituents import build_all_symbols_csv

    result = build_all_symbols_csv()
    print(json.dumps(result, indent=2, default=str))


def cmd_apply_nifty_industries(_args) -> None:
    from ingestion.niftyindices_constituents import apply_all_symbols_industries, apply_split_industries

    session = _session()
    applied = apply_all_symbols_industries(session)
    split = apply_split_industries(session)
    print(json.dumps({"industries": applied, "split_industries": split}, indent=2, default=str))


def cmd_split_industries(_args) -> None:
    from ingestion.niftyindices_constituents import apply_split_industries

    session = _session()
    result = apply_split_industries(session)
    print(json.dumps(result, indent=2, default=str))


def cmd_sync_nifty_constituents(_args) -> None:
    from ingestion.niftyindices_constituents import sync_constituents

    session = _session()
    result = sync_constituents(session)
    print(json.dumps(result, indent=2, default=str))


def cmd_backfill(args) -> None:
    from ingestion.ingest_stocks import backfill_prices

    session = _session()
    symbols = [item.strip().upper() for item in args.symbols.split(",")] if args.symbols else None
    stored = backfill_prices(session, symbols=symbols, period=args.period)
    print(f"Upserted {stored} price rows")


def cmd_backfill_yahoo_meta(args) -> None:
    from ingestion.yahoo_meta import backfill_yahoo_meta

    session = _session()
    symbols = [item.strip().upper() for item in args.symbols.split(",")] if args.symbols else None
    result = backfill_yahoo_meta(
        session,
        symbols=symbols,
        limit=args.limit,
        chunk_size=args.chunk_size,
        sleep_s=args.sleep,
        screener_sectors=not args.skip_screener,
        screener_cache_only=args.screener_cache_only,
        screener_delay_min=args.screener_delay_min,
        screener_delay_max=args.screener_delay_max,
    )
    print(json.dumps(result, indent=2, default=str))


def cmd_calculate(_args) -> None:
    from indicators.engine import calculate_all

    session = _session()
    count = calculate_all(session)
    print(f"Calculated indicators for {count} stocks")


def cmd_bootstrap(args) -> None:
    """Load symbols, try Google Sheet sync, then Yahoo history for a liquid subset."""
    from database.repository import upsert_stock
    from google_sheets.create_batches import load_master_symbols
    from indicators.engine import calculate_all
    from ingestion.ingest_stocks import backfill_prices
    from ingestion.read_batches import sync_all_batches

    session = _session()
    for row in load_master_symbols():
        upsert_stock(session, row["symbol"], row["company_name"], row.get("isin"))
    session.commit()
    print("Master symbols loaded.")

    sync_result = sync_all_batches(session)
    print("Sheet sync:", json.dumps(sync_result, indent=2))

    symbols = DEMO_SYMBOLS if args.demo else None
    print(f"Backfilling Yahoo prices ({'demo universe' if args.demo else 'all active'})...")
    stored = backfill_prices(session, symbols=symbols, period=args.period)
    print(f"Price rows: {stored}")
    count = calculate_all(session)
    print(f"Indicators calculated: {count}")


def cmd_google_login(_args) -> None:
    from google_sheets.sheets_client import google_login

    path = google_login()
    print(f"Signed in. Token saved to {path}")
    print("Next: python -m cli inspect-sheet")


def cmd_pull_nse_symbols(args) -> None:
    from ingestion.nse_universe import previous_weekday, pull_nse_symbols

    trade_date = args.date
    if not trade_date and not args.file:
        trade_date = previous_weekday().isoformat()
    result = pull_nse_symbols(trade_date=trade_date, file=args.file)
    print(json.dumps(result, indent=2))
    print(
        f"Master updated: {result.get('previous')} -> {result.get('new')} symbols. "
        "Next: python -m cli export-sheet-batches && python -m cli load-symbols"
    )


def cmd_inspect_sheet(_args) -> None:
    from config.settings import get_settings
    from google_sheets.sheets_client import inspect_spreadsheet

    info = inspect_spreadsheet(get_settings().google_spreadsheet_id)
    print(json.dumps(info, indent=2))


def cmd_setup_sheet(args) -> None:
    from google_sheets.create_spreadsheet import setup_drive_workbook

    result = setup_drive_workbook(limit=args.limit, batch_size=args.batch_size)
    print(json.dumps(result, indent=2, default=str))
    print("Open the workbook in the browser so GOOGLEFINANCE can calculate, then run: python -m cli sync")


def cmd_fill_batch_sheets(args) -> None:
    from google_sheets.fill_batch_spreadsheets import fill_batch_spreadsheets

    result = fill_batch_spreadsheets(only=getattr(args, "only", None))
    print(json.dumps(result, indent=2, default=str))
    if result.get("mode") == "apps_script":
        print(result.get("next", ""))
    else:
        print("Sheets written. Leave them open so GOOGLEFINANCE can calculate, then: python -m cli sync")


def cmd_export_sheet_batches(args) -> None:
    from google_sheets.export_batch_workbooks import export_all

    result = export_all(batch_size=args.batch_size)
    print(json.dumps(result, indent=2))
    print(
        "Paste FillExistingNseSpreadsheets.gs into Extensions > Apps Script. "
        "If StockFilter already has data, Run addMomentumAndFixTrendNse0_500. "
        "Blank books: Run fillNse0_500 / fillNse500_1000 / ..."
    )
    print("Or File > Import each NSE_STOCK_BATCH_0N.csv into the matching empty workbook.")


def cmd_create_sheets(_args) -> None:
    from google_sheets.create_spreadsheet import create_spreadsheets_for_batches

    created = create_spreadsheets_for_batches()
    print(json.dumps(created, indent=2))


def cmd_scrape_screener(args) -> None:
    from ingestion.screener_in.run import scrape_screener

    only = [part.strip().upper() for part in (args.only or "").split(",") if part.strip()] or None
    result = scrape_screener(
        limit=args.limit,
        only=only,
        resume=not args.no_resume,
        reparse_only=args.reparse_only,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        max_per_day=args.max_per_day,
        cache_ttl_days=args.cache_ttl_days,
        flush_every=args.flush_every,
        verbose=args.verbose,
        i_know=args.i_know,
    )
    print(json.dumps(result, indent=2, default=str))
    print(f"Watch live CSV/XLSX under: {result.get('out_dir')}")


def cmd_import_screener_excel(args) -> None:
    from ingestion.screener_in.import_excel import import_screener_excel

    session = _session()
    result = import_screener_excel(session, directory=Path(args.dir) if args.dir else None)
    print(json.dumps(result, indent=2, default=str))


def cmd_map_screener_sectors(_args) -> None:
    from ingestion.screener_in.map_sectors import map_screener_sectors

    session = _session()
    result = map_screener_sectors(session)
    print(json.dumps(result, indent=2, default=str))


def cmd_serve(args) -> None:
    import uvicorn

    uvicorn.run("main:app", host=args.host, port=args.port, reload=args.reload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NSE Stock Trend Screener")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("google-login", help="Sign in with the Google account that owns the Drive spreadsheet").set_defaults(
        func=cmd_google_login
    )
    sub.add_parser("inspect-sheet", help="List tabs in the configured Drive spreadsheet").set_defaults(
        func=cmd_inspect_sheet
    )
    setup = sub.add_parser("setup-sheet", help="Write GOOGLEFINANCE formulas into the Drive spreadsheet")
    setup.add_argument("--limit", type=int, help="Only the first N symbols (try 50 first)")
    setup.add_argument("--batch-size", type=int, dest="batch_size", help="Symbols per tab, default 500")
    setup.set_defaults(func=cmd_setup_sheet)

    sync = sub.add_parser("sync", help="Pull computed GOOGLEFINANCE values from Drive into the database")
    sync.add_argument("--local-csv", action="store_true", help="Fall back to data/sheet_export.csv if Google is unavailable")
    sync.set_defaults(func=cmd_sync)
    refresh = sub.add_parser(
        "refresh",
        help="Rewrite StockFilter GOOGLEFINANCE formulas, sync sheets, then calculate indicators",
    )
    refresh.add_argument("--skip-formulas", action="store_true", help="Skip formula rewrite; sync + calculate only")
    refresh.add_argument("--local-csv", action="store_true", help="Fall back to data/sheet_export.csv if Google is unavailable")
    refresh.set_defaults(func=cmd_refresh)
    sub.add_parser("load-symbols", help="Load NSE master list into stocks table").set_defaults(func=cmd_load_symbols)
    pull = sub.add_parser(
        "pull-nse-symbols",
        help="Rebuild nse_symbols.csv from NSE bhavcopy (pdDDMMYYYY or UDiFF CM)",
    )
    pull.add_argument("--date", help="Trade date YYYY-MM-DD or DDMMYYYY (default: last weekday)")
    pull.add_argument(
        "--file",
        help="Local bhavcopy path (e.g. data/bhavcopy/pd02092026.xlsx)",
    )
    pull.set_defaults(func=cmd_pull_nse_symbols)
    sub.add_parser("split-batches", help="Split master list into 500-symbol CSVs").set_defaults(func=cmd_split_batches)
    sub.add_parser("calculate", help="Recalculate moving averages, scores, signals").set_defaults(func=cmd_calculate)
    fill_batches = sub.add_parser(
        "fill-batch-sheets",
        help="Write StockFilter layout into shared NSE workbooks (use --only to avoid wiping filled books)",
    )
    fill_batches.add_argument(
        "--only",
        help="Comma-separated batch names, e.g. NSE_2500_3000,NSE_3000_3500,NSE_3500_3625",
    )
    fill_batches.set_defaults(func=cmd_fill_batch_sheets)
    export = sub.add_parser("export-sheet-batches", help="Write ~500-symbol GOOGLEFINANCE CSVs + Apps Script")
    export.add_argument("--batch-size", type=int, dest="batch_size", default=None)
    export.set_defaults(func=cmd_export_sheet_batches)
    sub.add_parser("create-sheets", help="Create separate Google workbooks per batch (needs API login)").set_defaults(
        func=cmd_create_sheets
    )

    scrape = sub.add_parser(
        "scrape-screener",
        help="Scrape screener.in fundamentals/shareholding/P&L/BS into Excel+CSV (polite, resumable)",
    )
    scrape.add_argument("--limit", type=int, help="Max symbols this run")
    scrape.add_argument("--only", help="Comma-separated NSE symbols")
    scrape.add_argument("--no-resume", action="store_true", help="Do not skip symbols already status=ok")
    scrape.add_argument("--reparse-only", action="store_true", help="Rebuild Excel from HTML cache only")
    scrape.add_argument("--delay-min", type=float, default=4.0)
    scrape.add_argument("--delay-max", type=float, default=8.0)
    scrape.add_argument("--max-per-day", type=int, default=400)
    scrape.add_argument("--cache-ttl-days", type=int, default=7)
    scrape.add_argument("--flush-every", type=int, default=1, help="Sync xlsx every N symbols (CSV always appends)")
    scrape.add_argument("--verbose", action="store_true")
    scrape.add_argument(
        "--i-know",
        action="store_true",
        help="Allow delay-min < 2 (increases block risk)",
    )
    scrape.set_defaults(func=cmd_scrape_screener)

    sub.add_parser(
        "scrape-indices",
        help="Fetch live NSE allIndices quotes into market_indices tables",
    ).set_defaults(func=cmd_scrape_indices)
    scrape_etfs = sub.add_parser(
        "scrape-etfs",
        help="Fetch Yahoo prices for the curated key ETF strip into stock snapshots/prices",
    )
    scrape_etfs.add_argument("--symbols", help="Comma-separated ETF symbols. Default: curated key ETFs.")
    scrape_etfs.set_defaults(func=cmd_scrape_etfs)

    backfill_idx = sub.add_parser(
        "backfill-index-prices",
        help="Backfill ~1y daily closes for sectoral + featured indices (Yahoo) for 3M returns / sparklines",
    )
    backfill_idx.add_argument("--period", default="1y")
    backfill_idx.set_defaults(func=cmd_backfill_index_prices)

    sub.add_parser(
        "scrape-nifty-constituents",
        help="Download Broad/Sectoral/Thematic Index Constituent CSVs from niftyindices/NSE",
    ).set_defaults(func=cmd_scrape_nifty_constituents)
    sub.add_parser(
        "import-nifty-constituents",
        help="Import data/niftyindices CSVs → memberships + Stock.sector from sectoral",
    ).set_defaults(func=cmd_import_nifty_constituents)
    sub.add_parser(
        "club-nifty-symbols",
        help="Club niftyindices CSVs → data/niftyindices/all_symbols.csv (thematic>sectoral>broad)",
    ).set_defaults(func=cmd_club_nifty_symbols)
    sub.add_parser(
        "apply-nifty-industries",
        help="Map all_symbols.csv Industry → Stock.industry and Stock.sector",
    ).set_defaults(func=cmd_apply_nifty_industries)
    sub.add_parser(
        "split-industries",
        help="Split comma-separated industries into separate sector tags (broad_industry)",
    ).set_defaults(func=cmd_split_industries)
    sub.add_parser(
        "sync-nifty-constituents",
        help="Download Index Constituent CSVs then import into the database",
    ).set_defaults(func=cmd_sync_nifty_constituents)

    import_sx = sub.add_parser(
        "import-screener-excel",
        help="Load screener.in Excel/CSV under data/screener_in into SQLite",
    )
    import_sx.add_argument("--dir", help="Directory with fundamentals.csv etc.")
    import_sx.set_defaults(func=cmd_import_screener_excel)

    sub.add_parser(
        "map-screener-sectors",
        help="Parse sector/industry from screener HTML cache into sectors.csv and stocks table",
    ).set_defaults(func=cmd_map_screener_sectors)

    backfill = sub.add_parser("backfill-prices", help="Fetch Yahoo Finance history")
    backfill.add_argument("--symbols", help="Comma-separated symbols. Default: all active stocks.")
    backfill.add_argument("--period", default="1y")
    backfill.set_defaults(func=cmd_backfill)

    yahoo_meta = sub.add_parser(
        "backfill-yahoo-meta",
        help="Backfill missing sector/industry/market_cap/pe from Yahoo Finance info",
    )
    yahoo_meta.add_argument("--symbols", help="Comma-separated symbols (default: gap stocks)")
    yahoo_meta.add_argument("--limit", type=int, help="Max symbols to process")
    yahoo_meta.add_argument("--chunk-size", type=int, default=40)
    yahoo_meta.add_argument("--sleep", type=float, default=0.35, help="Pause between Yahoo chunks (seconds)")
    yahoo_meta.add_argument(
        "--skip-screener",
        action="store_true",
        help="Skip Screener.in sector/industry fill for remaining gaps",
    )
    yahoo_meta.add_argument(
        "--screener-cache-only",
        action="store_true",
        help="Only use existing Screener.in HTML cache (no live fetches)",
    )
    yahoo_meta.add_argument("--screener-delay-min", type=float, default=2.0)
    yahoo_meta.add_argument("--screener-delay-max", type=float, default=4.0)
    yahoo_meta.set_defaults(func=cmd_backfill_yahoo_meta)

    bootstrap = sub.add_parser("bootstrap", help="Load symbols, sync sheet, backfill, calculate")
    bootstrap.add_argument("--demo", action="store_true", help="Limit Yahoo backfill to a liquid subset")
    bootstrap.add_argument("--period", default="1y")
    bootstrap.set_defaults(func=cmd_bootstrap)

    serve = sub.add_parser("serve", help="Run the API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=cmd_serve)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
