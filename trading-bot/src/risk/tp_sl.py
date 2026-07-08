from __future__ import annotations

from src.models import Side


def calculate_tp_sl(
    entry: float,
    side: Side,
    atr: float,
    config: dict,
) -> tuple[float, float]:
    method = config.get("method", "atr")
    sl_mult = config.get("sl_atr_mult", 1.5)
    tp_mult = config.get("tp_atr_mult", 3.0)

    if side == Side.HOLD:
        return entry, entry

    if method == "atr":
        if side == Side.BUY:
            stop_loss = entry - atr * sl_mult
            take_profit = entry + atr * tp_mult
        else:
            stop_loss = entry + atr * sl_mult
            take_profit = entry - atr * tp_mult
        return stop_loss, take_profit

    risk = entry * 0.01
    if side == Side.BUY:
        return entry - risk, entry + risk * 2
    return entry + risk, entry - risk * 2


def calculate_position_size(
    account_balance: float,
    risk_per_trade_pct: float,
    entry: float,
    stop_loss: float,
) -> float:
    risk_amount = account_balance * (risk_per_trade_pct / 100)
    risk_per_unit = abs(entry - stop_loss)
    if risk_per_unit <= 0:
        return 0.0
    return risk_amount / risk_per_unit
