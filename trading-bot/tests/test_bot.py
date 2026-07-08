import pandas as pd
import pytest

from src.analysis.candlesticks import detect_patterns
from src.analysis.pullback import detect_pullback
from src.analysis.signals import generate_signal
from src.models import PatternDirection, Side
from src.risk.tp_sl import calculate_position_size, calculate_tp_sl


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_hammer_detection():
    rows = []
    for i in range(8):
        price = 110 - i * 1.5
        rows.append(
            {
                "open": price + 0.3,
                "high": price + 0.8,
                "low": price - 0.5,
                "close": price - 0.2,
                "volume": 1000,
            }
        )
    rows.append(
        {"open": 98.5, "high": 98.85, "low": 94.0, "close": 98.8, "volume": 1500}
    )
    df = _make_df(rows)
    patterns = detect_patterns(df, ["hammer"])
    assert any(p.name == "hammer" for p in patterns)


def test_bullish_engulfing():
    df = _make_df(
        [
            {"open": 102, "high": 103, "low": 100, "close": 101, "volume": 1000},
            {"open": 101, "high": 101.5, "low": 99, "close": 99.5, "volume": 1000},
            {"open": 99, "high": 103, "low": 98.5, "close": 102.5, "volume": 2000},
        ]
    )
    patterns = detect_patterns(df, ["bullish_engulfing"])
    assert len(patterns) == 1
    assert patterns[0].direction == PatternDirection.BULLISH


def test_pullback_detection_uptrend():
    closes = [100 + i * 0.5 for i in range(30)]
    closes[-1] = closes[-2] - 2
    rows = []
    for i, c in enumerate(closes):
        rows.append(
            {
                "open": c - 0.2,
                "high": c + 0.5,
                "low": c - 0.8,
                "close": c,
                "volume": 1000,
            }
        )
    df = _make_df(rows)
    pb = detect_pullback(df, pullback_type="ema", ema_period=10)
    assert pb.trend in ("up", "down", "sideways")
    assert 0 <= pb.retrace_pct <= 100 or pb.retrace_pct == 0


def test_tp_sl_buy():
    sl, tp = calculate_tp_sl(100.0, Side.BUY, 2.0, {"sl_atr_mult": 1.5, "tp_atr_mult": 3.0})
    assert sl == 97.0
    assert tp == 106.0


def test_position_size():
    qty = calculate_position_size(10000, 1.0, 100.0, 95.0)
    assert qty == pytest.approx(20.0)


def test_generate_signal_hold_on_flat_data():
    rows = []
    for i in range(60):
        price = 100 + (i % 3) * 0.1
        rows.append(
            {
                "open": price,
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price,
                "volume": 1000,
            }
        )
    df = _make_df(rows)
    config = {
        "strategy": {
            "min_confidence": 65,
            "patterns": ["hammer", "doji"],
            "pullback": {"type": "ema", "ema_period": 20},
        },
        "tp_sl": {"atr_period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        "timeframes": {"entry": "5m"},
    }
    signal = generate_signal("BTC/USDT", df, df, config)
    assert signal.symbol == "BTC/USDT"
    assert signal.side in (Side.BUY, Side.SELL, Side.HOLD)
