from __future__ import annotations

import math
from typing import Any


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def moving_averages(closes: list[float]) -> dict[str, float | None]:
    """Latest-window simple moving averages from oldest → newest closes."""
    clean = [float(value) for value in closes if value is not None and not math.isnan(float(value))]
    return {
        "ma_3": _mean(clean[-3:]) if len(clean) >= 3 else None,
        "ma_7": _mean(clean[-7:]) if len(clean) >= 7 else None,
        "ma_20": _mean(clean[-20:]) if len(clean) >= 20 else None,
        "ma_21": _mean(clean[-21:]) if len(clean) >= 21 else None,
        "ma_50": _mean(clean[-50:]) if len(clean) >= 50 else None,
        "ma_200": _mean(clean[-200:]) if len(clean) >= 200 else None,
    }
