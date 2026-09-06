from __future__ import annotations

import csv
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config.settings import BACKEND_ROOT
from database.models import Stock, StockFinancialPeriod, StockFundamental, StockOwnership
from database.repository import upsert_stock
from database.session import init_db
from ingestion.screener_in.numbers import parse_number

OUT_DIR = BACKEND_ROOT / "data" / "screener_in"
STATUS_CSV = OUT_DIR / "scrape_status.csv"

LONG_GLOBS = [
    "profit_loss*.csv",
    "balance_sheet*.csv",
    "cash_flow*.csv",
    "quarters*.csv",
    "ratios*.csv",
    "shareholding_history*.csv",
]

CHUNK = 2000

logger = logging.getLogger(__name__)


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return parse_number(value)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _as_of_date(row: dict[str, str]) -> date:
    ts = _parse_ts(row.get("scraped_at"))
    return ts.date() if ts else date.today()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _iter_csv(path: Path) -> Iterable[dict[str, str]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def load_ok_symbols(status_path: Path = STATUS_CSV) -> set[str]:
    if not status_path.exists():
        return set()
    ok: set[str] = set()
    with status_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("status") or "").lower() == "ok":
                sym = (row.get("symbol") or "").strip().upper()
                if sym:
                    ok.add(sym)
    return ok


def _stock_map(session: Session) -> dict[str, Stock]:
    return {stock.symbol.upper(): stock for stock in session.scalars(select(Stock)).all()}


def _ensure_stock(session: Session, cache: dict[str, Stock], symbol: str, company_name: str | None = None) -> Stock:
    sym = symbol.upper()
    if sym in cache:
        stock = cache[sym]
        if company_name and not stock.company_name:
            stock.company_name = company_name
        return stock
    stock = upsert_stock(session, sym, company_name=company_name)
    cache[sym] = stock
    return stock


def import_fundamentals(
    session: Session,
    rows: Iterable[dict[str, str]],
    cache: dict[str, Stock],
    ok_symbols: set[str] | None,
) -> int:
    count = 0
    for row in rows:
        if (row.get("status") or "").lower() not in {"ok", ""}:
            continue
        symbol = (row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        if ok_symbols is not None and symbol not in ok_symbols:
            continue
        stock = _ensure_stock(session, cache, symbol, row.get("company_name"))
        as_of = _as_of_date(row)
        existing = session.scalar(
            select(StockFundamental).where(
                StockFundamental.stock_id == stock.id,
                StockFundamental.as_of_date == as_of,
            )
        )
        payload = {
            "market_cap": _f(row.get("market_cap")),
            "pe": _f(row.get("pe")),
            "book_value": _f(row.get("book_value")),
            "dividend_yield": _f(row.get("dividend_yield")),
            "roe": _f(row.get("roe")),
            "roce": _f(row.get("roce")),
            "sales": _f(row.get("sales_latest")),
            "pat": _f(row.get("pat_latest")),
            "eps": _f(row.get("eps_latest")),
            "debt_equity": _f(row.get("debt_to_equity")),
            "source": "screener.in",
            "source_url": row.get("source_url") or None,
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            session.add(StockFundamental(stock_id=stock.id, as_of_date=as_of, **payload))
        count += 1
        if count % CHUNK == 0:
            session.flush()
            logger.info("fundamentals flushed at %s", count)
    return count


def import_ownership(
    session: Session,
    rows: Iterable[dict[str, str]],
    cache: dict[str, Stock],
    ok_symbols: set[str] | None,
) -> int:
    count = 0
    for row in rows:
        if (row.get("status") or "").lower() not in {"ok", ""}:
            continue
        symbol = (row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        if ok_symbols is not None and symbol not in ok_symbols:
            continue
        period = (row.get("period") or "latest").strip() or "latest"
        stock = _ensure_stock(session, cache, symbol)
        existing = session.scalar(
            select(StockOwnership).where(
                StockOwnership.stock_id == stock.id,
                StockOwnership.period_label == period,
            )
        )
        payload = {
            "promoter_pct": _f(row.get("promoter_pct")),
            "fii_pct": _f(row.get("fii_pct")),
            "dii_pct": _f(row.get("dii_pct")),
            "public_pct": _f(row.get("public_pct")),
            "promoter_pledge_pct": _f(row.get("promoter_pledge_pct")),
            "source": "screener.in",
            "scraped_at": _parse_ts(row.get("scraped_at")),
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            session.add(StockOwnership(stock_id=stock.id, period_label=period, **payload))
        count += 1
        if count % CHUNK == 0:
            session.flush()
            logger.info("ownership flushed at %s", count)
    return count


def import_long_file(
    session: Session,
    path: Path,
    cache: dict[str, Stock],
    ok_symbols: set[str] | None,
    ok_stock_ids: set[int],
) -> int:
    """Replace screener period rows for ok stocks from one long CSV (chunked)."""
    logger.info("Importing long file %s", path.name)
    # Drop previous screener rows for these stocks in this file's section(s) as we go —
    # full delete of ok stock periods once per import is done by caller.
    batch: list[StockFinancialPeriod] = []
    seen_keys: set[tuple[int, str, str, str]] = set()
    count = 0
    skipped = 0
    for row in _iter_csv(path):
        symbol = (row.get("symbol") or "").strip().upper()
        section = (row.get("section") or "").strip()[:40]
        metric = (row.get("metric") or "").strip()[:120]
        period = (row.get("period") or "").strip()[:40]
        if not symbol or not section or not metric or not period:
            skipped += 1
            continue
        if ok_symbols is not None and symbol not in ok_symbols:
            skipped += 1
            continue
        stock = _ensure_stock(session, cache, symbol)
        ok_stock_ids.add(stock.id)
        key = (stock.id, section, metric, period)
        if key in seen_keys:
            skipped += 1
            continue
        seen_keys.add(key)
        batch.append(
            StockFinancialPeriod(
                stock_id=stock.id,
                section=section,
                metric=metric,
                period_label=period,
                value_num=_f(row.get("value_num") if row.get("value_num") not in (None, "") else row.get("value_raw")),
                value_raw=(row.get("value_raw") or None),
                source="screener.in",
                scraped_at=_parse_ts(row.get("scraped_at")),
            )
        )
        if len(batch) >= CHUNK:
            session.add_all(batch)
            session.flush()
            count += len(batch)
            batch.clear()
            logger.info("  %s: %s rows", path.name, count)
    if batch:
        session.add_all(batch)
        session.flush()
        count += len(batch)
        batch.clear()
    logger.info("Finished %s: inserted=%s skipped=%s", path.name, count, skipped)
    return count


def import_screener_excel(session: Session, directory: Path | None = None) -> dict[str, Any]:
    init_db()
    root = Path(directory) if directory else OUT_DIR
    ok_symbols = load_ok_symbols(root / "scrape_status.csv")
    if not ok_symbols:
        logger.warning("No ok symbols in scrape_status.csv; importing all rows with status=ok/blank")
        ok_filter: set[str] | None = None
    else:
        ok_filter = ok_symbols
        logger.info("Importing for %s ok scrape symbols", len(ok_symbols))

    cache = _stock_map(session)
    fundamentals = import_fundamentals(session, _iter_csv(root / "fundamentals.csv"), cache, ok_filter)
    session.commit()
    logger.info("Committed fundamentals=%s", fundamentals)

    ownership = import_ownership(session, _iter_csv(root / "shareholding_latest.csv"), cache, ok_filter)
    session.commit()
    logger.info("Committed ownership=%s", ownership)

    # Prefetch stock ids for ok symbols, then clear prior period rows for clean re-import
    ok_stock_ids: set[int] = set()
    if ok_filter:
        for sym in ok_filter:
            stock = cache.get(sym) or _ensure_stock(session, cache, sym)
            ok_stock_ids.add(stock.id)
        if ok_stock_ids:
            session.execute(
                delete(StockFinancialPeriod).where(StockFinancialPeriod.stock_id.in_(list(ok_stock_ids)))
            )
            session.commit()
            logger.info("Cleared prior financial_periods for %s stocks", len(ok_stock_ids))

    long_count = 0
    for pattern in LONG_GLOBS:
        for path in sorted(root.glob(pattern)):
            long_count += import_long_file(session, path, cache, ok_filter, ok_stock_ids)
            session.commit()

    return {
        "dir": str(root),
        "ok_symbols": len(ok_symbols),
        "fundamentals": fundamentals,
        "ownership": ownership,
        "financial_periods": long_count,
        "stocks_linked": len(ok_stock_ids) if ok_stock_ids else len(cache),
    }
