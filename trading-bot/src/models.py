from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PatternDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class CandlePattern:
    name: str
    direction: PatternDirection
    strength: float
    bar_index: int


@dataclass
class PullbackSignal:
    detected: bool
    pullback_type: str
    retrace_pct: float
    trend: Literal["up", "down", "sideways"]
    support_level: float
    strength: float


@dataclass
class TradeSignal:
    symbol: str
    timeframe: str
    side: Side
    confidence: float
    entry: float
    stop_loss: float
    take_profit: float
    reasons: list[str] = field(default_factory=list)
    patterns: list[CandlePattern] = field(default_factory=list)
    pullback: PullbackSignal | None = None


@dataclass
class Position:
    symbol: str
    side: Side
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    opened_at: str
    order_id: str | None = None


@dataclass
class OrderResult:
    success: bool
    order_id: str | None
    message: str
    fill_price: float | None = None
    quantity: float | None = None
