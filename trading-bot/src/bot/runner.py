from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from src.analysis.signals import generate_signal
from src.execution.ccxt_broker import CCXTBroker, create_broker
from src.models import Side, TradeSignal
from src.risk.tp_sl import calculate_position_size

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self, config: dict):
        self.config = config
        self.broker: CCXTBroker = create_broker(config)
        self.symbols: list[str] = config.get("symbols", ["BTC/USDT"])
        self.timeframes = config.get("timeframes", {})
        self.risk = config.get("risk", {})
        self.daily_pnl = 0.0
        self._last_signal_bar: dict[str, str] = {}

    def fetch_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        limit = self.config.get("bot", {}).get("candle_limit", 200)
        return self.broker.fetch_ohlcv(symbol, timeframe, limit=limit)

    def analyze(self, symbol: str) -> TradeSignal:
        entry_tf = self.timeframes.get("entry", "5m")
        trend_tf = self.timeframes.get("trend", "1h")

        entry_df = self.fetch_data(symbol, entry_tf)
        trend_df = self.fetch_data(symbol, trend_tf)

        return generate_signal(symbol, entry_df, trend_df, self.config)

    def _daily_loss_exceeded(self) -> bool:
        max_loss = self.risk.get("max_daily_loss_pct", 3.0)
        balance = self.risk.get("account_balance", 10000.0)
        return self.daily_pnl <= -(balance * max_loss / 100)

    def _can_open_position(self) -> bool:
        max_positions = self.risk.get("max_open_positions", 3)
        if len(self.broker.get_positions()) >= max_positions:
            return False
        if self._daily_loss_exceeded():
            logger.warning("Daily loss limit reached - no new trades")
            return False
        return True

    def _process_exits(self, symbol: str) -> None:
        try:
            price = self.broker.get_ticker_price(symbol)
        except Exception as exc:
            logger.error("Failed to get price for %s: %s", symbol, exc)
            return

        exit_reason = self.broker.check_exits(symbol, price)
        if exit_reason:
            pos = next(
                (p for p in self.broker.get_positions() if p.symbol == symbol),
                None,
            )
            result = self.broker.close_position(symbol, exit_price=price)
            if result.success and result.fill_price and pos:
                if pos.side == Side.BUY:
                    pnl = (result.fill_price - pos.entry_price) * pos.quantity
                else:
                    pnl = (pos.entry_price - result.fill_price) * pos.quantity
                self.daily_pnl += pnl
                logger.info(
                    "Exit triggered (%s) for %s @ %.4f - %s",
                    exit_reason,
                    symbol,
                    price,
                    result.message,
                )

    def _execute_entry(self, signal: TradeSignal) -> None:
        if signal.side == Side.HOLD:
            return

        bar_key = f"{signal.symbol}:{signal.timeframe}"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        if self._last_signal_bar.get(bar_key) == ts:
            return

        if not self._can_open_position():
            return

        balance = self.broker.get_balance()
        quantity = calculate_position_size(
            balance,
            self.risk.get("risk_per_trade_pct", 1.0),
            signal.entry,
            signal.stop_loss,
        )

        if quantity <= 0:
            logger.warning("Position size is zero for %s", signal.symbol)
            return

        quantity = round(quantity, 6)

        result = self.broker.open_position(
            symbol=signal.symbol,
            side=signal.side,
            quantity=quantity,
            entry_price=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

        if result.success:
            self.broker.place_bracket_orders(
                signal.symbol,
                signal.side,
                quantity,
                signal.stop_loss,
                signal.take_profit,
            )
            self._last_signal_bar[bar_key] = ts
            logger.info(
                "TRADE %s %s | confidence=%.1f | entry=%.4f SL=%.4f TP=%.4f | %s",
                signal.side.value,
                signal.symbol,
                signal.confidence,
                signal.entry,
                signal.stop_loss,
                signal.take_profit,
                ", ".join(signal.reasons),
            )
        else:
            logger.warning("Order failed for %s: %s", signal.symbol, result.message)

    def run_once(self) -> list[TradeSignal]:
        signals: list[TradeSignal] = []

        for symbol in self.symbols:
            try:
                if symbol in {p.symbol for p in self.broker.get_positions()}:
                    self._process_exits(symbol)
                    continue

                signal = self.analyze(symbol)
                signals.append(signal)

                logger.info(
                    "Signal %s: %s confidence=%.1f reasons=[%s]",
                    symbol,
                    signal.side.value,
                    signal.confidence,
                    ", ".join(signal.reasons) or "none",
                )

                self._execute_entry(signal)

            except Exception as exc:
                logger.exception("Error processing %s: %s", symbol, exc)

        for pos in self.broker.get_positions():
            self._process_exits(pos.symbol)

        return signals

    def status(self) -> dict:
        return {
            "mode": self.config.get("mode", "paper"),
            "balance": self.broker.get_balance(),
            "positions": [
                {
                    "symbol": p.symbol,
                    "side": p.side.value,
                    "entry": p.entry_price,
                    "quantity": p.quantity,
                    "stop_loss": p.stop_loss,
                    "take_profit": p.take_profit,
                }
                for p in self.broker.get_positions()
            ],
            "daily_pnl": self.daily_pnl,
        }
