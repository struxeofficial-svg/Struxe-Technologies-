from __future__ import annotations

import pandas as pd

from src.models import PullbackSignal


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _swing_high_low(df: pd.DataFrame, lookback: int = 20) -> tuple[float, float]:
    segment = df.tail(lookback)
    return float(segment["high"].max()), float(segment["low"].min())


def detect_ema_pullback(
    df: pd.DataFrame,
    ema_period: int = 20,
    min_retrace_pct: float = 23.6,
    max_retrace_pct: float = 61.8,
) -> PullbackSignal:
    if len(df) < ema_period + 5:
        return PullbackSignal(False, "ema", 0.0, "sideways", 0.0, 0.0)

    closes = df["close"]
    ema = _ema(closes, ema_period)
    current_close = float(closes.iloc[-1])
    current_ema = float(ema.iloc[-1])
    swing_high, swing_low = _swing_high_low(df)

    trend = "sideways"
    if ema.iloc[-1] > ema.iloc[-5] and current_close > ema.iloc[-10]:
        trend = "up"
    elif ema.iloc[-1] < ema.iloc[-5] and current_close < ema.iloc[-10]:
        trend = "down"

    impulse = swing_high - swing_low
    if impulse <= 0:
        return PullbackSignal(False, "ema", 0.0, trend, current_ema, 0.0)

    if trend == "up":
        retrace_pct = (swing_high - current_close) / impulse * 100
        near_ema = abs(current_close - current_ema) / current_close < 0.005
        in_zone = min_retrace_pct <= retrace_pct <= max_retrace_pct
        detected = in_zone and near_ema and current_close > current_ema * 0.995
        strength = min(1.0, retrace_pct / max_retrace_pct) if detected else 0.0
        return PullbackSignal(
            detected, "ema", retrace_pct, trend, current_ema, strength
        )

    if trend == "down":
        retrace_pct = (current_close - swing_low) / impulse * 100
        near_ema = abs(current_close - current_ema) / current_close < 0.005
        in_zone = min_retrace_pct <= retrace_pct <= max_retrace_pct
        detected = in_zone and near_ema and current_close < current_ema * 1.005
        strength = min(1.0, retrace_pct / max_retrace_pct) if detected else 0.0
        return PullbackSignal(
            detected, "ema", retrace_pct, trend, current_ema, strength
        )

    return PullbackSignal(False, "ema", 0.0, trend, current_ema, 0.0)


def detect_fib_pullback(
    df: pd.DataFrame,
    min_retrace_pct: float = 23.6,
    max_retrace_pct: float = 61.8,
) -> PullbackSignal:
    if len(df) < 20:
        return PullbackSignal(False, "fib", 0.0, "sideways", 0.0, 0.0)

    swing_high, swing_low = _swing_high_low(df)
    impulse = swing_high - swing_low
    if impulse <= 0:
        return PullbackSignal(False, "fib", 0.0, "sideways", 0.0, 0.0)

    current = float(df["close"].iloc[-1])
    trend = "up" if current > df["close"].iloc[-10] else "down"

    if trend == "up":
        retrace_pct = (swing_high - current) / impulse * 100
        fib_382 = swing_high - impulse * 0.382
        fib_618 = swing_high - impulse * 0.618
        in_zone = min_retrace_pct <= retrace_pct <= max_retrace_pct
        near_fib = fib_618 <= current <= fib_382
        detected = in_zone and near_fib
        support = (fib_382 + fib_618) / 2
    else:
        retrace_pct = (current - swing_low) / impulse * 100
        fib_382 = swing_low + impulse * 0.382
        fib_618 = swing_low + impulse * 0.618
        in_zone = min_retrace_pct <= retrace_pct <= max_retrace_pct
        near_fib = fib_382 <= current <= fib_618
        detected = in_zone and near_fib
        support = (fib_382 + fib_618) / 2

    strength = min(1.0, retrace_pct / max_retrace_pct) if detected else 0.0
    return PullbackSignal(detected, "fib", retrace_pct, trend, support, strength)


def detect_pullback(
    df: pd.DataFrame,
    pullback_type: str = "ema",
    ema_period: int = 20,
    min_retrace_pct: float = 23.6,
    max_retrace_pct: float = 61.8,
) -> PullbackSignal:
    if pullback_type == "fib":
        return detect_fib_pullback(df, min_retrace_pct, max_retrace_pct)
    return detect_ema_pullback(
        df, ema_period, min_retrace_pct, max_retrace_pct
    )
