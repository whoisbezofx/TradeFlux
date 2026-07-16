"""Paper-trading account with Kelly sizing.

Real account logic, virtual money. Every trade, fill, fee and P&L update is
computed exactly as a live account would — the only thing missing is the wire
to your bank. Run it live for weeks; the equity curve is your evidence.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field


@dataclass
class Trade:
    ts: float
    direction: str        # UP / DOWN
    stake: float          # dollars risked
    entry_price: float    # BTC price at entry
    prob: float           # engine-implied probability
    settle_price: float = 0.0
    won: bool = False
    pnl: float = 0.0
    open: bool = True


@dataclass
class PaperAccount:
    balance: float = 500.0
    starting: float = 500.0
    # Binary payout: risk `stake`, win pays stake*payout, lose pays -stake.
    payout: float = 0.9          # ~0.9 net is realistic for even-odds after fees
    fee_frac: float = 0.0        # extra flat fee fraction on stake, if any
    kelly_fraction: float = 0.25  # fractional Kelly (full Kelly is a wipeout)
    max_stake_frac: float = 0.1   # never risk more than this share of balance
    trades: list[Trade] = field(default_factory=list)

    def kelly_stake(self, prob: float) -> float:
        """Fractional-Kelly stake for a binary bet at odds `payout`."""
        b = self.payout
        p = prob
        q = 1.0 - p
        edge = (b * p - q) / b        # full Kelly fraction of bankroll
        if edge <= 0:
            return 0.0
        frac = min(edge * self.kelly_fraction, self.max_stake_frac)
        return round(self.balance * frac, 2)

    def open_trade(self, direction: str, prob: float, entry_price: float) -> Trade | None:
        stake = self.kelly_stake(prob)
        if stake <= 0 or stake > self.balance:
            return None
        t = Trade(ts=time.time(), direction=direction, stake=stake,
                  entry_price=entry_price, prob=prob)
        self.trades.append(t)
        return t

    def settle(self, trade: Trade, settle_price: float) -> None:
        up = settle_price > trade.entry_price
        won = (trade.direction == "UP" and up) or (trade.direction == "DOWN" and not up)
        fee = trade.stake * self.fee_frac
        trade.settle_price = settle_price
        trade.won = won
        trade.pnl = (trade.stake * self.payout if won else -trade.stake) - fee
        trade.open = False
        self.balance = round(self.balance + trade.pnl, 2)

    # --- reporting ------------------------------------------------------
    def closed(self) -> list[Trade]:
        return [t for t in self.trades if not t.open]

    def stats(self) -> dict:
        closed = self.closed()
        wins = [t for t in closed if t.won]
        pnl = round(self.balance - self.starting, 2)
        return {
            "balance": self.balance,
            "starting": self.starting,
            "net_pnl": pnl,
            "return_pct": round(100 * pnl / self.starting, 2) if self.starting else 0.0,
            "trades": len(closed),
            "wins": len(wins),
            "win_rate_pct": round(100 * len(wins) / len(closed), 1) if closed else 0.0,
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump({"account": {k: v for k, v in asdict(self).items() if k != "trades"},
                       "stats": self.stats(),
                       "trades": [asdict(t) for t in self.trades]}, f, indent=2)
