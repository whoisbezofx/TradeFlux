# TradeFlux — Quorum BTC Agent (Paper Mode)

An honest, runnable implementation of the "run 31 model paths, only fire when
28 agree" idea for short-horizon Bitcoin markets — plus the reality check the
sales pitch leaves out.

**No real funds are wired in. On purpose.** The agent trades a virtual $500
account against *real* live/historical BTC prices, so you can prove or
disprove the edge before risking a cent.

## Why paper-only

The "quorum" counts how many *simulated* paths agree. All 31 paths are drawn
from the same estimated drift/volatility, so a strong quorum measures the
model's confidence in itself — not the market. On a 5-minute horizon BTC is
close to a random walk, so this does not create a tradeable edge. Don't take
my word for it — run the backtest.

## Reality check (real Coinbase 5-min candles)

    python -m tradeflux.backtest

In a sample 29-hour window, win rates land around 50–53% (a coin flip) once
enough trades accumulate, and net P&L after fees is negative. The original
28/31 threshold fires almost never ("idle most days" — exactly as the pitch
admits). Windows that look green are a handful of coin-flips, i.e. noise.

## Live paper agent

    python -m tradeflux.bot --interval 300      # real live prices, virtual $500

Writes running state to `paper_state.json`. Run it for weeks; the equity curve
is your evidence.

## Legal note (Germany / EU)

5-minute yes/no price bets are **binary options**, which are **banned for EU
retail investors** (ESMA/BaFin, permanent since 2019). There is no licensed
German venue for that product — Polymarket included (no BaFin authorisation,
geoblocked). What *is* legal with real money: spot BTC on BaFin-/MiCA-regulated
platforms (Bison, Coinbase Germany, Bitpanda, Kraken). A licence does not turn
a coin flip into profit — it only changes whether you lose money legally.

## Layout

- `tradeflux/feed.py`     — real live BTC price feed (Coinbase public API)
- `tradeflux/engine.py`   — the 31-path quorum engine ("MiroFish", built honestly)
- `tradeflux/paper.py`    — paper account + fractional-Kelly sizing
- `tradeflux/bot.py`      — live paper-trading loop
- `tradeflux/backtest.py` — replay on real historical candles

This project is for education and honest evaluation. It is not financial advice.
