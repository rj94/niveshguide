from __future__ import annotations

TREND_LABELS = {
    5: "Strong Uptrend",
    4: "Uptrend",
    3: "Mild Uptrend",
    2: "Neutral",
    1: "Downtrend",
    0: "Strong Downtrend",
}


def classify_trend(score: int) -> str:
    return TREND_LABELS.get(max(0, min(5, score)), "Neutral")


def trend_score(
    ma_3: float | None,
    ma_7: float | None,
    ma_21: float | None,
    ma_50: float | None,
    ma_200: float | None,
    ltp: float | None,
) -> dict:
    crossover_3_7 = ma_3 is not None and ma_7 is not None and ma_3 > ma_7
    above_ma_21 = ltp is not None and ma_21 is not None and ltp > ma_21
    ma21_gt_ma50 = ma_21 is not None and ma_50 is not None and ma_21 > ma_50
    above_ma_200 = ltp is not None and ma_200 is not None and ltp > ma_200
    golden_cross = ma_50 is not None and ma_200 is not None and ma_50 > ma_200

    score = int(crossover_3_7) + int(above_ma_21) + int(ma21_gt_ma50) + int(above_ma_200) + int(golden_cross)
    return {
        "crossover_3_7": crossover_3_7 if ma_3 is not None and ma_7 is not None else None,
        "above_ma_21": above_ma_21 if ltp is not None and ma_21 is not None else None,
        "ma21_gt_ma50": ma21_gt_ma50 if ma_21 is not None and ma_50 is not None else None,
        "above_ma_200": above_ma_200 if ltp is not None and ma_200 is not None else None,
        "golden_cross": golden_cross if ma_50 is not None and ma_200 is not None else None,
        "trend_score": score,
        "trend": classify_trend(score),
    }


def distance_from_52w_high(ltp: float | None, high_52: float | None) -> float | None:
    if ltp is None or high_52 is None or high_52 == 0:
        return None
    return ((ltp / high_52) - 1) * 100
