"""
Bootstrap NiveshGuide production Postgres with core market data.

Usage (from backend/, with prod URL — never commit the URL):

  set DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST:5432/railway
  .\\.venv\\Scripts\\python.exe scripts\\bootstrap_prod.py

Or pass --database-url explicitly.
Requires network access to NSE / Google as used by existing CLIs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap NiveshGuide prod DB")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="Postgres URL (postgresql+psycopg2://...). Overrides env if set.",
    )
    parser.add_argument(
        "--skip-indices",
        action="store_true",
        help="Skip NSE index scrape",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip Google sheet sync (use when OAuth not available)",
    )
    parser.add_argument(
        "--skip-calculate",
        action="store_true",
        help="Skip indicator / momentum calculate",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: set DATABASE_URL or pass --database-url", file=sys.stderr)
        return 1
    if args.database_url.startswith("sqlite"):
        print(
            "WARNING: DATABASE_URL looks like SQLite. Use Railway Postgres for prod.",
            file=sys.stderr,
        )

    os.environ["DATABASE_URL"] = args.database_url

    from config.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    print(f"Using database: {settings.database_url.split(':', 1)[0]}")

    from database.session import SessionLocal, init_db

    init_db()
    print("Schema ready (create_all).")

    session = SessionLocal()
    try:
        if not args.skip_indices:
            print("Scraping NSE indices…")
            from ingestion.nse_indices import scrape_and_store

            try:
                result = scrape_and_store(session)
                print(json.dumps({"indices": result}, indent=2, default=str))
            except Exception as exc:  # noqa: BLE001
                print(f"Indices scrape failed (continuing): {exc}", file=sys.stderr)

        if not args.skip_sync:
            print("Syncing Google sheet batches…")
            from ingestion.read_batches import sync_all_batches

            try:
                result = sync_all_batches(session)
                print(json.dumps({"sync": result}, indent=2, default=str))
            except Exception as exc:  # noqa: BLE001
                print(f"Sheet sync failed (continuing): {exc}", file=sys.stderr)

        if not args.skip_calculate:
            print("Calculating indicators / momentum…")
            from indicators.engine import calculate_all

            n = calculate_all(session)
            print(json.dumps({"calculated": n}, indent=2))
    finally:
        session.close()

    print("Bootstrap finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
