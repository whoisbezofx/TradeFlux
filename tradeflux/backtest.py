"""Backtest the quorum agent on real historical 5-minute BTC candles.

This is the fast, honest reality check. It pulls real historical candles and
replays the exact live logic over them, so you see hundreds of rounds in
seconds instead of waiting days. Run with:  python -m tradeflux.backtest

Uses the same engine and the same paper account as the live bot — the only
difference is the price source (recorded history vs. live feed).
"""
from __future__ import annotations

import argparse
import json
import urllib.request
import math

from .engine import QuorumEngine, QuorumConfig
from .paper import PaperAccount

CANDLES = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity={g}"


def fetch_candles(granularity: int = 300) -> list[float]:
    """Return real historical close prices, oldest first."""
    url = CANDLES.format(g=granularity)
    req = urllib.request.Request(url, headers={"User-Agent": "tradeflux/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        rows = json.loads(r.read().decode())
    # each row: [time, low, high, open, close, volume]; API returns newest first
    rows.sort(key=lambda x: x[0])
    return [float(row[4]) for row in rows]


def backtest(closes: list[float], warmup: int = 24) -> dict:
    engine = QuorumEngine(QuorumConfig(), seed=7)  # fixed seed = reproducible
    acct = PaperAccount()
    log_returns: list[float] = []

    fired = 0
    for i in range(1, len(closes) - 1):
        log_returns.append(math.log(closes[i] / closes[i - 1]))
        if i < warmup:
            continue
        sig = engine.evaluate(log_returns)
        if not sig.fired:
            continue
        fired += 1
        trade = acct.open_trade(sig.direction, sig.prob, closes[i])
        if trade is not None:
            acct.settle(trade, closes[i + 1])  # settle on the very next candle

    out = acct.stats()
    out["candles"] = len(closes)
    out["signals_fired"] = fired
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="TradeFlux backtest on real candles")
    ap.add_argument("--granularity", type=int, default=300)
    args = ap.parse_args()
    closes = fetch_candles(args.granularity)
    print(f"Loaded {len(closes)} real BTC candles @ {args.granularity}s\n")
    result = backtest(closes)
    print(json.dumps(result, indent=2))
    print("\nRead the win rate and net_pnl after fees. That number, on real")
    print("data, is the whole argument — not the story in the pitch.")


if __name__ == "__main__":
    main()
