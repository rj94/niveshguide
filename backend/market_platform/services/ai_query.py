"""Natural-language stock queries → constrained plan → SQLAlchemy rows → grounded answer.

The LLM (or heuristic fallback) may only emit a JSON plan. SQL is built exclusively
by this module using allowlisted fields and operators.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from cache.redis_cache import PREFIX_AI, get_json, set_json
from config.settings import Settings, get_settings
from database.repository import latest_screener_query
from market_platform.schemas.ai import (
    AiQueryFilter,
    AiQueryRequest,
    AiQueryResponse,
    AiQueryRow,
    SafeAiQueryPlan,
)
from market_platform.services.stocks import (
    _analysis_row,
    _f,
    _fundamentals_by_stock_id,
    _latest_close_pair_by_stock_id,
    _latest_volume_by_stock_id,
)

logger = logging.getLogger(__name__)

ALLOWED_FIELDS = frozenset(
    {
        "symbol",
        "company_name",
        "sector",
        "industry",
        "ltp",
        "market_cap",
        "pe",
        "trend_score",
        "trend",
        "momentum_score",
        "momentum_acceleration",
        "return_1m",
        "return_3m",
        "return_6m",
        "volume_ratio",
        "distance_from_52w_high",
        "above_ma_21",
        "above_ma_200",
        "golden_cross",
        "crossover_3_7",
    }
)
ALLOWED_OPERATORS = frozenset({"=", "!=", ">", ">=", "<", "<=", "contains", "in"})
ALLOWED_INTENTS = frozenset({"screen", "compare", "explain_stock", "rank", "unknown"})
ABSOLUTE_MAX_ROWS = 100
DEFAULT_SORT = "momentum_score"
DEFAULT_LIMIT = 25
DISCLAIMER = "This is informational market data, not financial advice."
BANNED_PHRASES = ("you should buy", "guaranteed", "risk-free")
SQLISH_RE = re.compile(
    r"\b(select|drop|insert|update|delete|union|alter|truncate|exec|execute)\b",
    re.IGNORECASE,
)
SYMBOL_RE = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9&-]{1,14}\b")
STOPWORDS = frozenset(
    {
        "AND",
        "THE",
        "FOR",
        "WITH",
        "FROM",
        "SHOW",
        "FIND",
        "NEAR",
        "HIGH",
        "HIGHS",
        "DMA",
        "NSE",
        "BSE",
        "STOCK",
        "STOCKS",
        "COMPARE",
        "WHICH",
        "HAVE",
        "HAS",
        "STRONG",
        "WEAK",
        "VOLUME",
        "MOMENTUM",
        "TREND",
        "SCORE",
        "RETURN",
        "RETURNS",
        "ABOVE",
        "BELOW",
        "CLOSE",
        "WEEK",
        "MONTH",
        "YEAR",
        "PHARMA",
        "BANKING",
        "BANKS",
        "BANK",
        "SECTOR",
        "INDUSTRY",
        "TABLE",
        "DROP",
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "WHERE",
        "INTO",
        "VALUES",
        "UNION",
        "ALTER",
        "EXPLAIN",
        "RANK",
        "TOP",
        "BEST",
        "THAT",
        "THIS",
        "ARE",
        "WAS",
        "WERE",
        "ABOUT",
        "TELL",
        "GIVE",
        "LIST",
        "QUERY",
        "DATA",
        "PRICE",
        "VALUATION",
    }
)
SECTOR_ALIASES = {
    "pharma": "Pharmaceuticals",
    "pharmaceutical": "Pharmaceuticals",
    "pharmaceuticals": "Pharmaceuticals",
    "bank": "Banks",
    "banks": "Banks",
    "banking": "Banks",
    "it": "Information Technology",
    "software": "Information Technology",
    "tech": "Information Technology",
    "fmcg": "FMCG",
    "auto": "Automobile",
    "automobile": "Automobile",
    "metal": "Metals",
    "metals": "Metals",
    "energy": "Energy",
    "realty": "Realty",
    "oil": "Oil & Gas",
}
SYSTEM_PROMPT = """You translate user questions about NSE stocks into a constrained JSON query plan.
Return only valid JSON. Do not return SQL.
Use only the allowed fields and operators.
If the request asks for investment advice, produce a data lookup plan only.
Do not invent unavailable metrics.

Allowed intents: screen, compare, explain_stock, rank, unknown
Allowed fields: symbol, company_name, sector, industry, ltp, market_cap, pe, trend_score, trend, momentum_score, momentum_acceleration, return_1m, return_3m, return_6m, volume_ratio, distance_from_52w_high, above_ma_21, above_ma_200, golden_cross, crossover_3_7
Allowed operators: =, !=, >, >=, <, <=, contains, in

Numeric conventions:
- momentum_score and trend_score are the stored scores (momentum 0-100, trend 0-5).
- return_1m, return_3m, return_6m are percent values (20 means 20%).
- volume_ratio of 1.5 means 1.5x average volume.
- distance_from_52w_high is a fraction below the high (e.g. -0.05 means 5% below). Near highs: >= -0.10.
- Boolean DMA fields: above_ma_21, above_ma_200, golden_cross (50 DMA above 200 DMA), crossover_3_7.

JSON shape:
{"intent":"screen","symbols":[],"sector":null,"industry":null,"filters":[{"field":"momentum_score","op":">=","value":70}],"sort_by":"momentum_score","sort_dir":"desc","limit":25}

Example: "Find strong momentum stocks in pharma with volume expansion"
{"intent":"screen","symbols":[],"sector":"Pharmaceuticals","industry":null,"filters":[{"field":"momentum_score","op":">=","value":70},{"field":"volume_ratio","op":">=","value":1.5}],"sort_by":"momentum_score","sort_dir":"desc","limit":25}
"""


def _num(value: Any) -> float | None:
    return _f(value)


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    return None


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def _has_sqlish(query: str) -> bool:
    return bool(SQLISH_RE.search(query))


def _extract_symbols(text: str) -> list[str]:
    found: list[str] = []
    for token in SYMBOL_RE.findall(text):
        upper = token.upper()
        if upper in STOPWORDS or upper.lower() in SECTOR_ALIASES:
            continue
        if upper not in found:
            found.append(upper)
    return found


def _sector_from_query(text: str) -> str | None:
    lowered = text.lower()
    for alias, sector in SECTOR_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return sector
    return None


def _coerce_filter_value(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field in {"above_ma_21", "above_ma_200", "golden_cross", "crossover_3_7"}:
        coerced = _as_bool(value)
        return True if coerced is None else coerced
    if field in {"symbol", "company_name", "sector", "industry", "trend"}:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return str(value).strip()
    if field == "trend_score":
        number = _num(value)
        return int(number) if number is not None else value
    number = _num(value)
    return number if number is not None else value


def _normalize_op(raw: Any) -> str | None:
    op = str(raw or "").strip().lower()
    aliases = {
        "eq": "=",
        "==": "=",
        "equals": "=",
        "ne": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "like": "contains",
        "ilike": "contains",
        "in": "in",
    }
    op = aliases.get(op, str(raw or "").strip())
    return op if op in ALLOWED_OPERATORS else None


def validate_plan(raw: Any, *, requested_limit: int, max_rows: int) -> tuple[SafeAiQueryPlan, list[str]]:
    warnings: list[str] = []
    data = raw if isinstance(raw, dict) else {}
    if not isinstance(raw, dict):
        warnings.append("Ignored an invalid query plan and used safe defaults.")

    intent = str(data.get("intent") or "screen").strip().lower()
    if intent not in ALLOWED_INTENTS:
        warnings.append(f"Ignored unsupported intent {intent!r}.")
        intent = "unknown"

    symbols: list[str] = []
    for item in data.get("symbols") or []:
        token = str(item).strip().upper()
        if not token or token in STOPWORDS:
            continue
        if not re.fullmatch(r"[A-Z0-9&-]{1,15}", token):
            warnings.append(f"Ignored invalid symbol {token!r}.")
            continue
        if token not in symbols:
            symbols.append(token)

    sector = str(data["sector"]).strip() if data.get("sector") else None
    industry = str(data["industry"]).strip() if data.get("industry") else None

    filters: list[AiQueryFilter] = []
    for item in data.get("filters") or []:
        if not isinstance(item, dict):
            warnings.append("Ignored a malformed filter.")
            continue
        field = str(item.get("field") or "").strip()
        if field not in ALLOWED_FIELDS:
            warnings.append(f"Ignored unsupported metric {field or 'unknown'!r}.")
            continue
        op = _normalize_op(item.get("op") or item.get("operator"))
        if op is None:
            warnings.append(f"Ignored unsupported operator on {field}.")
            continue
        filters.append(
            AiQueryFilter(field=field, operator=op, value=_coerce_filter_value(field, item.get("value")))
        )

    sort_by = str(data.get("sort_by") or DEFAULT_SORT).strip()
    if sort_by not in ALLOWED_FIELDS:
        warnings.append(f"Ignored unsupported sort field {sort_by!r}.")
        sort_by = DEFAULT_SORT
    sort_dir = str(data.get("sort_dir") or "desc").strip().lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "desc"

    try:
        plan_limit = int(data.get("limit") or requested_limit or DEFAULT_LIMIT)
    except (TypeError, ValueError):
        plan_limit = requested_limit or DEFAULT_LIMIT
    cap = min(ABSOLUTE_MAX_ROWS, max(1, max_rows))
    limit = max(1, min(plan_limit, requested_limit, cap))
    if plan_limit > cap:
        warnings.append(f"Result limit was capped at {cap}.")

    return (
        SafeAiQueryPlan(
            intent=intent,  # type: ignore[arg-type]
            symbols=symbols,
            sector=sector,
            industry=industry,
            filters=filters,
            sort_by=sort_by,
            sort_dir=sort_dir,  # type: ignore[arg-type]
            limit=limit,
        ),
        warnings,
    )


def heuristic_plan(query: str) -> dict[str, Any]:
    text = query.strip()
    lowered = text.lower()
    symbols = _extract_symbols(text)
    sector = _sector_from_query(text)
    filters: list[dict[str, Any]] = []
    intent = "screen"
    sort_by = DEFAULT_SORT
    sort_dir = "desc"

    if "compare" in lowered and symbols:
        intent = "compare"
    elif re.search(r"\b(explain|tell me about|what about)\b", lowered) and symbols:
        intent = "explain_stock"
        symbols = symbols[:1]
    elif re.search(r"\b(rank|top|best|highest)\b", lowered):
        intent = "rank"

    mom_above = re.search(r"momentum(?:\s+score)?\s*(?:above|over|>|>=)\s*(\d+(?:\.\d+)?)", lowered)
    if mom_above:
        filters.append({"field": "momentum_score", "op": ">=", "value": float(mom_above.group(1))})
    elif re.search(r"strong\s+momentum|high\s+momentum|momentum", lowered):
        filters.append({"field": "momentum_score", "op": ">=", "value": 70})
    if re.search(r"volume\s+(expansion|mover|spike|surge)|unusual\s+volume", lowered):
        filters.append({"field": "volume_ratio", "op": ">=", "value": 1.5})
    if re.search(r"52[\s-]*week\s+high", lowered):
        filters.append({"field": "distance_from_52w_high", "op": ">=", "value": -0.10})
    trend_match = re.search(r"trend\s*score\s*(?:of|is|=)?\s*([0-5])", lowered)
    if trend_match:
        filters.append({"field": "trend_score", "op": "=", "value": int(trend_match.group(1))})
    if re.search(r"50\s*dma.{0,40}200\s*dma|200\s*dma.{0,40}50\s*dma|golden\s+cross", lowered):
        filters.append({"field": "golden_cross", "op": "=", "value": True})
        filters.append({"field": "above_ma_200", "op": "=", "value": True})
    elif re.search(r"above\s+200\s*dma|above\s+the\s+200", lowered):
        filters.append({"field": "above_ma_200", "op": "=", "value": True})
    if re.search(r"above\s+50\s*dma|above\s+the\s+50", lowered) and not any(
        item["field"] == "golden_cross" for item in filters
    ):
        filters.append({"field": "golden_cross", "op": "=", "value": True})
    if re.search(r"\b21\s*dma\b|\b50\s*day\b", lowered):
        filters.append({"field": "above_ma_21", "op": "=", "value": True})

    for period, field in (("1", "return_1m"), ("3", "return_3m"), ("6", "return_6m")):
        match = re.search(
            rf"{period}\s*(?:m|month|months)\s*(?:return)?\s*(?:above|over|>|>=)\s*(\d+(?:\.\d+)?)\s*%?",
            lowered,
        )
        if match:
            filters.append({"field": field, "op": ">=", "value": float(match.group(1))})

    if intent == "screen" and not filters and not sector and not symbols:
        if not re.search(r"\b(stock|stocks|nse|momentum|screen|find|show|list)\b", lowered):
            intent = "unknown"

    return {
        "intent": intent,
        "symbols": symbols if intent in {"compare", "explain_stock"} else [],
        "sector": sector,
        "industry": None,
        "filters": filters,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "limit": DEFAULT_LIMIT,
    }


def _llm_plan(query: str, settings: Settings) -> dict[str, Any]:
    payload = {
        "model": settings.ai_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
    }
    with httpx.Client(timeout=settings.ai_timeout_seconds) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("AI provider did not return a JSON object")
    return parsed


def build_safe_plan(
    query: str,
    *,
    requested_limit: int,
    max_rows: int,
    settings: Settings | None = None,
) -> tuple[SafeAiQueryPlan, list[str], float]:
    warnings: list[str] = []
    if _has_sqlish(query):
        warnings.append("Ignored SQL-like text in the query. Only allowlisted market filters are used.")
    settings = settings or get_settings()
    raw: dict[str, Any]
    latency_ms = 0.0
    started = datetime.now()
    if settings.ai_api_key:
        try:
            raw = _llm_plan(query, settings)
            latency_ms = (datetime.now() - started).total_seconds() * 1000
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI provider plan failed: %s", type(exc).__name__)
            warnings.append("AI provider was unavailable, so a built-in interpretation was used.")
            raw = heuristic_plan(query)
            latency_ms = (datetime.now() - started).total_seconds() * 1000
    else:
        raw = heuristic_plan(query)
        warnings.append("Using built-in query interpretation because no AI provider key is configured.")
    plan, plan_warnings = validate_plan(raw, requested_limit=requested_limit, max_rows=max_rows)
    warnings.extend(plan_warnings)
    return plan, warnings, latency_ms


def _row_values(row) -> dict[str, Any]:
    return {
        "symbol": row.symbol,
        "company_name": row.company_name,
        "sector": row.sector,
        "industry": row.industry,
        "ltp": _num(row.ltp),
        "market_cap": _num(row.market_cap),
        "pe": _num(row.pe),
        "trend_score": row.trend_score,
        "trend": row.trend,
        "momentum_score": _num(row.momentum_score),
        "momentum_acceleration": _num(row.momentum_acceleration),
        "return_1m": _num(row.return_1m_pct),
        "return_3m": _num(row.return_3m_pct),
        "return_6m": _num(row.return_6m_pct),
        "volume_ratio": _num(row.volume_ratio),
        "distance_from_52w_high": _num(row.distance_from_52w_high),
        "above_ma_21": row.above_ma_21,
        "above_ma_200": row.above_ma_200,
        "golden_cross": row.sma_50_above_200,
        "crossover_3_7": row.crossover_3_7,
    }


def _to_ai_row(values: dict[str, Any]) -> AiQueryRow:
    return AiQueryRow(
        symbol=values["symbol"],
        company_name=values.get("company_name"),
        sector=values.get("sector"),
        industry=values.get("industry"),
        ltp=values.get("ltp"),
        market_cap=values.get("market_cap"),
        pe=values.get("pe"),
        trend_score=values.get("trend_score"),
        trend=values.get("trend"),
        momentum_score=values.get("momentum_score"),
        momentum_acceleration=values.get("momentum_acceleration"),
        return_1m=values.get("return_1m"),
        return_3m=values.get("return_3m"),
        return_6m=values.get("return_6m"),
        volume_ratio=values.get("volume_ratio"),
        distance_from_52w_high=values.get("distance_from_52w_high"),
    )


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if actual is None:
        return False
    if operator == "contains":
        return str(expected).lower() in str(actual).lower()
    if operator == "in":
        options = expected if isinstance(expected, (list, tuple, set)) else [expected]
        haystack = {str(item).strip().upper() for item in options}
        return str(actual).strip().upper() in haystack
    if isinstance(actual, bool) or isinstance(expected, bool):
        left = _as_bool(actual)
        right = _as_bool(expected)
        if left is None or right is None:
            return False
        if operator == "=":
            return left is right
        if operator == "!=":
            return left is not right
        return False
    if isinstance(actual, str) or (isinstance(expected, str) and not isinstance(expected, (int, float))):
        left_s = str(actual).strip().lower()
        right_s = str(expected).strip().lower()
        if operator == "=":
            return left_s == right_s
        if operator == "!=":
            return left_s != right_s
        return False
    try:
        left_n = float(actual)
        right_n = float(expected)
    except (TypeError, ValueError):
        return False
    if operator == "=":
        return left_n == right_n
    if operator == "!=":
        return left_n != right_n
    if operator == ">":
        return left_n > right_n
    if operator == ">=":
        return left_n >= right_n
    if operator == "<":
        return left_n < right_n
    if operator == "<=":
        return left_n <= right_n
    return False


def _matches_plan(values: dict[str, Any], plan: SafeAiQueryPlan) -> bool:
    if plan.symbols and values["symbol"].upper() not in {item.upper() for item in plan.symbols}:
        return False
    if plan.sector:
        sector = values.get("sector") or ""
        if plan.sector.lower() not in sector.lower() and sector.lower() not in plan.sector.lower():
            return False
    if plan.industry:
        industry = values.get("industry") or ""
        if plan.industry.lower() not in industry.lower() and industry.lower() not in plan.industry.lower():
            return False
    for item in plan.filters:
        if not _compare(values.get(item.field), item.operator, item.value):
            return False
    return True


def _sort_values(items: list[dict[str, Any]], sort_by: str, sort_dir: str) -> list[dict[str, Any]]:
    reverse = sort_dir != "asc"

    def key(row: dict[str, Any]) -> tuple[bool, Any]:
        value = row.get(sort_by)
        missing = value is None
        if isinstance(value, str):
            return missing, value.lower()
        try:
            return missing, float(value)
        except (TypeError, ValueError):
            return missing, 0.0

    ordered = sorted(items, key=key, reverse=reverse)
    if sort_by in {"symbol", "company_name", "sector", "industry"} or not reverse:
        return ordered
    present = [row for row in ordered if row.get(sort_by) is not None]
    missing = [row for row in ordered if row.get(sort_by) is None]
    return present + missing


def query_stocks_for_ai(
    db: Session,
    plan: SafeAiQueryPlan,
    exchange: str = "NSE",
    limit: int = 25,
) -> tuple[list[AiQueryRow], int, str | None]:
    stmt = latest_screener_query(db)
    if exchange:
        from database.models import Stock

        stmt = stmt.where(Stock.exchange == exchange.upper())
    if plan.symbols:
        from database.models import Stock

        stmt = stmt.where(Stock.symbol.in_([item.upper() for item in plan.symbols]))

    rows = db.execute(stmt).all()
    missing_ltp_ids = [
        int(stock.id) for stock, _indicator, snapshot in rows if snapshot is None or snapshot.ltp is None
    ]
    missing_vol_ids = [
        int(stock.id) for stock, _indicator, snapshot in rows if snapshot is None or snapshot.volume is None
    ]
    close_fallback = _latest_close_pair_by_stock_id(db, missing_ltp_ids)
    volume_fallback = _latest_volume_by_stock_id(db, missing_vol_ids)
    fund_by_id = _fundamentals_by_stock_id(db, [int(stock.id) for stock, _, _ in rows])

    matched: list[dict[str, Any]] = []
    as_of: str | None = None
    for stock, indicator, snapshot in rows:
        row = _analysis_row(
            stock,
            indicator,
            snapshot,
            price_fallback=close_fallback.get(stock.id),
            fund_fallback=fund_by_id.get(stock.id),
            volume_fallback=volume_fallback.get(stock.id),
        )
        values = _row_values(row)
        if not _matches_plan(values, plan):
            continue
        matched.append(values)
        if as_of is None and row.as_of is not None:
            as_of = row.as_of.isoformat()

    matched = _sort_values(matched, plan.sort_by, plan.sort_dir)
    total = len(matched)
    capped = matched[: max(1, min(limit, ABSOLUTE_MAX_ROWS))]
    return [_to_ai_row(item) for item in capped], total, as_of


def _plan_is_too_broad(plan: SafeAiQueryPlan) -> bool:
    if plan.intent in {"compare", "explain_stock", "rank"}:
        return plan.intent != "rank" and not plan.symbols
    if plan.intent == "unknown":
        return True
    return not plan.filters and not plan.sector and not plan.industry and not plan.symbols


def _filter_summary(plan: SafeAiQueryPlan) -> list[AiQueryFilter]:
    filters = list(plan.filters)
    if plan.sector:
        filters.insert(0, AiQueryFilter(field="sector", operator="contains", value=plan.sector))
    if plan.industry:
        filters.insert(0, AiQueryFilter(field="industry", operator="contains", value=plan.industry))
    if plan.symbols:
        filters.insert(0, AiQueryFilter(field="symbol", operator="in", value=plan.symbols))
    return filters


def _interpreted_query(plan: SafeAiQueryPlan, exchange: str) -> str:
    parts = [f"{plan.intent.replace('_', ' ')} on {exchange}"]
    if plan.symbols:
        parts.append("symbols " + ", ".join(plan.symbols))
    if plan.sector:
        parts.append(f"sector contains {plan.sector}")
    if plan.industry:
        parts.append(f"industry contains {plan.industry}")
    for item in plan.filters:
        parts.append(f"{item.field} {item.operator} {item.value}")
    parts.append(f"sorted by {plan.sort_by} {plan.sort_dir}")
    return "; ".join(parts)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def _fmt_num(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _sanitize_answer(text: str) -> str:
    lowered = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            text = re.sub(re.escape(phrase), "matches the filters", text, flags=re.IGNORECASE)
    return text


def generate_answer(
    *,
    query: str,
    plan: SafeAiQueryPlan,
    rows: list[AiQueryRow],
    total: int,
    as_of: str | None,
    include_explanation: bool,
    extra_warnings: list[str],
) -> str:
    if _plan_is_too_broad(plan):
        body = (
            "That request is too broad or unclear to run safely. "
            "Try adding a sector, a metric such as momentum score, or specific symbols."
        )
        return _sanitize_answer(f"{body} {DISCLAIMER}")
    if not rows:
        body = "No listed stocks currently match those filters."
        if extra_warnings:
            body += " " + extra_warnings[0]
        return _sanitize_answer(f"{body} {DISCLAIMER}")

    intent_lead = {
        "compare": f"Compared {', '.join(plan.symbols) or 'the requested symbols'} on trend, momentum, returns, and valuation.",
        "explain_stock": f"Here is the latest market snapshot for {rows[0].symbol}.",
        "rank": f"Ranked {total} matching stocks by {plan.sort_by.replace('_', ' ')}.",
        "screen": f"Found {total} stocks matching your filters.",
        "unknown": f"Found {total} stocks for that lookup.",
    }[plan.intent]
    lines = [intent_lead]
    if include_explanation:
        applied = _filter_summary(plan)
        if applied:
            bits = [f"{item.field} {item.operator} {item.value}" for item in applied[:6]]
            lines.append("Applied filters: " + "; ".join(bits) + ".")
        strongest = rows[:5]
        summaries = []
        for row in strongest:
            name = row.company_name or row.symbol
            summaries.append(
                f"{row.symbol} ({name}): momentum {_fmt_num(row.momentum_score)}, "
                f"trend {row.trend_score if row.trend_score is not None else 'n/a'}, "
                f"3M {_fmt_pct(row.return_3m)}"
            )
        if summaries:
            lines.append("Strongest rows by the current sort: " + "; ".join(summaries) + ".")
        if as_of:
            lines.append(f"Indicator data as of {as_of}.")
    lines.append(DISCLAIMER)
    return _sanitize_answer(" ".join(lines))


def _market_hours_ttl(timezone_name: str) -> int:
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except Exception:  # noqa: BLE001
        now = datetime.now()
    if now.weekday() >= 5:
        return 300
    minutes = now.hour * 60 + now.minute
    if 9 * 60 + 15 <= minutes <= 15 * 60 + 30:
        return 60
    return 300


def _cache_key(query: str, exchange: str, limit: int, model: str) -> str:
    payload = json.dumps(
        {"q": _normalize_query(query).lower(), "ex": exchange.upper(), "lim": limit, "m": model},
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"{PREFIX_AI}{digest}"


def run_ai_query(
    db: Session,
    payload: AiQueryRequest,
    settings: Settings | None = None,
) -> AiQueryResponse:
    settings = settings or get_settings()
    query = _normalize_query(payload.query)
    exchange = (payload.exchange or "NSE").upper()
    cache_key = _cache_key(query, exchange, payload.limit, settings.ai_model)
    cached = get_json(cache_key)
    if cached is not None:
        try:
            return AiQueryResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            pass

    plan, warnings, latency_ms = build_safe_plan(
        query,
        requested_limit=payload.limit,
        max_rows=settings.ai_max_rows,
        settings=settings,
    )
    logger.info(
        "ai_query received intent=%s filters=%s symbols=%s latency_ms=%.0f",
        plan.intent,
        [(item.field, item.operator) for item in plan.filters],
        plan.symbols,
        latency_ms,
    )

    if _plan_is_too_broad(plan):
        warnings.append("Add a sector, metric, or stock symbol so the lookup stays specific.")
        response = AiQueryResponse(
            answer=generate_answer(
                query=query,
                plan=plan,
                rows=[],
                total=0,
                as_of=None,
                include_explanation=payload.include_explanation,
                extra_warnings=warnings,
            ),
            interpreted_query=_interpreted_query(plan, exchange),
            filters=_filter_summary(plan),
            rows=[],
            total=0,
            warnings=warnings,
        )
        set_json(cache_key, response.model_dump(), _market_hours_ttl(settings.timezone))
        return response

    rows, total, as_of = query_stocks_for_ai(db, plan, exchange=exchange, limit=plan.limit)
    logger.info("ai_query rows=%s total=%s", len(rows), total)
    if total == 0:
        warnings.append("No matching rows were found for the validated filters.")

    response = AiQueryResponse(
        answer=generate_answer(
            query=query,
            plan=plan,
            rows=rows,
            total=total,
            as_of=as_of,
            include_explanation=payload.include_explanation,
            extra_warnings=warnings,
        ),
        interpreted_query=_interpreted_query(plan, exchange),
        filters=_filter_summary(plan),
        rows=rows,
        total=total,
        warnings=warnings,
    )
    set_json(cache_key, response.model_dump(), _market_hours_ttl(settings.timezone))
    return response
