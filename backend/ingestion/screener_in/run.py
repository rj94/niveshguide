from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BACKEND_ROOT
from ingestion.screener_in.client import BlockedError, ScreenerClient
from ingestion.screener_in.excel_writer import IncrementalWriter, load_completed_symbols
from ingestion.screener_in.logging_util import setup_scrape_logger
from ingestion.screener_in.parse import ParsedCompany, parse_company_html
from ingestion.screener_in.symbols import load_eq_symbols, load_overrides

OUT_DIR = BACKEND_ROOT / "data" / "screener_in"


def scrape_screener(
    *,
    limit: int | None = None,
    only: list[str] | None = None,
    resume: bool = True,
    reparse_only: bool = False,
    delay_min: float = 4.0,
    delay_max: float = 8.0,
    max_per_day: int = 400,
    cache_ttl_days: int = 7,
    flush_every: int = 1,
    verbose: bool = False,
    i_know: bool = False,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    if delay_min < 2.0 and not i_know:
        raise ValueError("delay_min < 2 refused (anti-block). Pass i_know=True to override.")

    root = Path(out_dir) if out_dir else OUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    (root / "cache" / "html").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    overrides_path = root / "symbol_overrides.csv"
    if not overrides_path.exists():
        overrides_path.write_text("nse_symbol,screener_slug\n", encoding="utf-8")

    logger = setup_scrape_logger(root / "logs", verbose=verbose)
    overrides = load_overrides(overrides_path)

    symbols = load_eq_symbols()
    if only:
        wanted = {s.strip().upper() for s in only if s.strip()}
        symbols = [row for row in symbols if row["symbol"] in wanted]
        missing = wanted - {row["symbol"] for row in symbols}
        for sym in sorted(missing):
            symbols.append({"symbol": sym, "company_name": "", "isin": "", "segment": "EQ"})
    if resume:
        done = load_completed_symbols(root / "scrape_status.csv")
        before = len(symbols)
        symbols = [row for row in symbols if row["symbol"] not in done]
        logger.info("Resume: skipped %s already-ok symbols", before - len(symbols))
    if limit is not None:
        symbols = symbols[: max(0, limit)]

    writer = IncrementalWriter(root, flush_every=flush_every)
    summary: dict[str, Any] = {
        "total": len(symbols),
        "ok": 0,
        "failed": 0,
        "blocked_stop": False,
        "day_fetches": 0,
        "out_dir": str(root),
    }
    if not symbols:
        logger.info("Nothing to scrape")
        return summary

    client = ScreenerClient(
        root / "cache" / "html",
        delay_min=delay_min,
        delay_max=delay_max,
        cache_ttl_days=cache_ttl_days,
        allow_fast=i_know,
    )

    ok = fail = 0
    consecutive_blocks = 0
    try:
        for index, row in enumerate(symbols, start=1):
            if client.fetches >= max_per_day and not reparse_only:
                logger.warning(
                    "Daily fetch cap reached (%s). Resume tomorrow: python -m cli scrape-screener --resume",
                    max_per_day,
                )
                break

            symbol = row["symbol"]
            slug = overrides.get(symbol)
            started = time.time()
            try:
                html, url, cache_hit, status = client.fetch_company(
                    symbol, slug=slug, reparse_only=reparse_only
                )
                parsed = parse_company_html(symbol, html, source_url=url)
                writer.write_parsed(parsed, http_status=status, cache_hit=cache_hit)
                if parsed.status == "ok":
                    ok += 1
                else:
                    fail += 1
                consecutive_blocks = 0
                logger.info(
                    "[%s/%s] %s %s cache=%s rows=%s %.1fs | ok=%s fail=%s day_left=%s",
                    index,
                    len(symbols),
                    symbol,
                    parsed.status,
                    int(cache_hit),
                    len(parsed.long_rows),
                    time.time() - started,
                    ok,
                    fail,
                    max(0, max_per_day - client.fetches),
                )
            except BlockedError as exc:
                consecutive_blocks += 1
                parsed = ParsedCompany(
                    symbol=symbol,
                    status="blocked",
                    error=str(exc),
                    scraped_at=datetime.now(timezone.utc).isoformat(),
                )
                writer.write_parsed(parsed, http_status=403, error=str(exc))
                fail += 1
                logger.error("[%s/%s] %s BLOCKED: %s", index, len(symbols), symbol, exc)
                if consecutive_blocks >= 3:
                    summary["blocked_stop"] = True
                    logger.error(
                        "Stop-on-block after 3 consecutive failures. "
                        "Wait and resume: python -m cli scrape-screener --resume"
                    )
                    break
                # cool-down
                logger.info("Backing off 15 minutes after block signal")
                time.sleep(15 * 60)
            except Exception as exc:  # noqa: BLE001 — continue batch
                fail += 1
                parsed = ParsedCompany(
                    symbol=symbol,
                    status="error",
                    error=str(exc),
                    scraped_at=datetime.now(timezone.utc).isoformat(),
                )
                writer.write_parsed(parsed, error=str(exc))
                logger.warning("[%s/%s] %s error: %s", index, len(symbols), symbol, exc)
    finally:
        writer.flush_xlsx()
        client.close()

    summary.update({"ok": ok, "failed": fail, "day_fetches": client.fetches})
    logger.info("Done: %s", summary)
    return summary
