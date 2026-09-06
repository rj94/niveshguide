"""Download NiftyIndices Index Constituent CSVs and map Sectoral members to Stock.sector.

Personal / research use. CSVs come from niftyindices.com Index Constituent links
(same official NSE `ind_*list.csv` files). Broad/thematic → membership only;
sectoral → also updates Stock.sector.
"""

from __future__ import annotations

import csv
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config.settings import BACKEND_ROOT
from database.models import Stock, StockIndexMembership
from database.repository import get_stock_by_symbol

logger = logging.getLogger(__name__)

OUT_ROOT = BACKEND_ROOT / "data" / "niftyindices"
MANIFEST_PATH = OUT_ROOT / "manifest.csv"
CATALOG_PATH = OUT_ROOT / "catalog.json"
ALL_SYMBOLS_PATH = OUT_ROOT / "all_symbols.csv"

# Higher wins when clubbing unique symbols into all_symbols.csv
PRIORITY = {"thematic": 3, "sectoral": 2, "broad": 1}
PRIORITY_TO_CATEGORY = {3: "thematic", 2: "sectoral", 1: "broad"}

# Collapse casing / legacy Nifty Industry spellings onto one label
INDUSTRY_ALIASES: dict[str, str] = {
    "FINANCIAL SERVICES": "Financial Services",
    "CONSTRUCTION": "Construction",
    "METALS": "Metals & Mining",
    "CEMENT & CEMENT PRODUCTS": "Construction Materials",
    "CONSUMER GOODS": "Fast Moving Consumer Goods",
}


def normalize_industry(raw: str | None) -> str | None:
    if not raw:
        return None
    name = re.sub(r"\s+", " ", raw.strip())
    if not name:
        return None
    mapped = INDUSTRY_ALIASES.get(name) or INDUSTRY_ALIASES.get(name.upper())
    if mapped:
        return mapped
    # Title-case all-caps leftovers
    if name.isupper() and len(name) > 3:
        return name.title()
    return name


def split_industry_labels(raw: str | None) -> list[str]:
    """Split comma-separated industry into distinct labels (does not split on &)."""
    if not raw:
        return []
    # Prefer already-exploded pipe tags
    if "|" in raw and "," not in raw:
        parts = [normalize_industry(p) for p in raw.split("|")]
    else:
        parts = [normalize_industry(p) for p in raw.split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(part)
    return out

NIFTY_HOME = "https://www.niftyindices.com"
NSE_INDICES_BASE = "https://www.nseindia.com/content/indices"
NSE_WWW1_BASE = "https://www1.nseindia.com/content/indices"
NIFTY_CONSTITUENT_BASE = "https://www.niftyindices.com/IndexConstituent"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class IndexSpec:
    name: str
    category: str  # broad | sectoral | thematic
    csv_name: str
    page_path: str = ""

    @property
    def index_key(self) -> str:
        return re.sub(r"\s+", " ", self.name.strip().upper())


# Seed catalog — well-known equity indices with official NSE list filenames.
CATALOG: list[IndexSpec] = [
    # Broad
    IndexSpec("Nifty 50", "broad", "ind_nifty50list.csv", "/indices/equity/broad-based-indices/nifty-50"),
    IndexSpec("Nifty Next 50", "broad", "ind_niftynext50list.csv", "/indices/equity/broad-based-indices/nifty-next-50"),
    IndexSpec("Nifty 100", "broad", "ind_nifty100list.csv", "/indices/equity/broad-based-indices/nifty-100"),
    IndexSpec("Nifty 200", "broad", "ind_nifty200list.csv", "/indices/equity/broad-based-indices/nifty-200"),
    IndexSpec("Nifty 500", "broad", "ind_nifty500list.csv", "/indices/equity/broad-based-indices/nifty-500"),
    IndexSpec("Nifty Midcap 50", "broad", "ind_niftymidcap50list.csv", "/indices/equity/broad-based-indices/nifty-midcap-50"),
    IndexSpec("Nifty Midcap 100", "broad", "ind_niftymidcap100list.csv", "/indices/equity/broad-based-indices/nifty-midcap-100"),
    IndexSpec("Nifty Midcap 150", "broad", "ind_niftymidcap150list.csv", "/indices/equity/broad-based-indices/nifty-midcap-150"),
    IndexSpec("Nifty Smallcap 50", "broad", "ind_niftysmallcap50list.csv", "/indices/equity/broad-based-indices/nifty-smallcap-50"),
    IndexSpec("Nifty Smallcap 100", "broad", "ind_niftysmallcap100list.csv", "/indices/equity/broad-based-indices/nifty-smallcap-100"),
    IndexSpec("Nifty Smallcap 250", "broad", "ind_niftysmallcap250list.csv", "/indices/equity/broad-based-indices/nifty-smallcap-250"),
    IndexSpec("Nifty LargeMidcap 250", "broad", "ind_niftylargemidcap250list.csv", "/indices/equity/broad-based-indices/nifty-largemidcap-250"),
    IndexSpec("Nifty MidSmallcap 400", "broad", "ind_niftymidsmallcap400list.csv", "/indices/equity/broad-based-indices/nifty-midsmallcap-400"),
    IndexSpec("Nifty Microcap 250", "broad", "ind_niftymicrocap250_list.csv", "/indices/equity/broad-based-indices/nifty-microcap-250"),
    IndexSpec("Nifty Total Market", "broad", "ind_niftytotalmarket_list.csv", "/indices/equity/broad-based-indices/nifty-total-market"),
    # Sectoral
    IndexSpec("Nifty Auto", "sectoral", "ind_niftyautolist.csv", "/indices/equity/sectoral-indices/nifty-auto"),
    IndexSpec("Nifty Bank", "sectoral", "ind_niftybanklist.csv", "/indices/equity/sectoral-indices/nifty-bank"),
    IndexSpec("Nifty Financial Services", "sectoral", "ind_niftyfinancelist.csv", "/indices/equity/sectoral-indices/nifty-financial-services"),
    IndexSpec("Nifty FMCG", "sectoral", "ind_niftyfmcglist.csv", "/indices/equity/sectoral-indices/nifty-fmcg"),
    IndexSpec("Nifty IT", "sectoral", "ind_niftyitlist.csv", "/indices/equity/sectoral-indices/nifty-it"),
    IndexSpec("Nifty Media", "sectoral", "ind_niftymedialist.csv", "/indices/equity/sectoral-indices/nifty-media"),
    IndexSpec("Nifty Metal", "sectoral", "ind_niftymetallist.csv", "/indices/equity/sectoral-indices/nifty-metal"),
    IndexSpec("Nifty Pharma", "sectoral", "ind_niftypharmalist.csv", "/indices/equity/sectoral-indices/nifty-pharma"),
    IndexSpec("Nifty Private Bank", "sectoral", "ind_nifty_privatebanklist.csv", "/indices/equity/sectoral-indices/nifty-private-bank"),
    IndexSpec("Nifty PSU Bank", "sectoral", "ind_niftypsubanklist.csv", "/indices/equity/sectoral-indices/nifty-psu-bank"),
    IndexSpec("Nifty Realty", "sectoral", "ind_niftyrealtylist.csv", "/indices/equity/sectoral-indices/nifty-realty"),
    IndexSpec("Nifty Healthcare", "sectoral", "ind_niftyhealthcarelist.csv", "/indices/equity/sectoral-indices/nifty-healthcare"),
    IndexSpec("Nifty Consumer Durables", "sectoral", "ind_niftyconsumerdurableslist.csv", "/indices/equity/sectoral-indices/nifty-consumer-durables"),
    IndexSpec("Nifty Oil & Gas", "sectoral", "ind_niftyoilgaslist.csv", "/indices/equity/sectoral-indices/nifty-oil-gas"),
    IndexSpec("Nifty Chemicals", "sectoral", "ind_niftychemicalslist.csv", "/indices/equity/sectoral-indices/nifty-chemicals"),
    IndexSpec("Nifty Financial Services Ex-Bank", "sectoral", "ind_niftyfinancialservicesexbank_list.csv", "/indices/equity/sectoral-indices/nifty-financial-services-ex-bank"),
    # Thematic
    IndexSpec("Nifty Commodities", "thematic", "ind_niftycommoditieslist.csv", "/indices/equity/thematic-indices/nifty-commodities"),
    IndexSpec("Nifty CPSE", "thematic", "ind_niftycpselist.csv", "/indices/equity/thematic-indices/nifty-cpse"),
    IndexSpec("Nifty Energy", "thematic", "ind_niftyenergylist.csv", "/indices/equity/thematic-indices/nifty-energy"),
    IndexSpec("Nifty India Consumption", "thematic", "ind_niftyconsumptionlist.csv", "/indices/equity/thematic-indices/nifty-india-consumption"),
    IndexSpec("Nifty Infrastructure", "thematic", "ind_niftyinfralist.csv", "/indices/equity/thematic-indices/nifty-infrastructure"),
    IndexSpec("Nifty India Manufacturing", "thematic", "ind_niftyindiamanufacturing_list.csv", "/indices/equity/thematic-indices/nifty-india-manufacturing"),
    IndexSpec("Nifty MNC", "thematic", "ind_niftymnclist.csv", "/indices/equity/thematic-indices/nifty-mnc"),
    IndexSpec("Nifty PSE", "thematic", "ind_niftypselist.csv", "/indices/equity/thematic-indices/nifty-pse"),
    IndexSpec("Nifty Services Sector", "thematic", "ind_niftyservicelist.csv", "/indices/equity/thematic-indices/nifty-services-sector"),
    IndexSpec("Nifty India Digital", "thematic", "ind_niftyindiadigital_list.csv", "/indices/equity/thematic-indices/nifty-india-digital"),
    IndexSpec("Nifty India Defence", "thematic", "ind_niftyindiadefence_list.csv", "/indices/equity/thematic-indices/nifty-india-defence"),
    IndexSpec("Nifty Mobility", "thematic", "ind_niftymobility_list.csv", "/indices/equity/thematic-indices/nifty-mobility"),
    IndexSpec("Nifty Non-Cyclical Consumer", "thematic", "ind_niftynoncyclicalconsumer_list.csv", "/indices/equity/thematic-indices/nifty-non-cyclical-consumer"),
    IndexSpec("Nifty Housing", "thematic", "ind_niftyhousing_list.csv", "/indices/equity/thematic-indices/nifty-housing"),
    IndexSpec("Nifty Transportation & Logistics", "thematic", "ind_niftytransportationandlogistics_list.csv", "/indices/equity/thematic-indices/nifty-transportation-logistics"),
    IndexSpec("Nifty India Tourism", "thematic", "ind_niftyindiatourism_list.csv", "/indices/equity/thematic-indices/nifty-india-tourism"),
    IndexSpec("Nifty Capital Markets", "thematic", "ind_niftycapitalmarkets_list.csv", "/indices/equity/thematic-indices/nifty-capital-markets"),
    IndexSpec("Nifty Rural", "thematic", "ind_niftyrural_list.csv", "/indices/equity/thematic-indices/nifty-rural"),
    IndexSpec("Nifty REITs & InvITs", "thematic", "ind_niftyreitsandinvits_list.csv", "/indices/equity/thematic-indices/nifty-reits-invits"),
]


def _session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(HEADERS)
    try:
        sess.get(NIFTY_HOME, timeout=20)
    except requests.RequestException:
        pass
    try:
        sess.get("https://www.nseindia.com", timeout=20)
    except requests.RequestException:
        pass
    return sess


def sector_label_from_index(name: str) -> str:
    """Nifty IT → IT; Nifty Financial Services → Financial Services."""
    text = re.sub(r"^nifty\s+", "", name.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text or name.strip()


def index_key_from_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().upper())


def _candidate_urls(spec: IndexSpec, page_csv_href: str | None = None) -> list[str]:
    urls: list[str] = []
    if page_csv_href:
        urls.append(page_csv_href)
    urls.extend(
        [
            f"{NIFTY_CONSTITUENT_BASE}/{spec.csv_name}",
            f"{NSE_INDICES_BASE}/{spec.csv_name}",
            f"{NSE_WWW1_BASE}/{spec.csv_name}",
        ]
    )
    # Alternate underscore conventions sometimes used by NSE.
    alt = spec.csv_name.replace("list.csv", "_list.csv")
    if alt != spec.csv_name:
        urls.extend(
            [
                f"{NIFTY_CONSTITUENT_BASE}/{alt}",
                f"{NSE_INDICES_BASE}/{alt}",
                f"{NSE_WWW1_BASE}/{alt}",
            ]
        )
    # Dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _find_csv_on_page(sess: requests.Session, page_path: str) -> str | None:
    if not page_path:
        return None
    url = urljoin(NIFTY_HOME, page_path)
    try:
        resp = sess.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        html = resp.text
    except requests.RequestException:
        return None
    # Prefer explicit Index Constituent / ind_*list.csv links
    patterns = [
        r'href=["\']([^"\']*IndexConstituent[^"\']+\.csv)["\']',
        r'href=["\']([^"\']*ind_[^"\']*list\.csv)["\']',
        r'href=["\']([^"\']+\.csv)["\']',
    ]
    for pat in patterns:
        for match in re.finditer(pat, html, flags=re.IGNORECASE):
            href = match.group(1)
            if "list" in href.lower() or "constituent" in href.lower() or "ind_" in href.lower():
                return urljoin(url, href)
    return None


def _looks_like_constituent_csv(text: str) -> bool:
    head = text[:500].lower()
    return "symbol" in head and ("company" in head or "isin" in head or "industry" in head)


def download_one(sess: requests.Session, spec: IndexSpec, dest_dir: Path) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / spec.csv_name
    page_href = _find_csv_on_page(sess, spec.page_path)
    last_err = ""
    for url in _candidate_urls(spec, page_href):
        try:
            resp = sess.get(url, timeout=40)
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code} {url}"
                continue
            content_type = (resp.headers.get("Content-Type") or "").lower()
            text = resp.content.decode("utf-8-sig", errors="replace")
            if "html" in content_type and not _looks_like_constituent_csv(text):
                last_err = f"HTML not CSV {url}"
                continue
            if not _looks_like_constituent_csv(text):
                last_err = f"Unexpected body {url}"
                continue
            dest.write_bytes(resp.content)
            rows = max(0, text.count("\n") - 1)
            return {
                "ok": True,
                "name": spec.name,
                "category": spec.category,
                "csv_name": spec.csv_name,
                "source_url": url,
                "local_path": str(dest.relative_to(BACKEND_ROOT)).replace("\\", "/"),
                "row_count": rows,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }
        except requests.RequestException as exc:
            last_err = str(exc)
            time.sleep(0.4)
    return {
        "ok": False,
        "name": spec.name,
        "category": spec.category,
        "csv_name": spec.csv_name,
        "source_url": "",
        "local_path": "",
        "row_count": 0,
        "error": last_err,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }


def download_all(*, pause_s: float = 0.35) -> dict[str, Any]:
    """Discover/download Index Constituent CSVs into data/niftyindices/{category}/."""
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    sess = _session()
    results: list[dict[str, Any]] = []
    for spec in CATALOG:
        dest_dir = OUT_ROOT / spec.category
        result = download_one(sess, spec, dest_dir)
        results.append(result)
        status = "ok" if result["ok"] else f"FAIL {result.get('error', '')}"
        logger.info("%s [%s]: %s", spec.name, spec.category, status)
        time.sleep(pause_s)

    # Write manifest
    fields = ["name", "category", "csv_name", "source_url", "local_path", "row_count", "downloaded_at", "ok", "error"]
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    ok = [r for r in results if r.get("ok")]
    fail = [r for r in results if not r.get("ok")]
    clubbed = build_all_symbols_csv()
    return {
        "downloaded": len(ok),
        "failed": len(fail),
        "total": len(results),
        "manifest": str(MANIFEST_PATH),
        "failures": [{"name": r["name"], "error": r.get("error")} for r in fail],
        "all_symbols": clubbed,
    }


def _normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def parse_constituent_csv(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        return []
    header_map = {_normalize_header(h): h for h in reader.fieldnames}

    def col(*aliases: str) -> str | None:
        for a in aliases:
            key = _normalize_header(a)
            if key in header_map:
                return header_map[key]
        return None

    sym_col = col("Symbol", "NSE Symbol", "Ticker")
    name_col = col("Company Name", "Company", "Security Name")
    ind_col = col("Industry", "Basic Industry", "Sector")
    series_col = col("Series")
    isin_col = col("ISIN Code", "ISIN")
    weight_col = col("Weightage", "Weight", "Weight (%)")
    if not sym_col:
        return []

    rows: list[dict[str, Any]] = []
    for raw in reader:
        symbol = (raw.get(sym_col) or "").strip().upper()
        if not symbol or symbol == "SYMBOL":
            continue
        weight = None
        if weight_col and raw.get(weight_col):
            try:
                weight = float(str(raw[weight_col]).replace("%", "").replace(",", "").strip())
            except ValueError:
                weight = None
        rows.append(
            {
                "symbol": symbol,
                "company_name": (raw.get(name_col) or "").strip() if name_col else None,
                "industry": (raw.get(ind_col) or "").strip() if ind_col else None,
                "series": (raw.get(series_col) or "").strip() if series_col else None,
                "isin": (raw.get(isin_col) or "").strip() if isin_col else None,
                "weight": weight,
            }
        )
    return rows


def build_all_symbols_csv(*, root: Path | None = None, out_path: Path | None = None) -> dict[str, Any]:
    """Dedupe all constituent CSVs into one row per Symbol with thematic>sectoral>broad priority."""
    base = Path(root) if root else OUT_ROOT
    dest = Path(out_path) if out_path else ALL_SYMBOLS_PATH
    if not base.exists():
        return {"ok": False, "error": f"No data at {base}", "path": str(dest), "rows": 0}

    # symbol → aggregation state
    agg: dict[str, dict[str, Any]] = {}
    files_read = 0

    csv_files = sorted(base.glob("*/*.csv"))
    for path in csv_files:
        category = path.parent.name
        if category not in PRIORITY:
            continue
        spec = _spec_for_csv(path)
        if spec is None:
            continue
        rows = parse_constituent_csv(path)
        if not rows:
            continue
        files_read += 1
        cat_priority = PRIORITY[category]
        for row in rows:
            symbol = row["symbol"]
            state = agg.get(symbol)
            if state is None:
                state = {
                    "symbol": symbol,
                    "company_name": row.get("company_name") or "",
                    "industry": row.get("industry") or "",
                    "series": row.get("series") or "",
                    "isin": row.get("isin") or "",
                    "priority": cat_priority,
                    "indices": set(),
                    "categories": set(),
                    "indices_by_category": defaultdict(set),
                    "meta_by_priority": {},
                }
                agg[symbol] = state

            state["indices"].add(spec.name)
            state["categories"].add(category)
            state["indices_by_category"][category].add(spec.name)

            if cat_priority > state["priority"]:
                state["priority"] = cat_priority

            # Prefer identity fields from the highest-priority category seen
            meta = {
                "company_name": row.get("company_name") or "",
                "industry": row.get("industry") or "",
                "series": row.get("series") or "",
                "isin": row.get("isin") or "",
            }
            prev_meta_p = state["meta_by_priority"].get(cat_priority)
            if prev_meta_p is None:
                state["meta_by_priority"][cat_priority] = meta
            else:
                # Fill blanks from later files in same category
                for key, val in meta.items():
                    if val and not prev_meta_p.get(key):
                        prev_meta_p[key] = val

    out_rows: list[dict[str, Any]] = []
    for symbol, state in agg.items():
        priority = int(state["priority"])
        priority_category = PRIORITY_TO_CATEGORY[priority]
        winning_indices = sorted(state["indices_by_category"].get(priority_category, set()))
        primary_index = winning_indices[0] if winning_indices else ""
        meta = state["meta_by_priority"].get(priority) or {}
        industry_raw = meta.get("industry") or state["industry"]
        out_rows.append(
            {
                "Symbol": symbol,
                "Company Name": meta.get("company_name") or state["company_name"],
                "Industry": normalize_industry(industry_raw) or industry_raw or "",
                "Series": meta.get("series") or state["series"],
                "ISIN Code": meta.get("isin") or state["isin"],
                "priority": priority,
                "priority_category": priority_category,
                "primary_index": primary_index,
                "indices": "|".join(sorted(state["indices"])),
                "categories": "|".join(
                    sorted(state["categories"], key=lambda c: (-PRIORITY[c], c))
                ),
            }
        )

    out_rows.sort(key=lambda r: (-int(r["priority"]), r["Symbol"]))
    dest.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "Symbol",
        "Company Name",
        "Industry",
        "Series",
        "ISIN Code",
        "priority",
        "priority_category",
        "primary_index",
        "indices",
        "categories",
    ]
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    by_priority = {3: 0, 2: 0, 1: 0}
    for row in out_rows:
        by_priority[int(row["priority"])] = by_priority.get(int(row["priority"]), 0) + 1

    try:
        rel_path = str(dest.relative_to(BACKEND_ROOT)).replace("\\", "/")
    except ValueError:
        rel_path = str(dest)

    return {
        "ok": True,
        "path": rel_path,
        "rows": len(out_rows),
        "files_read": files_read,
        "by_priority": {
            "thematic": by_priority.get(3, 0),
            "sectoral": by_priority.get(2, 0),
            "broad": by_priority.get(1, 0),
        },
    }


def _spec_for_csv(path: Path) -> IndexSpec | None:
    name = path.name.lower()
    for spec in CATALOG:
        if spec.csv_name.lower() == name:
            return spec
        alt = spec.csv_name.replace("list.csv", "_list.csv").lower()
        if alt == name:
            return spec
    # Infer category from parent folder
    category = path.parent.name if path.parent.name in {"broad", "sectoral", "thematic"} else "thematic"
    stem = path.stem
    pretty = stem.replace("ind_", "").replace("_list", "").replace("list", "")
    pretty = pretty.replace("_", " ").replace("nifty", "Nifty").strip()
    return IndexSpec(pretty.title(), category, path.name, "")


def _majority_industry(values: list[str]) -> str | None:
    if not values:
        return None
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    # Prefer highest count; ties → longest label (more specific) then alpha
    return max(counts.items(), key=lambda kv: (kv[1], len(kv[0]), kv[0]))[0]


def import_constituents(session: Session, *, root: Path | None = None) -> dict[str, Any]:
    """Load CSVs → memberships + Stock.sector/industry.

    Industry on Stock is the *majority* Industry within the stock's winning
    Nifty sectoral index (so Nifty Metal members show Metals & Mining even when
    NSE tags a name Capital Goods). Broad/thematic still contribute memberships.
    """
    base = Path(root) if root else OUT_ROOT
    if not base.exists():
        return {"ok": False, "error": f"No data at {base}; run scrape-nifty-constituents first"}

    category_rank = {"sectoral": 3, "broad": 2, "thematic": 1}
    as_of = date.today()
    csv_files = sorted(base.glob("*/*.csv"))
    csv_files = [p for p in csv_files if p.name.lower() != "manifest.csv"]

    memberships_written = 0
    memberships_with_industry = 0
    unknown_symbols: set[str] = set()
    sector_updates = 0
    industry_updates = 0
    industry_aligned = 0
    conflicts: list[str] = []
    indices_loaded = 0

    # Sectoral → Stock.sector: symbol → (weight, sector_label, index_name)
    sectoral_best: dict[str, tuple[float, str, str]] = {}
    # Per sectoral index: list of Industry values from constituent CSV
    sectoral_industries: dict[str, list[str]] = defaultdict(list)
    # Fallback primary when no sectoral: symbol → (rank, weight, industry)
    industry_best: dict[str, tuple[int, float, str]] = {}
    industries_by_symbol: dict[str, set[str]] = {}

    for path in csv_files:
        if path.parent.name not in {"broad", "sectoral", "thematic"}:
            continue
        spec = _spec_for_csv(path)
        if spec is None:
            continue
        rows = parse_constituent_csv(path)
        if not rows:
            logger.warning("No rows parsed: %s", path)
            continue
        indices_loaded += 1
        index_key = spec.index_key
        session.execute(delete(StockIndexMembership).where(StockIndexMembership.index_key == index_key))

        for row in rows:
            symbol = row["symbol"]
            stock = get_stock_by_symbol(session, symbol)
            if stock is None:
                unknown_symbols.add(symbol)
                continue
            weight = row.get("weight")
            industry = (row.get("industry") or "").strip() or None
            session.add(
                StockIndexMembership(
                    stock_id=stock.id,
                    index_key=index_key,
                    index_name=spec.name,
                    category=spec.category,
                    industry=industry,
                    weight=weight,
                    as_of=as_of,
                )
            )
            memberships_written += 1
            if industry:
                memberships_with_industry += 1
                industries_by_symbol.setdefault(symbol, set()).add(industry)
                rank = category_rank.get(spec.category, 0)
                w = float(weight) if weight is not None else 0.0
                prev = industry_best.get(symbol)
                if prev is None or rank > prev[0] or (rank == prev[0] and w > prev[1]):
                    industry_best[symbol] = (rank, w, industry)

            if spec.category == "sectoral":
                if industry:
                    sectoral_industries[spec.name].append(industry)
                label = sector_label_from_index(spec.name)
                w = float(weight) if weight is not None else 0.0
                prev = sectoral_best.get(symbol)
                if prev is None or w > prev[0]:
                    if prev is not None and prev[2] != spec.name and prev[0] == w == 0.0:
                        conflicts.append(f"{symbol}: {prev[2]} vs {spec.name}")
                    sectoral_best[symbol] = (w, label, spec.name)

        session.flush()

    sectoral_mode: dict[str, str] = {
        name: mode
        for name, values in sectoral_industries.items()
        if (mode := _majority_industry(values))
    }

    # Apply sectoral → Stock.sector + align industry to that index's majority Industry
    for symbol, (_w, label, index_name) in sectoral_best.items():
        stock = get_stock_by_symbol(session, symbol)
        if stock is None:
            continue
        if stock.sector != label:
            stock.sector = label
            sector_updates += 1
        mode_ind = sectoral_mode.get(index_name)
        if mode_ind and stock.industry != mode_ind:
            if stock.industry and stock.industry != mode_ind:
                industry_aligned += 1
            stock.industry = mode_ind
            industry_updates += 1
            industries_by_symbol.setdefault(symbol, set()).add(mode_ind)

    # Non-sectoral symbols: primary industry from broad/thematic (sectoral already handled)
    for symbol, (_rank, _w, industry) in industry_best.items():
        if symbol in sectoral_best:
            continue
        stock = get_stock_by_symbol(session, symbol)
        if stock is None:
            continue
        if stock.industry != industry:
            stock.industry = industry
            industry_updates += 1

    multi_industry = sum(1 for inds in industries_by_symbol.values() if len(inds) > 1)

    session.commit()
    return {
        "ok": True,
        "indices_loaded": indices_loaded,
        "memberships": memberships_written,
        "memberships_with_industry": memberships_with_industry,
        "sector_updates": sector_updates,
        "industry_updates": industry_updates,
        "industry_aligned_to_sectoral_mode": industry_aligned,
        "sectoral_industry_modes": sectoral_mode,
        "symbols_with_industry": len(industry_best),
        "symbols_multi_industry": multi_industry,
        "unknown_symbols": len(unknown_symbols),
        "unknown_sample": sorted(unknown_symbols)[:20],
        "sector_conflicts": len(conflicts),
        "conflict_sample": conflicts[:15],
        "as_of": as_of.isoformat(),
    }


def sync_constituents(session: Session) -> dict[str, Any]:
    download = download_all()  # also rebuilds all_symbols.csv
    imported = import_constituents(session)
    # Rebuild after import in case local CSVs changed without re-download
    clubbed = build_all_symbols_csv()
    applied = apply_all_symbols_industries(session)
    split = apply_split_industries(session)
    return {
        "download": download,
        "import": imported,
        "all_symbols": clubbed,
        "industries": applied,
        "split_industries": split,
    }


def apply_all_symbols_industries(session: Session, *, path: Path | None = None) -> dict[str, Any]:
    """Set Stock.industry and Stock.sector from all_symbols.csv Industry (normalized)."""
    csv_path = Path(path) if path else ALL_SYMBOLS_PATH
    if not csv_path.exists():
        clubbed = build_all_symbols_csv()
        if not clubbed.get("ok"):
            return {"ok": False, "error": f"Missing {csv_path}", "club": clubbed}

    updated = 0
    unchanged = 0
    missing = 0
    blank = 0
    missing_sample: list[str] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symbol = (row.get("Symbol") or "").strip().upper()
            if not symbol:
                continue
            industry = normalize_industry(row.get("Industry"))
            if not industry:
                blank += 1
                continue
            stock = get_stock_by_symbol(session, symbol)
            if stock is None:
                missing += 1
                if len(missing_sample) < 20:
                    missing_sample.append(symbol)
                continue
            if stock.industry == industry and stock.sector == industry:
                unchanged += 1
                continue
            stock.industry = industry
            stock.sector = industry
            updated += 1

    session.commit()
    return {
        "ok": True,
        "path": str(csv_path),
        "updated": updated,
        "unchanged": unchanged,
        "missing": missing,
        "blank_industry": blank,
        "missing_sample": missing_sample,
    }


def apply_split_industries(session: Session) -> dict[str, Any]:
    """Explode comma-separated industries into primary + broad_industry tags for all stocks."""
    stocks = session.scalars(select(Stock).where(Stock.is_active.is_(True))).all()
    updated = 0
    unchanged = 0
    blank = 0
    multi = 0
    samples: list[dict[str, str]] = []

    for stock in stocks:
        raw = (stock.industry or stock.sector or "").strip()
        if not raw:
            blank += 1
            continue
        # If industry already pipe-tagged but sector/industry still have commas, prefer industry
        parts = split_industry_labels(raw)
        if not parts and stock.sector:
            parts = split_industry_labels(stock.sector)
        if not parts:
            blank += 1
            continue
        primary = parts[0]
        tags = "|".join(parts)
        if len(parts) > 1:
            multi += 1
        if (
            stock.industry == primary
            and stock.sector == primary
            and (stock.broad_industry or "") == tags
        ):
            unchanged += 1
            continue
        stock.industry = primary
        stock.sector = primary
        stock.broad_industry = tags
        updated += 1
        if len(samples) < 15 and len(parts) > 1:
            samples.append(
                {
                    "symbol": stock.symbol,
                    "from": raw,
                    "primary": primary,
                    "tags": tags,
                }
            )

    session.commit()
    return {
        "ok": True,
        "updated": updated,
        "unchanged": unchanged,
        "blank": blank,
        "multi_tag_stocks": multi,
        "sample_splits": samples,
    }
