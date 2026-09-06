"""Fetch live NSE equity / ETF quotes via unofficial quote-equity API.

Personal / research use. Reuses the same session warm-up as index scraping.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ingestion.nse_indices import nse_session

logger = logging.getLogger(__name__)

QUOTE_URL = "https://www.nseindia.com/api/quote-equity"

_QUOTE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_QUOTE_TTL_S = 25.0


def _f(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def fetch_equity_quote(
    symbol: str,
    *,
    sess: requests.Session | None = None,
    retries: int = 2,
) -> dict[str, Any] | None:
    """Return normalized {ltp, change, change_pct, prev_close, as_of} or None."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return None

    now = time.monotonic()
    cached = _QUOTE_CACHE.get(sym)
    if cached and now - cached[0] < _QUOTE_TTL_S:
        return cached[1]

    session = sess or nse_session()
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            # Warm quote page so cookies allow quote-equity
            session.headers["Referer"] = "https://www.nseindia.com/"
            session.get(
                f"https://www.nseindia.com/get-quotes/equity?symbol={sym}",
                timeout=20,
            )
            session.headers["Referer"] = (
                f"https://www.nseindia.com/get-quotes/equity?symbol={sym}"
            )
            resp = session.get(QUOTE_URL, params={"symbol": sym}, timeout=20)
            if resp.status_code in {401, 403}:
                session = nse_session()
                time.sleep(0.6 * attempt)
                continue
            if resp.status_code != 200:
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                time.sleep(0.4 * attempt)
                continue
            payload = resp.json()
            price_info = payload.get("priceInfo") or {}
            ltp = _f(price_info.get("lastPrice"))
            if ltp is None:
                last_err = RuntimeError("missing lastPrice")
                continue
            change = _f(price_info.get("change"))
            change_pct = _f(price_info.get("pChange"))
            prev = _f(price_info.get("previousClose"))
            if change is None and prev is not None:
                change = ltp - prev
            if change_pct is None and prev:
                change_pct = (change / prev) * 100 if change is not None else None
            out = {
                "symbol": sym,
                "ltp": ltp,
                "change": round(change, 4) if change is not None else None,
                "change_pct": round(change_pct, 4) if change_pct is not None else None,
                "prev_close": prev,
            }
            _QUOTE_CACHE[sym] = (time.monotonic(), out)
            return out
        except (requests.RequestException, ValueError, TypeError) as exc:
            last_err = exc
            logger.warning("NSE quote-equity %s attempt %s: %s", sym, attempt, exc)
            time.sleep(0.5 * attempt)
            session = nse_session()

    logger.warning("NSE quote-equity failed for %s: %s", sym, last_err)
    return None


def fetch_equity_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Batch fetch with one warmed session."""
    sess = nse_session()
    out: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        q = fetch_equity_quote(symbol, sess=sess)
        if q:
            out[symbol.upper()] = q
        time.sleep(0.15)
    return out
