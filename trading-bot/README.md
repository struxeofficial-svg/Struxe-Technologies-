# Multi-Asset Trading Bot

Automated trading bot with candlestick pattern detection, pullback analysis, buy/sell signal scoring, and automatic take-profit / stop-loss management.

## Features

1. **Buy / Sell signals** — Aggregates candlestick patterns, pullbacks, and higher-timeframe trend into a confidence score
2. **Candlestick patterns** — Hammer, shooting star, doji, engulfing, morning/evening star
3. **Pullback detection** — EMA and Fibonacci retracement zones
4. **Automated trading** — Continuous polling loop with paper or live execution
5. **Auto TP / SL** — ATR-based brackets attached on every entry

## Quick Start

```bash
cd trading-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Analyze current market (no trades)
python main.py analyze

# Run one paper-trading cycle
python main.py run --once

# Run continuously (paper mode)
python main.py run
```

## Configuration

Edit `config/settings.yaml`:

| Section | Purpose |
|---------|---------|
| `mode` | `paper` or `live` |
| `symbols` | Trading pairs (e.g. `BTC/USDT`) |
| `timeframes` | Trend (1h), setup (15m), entry (5m) |
| `strategy` | Patterns, pullback settings, min confidence |
| `risk` | Position sizing, max positions, daily loss limit |
| `tp_sl` | ATR multipliers for stop-loss and take-profit |

For live trading, copy `config/secrets.env.example` to `config/.env` and add API keys.

## Commands

```bash
# Analyze a specific symbol
python main.py analyze --symbol ETH/USDT

# Paper trade one symbol
python main.py run --once --symbol BTC/USDT

# Live mode (requires API keys)
python main.py run --mode live
```

## Architecture

```
main.py
  └── TradingBot (src/bot/runner.py)
        ├── CCXTBroker (src/execution/ccxt_broker.py)  — crypto via CCXT
        ├── PaperBroker (src/execution/paper.py)          — simulated fills
        ├── candlesticks.py  — pattern detection
        ├── pullback.py      — EMA / Fib pullback
        ├── signals.py       — buy/sell scoring
        └── tp_sl.py         — position sizing + brackets
```

## Supported Markets

| Market | Status | Connector |
|--------|--------|-----------|
| Crypto | Ready | CCXT (Binance, Bybit, 100+ exchanges) |
| Forex | Planned | OANDA / IBKR adapter |
| Stocks | Planned | Alpaca / IBKR adapter |

The broker adapter pattern makes it straightforward to add forex and stock connectors.

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## Risk Warning

This bot is for educational purposes. Always start in **paper mode**. Past performance does not guarantee future results. Never risk money you cannot afford to lose.
