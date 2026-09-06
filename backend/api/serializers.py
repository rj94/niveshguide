from __future__ import annotations

from typing import Any

from database.models import Stock, StockIndicator, StockSignal, StockSnapshot


def _num(value) -> float | None:
    return float(value) if value is not None else None


def serialize_row(stock: Stock, indicator: StockIndicator | None, snapshot: StockSnapshot | None) -> dict[str, Any]:
    return {
        "symbol": stock.symbol,
        "company_name": stock.company_name,
        "exchange": stock.exchange,
        "ltp": _num(snapshot.ltp) if snapshot else None,
        "market_cap": _num(snapshot.market_cap) if snapshot else None,
        "day_high": _num(snapshot.day_high) if snapshot else None,
        "prev_close": _num(snapshot.prev_close) if snapshot else None,
        "high_52_week": _num(snapshot.high_52_week) if snapshot else None,
        "low_52_week": _num(snapshot.low_52_week) if snapshot else None,
        "pe": _num(snapshot.pe) if snapshot else None,
        "eps": _num(snapshot.eps) if snapshot else None,
        "volume": int(snapshot.volume) if snapshot and snapshot.volume is not None else None,
        "avg_volume_3m": _num(snapshot.avg_volume_3m) if snapshot else None,
        "avg_volume_6m": _num(snapshot.avg_volume_6m) if snapshot else None,
        "avg_volume_1y": _num(snapshot.avg_volume_1y) if snapshot else None,
        "ma_3": _num(indicator.ma_3) if indicator else None,
        "ma_7": _num(indicator.ma_7) if indicator else None,
        "ma_21": _num(indicator.ma_21) if indicator else None,
        "ma_50": _num(indicator.ma_50) if indicator else None,
        "ma_200": _num(indicator.ma_200) if indicator else None,
        "crossover_3_7": indicator.crossover_3_7 if indicator else None,
        "above_ma_21": indicator.above_ma_21 if indicator else None,
        "ma21_gt_ma50": indicator.ma21_gt_ma50 if indicator else None,
        "above_ma_200": indicator.above_ma_200 if indicator else None,
        "golden_cross": indicator.golden_cross if indicator else None,
        "trend_score": indicator.trend_score if indicator else None,
        "trend": indicator.trend if indicator else None,
        "distance_from_52w_high": _num(indicator.distance_from_52w_high) if indicator else None,
        "return_3m": _num(getattr(indicator, "return_3m", None)) if indicator else None,
        "return_6m": _num(getattr(indicator, "return_6m", None)) if indicator else None,
        "as_of": (indicator.calculation_date.isoformat() if indicator else None),
        "snapshot_date": snapshot.snapshot_date.isoformat() if snapshot else None,
        "source": snapshot.source if snapshot else None,
    }


def serialize_signal(stock: Stock, signal: StockSignal) -> dict[str, Any]:
    return {
        "symbol": stock.symbol,
        "company_name": stock.company_name,
        "signal_type": signal.signal_type,
        "direction": signal.direction,
        "signal_date": signal.signal_date.isoformat(),
        "metadata": signal.metadata_json,
    }
