from __future__ import annotations

import pandas as pd
import ta

from src.analysis.candlesticks import detect_patterns
from src.analysis.pullback import detect_pullback
from src.models import PatternDirection, Side, TradeSignal
from src.risk.tp_sl import calculate_tp_sl


def _trend_from_higher_tf(df: pd.DataFrame) -> str:
    if len(df) < 50:
        return "sideways"
    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    if ema20.iloc[-1] > ema50.iloc[-1] and df["close"].iloc[-1] > ema20.iloc[-1]:
        return "up"
    if ema20.iloc[-1] < ema50.iloc[-1] and df["close"].iloc[-1] < ema20.iloc[-1]:
        return "down"
    return "sideways"


def generate_signal(
    symbol: str,
    entry_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    config: dict,
) -> TradeSignal:
    strategy = config.get("strategy", {})
    tp_sl_cfg = config.get("tp_sl", {})
    pullback_cfg = strategy.get("pullback", {})

    patterns = detect_patterns(entry_df, strategy.get("patterns"))
    pullback = detect_pullback(
        entry_df,
        pullback_type=pullback_cfg.get("type", "ema"),
        ema_period=pullback_cfg.get("ema_period", 20),
        min_retrace_pct=pullback_cfg.get("min_retrace_pct", 23.6),
        max_retrace_pct=pullback_cfg.get("max_retrace_pct", 61.8),
    )
    higher_trend = _trend_from_higher_tf(trend_df)

    bullish_score = 0.0
    bearish_score = 0.0
    reasons: list[str] = []

    for p in patterns:
        if p.direction == PatternDirection.BULLISH:
            bullish_score += 25 * p.strength
            reasons.append(p.name)
        elif p.direction == PatternDirection.BEARISH:
            bearish_score += 25 * p.strength
            reasons.append(p.name)

    if pullback.detected:
        reasons.append(f"pullback_{pullback.pullback_type}")
        if pullback.trend == "up":
            bullish_score += 30 * pullback.strength
        elif pullback.trend == "down":
            bearish_score += 30 * pullback.strength

    if higher_trend == "up":
        bullish_score += 15
        reasons.append("higher_tf_uptrend")
    elif higher_trend == "down":
        bearish_score += 15
        reasons.append("higher_tf_downtrend")

    entry_price = float(entry_df["close"].iloc[-1])
    atr = ta.volatility.average_true_range(
        entry_df["high"],
        entry_df["low"],
        entry_df["close"],
        window=tp_sl_cfg.get("atr_period", 14),
    ).iloc[-1]

    side = Side.HOLD
    confidence = 0.0

    if bullish_score > bearish_score and bullish_score >= strategy.get(
        "min_confidence", 65
    ):
        side = Side.BUY
        confidence = min(100.0, bullish_score)
    elif bearish_score > bullish_score and bearish_score >= strategy.get(
        "min_confidence", 65
    ):
        side = Side.SELL
        confidence = min(100.0, bearish_score)

    stop_loss, take_profit = calculate_tp_sl(
        entry_price,
        side,
        float(atr),
        tp_sl_cfg,
    )

    return TradeSignal(
        symbol=symbol,
        timeframe=config.get("timeframes", {}).get("entry", "5m"),
        side=side,
        confidence=confidence,
        entry=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reasons=reasons,
        patterns=patterns,
        pullback=pullback,
    )
