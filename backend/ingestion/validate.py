from __future__ import annotations

from typing import Any


def validate_rows(rows: list[dict[str, Any]], known_symbols: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    valid: list[dict] = []
    invalid: list[dict] = []
    seen: set[str] = set()

    for row in rows:
        symbol = (row.get("symbol") or "").strip().upper()
        reasons: list[str] = []
        if not symbol:
            reasons.append("blank symbol")
        elif symbol in seen:
            reasons.append("duplicate symbol in batch")
        if known_symbols is not None and symbol and symbol not in known_symbols:
            reasons.append("symbol not in master list")
        ltp = row.get("ltp")
        if ltp is None:
            reasons.append("missing ltp")
        elif ltp <= 0:
            reasons.append("ltp must be greater than zero")
        if reasons:
            invalid.append({**row, "errors": reasons})
            continue
        seen.add(symbol)
        valid.append(row)
    return valid, invalid
