"""Markets overview: live NSE index levels + equity ETF proxies for sector tiles."""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    MarketIndex,
    MarketIndexPrice,
    MarketIndexSnapshot,
    StockPrice,
    StockSnapshot,
)
from database.repository import get_stock_by_symbol
from ingestion.nse_indices import FEATURED_INDICES
from market_platform.schemas.markets import (
    MarketEtfsResponse,
    MarketIndicesResponse,
    MarketQuoteCard,
    MarketsOverviewResponse,
)

# Fallback when NSE index snapshots are not yet scraped.
INDEX_ETFS = (
    ("NIFTYBEES", "Nifty 50", "index"),
    ("BANKBEES", "Bank Nifty", "index"),
    ("JUNIORBEES", "Nifty Next 50", "index"),
    ("MONIFTY500", "Nifty 500", "index"),
    ("NIF100BEES", "Nifty 100", "index"),
)

SECTOR_ETFS = (
    ("ITBEES", "IT", "sector", "Information Technology"),
    ("PHARMABEES", "Pharma", "sector", "Healthcare"),
    ("PSUBNKBEES", "PSU Bank", "sector", "Financials"),
    ("AUTOBEES", "Auto", "sector", "Consumer"),
    ("INFRABEES", "Infra", "sector", "Industrials"),
    ("CONSUMBEES", "Consumption", "sector", "Consumer"),
    # Commodities: India ETFs where possible; Yahoo futures proxies otherwise.
    ("GOLDBEES", "Gold ETF", "commodity", None),
    ("SILVERBEES", "Silver ETF", "commodity", None),
    ("CL=F", "Crude Oil (WTI)", "commodity", None),
    ("BZ=F", "Brent Crude", "commodity", None),
    ("NG=F", "Natural Gas", "commodity", None),
    ("HG=F", "Copper", "commodity", None),
)

KEY_ETFS = (*INDEX_ETFS, *SECTOR_ETFS)

# In-process TTL so overview spam does not re-query heavily; scrape is source of truth.
_LIST_CACHE: tuple[float, list[MarketQuoteCard]] | None = None
_LIST_TTL_S = 60.0
_OVERVIEW_CACHE: tuple[float, MarketsOverviewResponse] | None = None
_OVERVIEW_TTL_S = 25.0


def _f(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dec(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, 4)))


def _latest_snapshot(session: Session, stock_id: int) -> StockSnapshot | None:
    return session.scalar(
        select(StockSnapshot)
        .where(StockSnapshot.stock_id == stock_id)
        .order_by(StockSnapshot.snapshot_date.desc())
        .limit(1)
    )


def _etf_sparkline(session: Session, stock_id: int, limit: int = 20) -> list[float]:
    rows = session.scalars(
        select(StockPrice.close)
        .where(StockPrice.stock_id == stock_id, StockPrice.close.is_not(None))
        .order_by(StockPrice.price_date.desc())
        .limit(limit)
    ).all()
    points = [float(v) for v in reversed(rows) if v is not None]
    # Hide fake 2-point slopes; need a real mini-series.
    return points if len(points) >= 5 else []


def _index_sparkline(session: Session, index_id: int, limit: int = 20) -> list[float]:
    rows = session.scalars(
        select(MarketIndexPrice.close)
        .where(MarketIndexPrice.index_id == index_id, MarketIndexPrice.close.is_not(None))
        .order_by(MarketIndexPrice.price_date.desc())
        .limit(limit)
    ).all()
    points = [float(v) for v in reversed(rows) if v is not None]
    return points if len(points) >= 5 else []


def _card_from_etf(
    session: Session,
    symbol: str,
    name: str,
    kind: str,
    *,
    sector_name: str | None = None,
) -> MarketQuoteCard | None:
    stock = get_stock_by_symbol(session, symbol)
    if stock is None:
        return None
    snap = _latest_snapshot(session, stock.id)
    if snap is None or snap.ltp is None:
        return None
    ltp = _f(snap.ltp)
    prev = _f(snap.prev_close)
    if ltp is None:
        return None
    change = None
    change_pct = None
    if prev is not None and prev != 0:
        change = ltp - prev
        change_pct = round((change / prev) * 100, 4)
    return MarketQuoteCard(
        id=f"etf-{symbol}",
        symbol=symbol,
        name=name,
        kind=kind,
        exchange=stock.exchange or "NSE",
        value=Decimal(str(ltp)),
        change=Decimal(str(round(change, 4))) if change is not None else None,
        change_pct=change_pct,
        sparkline=_etf_sparkline(session, stock.id),
        as_of=snap.snapshot_date,
        sector_name=sector_name,
    )


def _key_etf_cards(session: Session) -> tuple[list[MarketQuoteCard], list[MarketQuoteCard]]:
    sector_etfs: list[MarketQuoteCard] = []
    commodities: list[MarketQuoteCard] = []
    for symbol, name, kind, sector_name in SECTOR_ETFS:
        card = _card_from_etf(session, symbol, name, kind, sector_name=sector_name)
        if not card:
            continue
        if kind == "commodity":
            commodities.append(card)
        else:
            sector_etfs.append(card)
    return sector_etfs, commodities


def _latest_index_snapshot(session: Session, index_id: int) -> MarketIndexSnapshot | None:
    return session.scalar(
        select(MarketIndexSnapshot)
        .where(MarketIndexSnapshot.index_id == index_id)
        .order_by(MarketIndexSnapshot.as_of.desc())
        .limit(1)
    )


def _card_from_index(
    session: Session,
    idx: MarketIndex,
    *,
    display_name: str | None = None,
) -> MarketQuoteCard | None:
    snap = _latest_index_snapshot(session, idx.id)
    if snap is None or snap.last is None:
        return None
    last = _f(snap.last)
    if last is None:
        return None
    change = _f(snap.change)
    change_pct = _f(snap.change_pct)
    if change is None:
        prev = _f(snap.prev_close)
        if prev is not None:
            change = last - prev
            if prev:
                change_pct = round((change / prev) * 100, 4)
    slug = idx.key.replace(" ", "_")
    return MarketQuoteCard(
        id=f"idx-{slug}",
        symbol=idx.key,
        name=display_name or idx.name,
        kind="index",
        exchange="NSE",
        value=_dec(last),
        change=_dec(change),
        change_pct=round(change_pct, 4) if change_pct is not None else None,
        sparkline=_index_sparkline(session, idx.id),
        as_of=snap.as_of,
    )


def _featured_index_cards(session: Session) -> list[MarketQuoteCard]:
    cards: list[MarketQuoteCard] = []
    etf_map = {name: sym for sym, name, _ in INDEX_ETFS}
    for key, display_name in FEATURED_INDICES:
        idx = session.scalar(select(MarketIndex).where(MarketIndex.key == key))
        card = _card_from_index(session, idx, display_name=display_name) if idx else None
        etf_sym = etf_map.get(display_name)
        if card is None and etf_sym:
            card = _card_from_etf(session, etf_sym, display_name, "index")
        elif card is not None and len(card.sparkline) < 5 and etf_sym:
            # Prefer ETF history for sparkline only (avoid mixing ETF closes into index prices).
            etf_card = _card_from_etf(session, etf_sym, display_name, "index")
            if etf_card and len(etf_card.sparkline) >= 5:
                card = card.model_copy(update={"sparkline": etf_card.sparkline})
        if card:
            cards.append(card)
    return cards


def _card_from_live_quote(
    *,
    symbol: str,
    name: str,
    kind: str,
    quote: dict,
    sparkline: list[float],
    sector_name: str | None = None,
) -> MarketQuoteCard:
    from datetime import date as date_cls

    ltp = quote.get("ltp")
    change = quote.get("change")
    change_pct = quote.get("change_pct")
    return MarketQuoteCard(
        id=f"etf-{symbol}",
        symbol=symbol,
        name=name,
        kind=kind,
        exchange="NSE",
        value=Decimal(str(ltp)) if ltp is not None else Decimal("0"),
        change=Decimal(str(round(change, 4))) if change is not None else None,
        change_pct=round(change_pct, 4) if change_pct is not None else None,
        sparkline=sparkline,
        as_of=date_cls.today(),
        sector_name=sector_name,
    )


def markets_overview(session: Session, *, use_cache: bool = True) -> MarketsOverviewResponse:
    global _OVERVIEW_CACHE
    now = time.monotonic()
    if use_cache and _OVERVIEW_CACHE is not None:
        cached_at, cached = _OVERVIEW_CACHE
        if now - cached_at < _OVERVIEW_TTL_S:
            return cached

    from cache.redis_cache import PREFIX_MARKETS, get_json, set_json

    redis_key = f"{PREFIX_MARKETS}overview"
    if use_cache:
        cached_payload = get_json(redis_key)
        if cached_payload is not None:
            try:
                result = MarketsOverviewResponse.model_validate(cached_payload)
                _OVERVIEW_CACHE = (now, result)
                return result
            except Exception:  # noqa: BLE001
                pass

    indices = _featured_index_cards(session)

    # Serve from DB snapshots only on the request path (NSE live quotes are too slow/cold).
    # Scheduler / scrape keeps snapshots fresh.
    sector_etfs, commodities = _key_etf_cards(session)

    as_of = None
    for card in (*indices, *sector_etfs, *commodities):
        if card.as_of:
            as_of = card.as_of
            break
    result = MarketsOverviewResponse(
        indices=indices,
        sector_etfs=sector_etfs,
        commodities=commodities,
        sectors=[],
        as_of=as_of or date.today(),
    )
    _OVERVIEW_CACHE = (now, result)
    if use_cache:
        set_json(redis_key, result.model_dump(mode="json"), 30)
    return result


def list_market_etfs(session: Session, *, use_cache: bool = True) -> MarketEtfsResponse:
    from cache.redis_cache import PREFIX_MARKETS, get_json, set_json

    redis_key = f"{PREFIX_MARKETS}etfs"
    if use_cache:
        cached_payload = get_json(redis_key)
        if cached_payload is not None:
            try:
                return MarketEtfsResponse.model_validate(cached_payload)
            except Exception:  # noqa: BLE001
                pass

    cards: list[MarketQuoteCard] = []
    for symbol, name, kind, *rest in KEY_ETFS:
        sector_name = rest[0] if rest else None
        card = _card_from_etf(session, symbol, name, kind, sector_name=sector_name)
        if card:
            cards.append(card)

    as_of = next((card.as_of for card in cards if card.as_of), date.today())
    result = MarketEtfsResponse(items=cards, total=len(cards), as_of=as_of)
    if use_cache:
        set_json(redis_key, result.model_dump(mode="json"), 60)
    return result


def list_market_indices(session: Session, *, use_cache: bool = True) -> MarketIndicesResponse:
    global _LIST_CACHE
    now = time.monotonic()
    if use_cache and _LIST_CACHE is not None:
        cached_at, cached_items = _LIST_CACHE
        if now - cached_at < _LIST_TTL_S:
            return MarketIndicesResponse(items=cached_items, as_of=cached_items[0].as_of if cached_items else date.today())

    from cache.redis_cache import PREFIX_MARKETS, get_json, set_json

    redis_key = f"{PREFIX_MARKETS}indices"
    if use_cache:
        cached_payload = get_json(redis_key)
        if cached_payload is not None:
            try:
                result = MarketIndicesResponse.model_validate(cached_payload)
                _LIST_CACHE = (now, result.items)
                return result
            except Exception:  # noqa: BLE001
                pass

    rows = session.scalars(
        select(MarketIndex).where(MarketIndex.is_active.is_(True)).order_by(MarketIndex.key)
    ).all()
    items: list[MarketQuoteCard] = []
    for idx in rows:
        card = _card_from_index(session, idx)
        if card:
            items.append(card)

    _LIST_CACHE = (now, items)
    as_of = items[0].as_of if items else date.today()
    result = MarketIndicesResponse(items=items, as_of=as_of)
    if use_cache:
        set_json(redis_key, result.model_dump(mode="json"), 60)
    return result
