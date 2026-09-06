from __future__ import annotations

import csv
from pathlib import Path

from google_sheets.create_batches import MASTER_PATH, load_master_symbols


def load_eq_symbols(master_path: Path | None = None) -> list[dict[str, str]]:
    path = master_path or MASTER_PATH
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for item in load_master_symbols(path):
        if (item.get("segment") or "EQ").upper() != "EQ":
            continue
        sym = item["symbol"]
        if sym in seen:
            continue
        # Skip G-sec / numbered tickers that slip into EQ
        if sym[:1].isdigit() or sym.startswith("SGB"):
            continue
        seen.add(sym)
        out.append(item)
    return out


def load_overrides(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mapping: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            nse = (row.get("nse_symbol") or row.get("symbol") or "").strip().upper()
            slug = (row.get("screener_slug") or row.get("slug") or "").strip()
            if nse and slug:
                mapping[nse] = slug
    return mapping
