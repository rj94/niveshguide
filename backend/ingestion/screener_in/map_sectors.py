from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import BACKEND_ROOT
from database.models import Stock
from database.repository import upsert_stock
from database.session import init_db
from ingestion.screener_in.parse import parse_peers_taxonomy

OUT_DIR = BACKEND_ROOT / "data" / "screener_in"
CACHE_DIR = OUT_DIR / "cache" / "html"
SECTORS_CSV = OUT_DIR / "sectors.csv"
STATUS_CSV = OUT_DIR / "scrape_status.csv"

SECTOR_HEADERS = [
    "symbol",
    "broad_sector",
    "sector",
    "broad_industry",
    "industry",
    "source_url",
]

logger = logging.getLogger(__name__)


def _ok_symbols(status_path: Path = STATUS_CSV) -> set[str] | None:
    if not status_path.exists():
        return None
    ok: set[str] = set()
    with status_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("status") or "").lower() == "ok":
                sym = (row.get("symbol") or "").strip().upper()
                if sym:
                    ok.add(sym)
    return ok


def parse_sector_from_html_file(path: Path) -> dict[str, Any]:
    symbol = path.stem.upper()
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    taxonomy = parse_peers_taxonomy(soup)
    return {
        "symbol": symbol,
        "broad_sector": taxonomy.get("broad_sector"),
        "sector": taxonomy.get("sector"),
        "broad_industry": taxonomy.get("broad_industry"),
        "industry": taxonomy.get("industry"),
        "source_url": f"https://www.screener.in/company/{symbol}/consolidated/",
    }


def build_sectors_csv(
    *,
    cache_dir: Path | None = None,
    out_csv: Path | None = None,
    only_ok: bool = True,
) -> dict[str, Any]:
    root = Path(cache_dir) if cache_dir else CACHE_DIR
    dest = Path(out_csv) if out_csv else SECTORS_CSV
    dest.parent.mkdir(parents=True, exist_ok=True)
    ok = _ok_symbols() if only_ok else None

    rows: list[dict[str, Any]] = []
    missing = 0
    files = sorted(root.glob("*.html"))
    for path in files:
        symbol = path.stem.upper()
        if ok is not None and symbol not in ok:
            continue
        row = parse_sector_from_html_file(path)
        if not row.get("sector") and not row.get("industry") and not row.get("broad_sector"):
            missing += 1
        rows.append(row)

    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SECTOR_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) or "" for key in SECTOR_HEADERS})

    mapped = sum(1 for row in rows if row.get("sector") or row.get("industry") or row.get("broad_sector"))
    return {
        "cache_files": len(files),
        "rows_written": len(rows),
        "mapped": mapped,
        "missing_taxonomy": missing,
        "sectors_csv": str(dest),
    }


def apply_sectors_to_stocks(session: Session, sectors_csv: Path | None = None) -> dict[str, Any]:
    init_db()
    path = Path(sectors_csv) if sectors_csv else SECTORS_CSV
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run map-screener-sectors first")

    updated = 0
    created = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            before = session.scalar(select(Stock.id).where(Stock.symbol == symbol))
            stock = upsert_stock(session, symbol)
            stock.broad_sector = (row.get("broad_sector") or "").strip() or None
            stock.sector = (row.get("sector") or "").strip() or None
            stock.broad_industry = (row.get("broad_industry") or "").strip() or None
            stock.industry = (row.get("industry") or "").strip() or None
            if before is None:
                created += 1
            else:
                updated += 1
            if (updated + created) % 500 == 0:
                session.flush()
    session.commit()
    return {"updated": updated, "created": created, "sectors_csv": str(path)}


def map_screener_sectors(session: Session) -> dict[str, Any]:
    built = build_sectors_csv()
    logger.info(
        "sectors.csv written: %s mapped / %s rows (%s missing taxonomy)",
        built["mapped"],
        built["rows_written"],
        built["missing_taxonomy"],
    )
    applied = apply_sectors_to_stocks(session)
    return {**built, **applied}
