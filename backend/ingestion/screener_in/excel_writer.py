from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook

from ingestion.screener_in.parse import LongRow, ParsedCompany

FUNDAMENTALS_HEADERS = [
    "symbol",
    "company_name",
    "market_cap",
    "pe",
    "book_value",
    "dividend_yield",
    "roe",
    "roce",
    "sales_latest",
    "pat_latest",
    "eps_latest",
    "debt_to_equity",
    "scraped_at",
    "source_url",
    "status",
]

SHAREHOLDING_HEADERS = [
    "symbol",
    "period",
    "promoter_pct",
    "fii_pct",
    "dii_pct",
    "public_pct",
    "promoter_pledge_pct",
    "scraped_at",
    "status",
]

LONG_HEADERS = [
    "symbol",
    "section",
    "metric",
    "period",
    "value_raw",
    "value_num",
    "scraped_at",
]

STATUS_HEADERS = [
    "symbol",
    "http_status",
    "cache_hit",
    "status",
    "error",
    "source_url",
    "scraped_at",
    "long_rows",
]

SECTION_TO_STEM = {
    "quarters": "quarters",
    "profit-loss": "profit_loss",
    "balance-sheet": "balance_sheet",
    "cash-flow": "cash_flow",
    "ratios": "ratios",
    "shareholding": "shareholding_history",
}


class IncrementalWriter:
    """Append CSV after every symbol; sync xlsx on flush for live Excel viewing."""

    def __init__(self, out_dir: Path, *, flush_every: int = 1, max_long_rows_per_file: int = 200_000) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.flush_every = max(1, flush_every)
        self.max_long_rows = max_long_rows_per_file
        self._since_flush = 0
        self._section_stem = dict(SECTION_TO_STEM)
        self._stem_counts: dict[str, int] = {stem: 0 for stem in self._section_stem.values()}
        self._stem_part: dict[str, int] = {stem: 1 for stem in set(SECTION_TO_STEM.values())}
        self._ensure_headers()

    def _csv_path(self, stem: str) -> Path:
        return self.out_dir / f"{stem}.csv"

    def _xlsx_path(self, stem: str) -> Path:
        return self.out_dir / f"{stem}.xlsx"

    def _ensure_csv(self, stem: str, headers: list[str]) -> None:
        path = self._csv_path(stem)
        if path.exists():
            return
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=headers).writeheader()

    def _ensure_headers(self) -> None:
        self._ensure_csv("fundamentals", FUNDAMENTALS_HEADERS)
        self._ensure_csv("shareholding_latest", SHAREHOLDING_HEADERS)
        self._ensure_csv("scrape_status", STATUS_HEADERS)
        for stem in set(self._section_stem.values()):
            self._ensure_csv(stem, LONG_HEADERS)

    def _append_csv(self, stem: str, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
        with self._csv_path(stem).open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
            for row in rows:
                writer.writerow({key: row.get(key) for key in headers})

    def _sync_xlsx_from_csv(self, stem: str) -> None:
        csv_path = self._csv_path(stem)
        if not csv_path.exists():
            return
        wb = Workbook()
        ws = wb.active
        ws.title = stem[:31]
        with csv_path.open(encoding="utf-8", newline="") as handle:
            for i, row in enumerate(csv.reader(handle), start=1):
                for j, value in enumerate(row, start=1):
                    ws.cell(row=i, column=j, value=value)
        try:
            wb.save(self._xlsx_path(stem))
        except PermissionError:
            pass

    def _fundamentals_row(self, parsed: ParsedCompany) -> dict[str, Any]:
        r = parsed.ratios
        return {
            "symbol": parsed.symbol,
            "company_name": parsed.company_name,
            "market_cap": r.get("market_cap_num", r.get("market_cap")),
            "pe": r.get("pe_num", r.get("pe")),
            "book_value": r.get("book_value_num", r.get("book_value")),
            "dividend_yield": r.get("dividend_yield_num", r.get("dividend_yield")),
            "roe": r.get("roe_num"),
            "roce": r.get("roce_num"),
            "sales_latest": r.get("sales_latest_num"),
            "pat_latest": r.get("pat_latest_num"),
            "eps_latest": r.get("eps_latest_num"),
            "debt_to_equity": r.get("debt_to_equity_num"),
            "scraped_at": parsed.scraped_at,
            "source_url": parsed.source_url,
            "status": parsed.status,
        }

    def _shareholding_row(self, parsed: ParsedCompany) -> dict[str, Any]:
        s = parsed.shareholding_latest
        return {
            "symbol": parsed.symbol,
            "period": s.get("period"),
            "promoter_pct": s.get("promoter_pct"),
            "fii_pct": s.get("fii_pct"),
            "dii_pct": s.get("dii_pct"),
            "public_pct": s.get("public_pct"),
            "promoter_pledge_pct": s.get("promoter_pledge_pct"),
            "scraped_at": parsed.scraped_at,
            "status": parsed.status,
        }

    def _roll_stem(self, base_stem: str) -> str:
        part = self._stem_part.get(base_stem, 1) + 1
        self._stem_part[base_stem] = part
        new_stem = f"{base_stem}_{part:02d}"
        self._stem_counts[new_stem] = 0
        self._ensure_csv(new_stem, LONG_HEADERS)
        return new_stem

    def write_parsed(
        self,
        parsed: ParsedCompany,
        *,
        http_status: int | None = None,
        cache_hit: bool = False,
        error: str | None = None,
    ) -> None:
        self._append_csv("fundamentals", FUNDAMENTALS_HEADERS, [self._fundamentals_row(parsed)])
        self._append_csv("shareholding_latest", SHAREHOLDING_HEADERS, [self._shareholding_row(parsed)])

        by_section: dict[str, list[LongRow]] = {}
        for row in parsed.long_rows:
            by_section.setdefault(row.section, []).append(row)

        for section_id, rows in by_section.items():
            stem = self._section_stem.get(section_id)
            if not stem or not rows:
                continue
            base = SECTION_TO_STEM.get(section_id, stem)
            if self._stem_counts.get(stem, 0) + len(rows) > self.max_long_rows:
                stem = self._roll_stem(base)
                self._section_stem[section_id] = stem
            self._append_csv(
                stem,
                LONG_HEADERS,
                [
                    {
                        "symbol": parsed.symbol,
                        "section": row.section,
                        "metric": row.metric,
                        "period": row.period,
                        "value_raw": row.value_raw,
                        "value_num": row.value_num,
                        "scraped_at": parsed.scraped_at,
                    }
                    for row in rows
                ],
            )
            self._stem_counts[stem] = self._stem_counts.get(stem, 0) + len(rows)

        self._append_csv(
            "scrape_status",
            STATUS_HEADERS,
            [
                {
                    "symbol": parsed.symbol,
                    "http_status": http_status,
                    "cache_hit": int(cache_hit),
                    "status": parsed.status,
                    "error": error or parsed.error,
                    "source_url": parsed.source_url,
                    "scraped_at": parsed.scraped_at,
                    "long_rows": len(parsed.long_rows),
                }
            ],
        )

        self._since_flush += 1
        if self._since_flush >= self.flush_every:
            self.flush_xlsx()
            self._since_flush = 0

    def flush_xlsx(self) -> None:
        stems = {"fundamentals", "shareholding_latest", "scrape_status", *self._stem_counts.keys()}
        for stem in stems:
            self._sync_xlsx_from_csv(stem)


def load_completed_symbols(status_csv: Path) -> set[str]:
    if not status_csv.exists():
        return set()
    done: set[str] = set()
    with status_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("status") or "").lower() == "ok":
                sym = (row.get("symbol") or "").strip().upper()
                if sym:
                    done.add(sym)
    return done
