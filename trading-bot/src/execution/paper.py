from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import pandas as pd

from src.models import OrderResult, Position, Side

logger = logging.getLogger(__name__)


class BaseBroker(ABC):
    @abstractmethod
    def get_balance(self) -> float:
        pass

    @abstractmethod
    def get_positions(self) -> list[Position]:
        pass

    @abstractmethod
    def place_market_order(
        self, symbol: str, side: Side, quantity: float
    ) -> OrderResult:
        pass

    @abstractmethod
    def place_bracket_orders(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        stop_loss: float,
        take_profit: float,
    ) -> OrderResult:
        pass

    @abstractmethod
    def check_exits(self, symbol: str, current_price: float) -> str | None:
        pass

    @abstractmethod
    def close_position(self, symbol: str) -> OrderResult:
        pass


class PaperBroker(BaseBroker):
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.positions: dict[str, Position] = {}
        self._order_counter = 0

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"paper-{self._order_counter}"

    def get_balance(self) -> float:
        return self.balance

    def get_positions(self) -> list[Position]:
        return list(self.positions.values())

    def place_market_order(
        self, symbol: str, side: Side, quantity: float
    ) -> OrderResult:
        if side == Side.HOLD:
            return OrderResult(False, None, "HOLD signal - no order placed")

        if symbol in self.positions:
            return OrderResult(False, None, f"Position already open for {symbol}")

        order_id = self._next_order_id()
        fill_price = 0.0
        cost = fill_price * quantity

        self.positions[symbol] = Position(
            symbol=symbol,
            side=side,
            entry_price=fill_price,
            quantity=quantity,
            stop_loss=0.0,
            take_profit=0.0,
            opened_at=datetime.now(timezone.utc).isoformat(),
            order_id=order_id,
        )

        return OrderResult(
            True,
            order_id,
            f"Paper market order placed: {side.value} {quantity} {symbol}",
            fill_price=fill_price,
            quantity=quantity,
        )

    def open_position(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> OrderResult:
        if symbol in self.positions:
            return OrderResult(False, None, f"Position already open for {symbol}")

        order_id = self._next_order_id()
        cost = entry_price * quantity

        if side == Side.BUY and cost > self.balance:
            return OrderResult(False, None, "Insufficient balance")

        self.positions[symbol] = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            opened_at=datetime.now(timezone.utc).isoformat(),
            order_id=order_id,
        )

        if side == Side.BUY:
            self.balance -= cost
        else:
            self.balance += cost

        logger.info(
            "Opened %s position: %s qty=%.6f entry=%.4f SL=%.4f TP=%.4f",
            side.value,
            symbol,
            quantity,
            entry_price,
            stop_loss,
            take_profit,
        )

        return OrderResult(
            True,
            order_id,
            f"Position opened: {side.value} {quantity} {symbol} @ {entry_price}",
            fill_price=entry_price,
            quantity=quantity,
        )

    def place_bracket_orders(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        stop_loss: float,
        take_profit: float,
    ) -> OrderResult:
        if symbol not in self.positions:
            return OrderResult(False, None, f"No position for {symbol}")

        pos = self.positions[symbol]
        pos.stop_loss = stop_loss
        pos.take_profit = take_profit
        logger.info(
            "Bracket orders set for %s: SL=%.4f TP=%.4f",
            symbol,
            stop_loss,
            take_profit,
        )
        return OrderResult(True, pos.order_id, "Bracket TP/SL attached")

    def check_exits(self, symbol: str, current_price: float) -> str | None:
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        if pos.side == Side.BUY:
            if current_price <= pos.stop_loss:
                return "stop_loss"
            if current_price >= pos.take_profit:
                return "take_profit"
        elif pos.side == Side.SELL:
            if current_price >= pos.stop_loss:
                return "stop_loss"
            if current_price <= pos.take_profit:
                return "take_profit"

        return None

    def close_position(self, symbol: str, exit_price: float | None = None) -> OrderResult:
        if symbol not in self.positions:
            return OrderResult(False, None, f"No position for {symbol}")

        pos = self.positions.pop(symbol)
        price = exit_price or pos.entry_price

        if pos.side == Side.BUY:
            pnl = (price - pos.entry_price) * pos.quantity
            self.balance += price * pos.quantity
        else:
            pnl = (pos.entry_price - price) * pos.quantity
            self.balance -= price * pos.quantity

        logger.info(
            "Closed %s: entry=%.4f exit=%.4f pnl=%.2f balance=%.2f",
            symbol,
            pos.entry_price,
            price,
            pnl,
            self.balance,
        )

        return OrderResult(
            True,
            pos.order_id,
            f"Position closed. PnL: {pnl:.2f}",
            fill_price=price,
            quantity=pos.quantity,
        )
