"""The quorum engine (the 'MiroFish' idea, built honestly).

The pitch: run 31 model paths, only fire when >= 28 agree; kill below 26.

This implements exactly that. It estimates drift (mu) and volatility (sigma)
from the recent real return history, then runs N Monte Carlo paths of a
geometric Brownian motion over the market's horizon. Each path 'votes' on
whether BTC ends higher or lower. If enough paths agree, the engine fires.

IMPORTANT — read this, it is the whole point:
Counting how many *simulated* paths agree measures how confident THIS MODEL
is in itself. It does not measure the market. All 31 paths are drawn from the
same estimated mu/sigma, so a strong quorum mostly means recent drift was
large relative to noise — which on a 5-minute horizon is itself mostly noise.
The paper-trading account exists so you can watch, on live data, whether this
'consensus' actually turns into money after fees. Let the numbers judge it.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass


@dataclass
class Signal:
    direction: str        # "UP", "DOWN", or "FLAT"
    up_votes: int
    down_votes: int
    n_paths: int
    prob: float           # implied probability of the chosen direction (votes / n)
    fired: bool           # True if it passed the quorum threshold
    mu: float
    sigma: float


@dataclass
class QuorumConfig:
    n_paths: int = 31           # number of Monte Carlo model paths
    fire_threshold: int = 28    # need >= this many agreeing to fire
    kill_threshold: int = 26    # below this many, always kill (no trade)
    horizon_steps: int = 1      # steps ahead to simulate (1 = one market interval)
    min_history: int = 20       # need at least this many returns to run


class QuorumEngine:
    def __init__(self, cfg: QuorumConfig | None = None, seed: int | None = None):
        self.cfg = cfg or QuorumConfig()
        self._rng = random.Random(seed)

    def evaluate(self, log_returns: list[float]) -> Signal:
        cfg = self.cfg
        if len(log_returns) < cfg.min_history:
            return Signal("FLAT", 0, 0, cfg.n_paths, 0.0, False, 0.0, 0.0)

        mu = statistics.fmean(log_returns)
        sigma = statistics.pstdev(log_returns) or 1e-9

        up = 0
        for _ in range(cfg.n_paths):
            logp = 0.0
            for _ in range(cfg.horizon_steps):
                logp += self._rng.gauss(mu, sigma)
            if logp > 0:
                up += 1
        down = cfg.n_paths - up

        winner = "UP" if up >= down else "DOWN"
        votes = max(up, down)
        prob = votes / cfg.n_paths

        fired = votes >= cfg.fire_threshold and votes >= cfg.kill_threshold
        direction = winner if fired else "FLAT"

        return Signal(direction, up, down, cfg.n_paths, prob, fired, mu, sigma)
