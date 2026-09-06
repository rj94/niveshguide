"""Normalize spreadsheet rows using header names rather than fixed column letters.

Sheet tabs are mapped by header text so
layout drift (extra columns, reordered fields) does not break ingestion.
"""

from __future__ import annotations

import math
import re
from typing import Any

HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "ticker", "nse symbol", "scrip", "scrip name", "name"),
    "company_name": ("company", "company name", "name of company"),
    "market_cap": ("market cap", "mcap", "marketcap", "mkt cap", "mkt. cap"),
    "ltp": ("ltp", "price", "last", "last price", "last traded price", "close", "cmp"),
    "day_high": ("day high", "high", "today high", "high price"),
    "prev_close": ("prev close", "previous close", "closeyest", "prev. close", "yesterday close"),
    "high_52_week": ("52 week high", "52w high", "high52", "fifty two week high", "52-week high"),
    "low_52_week": ("52 week low", "52w low", "low52", "fifty two week low", "52-week low"),
    "ma_3": ("3 day ma", "3 days ma", "3d ma", "ma3", "sma 3", "3days ma"),
    "ma_7": ("7 day ma", "7 days ma", "7d ma", "ma7", "sma 7", "7days ma"),
    "ma_21": ("21 day ma", "21 days ma", "21d ma", "ma21", "sma 21", "21days ma"),
    "ma_50": ("50 day ma", "50 days ma", "50d ma", "ma50", "sma 50", "50days ma"),
    "ma_200": ("200 day ma", "200 days ma", "200d ma", "ma200", "sma 200", "200days ma"),
    "crossover_3_7": ("3d > 7d", "crossover 3d > 7d", "3d>7d", "ma3 > ma7", "crossover(3d>7d)"),
    "above_ma_21": ("ltp > 21d", "above 21d", "ltp > 21", "ltp > 21 d"),
    "above_ma_200": ("ltp > 200d", "above 200d", "ltp > 200", "ltp > 200 d"),
    "golden_cross": ("50d > 200d", "crossover 50d > 200d", "golden cross", "crossover(50d>200d)"),
    "trend_score": ("trend score", "score"),
    "trend": ("trend", "trend label"),
    "pe": ("pe", "p/e", "pe ratio"),
    "eps": ("eps",),
    "volume": ("volume", "vol", "day volume", "traded volume"),
    "avg_volume_3m": ("3m avg vol", "3m average volume", "avg volume 3m", "3 month avg vol"),
    "avg_volume_6m": ("6m avg vol", "6m average volume", "avg volume 6m", "6 month avg vol"),
    "avg_volume_1y": ("1year avg vol", "1y avg vol", "1 year avg vol", "avg volume 1y", "1year average volume"),
    "distance_from_52w_high": ("distance from 52w high", "dist 52w", "% from 52w high"),
}


ERROR_TOKENS = {"", "#n/a", "#value!", "#ref!", "#div/0!", "#name?", "#num!", "#error!", "n/a", "na", "-", "—", "none", "null"}


def _clean_header(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("(", " ").replace(")", " ")
    text = text.replace(">", " > ").replace("<", " < ")
    text = re.sub(r"(\d+)(days)", r"\1 \2", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _compact_header(value: str) -> str:
    return re.sub(r"[^a-z0-9>]+", "", _clean_header(value))


def build_header_map(headers: list[str]) -> dict[str, int]:
    cleaned = [_clean_header(item) for item in headers]
    compacted = [_compact_header(item) for item in headers]
    mapping: dict[str, int] = {}
    for field, aliases in HEADER_ALIASES.items():
        compact_aliases = {_compact_header(alias) for alias in aliases}
        for index, header in enumerate(cleaned):
            if header in aliases or compacted[index] in compact_aliases:
                mapping[field] = index
                break
    if "symbol" not in mapping and cleaned:
        mapping["symbol"] = 0
    return mapping


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.lower() in ERROR_TOKENS:
        return None
    text = text.replace("%", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ERROR_TOKENS:
        return None
    if text in {"yes", "y", "true", "1", "bullish"}:
        return True
    if text in {"no", "n", "false", "0", "bearish"}:
        return False
    return None


TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.&-]{0,19}$")
SKIP_LABELS = {
    "symbol",
    "nse data",
    "close",
    "date",
    "marketcap",
    "market cap",
    "price",
    "high",
    "low",
    "ltp",
    "pe",
    "eps",
    "trend",
    "yes",
    "no",
    "up",
    "down",
}


def _is_ticker(value: str) -> bool:
    text = value.strip().upper()
    if not text or _clean_header(text) in SKIP_LABELS:
        return False
    return bool(TICKER_RE.match(text))


def _looks_wide(raw: list[list[str]]) -> bool:
    if len(raw) < 3:
        return False
    header0 = [_clean_header(str(cell)) for cell in raw[0][:8]]
    if header0 and header0[0] in {"symbol", "ticker"} and any("market" in item or item == "ltp" for item in header0):
        return False
    tickers = [cell for cell in raw[0] if _is_ticker(str(cell))]
    row_labels = {_clean_header(str(cell)) for row in raw[1:15] for cell in row[:4]}
    return len(tickers) >= 3 and ("marketcap" in row_labels or "price" in row_labels)


def _normalize_wide(raw: list[list[str]]) -> list[dict[str, Any]]:
    header = raw[0]
    symbol_cols: list[tuple[int, str]] = []
    for index, cell in enumerate(header):
        if _is_ticker(str(cell)):
            symbol_cols.append((index, str(cell).strip().upper()))
    metric_row: dict[str, int] = {}
    for row_index, row in enumerate(raw[:40]):
        labels = [_clean_header(str(cell)) for cell in row[:6]]
        for label in labels:
            if label in {"marketcap", "market cap", "mcap"}:
                metric_row["market_cap"] = row_index
            elif label in {"price", "ltp", "close"} and "price" not in metric_row and label != "close":
                metric_row["ltp"] = row_index
            elif label == "price":
                metric_row["ltp"] = row_index
            elif label in {"high", "day high"}:
                metric_row["day_high"] = row_index
            elif label in {"pe", "p/e"}:
                metric_row["pe"] = row_index
            elif label == "eps":
                metric_row["eps"] = row_index
            elif label in {"high52", "52 week high"}:
                metric_row["high_52_week"] = row_index
            elif label in {"low52", "52 week low"}:
                metric_row["low_52_week"] = row_index
    records = []
    for col, symbol in symbol_cols:
        record: dict[str, Any] = {"symbol": symbol}
        for field, row_index in metric_row.items():
            row = raw[row_index]
            record[field] = parse_number(row[col] if col < len(row) else None)
        records.append(record)
    return records


def normalize_rows(raw: list[list[str]]) -> list[dict[str, Any]]:
    if not raw:
        return []
    if _looks_wide(raw):
        return _normalize_wide(raw)
    header_row_index = 0
    for index, row in enumerate(raw[:8]):
        joined = " ".join(_clean_header(cell) for cell in row)
        if "symbol" in joined or "ticker" in joined:
            header_row_index = index
            break
    headers = raw[header_row_index]
    mapping = build_header_map(headers)
    records: list[dict[str, Any]] = []
    for row in raw[header_row_index + 1 :]:
        if not row or not any(str(cell).strip() for cell in row):
            continue
        record: dict[str, Any] = {}
        for field, index in mapping.items():
            cell = row[index] if index < len(row) else ""
            if field in {"symbol", "company_name", "trend"}:
                record[field] = str(cell).strip().upper() if field == "symbol" else str(cell).strip()
            elif field.startswith("crossover") or field.startswith("above") or field == "golden_cross":
                record[field] = parse_bool(cell)
            else:
                record[field] = parse_number(cell)
        if record.get("symbol"):
            records.append(record)
    return records
