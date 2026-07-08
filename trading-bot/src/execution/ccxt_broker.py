from __future__ import annotations

import logging
import os
from typing import Any

import ccxt
import pandas as pd

from src.execution.paper import PaperBroker
from src.models import OrderResult, Position, Side

logger = logging.getLogger(__name__)


class CCXTBroker(PaperBroker):
  """Live crypto broker via CCXT. Falls back to paper semantics for dry-run."""

  def __init__(
      self,
      exchange_id: str = "binance",
      api_key: str = "",
      api_secret: str = "",
      sandbox: bool = True,
      initial_balance: float = 10000.0,
  ):
      super().__init__(initial_balance=initial_balance)
      self.exchange_id = exchange_id
      self.sandbox = sandbox
      self._exchange: Any = None

      exchange_class = getattr(ccxt, exchange_id, None)
      if exchange_class is None:
          raise ValueError(f"Unsupported exchange: {exchange_id}")

      params: dict[str, Any] = {"enableRateLimit": True}
      if api_key:
          params["apiKey"] = api_key
          params["secret"] = api_secret

      self._exchange = exchange_class(params)

      if sandbox and hasattr(self._exchange, "set_sandbox_mode"):
          self._exchange.set_sandbox_mode(True)

  def fetch_ohlcv(
      self, symbol: str, timeframe: str, limit: int = 200
  ) -> pd.DataFrame:
      try:
          raw = self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
          df = pd.DataFrame(
              raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
          )
          df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
          return df
      except Exception as exc:
          logger.warning(
              "Exchange fetch failed (%s), using sample data for %s",
              exc,
              symbol,
          )
          from src.data.mock_feed import generate_sample_ohlcv

          return generate_sample_ohlcv(symbol, bars=limit, timeframe=timeframe)

  def get_ticker_price(self, symbol: str) -> float:
      try:
          ticker = self._exchange.fetch_ticker(symbol)
          return float(ticker["last"])
      except Exception:
          from src.data.mock_feed import generate_sample_ohlcv

          df = generate_sample_ohlcv(symbol, bars=5, timeframe="5m")
          return float(df["close"].iloc[-1])

  def get_balance(self) -> float:
      if not self._exchange.apiKey:
          return super().get_balance()
      try:
          balance = self._exchange.fetch_balance()
          return float(balance.get("USDT", {}).get("free", self.balance))
      except Exception:
          return super().get_balance()

  def open_position(
      self,
      symbol: str,
      side: Side,
      quantity: float,
      entry_price: float,
      stop_loss: float,
      take_profit: float,
  ) -> OrderResult:
      if not self._exchange.apiKey:
          return super().open_position(
              symbol, side, quantity, entry_price, stop_loss, take_profit
          )

      try:
          order_side = "buy" if side == Side.BUY else "sell"
          order = self._exchange.create_market_order(symbol, order_side, quantity)
          fill_price = float(order.get("average") or order.get("price") or entry_price)

          result = super().open_position(
              symbol, side, quantity, fill_price, stop_loss, take_profit
          )
          result.order_id = order.get("id", result.order_id)
          result.message = f"Live order filled: {order_side} {quantity} {symbol}"
          return result
      except Exception as exc:
          logger.error("Live order failed: %s", exc)
          return OrderResult(False, None, str(exc))

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

      if not self._exchange.apiKey:
          return super().place_bracket_orders(
              symbol, side, quantity, stop_loss, take_profit
          )

      try:
          close_side = "sell" if side == Side.BUY else "buy"
          self._exchange.create_order(
              symbol,
              "stop_market",
              close_side,
              quantity,
              None,
              {"stopPrice": stop_loss},
          )
          self._exchange.create_order(
              symbol,
              "limit",
              close_side,
              quantity,
              take_profit,
          )
          logger.info("Live bracket orders placed for %s", symbol)
          return OrderResult(True, pos.order_id, "Live bracket TP/SL placed")
      except Exception as exc:
          logger.warning(
              "Exchange bracket orders failed (%s), using bot-managed exits",
              exc,
          )
          return OrderResult(
              True,
              pos.order_id,
              f"Bot-managed TP/SL (exchange error: {exc})",
          )


def create_broker(config: dict) -> CCXTBroker:
  exchange_cfg = config.get("exchange", {})
  risk_cfg = config.get("risk", {})
  mode = config.get("mode", "paper")

  api_key = os.getenv("EXCHANGE_API_KEY", "")
  api_secret = os.getenv("EXCHANGE_API_SECRET", "")

  sandbox = mode == "paper" or exchange_cfg.get("sandbox", True)

  return CCXTBroker(
      exchange_id=exchange_cfg.get("name", "binance"),
      api_key=api_key if mode == "live" else "",
      api_secret=api_secret if mode == "live" else "",
      sandbox=sandbox,
      initial_balance=risk_cfg.get("account_balance", 10000.0),
  )
