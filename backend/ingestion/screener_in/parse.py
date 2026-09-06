from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from ingestion.screener_in.numbers import normalize_key, parse_number

SECTION_IDS = (
    "quarters",
    "profit-loss",
    "balance-sheet",
    "cash-flow",
    "ratios",
    "shareholding",
)

RATIO_ALIASES = {
    "market cap": "market_cap",
    "current price": "current_price",
    "high / low": "high_low",
    "stock p/e": "pe",
    "book value": "book_value",
    "dividend yield": "dividend_yield",
    "roce": "roce",
    "roe": "roe",
    "face value": "face_value",
}


@dataclass
class LongRow:
    section: str
    metric: str
    period: str
    value_raw: str
    value_num: float | None


@dataclass
class ParsedCompany:
    symbol: str
    company_name: str | None = None
    source_url: str | None = None
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ok"
    error: str | None = None
    ratios: dict[str, Any] = field(default_factory=dict)
    shareholding_latest: dict[str, Any] = field(default_factory=dict)
    long_rows: list[LongRow] = field(default_factory=list)
    broad_sector: str | None = None
    sector: str | None = None
    broad_industry: str | None = None
    industry: str | None = None


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True) if el else "").strip()


def parse_peers_taxonomy(soup: BeautifulSoup) -> dict[str, str | None]:
    """Read Broad Sector / Sector / Broad Industry / Industry from #peers breadcrumb."""
    out: dict[str, str | None] = {
        "broad_sector": None,
        "sector": None,
        "broad_industry": None,
        "industry": None,
    }
    peers = soup.select_one("section#peers") or soup.select_one("#peers")
    if peers is None:
        return out
    title_map = {
        "broad sector": "broad_sector",
        "sector": "sector",
        "broad industry": "broad_industry",
        "industry": "industry",
    }
    for link in peers.select("a[title]"):
        title = (link.get("title") or "").strip().lower()
        key = title_map.get(title)
        if not key:
            continue
        value = _text(link)
        if value:
            out[key] = value
    return out


def parse_top_ratios(soup: BeautifulSoup) -> dict[str, Any]:
    out: dict[str, Any] = {}
    # Common layouts: ul#top-ratios li, or .company-ratios li
    items = soup.select("#top-ratios li") or soup.select(".company-ratios li") or soup.select("ul#top-ratios li")
    for li in items:
        name_el = li.select_one(".name") or li.select_one("span.name")
        value_el = li.select_one(".value") or li.select_one("span.value")
        if not name_el and not value_el:
            # fallback: first text / second text
            parts = [p for p in _text(li).split("  ") if p]
            if len(parts) >= 2:
                name, value = parts[0], parts[-1]
            else:
                continue
        else:
            name, value = _text(name_el), _text(value_el)
        key = RATIO_ALIASES.get(normalize_key(name), normalize_key(name).replace(" ", "_").replace("/", "_"))
        out[key] = value
        out[f"{key}_num"] = parse_number(value)
    return out


def parse_data_table(section, section_id: str) -> list[LongRow]:
    rows: list[LongRow] = []
    if section is None:
        return rows
    # Prefer quarterly table when multiple tables exist (shareholding)
    tables = section.select("table.data-table") or section.select("table")
    if not tables:
        return rows
    table = tables[0]
    header_cells = table.select("thead tr th")
    if not header_cells:
        first = table.select_one("tr")
        header_cells = first.find_all(["th", "td"]) if first else []
    periods = [_text(cell) for cell in header_cells[1:]]
    body_rows = table.select("tbody tr")
    if not body_rows:
        body_rows = table.select("tr")[1:]
    for tr in body_rows:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        metric = _text(cells[0]).rstrip("+").strip()
        if not metric:
            continue
        for period, cell in zip(periods, cells[1:]):
            if not period or period.lower() in {"", "+"}:
                continue
            raw = _text(cell)
            rows.append(
                LongRow(
                    section=section_id,
                    metric=metric,
                    period=period,
                    value_raw=raw,
                    value_num=parse_number(raw),
                )
            )
    return rows


def _latest_shareholding(long_rows: list[LongRow]) -> dict[str, Any]:
    by_metric: dict[str, list[LongRow]] = {}
    for row in long_rows:
        if row.section != "shareholding":
            continue
        by_metric.setdefault(normalize_key(row.metric), []).append(row)

    def latest(metric_key: str) -> LongRow | None:
        items = by_metric.get(metric_key) or []
        return items[-1] if items else None

    promoters = latest("promoters") or latest("promoter")
    fii = latest("fiis") or latest("fii") or latest("fpis") or latest("fii+")
    dii = latest("diis") or latest("dii") or latest("diis+")
    public = latest("public")
    pledge = latest("pledged percentage") or latest("promoter holding pledged")

    period = None
    for candidate in (promoters, fii, dii, public):
        if candidate:
            period = candidate.period
            break
    return {
        "period": period,
        "promoter_pct": promoters.value_num if promoters else None,
        "fii_pct": fii.value_num if fii else None,
        "dii_pct": dii.value_num if dii else None,
        "public_pct": public.value_num if public else None,
        "promoter_pledge_pct": pledge.value_num if pledge else None,
    }


def _latest_metric(long_rows: list[LongRow], section: str, *metric_names: str) -> float | None:
    wanted = {normalize_key(name) for name in metric_names}
    matches = [
        row
        for row in long_rows
        if row.section == section and normalize_key(row.metric) in wanted and row.value_num is not None
    ]
    return matches[-1].value_num if matches else None


def parse_company_html(symbol: str, html: str, source_url: str | None = None) -> ParsedCompany:
    soup = BeautifulSoup(html, "lxml")
    parsed = ParsedCompany(symbol=symbol.upper(), source_url=source_url)

    h1 = soup.select_one("h1")
    parsed.company_name = _text(h1) if h1 else None
    parsed.ratios = parse_top_ratios(soup)
    taxonomy = parse_peers_taxonomy(soup)
    parsed.broad_sector = taxonomy.get("broad_sector")
    parsed.sector = taxonomy.get("sector")
    parsed.broad_industry = taxonomy.get("broad_industry")
    parsed.industry = taxonomy.get("industry")

    for section_id in SECTION_IDS:
        section = soup.select_one(f"section#{section_id}") or soup.select_one(f"#{section_id}")
        parsed.long_rows.extend(parse_data_table(section, section_id))

    parsed.shareholding_latest = _latest_shareholding(parsed.long_rows)

    # Enrich snapshot from statement latest cells when top ratios missing
    if parsed.ratios.get("roe_num") is None:
        parsed.ratios["roe_num"] = _latest_metric(parsed.long_rows, "ratios", "ROE %", "ROE")
    if parsed.ratios.get("roce_num") is None:
        parsed.ratios["roce_num"] = _latest_metric(parsed.long_rows, "ratios", "ROCE %", "ROCE")

    sales = _latest_metric(parsed.long_rows, "profit-loss", "Sales", "Revenue")
    pat = _latest_metric(parsed.long_rows, "profit-loss", "Net Profit", "PAT", "Profit after tax")
    eps = _latest_metric(parsed.long_rows, "profit-loss", "EPS in Rs", "EPS")
    debt_eq = _latest_metric(parsed.long_rows, "ratios", "Debt to equity", "Debt to Equity")
    parsed.ratios["sales_latest_num"] = sales
    parsed.ratios["pat_latest_num"] = pat
    parsed.ratios["eps_latest_num"] = eps
    parsed.ratios["debt_to_equity_num"] = debt_eq

    if not parsed.ratios and not parsed.long_rows:
        parsed.status = "parse_empty"
        parsed.error = "No ratios or tables found"
    return parsed
