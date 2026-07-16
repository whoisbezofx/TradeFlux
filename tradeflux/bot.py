"""Live paper-trading loop.

Runs the real quorum agent against real live BTC prices, keeping a virtual
$500 account. Each round:
  1. read the real spot price
  2. wait one interval (the '5-minute market'), collecting the outcome
  3. run the 31-path quorum on the recent real returns
  4. if it fires, open a paper trade and settle it against the real move
  5. print honest running stats

Nothing here touches real funds. That is deliberate: prove the edge on live
data first. Run with:  python -m tradeflux.bot --interval 300
"""
from __future__ import annotations

import argparse
import time

from .feed import fetch_spot, PriceHistory
from .engine import QuorumEngine, QuorumConfig
from .paper import PaperAccount


def run(interval: float, rounds: int, out: str) -> None:
    hist = PriceHistory(maxlen=max(64, int(4 * 3600 / interval)))
    engine = QuorumEngine(QuorumConfig())
    acct = PaperAccount()

    print(f"TradeFlux paper agent — live BTC, virtual ${acct.balance:.2f}")
    print(f"interval={interval:.0f}s  quorum={engine.cfg.fire_threshold}/"
          f"{engine.cfg.n_paths}  (no real funds at risk)\n")

    round_i = 0
    while rounds <= 0 or round_i < rounds:
        round_i += 1
        try:
            tick = fetch_spot()
        except Exception as e:  # network hiccup — skip, don't crash
            print(f"[{round_i}] feed error: {e}; retrying next round")
            time.sleep(interval)
            continue
        hist.add(tick)

        sig = engine.evaluate(hist.log_returns())
        entry_price = tick.price

        trade = None
        if sig.fired:
            trade = acct.open_trade(sig.direction, sig.prob, entry_price)

        # wait one market interval to observe the real outcome
        time.sleep(interval)

        if trade is not None:
            try:
                settle = fetch_spot().price
            except Exception:
                settle = entry_price  # neutral settle on feed failure
            acct.settle(trade, settle)
            s = acct.stats()
            print(f"[{round_i}] {sig.direction} votes={max(sig.up_votes, sig.down_votes)}"
                  f"/{sig.n_paths} stake=${trade.stake:.2f} -> "
                  f"{'WIN ' if trade.won else 'LOSS'} pnl=${trade.pnl:+.2f} | "
                  f"bal=${s['balance']:.2f} ({s['return_pct']:+.1f}%) "
                  f"wr={s['win_rate_pct']}% n={s['trades']}")
        else:
            reason = "no quorum" if not sig.fired else "no stake"
            print(f"[{round_i}] FLAT ({reason}) "
                  f"up={sig.up_votes} down={sig.down_votes} "
                  f"px=${entry_price:,.0f}")

        acct.save(out)

    print("\nFinal:", acct.stats())


def main() -> None:
    ap = argparse.ArgumentParser(description="TradeFlux live paper agent")
    ap.add_argument("--interval", type=float, default=300.0,
                    help="market interval in seconds (default 300 = 5 min)")
    ap.add_argument("--rounds", type=int, default=0,
                    help="number of rounds (0 = run forever)")
    ap.add_argument("--out", default="paper_state.json",
                    help="where to write account state")
    args = ap.parse_args()
    run(args.interval, args.rounds, args.out)


if __name__ == "__main__":
    main()
