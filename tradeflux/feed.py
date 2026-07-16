"""Live BTC price feed.

Pulls the real spot price from Coinbase's public API. No key required.
This is the *real* data source — the same prices the market moves on.
"""
from __future__ import annotations

import time
import urllib.request
import json
from collections import deque
from dataclasses import dataclass


COINBASE_SPOT = "https://api.coinbase.com/v2/prices/BTC-USD/spot"


@dataclass
class Tick:
    ts: float          # unix seconds
    price: float       # USD


def fetch_spot(timeout: float = 10.0) -> Tick:
    """Fetch the current real BTC/USD spot price."""
    req = urllib.request.Request(COINBASE_SPOT, headers={"User-Agent": "tradeflux/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.loads(r.read().decode())
    return Tick(ts=time.time(), price=float(payload["data"]["amount"]))


class PriceHistory:
    """Rolling window of recent ticks, used to estimate drift/volatility."""

    def __init__(self, maxlen: int = 240):
        self._ticks: deque[Tick] = deque(maxlen=maxlen)

    def add(self, tick: Tick) -> None:
        self._ticks.append(tick)

    def __len__(self) -> int:
        return len(self._ticks)

    def prices(self) -> list[float]:
        return [t.price for t in self._ticks]

    def log_returns(self) -> list[float]:
        import math
        p = self.prices()
        return [math.log(p[i] / p[i - 1]) for i in range(1, len(p)) if p[i - 1] > 0]

    def last(self) -> Tick | None:
        return self._ticks[-1] if self._ticks else None
