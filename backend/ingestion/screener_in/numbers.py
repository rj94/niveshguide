from __future__ import annotations

import re
from typing import Any


_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_number(raw: Any) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text in {"-", "—", "–", "NA", "N/A", "n/a"}:
        return None
    neg = text.startswith("(") and text.endswith(")")
    cleaned = text.replace(",", "").replace("%", "").replace("₹", "").replace("Cr", "").replace("cr", "")
    cleaned = cleaned.replace("(", "").replace(")", "").strip()
    match = _NUM_RE.search(cleaned)
    if not match:
        return None
    try:
        value = float(match.group(0))
    except ValueError:
        return None
    return -value if neg else value


def normalize_key(name: str) -> str:
    text = re.sub(r"\s+", " ", (name or "").strip().lower())
    text = text.rstrip("+").strip()
    return text
