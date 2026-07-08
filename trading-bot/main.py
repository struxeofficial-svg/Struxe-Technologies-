#!/usr/bin/env python3
"""Multi-asset automated trading bot with candlestick, pullback, and TP/SL."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.bot.runner import TradingBot  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_run(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    if args.mode:
        config["mode"] = args.mode
    if args.symbol:
        config["symbols"] = [args.symbol]

    bot = TradingBot(config)
    interval = config.get("bot", {}).get("poll_interval_seconds", 30)

    logger.info(
        "Starting bot | mode=%s | symbols=%s | interval=%ds",
        config.get("mode"),
        config.get("symbols"),
        interval,
    )

    if args.once:
        signals = bot.run_once()
        for s in signals:
            print(
                f"{s.symbol}: {s.side.value} ({s.confidence:.0f}%) "
                f"entry={s.entry:.2f} SL={s.stop_loss:.2f} TP={s.take_profit:.2f}"
            )
        print("Status:", bot.status())
        return

    try:
        while True:
            bot.run_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("Final status:", bot.status())


def cmd_analyze(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    if args.symbol:
        config["symbols"] = [args.symbol]

    bot = TradingBot(config)
    for symbol in config["symbols"]:
        signal = bot.analyze(symbol)
        print(f"\n=== {symbol} ===")
        print(f"Side:       {signal.side.value}")
        print(f"Confidence: {signal.confidence:.1f}%")
        print(f"Entry:      {signal.entry:.4f}")
        print(f"Stop Loss:  {signal.stop_loss:.4f}")
        print(f"Take Profit:{signal.take_profit:.4f}")
        print(f"Reasons:    {', '.join(signal.reasons) or 'none'}")
        if signal.patterns:
            print("Patterns:")
            for p in signal.patterns:
                print(f"  - {p.name} ({p.direction.value}, strength={p.strength:.2f})")
        if signal.pullback:
            pb = signal.pullback
            print(
                f"Pullback:   detected={pb.detected} type={pb.pullback_type} "
                f"retrace={pb.retrace_pct:.1f}% trend={pb.trend}"
            )


def main() -> None:
    load_dotenv(ROOT / "config" / ".env")
    load_dotenv(ROOT / "config" / "secrets.env")

    parser = argparse.ArgumentParser(description="Automated multi-asset trading bot")
    parser.add_argument(
        "--config",
        default=str(ROOT / "config" / "settings.yaml"),
        help="Path to settings YAML",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the trading bot")
    run_p.add_argument("--once", action="store_true", help="Run one cycle and exit")
    run_p.add_argument("--mode", choices=["paper", "live"], help="Override mode")
    run_p.add_argument("--symbol", help="Trade a single symbol")
    run_p.set_defaults(func=cmd_run)

    analyze_p = sub.add_parser("analyze", help="Analyze without trading")
    analyze_p.add_argument("--symbol", help="Analyze a single symbol")
    analyze_p.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
