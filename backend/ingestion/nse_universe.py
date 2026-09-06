"""Pull NSE cash-market universe from daily bhavcopy (UDiFF or local pdDDMMYYYY)."""

from __future__ import annotations

import csv
import io
import json
import shutil
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config.settings import BACKEND_ROOT
from google_sheets.create_batches import MASTER_PATH

BHAV_DIR = BACKEND_ROOT / "data" / "bhavcopy"

# Cash / SME / ETF-like series we keep for StockFilter.
KEEP_SERIES = {
    "EQ",
    "BE",
    "BZ",
    "SM",
    "ST",
    "SZ",
    "IV",
    "RR",
    "GB",
    "GS",
    "E1",
}

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/all-reports",
}


def _parse_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    if not value:
        # Default: last weekday on/before "today" in local sense — caller usually passes date.
        return date.today()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y%m%d", "%d%m%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value}")


def pd_stem(day: date) -> str:
    return f"pd{day.strftime('%d%m%Y')}"


def classify_segment(series: str, isin: str, name: str) -> str:
    series_u = (series or "").strip().upper()
    isin_u = (isin or "").strip().upper()
    name_u = (name or "").upper()
    if series_u in {"SM", "ST", "SZ"}:
        return "SME"
    if isin_u.startswith("INF") or "ETF" in name_u or name_u.endswith(" BEES") or "BEES" in name_u:
        return "ETF"
    if series_u in {"IV"}:
        return "INVIT"
    return "EQ"


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip(): c for c in frame.columns}
    lower = {str(c).strip().lower(): c for c in frame.columns}

    def pick(*names: str) -> Any:
        for name in names:
            if name in cols:
                return cols[name]
            if name.lower() in lower:
                return lower[name.lower()]
        return None

    sym_col = pick("SYMBOL", "TckrSymb", "Security Symbol", "symbol")
    series_col = pick("SERIES", "SctySrs", "series")
    isin_col = pick("ISIN", "Isin", "isin")
    name_col = pick(
        "FinInstrmNm",
        "SECURITY",
        "Security Name",
        "NAME OF COMPANY",
        "company_name",
        "FinInstrmNm",
    )
    if sym_col is None:
        raise ValueError(f"No symbol column in bhavcopy columns={list(frame.columns)}")

    out = pd.DataFrame()
    out["nse_symbol"] = frame[sym_col].astype(str).str.strip().str.upper()
    out["series"] = frame[series_col].astype(str).str.strip().str.upper() if series_col else ""
    out["isin"] = frame[isin_col].astype(str).str.strip().str.upper() if isin_col else ""
    out["company_name"] = frame[name_col].astype(str).str.strip() if name_col else out["nse_symbol"]
    out = out[out["nse_symbol"].notna() & (out["nse_symbol"] != "") & (out["nse_symbol"] != "NAN")]
    # Drop junk
    out = out[~out["nse_symbol"].isin({"SYMBOL", "TCKRSYMB"})]
    if series_col:
        out = out[out["series"].isin(KEEP_SERIES) | out["series"].eq("") | out["isin"].str.startswith("INF")]
    # Prefer EQ over other series for same symbol
    series_rank = {s: i for i, s in enumerate(["EQ", "BE", "BZ", "SM", "ST", "SZ", "IV", "RR", "GB", "GS", "E1", ""])}
    out["_rank"] = out["series"].map(lambda s: series_rank.get(s, 99))
    out = out.sort_values(["nse_symbol", "_rank"]).drop_duplicates("nse_symbol", keep="first")
    out["segment"] = [
        classify_segment(s, i, n) for s, i, n in zip(out["series"], out["isin"], out["company_name"])
    ]
    out["listing_date"] = ""
    out["active_flag"] = "True"
    return out.drop(columns=["_rank"])


def _session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(NSE_HEADERS)
    # Warm cookies
    try:
        sess.get("https://www.nseindia.com", timeout=20)
    except requests.RequestException:
        pass
    return sess


def download_udiff_cm(day: date, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    ymd = day.strftime("%Y%m%d")
    filename = f"BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"
    url = f"https://nsearchives.nseindia.com/content/cm/{filename}"
    out = dest_dir / filename
    sess = _session()
    resp = sess.get(url, timeout=60)
    if resp.status_code != 200:
        raise FileNotFoundError(f"UDiFF bhavcopy HTTP {resp.status_code} for {url}")
    out.write_bytes(resp.content)
    return out


def download_sec_bhavdata_full(day: date, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    ddmmyyyy = day.strftime("%d%m%Y")
    filename = f"sec_bhavdata_full_{ddmmyyyy}.csv"
    url = f"https://nsearchives.nseindia.com/products/content/{filename}"
    out = dest_dir / filename
    sess = _session()
    resp = sess.get(url, timeout=60)
    if resp.status_code != 200:
        raise FileNotFoundError(f"sec_bhavdata_full HTTP {resp.status_code} for {url}")
    out.write_bytes(resp.content)
    return out


def find_local_pd(day: date, dest_dir: Path) -> Path | None:
    stem = pd_stem(day)
    for ext in (".xlsx", ".xls", ".csv", ".CSV", ".XLSX", ".XLS"):
        path = dest_dir / f"{stem}{ext}"
        if path.exists():
            return path
    # Any file starting with pd stem
    if dest_dir.exists():
        for path in dest_dir.glob(f"{stem}*"):
            if path.is_file():
                return path
    return None


def load_bhav_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError(f"No CSV inside {path}")
            with zf.open(names[0]) as handle:
                return pd.read_csv(handle)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def resolve_bhav_file(day: date, file: Path | None = None) -> tuple[Path, str]:
    BHAV_DIR.mkdir(parents=True, exist_ok=True)
    if file is not None:
        path = Path(file)
        if not path.is_absolute():
            path = (BACKEND_ROOT / path).resolve() if not path.exists() else path.resolve()
        if not path.exists():
            # also try under bhavcopy
            alt = BHAV_DIR / Path(file).name
            if alt.exists():
                path = alt
            else:
                raise FileNotFoundError(path)
        return path, "local-file"

    local = find_local_pd(day, BHAV_DIR)
    if local:
        return local, "local-pd"

    errors: list[str] = []
    try:
        return download_udiff_cm(day, BHAV_DIR), "udiff-cm"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"udiff: {exc}")
    try:
        return download_sec_bhavdata_full(day, BHAV_DIR), "sec-bhavdata-full"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"sec_bhavdata: {exc}")
    raise FileNotFoundError(
        f"Could not obtain bhavcopy for {day.isoformat()}. "
        f"Place {pd_stem(day)}.xlsx under {BHAV_DIR}. Errors: {'; '.join(errors)}"
    )


def write_master(rows: pd.DataFrame, path: Path = MASTER_PATH) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = 0
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            previous = max(0, sum(1 for _ in handle) - 1)
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)

    fieldnames = [
        "nse_symbol",
        "isin",
        "company_name",
        "listing_date",
        "active_flag",
        "segment",
        "series",
    ]
    ordered = rows.sort_values("nse_symbol")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for _, row in ordered.iterrows():
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    by_segment: dict[str, int] = {}
    for seg, count in ordered["segment"].value_counts().items():
        by_segment[str(seg)] = int(count)
    by_series: dict[str, int] = {}
    for ser, count in ordered["series"].value_counts().head(20).items():
        by_series[str(ser)] = int(count)

    report = {
        "previous": previous,
        "new": int(len(ordered)),
        "by_segment": by_segment,
        "by_series": by_series,
        "etf_sample": ordered.loc[ordered["segment"] == "ETF", "nse_symbol"].head(15).tolist(),
        "sme_sample": ordered.loc[ordered["segment"] == "SME", "nse_symbol"].head(15).tolist(),
        "master_path": str(path),
    }
    return report


def pull_nse_symbols(
    *,
    trade_date: str | date | None = None,
    file: str | Path | None = None,
) -> dict[str, Any]:
    day = _parse_date(trade_date) if trade_date or not file else date.today()
    if file:
        # Infer date from pdDDMMYYYY if possible
        name = Path(file).stem.lower()
        if name.startswith("pd") and len(name) >= 10:
            try:
                day = datetime.strptime(name[2:10], "%d%m%Y").date()
            except ValueError:
                day = _parse_date(trade_date) if trade_date else date.today()
        elif trade_date:
            day = _parse_date(trade_date)

    path, source = resolve_bhav_file(day, Path(file) if file else None)
    frame = load_bhav_dataframe(path)
    normalized = _normalize_frame(frame)
    report = write_master(normalized)
    report.update(
        {
            "trade_date": day.isoformat(),
            "source": source,
            "source_file": str(path),
        }
    )
    report_path = BHAV_DIR / f"pull_report_{day.strftime('%Y%m%d')}.json"
    BHAV_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def previous_weekday(day: date | None = None) -> date:
    cursor = day or date.today()
    while cursor.weekday() >= 5:  # Sat/Sun
        cursor -= timedelta(days=1)
    # If today is weekday but market may not have published yet, caller can pass explicit date.
    return cursor
