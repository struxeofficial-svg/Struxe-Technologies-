from __future__ import annotations

import numpy as np
import pandas as pd

from src.models import CandlePattern, PatternDirection


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _upper_wick(h: float, o: float, c: float) -> float:
    return h - max(o, c)


def _lower_wick(l: float, o: float, c: float) -> float:
    return min(o, c) - l


def _is_bullish(o: float, c: float) -> bool:
    return c > o


def _prior_trend(closes: pd.Series, idx: int, lookback: int = 5) -> str:
    if idx < lookback:
        return "sideways"
    segment = closes.iloc[idx - lookback : idx]
    if segment.iloc[-1] > segment.iloc[0] * 1.002:
        return "up"
    if segment.iloc[-1] < segment.iloc[0] * 0.998:
        return "down"
    return "sideways"


def detect_hammer(row: pd.Series, trend: str) -> CandlePattern | None:
    body = _body(row["open"], row["close"])
    lower = _lower_wick(row["low"], row["open"], row["close"])
    upper = _upper_wick(row["high"], row["open"], row["close"])
    if body == 0:
        body = row["close"] * 0.0001
    if lower >= 2 * body and upper <= body * 0.5 and trend == "down":
        strength = min(1.0, lower / (body * 3))
        return CandlePattern("hammer", PatternDirection.BULLISH, strength, -1)
    return None


def detect_shooting_star(row: pd.Series, trend: str) -> CandlePattern | None:
    body = _body(row["open"], row["close"])
    upper = _upper_wick(row["high"], row["open"], row["close"])
    lower = _lower_wick(row["low"], row["open"], row["close"])
    if body == 0:
        body = row["close"] * 0.0001
    if upper >= 2 * body and lower <= body * 0.5 and trend == "up":
        strength = min(1.0, upper / (body * 3))
        return CandlePattern("shooting_star", PatternDirection.BEARISH, strength, -1)
    return None


def detect_doji(row: pd.Series) -> CandlePattern | None:
    body = _body(row["open"], row["close"])
    total_range = row["high"] - row["low"]
    if total_range == 0:
        return None
    if body / total_range <= 0.1:
        return CandlePattern("doji", PatternDirection.NEUTRAL, 0.5, -1)
    return None


def detect_engulfing(df: pd.DataFrame, idx: int) -> CandlePattern | None:
    if idx < 1:
        return None
    prev, curr = df.iloc[idx - 1], df.iloc[idx]
    prev_bull = _is_bullish(prev["open"], prev["close"])
    curr_bull = _is_bullish(curr["open"], curr["close"])

    if not prev_bull and curr_bull:
        if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
            body_ratio = _body(curr["open"], curr["close"]) / max(
                _body(prev["open"], prev["close"]), 1e-9
            )
            return CandlePattern(
                "bullish_engulfing",
                PatternDirection.BULLISH,
                min(1.0, body_ratio),
                idx,
            )

    if prev_bull and not curr_bull:
        if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
            body_ratio = _body(curr["open"], curr["close"]) / max(
                _body(prev["open"], prev["close"]), 1e-9
            )
            return CandlePattern(
                "bearish_engulfing",
                PatternDirection.BEARISH,
                min(1.0, body_ratio),
                idx,
            )
    return None


def detect_morning_star(df: pd.DataFrame, idx: int) -> CandlePattern | None:
    if idx < 2:
        return None
    first, second, third = df.iloc[idx - 2], df.iloc[idx - 1], df.iloc[idx]
    if not _is_bullish(first["open"], first["close"]):
        if _is_bullish(third["open"], third["close"]):
            first_body = _body(first["open"], first["close"])
            second_body = _body(second["open"], second["close"])
            if second_body < first_body * 0.5 and third["close"] > (
                first["open"] + first["close"]
            ) / 2:
                return CandlePattern(
                    "morning_star", PatternDirection.BULLISH, 0.8, idx
                )
    return None


def detect_evening_star(df: pd.DataFrame, idx: int) -> CandlePattern | None:
    if idx < 2:
        return None
    first, second, third = df.iloc[idx - 2], df.iloc[idx - 1], df.iloc[idx]
    if _is_bullish(first["open"], first["close"]):
        if not _is_bullish(third["open"], third["close"]):
            first_body = _body(first["open"], first["close"])
            second_body = _body(second["open"], second["close"])
            if second_body < first_body * 0.5 and third["close"] < (
                first["open"] + first["close"]
            ) / 2:
                return CandlePattern(
                    "evening_star", PatternDirection.BEARISH, 0.8, idx
                )
    return None


DETECTORS = {
    "hammer": lambda df, i: detect_hammer(
        df.iloc[i], _prior_trend(df["close"], i)
    ),
    "shooting_star": lambda df, i: detect_shooting_star(
        df.iloc[i], _prior_trend(df["close"], i)
    ),
    "doji": lambda df, i: detect_doji(df.iloc[i]),
    "bullish_engulfing": lambda df, i: detect_engulfing(df, i),
    "bearish_engulfing": lambda df, i: detect_engulfing(df, i),
    "morning_star": lambda df, i: detect_morning_star(df, i),
    "evening_star": lambda df, i: detect_evening_star(df, i),
}


def detect_patterns(
    df: pd.DataFrame, enabled: list[str] | None = None
) -> list[CandlePattern]:
    if df.empty or len(df) < 3:
        return []

    enabled = enabled or list(DETECTORS.keys())
    patterns: list[CandlePattern] = []
    idx = len(df) - 1

    for name in enabled:
        detector = DETECTORS.get(name)
        if detector is None:
            continue
        result = detector(df, idx)
        if result is not None and result.name == name:
            patterns.append(result)

    return patterns
