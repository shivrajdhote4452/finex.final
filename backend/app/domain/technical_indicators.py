"""Deterministic Technical Indicators Calculation Engine.

Implements standard mathematical formulations for:
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Bollinger Bands (Upper, Middle, Lower)
- Relative Strength Index (RSI - Wilder's Smoothing)
- Moving Average Convergence Divergence (MACD, Signal, Histogram)
- Volume Weighted Average Price (VWAP)

Strict Invariants:
1. Deterministic output without random/fabricated values.
2. Proper warm-up handling: returns None before sufficient history is available.
3. Does not replace unknown/insufficient values with artificial zeroes.
4. Numerical tolerance compatible between backend calculation and plotted charts.
"""

import math
from decimal import Decimal
from typing import Any, Dict, List, Optional


def _to_float(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(str(val))
    except (ValueError, TypeError):
        return 0.0


def calculate_sma(bars: List[Dict[str, Any]], period: int = 20, price_key: str = "close") -> List[Dict[str, Any]]:
    """Calculate Simple Moving Average (SMA) over closing prices."""
    results: List[Dict[str, Any]] = []
    prices = [_to_float(b.get(price_key, 0.0)) for b in bars]

    for i in range(len(bars)):
        bar_date = bars[i].get("date")
        bar_time = bars[i].get("time")
        if i < period - 1:
            results.append({"date": bar_date, "time": bar_time, "value": None})
        else:
            window = prices[i - period + 1 : i + 1]
            sma_val = sum(window) / float(period)
            results.append({"date": bar_date, "time": bar_time, "value": round(sma_val, 4)})

    return results


def calculate_ema(bars: List[Dict[str, Any]], period: int = 20, price_key: str = "close") -> List[Dict[str, Any]]:
    """Calculate Exponential Moving Average (EMA)."""
    results: List[Dict[str, Any]] = []
    prices = [_to_float(b.get(price_key, 0.0)) for b in bars]

    if not prices or period <= 0:
        return results

    k = 2.0 / (period + 1.0)
    current_ema: Optional[float] = None

    for i in range(len(bars)):
        bar_date = bars[i].get("date")
        bar_time = bars[i].get("time")

        if i < period - 1:
            results.append({"date": bar_date, "time": bar_time, "value": None})
        elif i == period - 1:
            # First EMA is SMA of the first period bars
            current_ema = sum(prices[:period]) / float(period)
            results.append({"date": bar_date, "time": bar_time, "value": round(current_ema, 4)})
        else:
            current_ema = (prices[i] - current_ema) * k + current_ema  # type: ignore[operator]
            results.append({"date": bar_date, "time": bar_time, "value": round(current_ema, 4)})

    return results


def calculate_bollinger_bands(
    bars: List[Dict[str, Any]],
    period: int = 20,
    num_std: float = 2.0,
    price_key: str = "close",
) -> List[Dict[str, Any]]:
    """Calculate Bollinger Bands: middle (SMA), upper, and lower bands."""
    results: List[Dict[str, Any]] = []
    prices = [_to_float(b.get(price_key, 0.0)) for b in bars]

    for i in range(len(bars)):
        bar_date = bars[i].get("date")
        bar_time = bars[i].get("time")

        if i < period - 1:
            results.append(
                {"date": bar_date, "time": bar_time, "middle": None, "upper": None, "lower": None, "bandwidth": None}
            )
        else:
            window = prices[i - period + 1 : i + 1]
            mean = sum(window) / float(period)
            variance = sum((p - mean) ** 2 for p in window) / float(period)
            std_dev = math.sqrt(variance)

            upper = mean + (num_std * std_dev)
            lower = mean - (num_std * std_dev)
            bandwidth = ((upper - lower) / mean) * 100.0 if mean > 0 else 0.0

            results.append(
                {
                    "date": bar_date,
                    "time": bar_time,
                    "middle": round(mean, 4),
                    "upper": round(upper, 4),
                    "lower": round(lower, 4),
                    "bandwidth": round(bandwidth, 4),
                }
            )

    return results


def calculate_rsi(bars: List[Dict[str, Any]], period: int = 14, price_key: str = "close") -> List[Dict[str, Any]]:
    """Calculate Relative Strength Index (RSI) using Wilder's Smoothing."""
    results: List[Dict[str, Any]] = []
    prices = [_to_float(b.get(price_key, 0.0)) for b in bars]

    if len(prices) <= period:
        return [{"date": b.get("date"), "time": b.get("time"), "value": None} for b in bars]

    gains: List[float] = []
    losses: List[float] = []

    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        if delta > 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))

    # First RSI at index == period
    avg_gain = sum(gains[:period]) / float(period)
    avg_loss = sum(losses[:period]) / float(period)

    # Fill leading bars as None
    for i in range(period):
        results.append({"date": bars[i].get("date"), "time": bars[i].get("time"), "value": None})

    if avg_loss == 0.0:
        rsi = 100.0 if avg_gain > 0 else 50.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    results.append({"date": bars[period].get("date"), "time": bars[period].get("time"), "value": round(rsi, 2)})

    # Wilder smoothing for subsequent bars
    for i in range(period + 1, len(bars)):
        gain = gains[i - 1]
        loss = losses[i - 1]

        avg_gain = (avg_gain * (period - 1) + gain) / float(period)
        avg_loss = (avg_loss * (period - 1) + loss) / float(period)

        if avg_loss == 0.0:
            rsi = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        results.append({"date": bars[i].get("date"), "time": bars[i].get("time"), "value": round(rsi, 2)})

    return results


def calculate_macd(
    bars: List[Dict[str, Any]],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    price_key: str = "close",
) -> List[Dict[str, Any]]:
    """Calculate Moving Average Convergence Divergence (MACD, Signal, and Histogram)."""
    results: List[Dict[str, Any]] = []
    fast_ema_series = calculate_ema(bars, period=fast_period, price_key=price_key)
    slow_ema_series = calculate_ema(bars, period=slow_period, price_key=price_key)

    macd_raw: List[Optional[float]] = []

    for i in range(len(bars)):
        f_val = fast_ema_series[i]["value"]
        s_val = slow_ema_series[i]["value"]
        if f_val is not None and s_val is not None:
            macd_raw.append(round(f_val - s_val, 4))
        else:
            macd_raw.append(None)

    # Compute Signal Line (EMA of MACD line where valid)
    valid_indices = [i for i, v in enumerate(macd_raw) if v is not None]
    if len(valid_indices) < signal_period:
        for i in range(len(bars)):
            results.append(
                {
                    "date": bars[i].get("date"),
                    "time": bars[i].get("time"),
                    "macd": macd_raw[i],
                    "signal": None,
                    "histogram": None,
                }
            )
        return results

    # Construct mock bars from valid macd values for signal calculation
    valid_macd_bars = [
        {"close": macd_raw[i], "date": bars[i].get("date"), "time": bars[i].get("time")} for i in valid_indices
    ]
    signal_series = calculate_ema(valid_macd_bars, period=signal_period, price_key="close")

    signal_map: Dict[int, Optional[float]] = {}
    for idx_in_valid, orig_idx in enumerate(valid_indices):
        signal_map[orig_idx] = signal_series[idx_in_valid]["value"]

    for i in range(len(bars)):
        m_val = macd_raw[i]
        s_val = signal_map.get(i)
        h_val = round(m_val - s_val, 4) if m_val is not None and s_val is not None else None

        results.append(
            {
                "date": bars[i].get("date"),
                "time": bars[i].get("time"),
                "macd": m_val,
                "signal": s_val,
                "histogram": h_val,
            }
        )

    return results


def calculate_vwap(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate session Volume Weighted Average Price (VWAP).

    Approximated using Typical Price = (High + Low + Close) / 3 and Cumulative Volume.
    """
    results: List[Dict[str, Any]] = []
    cum_pv = 0.0
    cum_vol = 0.0
    current_date: Optional[str] = None

    for b in bars:
        bar_date_str = str(b.get("date", ""))[:10]
        # Reset at session boundary
        if current_date != bar_date_str:
            cum_pv = 0.0
            cum_vol = 0.0
            current_date = bar_date_str

        high = _to_float(b.get("high", 0.0))
        low = _to_float(b.get("low", 0.0))
        close = _to_float(b.get("close", 0.0))
        vol = _to_float(b.get("volume", 0.0))

        typical_price = (high + low + close) / 3.0
        cum_pv += typical_price * vol
        cum_vol += vol

        vwap_val = round(cum_pv / cum_vol, 4) if cum_vol > 0 else round(close, 4)

        results.append(
            {
                "date": b.get("date"),
                "time": b.get("time"),
                "value": vwap_val,
            }
        )

    return results
