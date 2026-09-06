"""Split the NSE master list into 400-500 symbol CSV batches."""

from __future__ import annotations

import csv
from pathlib import Path

from config.settings import BACKEND_ROOT, get_settings

MASTER_PATH = BACKEND_ROOT / "data" / "nse_symbols.csv"
BATCH_DIR = BACKEND_ROOT / "data" / "batches"


def load_master_symbols(path: Path = MASTER_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            symbol = (row.get("nse_symbol") or row.get("SYMBOL") or row.get("symbol") or "").strip()
            if not symbol:
                continue
            if str(row.get("active_flag", "True")).lower() in {"false", "0", "no"}:
                continue
            rows.append(
                {
                    "symbol": symbol.upper(),
                    "company_name": (row.get("company_name") or row.get("NAME OF COMPANY") or "").strip(),
                    "isin": (row.get("isin") or row.get("ISIN NUMBER") or "").strip(),
                    "listing_date": (row.get("listing_date") or "").strip(),
                    "segment": (row.get("segment") or "EQ").strip().upper() or "EQ",
                    "series": (row.get("series") or "").strip().upper(),
                }
            )
        return rows


def split_batches(batch_size: int | None = None) -> list[Path]:
    size = batch_size or get_settings().batch_size
    symbols = load_master_symbols()
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, start in enumerate(range(0, len(symbols), size), start=1):
        chunk = symbols[start : start + size]
        path = BATCH_DIR / f"batch_{index:02d}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "company_name", "isin", "listing_date"])
            writer.writeheader()
            writer.writerows(chunk)
        written.append(path)
    return written
