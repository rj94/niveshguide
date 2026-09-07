"""Shared Redis JSON cache. No-ops when REDIS_URL is unset."""

from __future__ import annotations

import json
import logging
from typing import Any

from config.settings import get_settings

logger = logging.getLogger(__name__)

_client = None
_client_failed = False

PREFIX_STRATEGY = "strategy:"
PREFIX_SCREENER = "screener:"
PREFIX_INDUSTRY = "industry_strength:"
PREFIX_MARKETS = "markets:"


def _get_client():
    global _client, _client_failed
    if _client_failed:
        return None
    if _client is not None:
        return _client
    url = get_settings().redis_url
    if not url:
        _client_failed = True
        return None
    try:
        import redis

        _client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        _client.ping()
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable; caching disabled: %s", type(exc).__name__)
        _client_failed = True
        _client = None
        return None


def get_json(key: str) -> Any | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("redis get_json failed: %s", type(exc).__name__)
        return None


def set_json(key: str, value: Any, ttl: int) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, int(ttl), json.dumps(value, default=str))
    except Exception as exc:  # noqa: BLE001
        logger.debug("redis set_json failed: %s", type(exc).__name__)


def delete_prefix(prefix: str, *, count: int = 200) -> int:
    """Best-effort delete of keys matching prefix* via SCAN."""
    client = _get_client()
    if client is None:
        return 0
    deleted = 0
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=f"{prefix}*", count=count)
            if keys:
                deleted += int(client.delete(*keys))
            if cursor == 0:
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("redis delete_prefix failed: %s", type(exc).__name__)
    return deleted


def invalidate_market_caches() -> None:
    delete_prefix(PREFIX_STRATEGY)
    delete_prefix(PREFIX_SCREENER)
    delete_prefix(PREFIX_INDUSTRY)
    delete_prefix(PREFIX_MARKETS)
