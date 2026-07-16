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
    return [c[4] for c in fetch_ohlc(granularity)]


def fetch_ohlc(granularity: int = 300) -> list[list[float]]:
    """Return real historical OHLC rows [time, low, high, open, close], oldest first."""
    url = CANDLES.format(g=granularity)
    req = urllib.request.Request(url, headers={"User-Agent": "tradeflux/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        rows = json.loads(r.read().decode())
    # each row: [time, low, high, open, close, volume]; API returns newest first
    rows.sort(key=lambda x: x[0])
    return [[float(v) for v in row[:5]] for row in rows]


def backtest_futures(ohlc: list[list[float]], leverage: float = 100.0,
                     warmup: int = 24, fee_frac: float = 0.0006,
                     starting: float = 500.0) -> dict:
    """Replay the quorum agent as leveraged futures, with a liquidation model.

    fee_frac is charged on notional (margin * leverage) — realistic taker fees.
    """
    engine = QuorumEngine(QuorumConfig(), seed=7)
    acct = PaperAccount(balance=starting, starting=starting, fee_frac=fee_frac)
    log_returns: list[float] = []

    for i in range(1, len(ohlc) - 1):
        prev_c, cur_c = ohlc[i - 1][4], ohlc[i][4]
        log_returns.append(math.log(cur_c / prev_c))
        if i < warmup:
            continue
        sig = engine.evaluate(log_returns)
        if not sig.fired:
            continue
        entry = ohlc[i][4]
        trade = acct.open_futures(sig.direction, sig.prob, entry, leverage)
        if trade is None:
            continue
        nxt = ohlc[i + 1]           # [time, low, high, open, close]
        acct.settle_futures(trade, low=nxt[1], high=nxt[2], close=nxt[4])
        if acct.balance < 5:
            break

    out = acct.stats()
    out["leverage"] = leverage
    out["candles"] = len(ohlc)
    return out


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
    ap.add_argument("--futures", action="store_true",
                    help="run the leveraged futures backtest with liquidation")
    ap.add_argument("--leverage", type=float, default=100.0)
    ap.add_argument("--starting", type=float, default=500.0)
    args = ap.parse_args()

    if args.futures:
        ohlc = fetch_ohlc(args.granularity)
        print(f"Loaded {len(ohlc)} real BTC candles @ {args.granularity}s | "
              f"{args.leverage:.0f}x leverage | start {args.starting:.0f}\n")
        result = backtest_futures(ohlc, leverage=args.leverage, starting=args.starting)
        print(json.dumps(result, indent=2))
        print("\nEvery liquidation = margin gone. At 100x a single ~1% adverse")
        print("move does it — routine for BTC. No edge + leverage = ruin.")
        return

    closes = fetch_candles(args.granularity)
    print(f"Loaded {len(closes)} real BTC candles @ {args.granularity}s\n")
    result = backtest(closes)
    print(json.dumps(result, indent=2))
    print("\nRead the win rate and net_pnl after fees. That number, on real")
    print("data, is the whole argument — not the story in the pitch.")


if __name__ == "__main__":
    main()
