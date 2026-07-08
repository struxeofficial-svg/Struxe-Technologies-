from __future__ import annotations

import numpy as np
import pandas as pd


def generate_sample_ohlcv(
    symbol: str = "BTC/USDT",
    bars: int = 200,
    timeframe: str = "5m",
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate realistic sample OHLCV for offline testing."""
    rng = np.random.default_rng(seed or hash(symbol + timeframe) % 2**32)
    base = 65000.0 if "BTC" in symbol else 3500.0

    timestamps = pd.date_range(
        end=pd.Timestamp.now(tz="UTC"),
        periods=bars,
        freq=_timeframe_to_pandas_freq(timeframe),
    )

    returns = rng.normal(0.0001, 0.002, bars)
    closes = base * np.cumprod(1 + returns)

    rows = []
    for i, close in enumerate(closes):
        volatility = abs(rng.normal(0, close * 0.001))
        open_ = close * (1 + rng.normal(0, 0.0005))
        high = max(open_, close) + volatility
        low = min(open_, close) - volatility
        volume = float(rng.uniform(100, 5000))
        rows.append(
            {
                "timestamp": timestamps[i],
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    return pd.DataFrame(rows)


def _timeframe_to_pandas_freq(tf: str) -> str:
    mapping = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1D",
    }
    return mapping.get(tf, "5min")
