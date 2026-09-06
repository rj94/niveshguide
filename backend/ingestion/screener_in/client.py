from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class BlockedError(RuntimeError):
    """Raised when screener signals a block / challenge."""


class ScreenerClient:
    def __init__(
        self,
        cache_dir: Path,
        *,
        delay_min: float = 4.0,
        delay_max: float = 8.0,
        cache_ttl_days: int = 7,
        timeout: float = 30.0,
        allow_fast: bool = False,
    ) -> None:
        if delay_min < 2.0 and not allow_fast:
            raise ValueError("delay_min must be >= 2 unless allow_fast=True")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay_min = delay_min
        self.delay_max = max(delay_max, delay_min)
        self.cache_ttl = timedelta(days=cache_ttl_days)
        self._fetches = 0
        self._consecutive_blocks = 0
        self._client = httpx.Client(
            headers={
                "User-Agent": DEFAULT_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                "Connection": "keep-alive",
            },
            follow_redirects=True,
            timeout=timeout,
        )
        self._warmed = False

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ScreenerClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @property
    def fetches(self) -> int:
        return self._fetches

    @property
    def consecutive_blocks(self) -> int:
        return self._consecutive_blocks

    def warm_up(self) -> None:
        if self._warmed:
            return
        logger.info("Warm-up GET https://www.screener.in/")
        try:
            resp = self._client.get("https://www.screener.in/")
            logger.info("Warm-up status=%s", resp.status_code)
        except httpx.HTTPError as exc:
            logger.warning("Warm-up failed: %s", exc)
        self._warmed = True
        time.sleep(random.uniform(2.0, 5.0))

    def cache_path(self, symbol: str) -> Path:
        safe = symbol.upper().replace("/", "_")
        return self.cache_dir / f"{safe}.html"

    def _cache_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return datetime.now(timezone.utc) - mtime <= self.cache_ttl

    def _sleep_jitter(self) -> None:
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug("Sleep %.1fs before next request", delay)
        time.sleep(delay)

    def burst_pause(self, every: int = 40) -> None:
        if self._fetches > 0 and self._fetches % every == 0:
            pause = random.uniform(60.0, 120.0)
            logger.info("Burst pause after %s fetches: sleeping %.0fs", self._fetches, pause)
            time.sleep(pause)

    def _is_block_response(self, resp: httpx.Response, text: str) -> bool:
        if resp.status_code in {403, 429, 503}:
            return True
        lowered = text[:2000].lower()
        markers = ("captcha", "cf-browser-verification", "access denied", "too many requests")
        return any(marker in lowered for marker in markers)

    def fetch_company(
        self,
        symbol: str,
        *,
        slug: str | None = None,
        reparse_only: bool = False,
    ) -> tuple[str, str, bool, int]:
        """Return (html, final_url, cache_hit, http_status)."""
        path = self.cache_path(symbol)
        if self._cache_fresh(path):
            html = path.read_text(encoding="utf-8", errors="replace")
            url = f"https://www.screener.in/company/{slug or symbol}/consolidated/"
            logger.debug("Cache hit %s", path.name)
            return html, url, True, 200

        if reparse_only:
            if path.exists():
                html = path.read_text(encoding="utf-8", errors="replace")
                return html, f"cache://{path.name}", True, 200
            raise FileNotFoundError(f"No cache for {symbol} and --reparse-only set")

        self.warm_up()
        self.burst_pause()
        self._sleep_jitter()

        slug = (slug or symbol).strip()
        urls = [
            f"https://www.screener.in/company/{slug}/consolidated/",
            f"https://www.screener.in/company/{slug}/",
        ]
        last_status = 0
        last_error = ""
        for url in urls:
            try:
                resp = self._client.get(url, headers={"Referer": "https://www.screener.in/"})
                last_status = resp.status_code
                text = resp.text
                self._fetches += 1
                if self._is_block_response(resp, text):
                    self._consecutive_blocks += 1
                    logger.error("Block signal status=%s url=%s", resp.status_code, url)
                    raise BlockedError(f"Blocked or challenged: HTTP {resp.status_code} for {url}")
                if resp.status_code == 404:
                    last_error = "404"
                    continue
                if resp.status_code >= 400:
                    last_error = f"HTTP {resp.status_code}"
                    continue
                self._consecutive_blocks = 0
                path.write_text(text, encoding="utf-8")
                return text, str(resp.url), False, resp.status_code
            except BlockedError:
                raise
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.warning("Request failed %s: %s", url, exc)
                continue

        self._consecutive_blocks = 0
        raise LookupError(f"Company page not found for {symbol}: {last_error or last_status}")
