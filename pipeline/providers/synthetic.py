"""Deterministic synthetic market data (PRD §6.1, default for offline/CI).

Generates reproducible, correlated OHLCV series so the full pipeline — regime,
RSS, breadth, classification — produces a realistic, varied ``latest.json`` with
no network or API keys. Seeded entirely from the symbol string, so output is
identical on every run (important for CI smoke tests).

Model: a common market factor (SPY) drives a one-factor structure. Each sector
ETF = beta*market + sector-alpha + idiosyncratic; each stock = beta*its-sector +
stock-alpha + idiosyncratic. Distinct deterministic alphas create a spread of
leaders and laggards; idiosyncratic stock noise creates within-sector dispersion
(varied 52w-high distance, SMA position, ATR contraction).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .base import PriceProvider, normalize_frame


def _seed(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)


def _unit(symbol: str, salt: str) -> float:
    """Deterministic float in [0, 1) from a symbol + salt."""
    h = hashlib.sha256(f"{symbol}:{salt}".encode()).hexdigest()[:8]
    return int(h, 16) / 0xFFFFFFFF


class SyntheticProvider(PriceProvider):
    name = "synthetic"

    def __init__(self, benchmark: str = "SPY", sector_of: dict | None = None):
        self.benchmark = benchmark
        # maps stock ticker -> its sector ETF ticker, and ETF -> itself
        self.sector_of = sector_of or {}

    def fetch(self, symbols, start, end):
        start = pd.Timestamp(start).tz_localize(None)
        end = pd.Timestamp(end).tz_localize(None)
        dates = pd.bdate_range(start=start, end=end)
        n = len(dates)
        if n < 60:
            raise ValueError("synthetic window too short")

        # --- common market factor (SPY) ---
        rng_m = np.random.default_rng(_seed(self.benchmark))
        mkt_ret = rng_m.normal(0.0004, 0.010, n)  # mild uptrend so regime can be risk_on

        cache: dict[str, np.ndarray] = {self.benchmark: mkt_ret}

        out: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            ret = self._returns_for(sym, mkt_ret, cache, n)
            out[sym] = self._frame(sym, ret, dates)
        return out

    def _returns_for(self, sym, mkt_ret, cache, n):
        if sym in cache:
            base = cache[sym]
            if sym == self.benchmark:
                return base
        rng = np.random.default_rng(_seed(sym))
        if sym == self.benchmark:
            return mkt_ret
        parent = self.sector_of.get(sym)
        if parent and parent != sym and parent in cache:
            factor = cache[parent]
            beta = 0.7 + 0.7 * _unit(sym, "beta")          # 0.7..1.4
            alpha = (_unit(sym, "alpha") - 0.45) * 0.0016    # ~ -0.0007..+0.0009 /day
            idio = rng.normal(0.0, 0.015, n)
        else:
            # a sector ETF (or unknown): driven by the market factor
            factor = mkt_ret
            beta = 0.8 + 0.4 * _unit(sym, "beta")            # 0.8..1.2
            alpha = (_unit(sym, "alpha") - 0.42) * 0.0022    # spread of sector leaders/laggards
            idio = rng.normal(0.0, 0.008, n)
        ret = beta * factor + alpha + idio
        # Deterministic recent price shapes so the demo fixture exercises every
        # classification path (PRD §5.6). Pure function of the ticker.
        if parent and parent != sym:
            u = _unit(sym, "shape")
            if u > 0.72:                 # ~28%: pullback then a flat low-vol base -> SETUP
                ret = ret.copy()
                ret[-45:-35] += -0.008   # ~8% pullback off the highs (clears the 5% leader band)
                ret[-35:] = idio[-35:] * 0.10   # long flat base: SMA50 converges tightly, ATR contracts
            elif u > 0.52:               # ~20%: recent volatility contraction
                ret = ret.copy()
                ret[-18:] *= 0.30
        cache[sym] = ret
        return ret

    def _frame(self, sym, ret, dates):
        n = len(dates)
        rng = np.random.default_rng(_seed(sym) ^ 0x5EED)
        p0 = 20.0 + 380.0 * _unit(sym, "p0")                 # 20..400 start price
        close = p0 * np.exp(np.cumsum(ret))
        # intraday range proportional to that day's move magnitude
        rng_frac = 0.004 + 0.012 * np.abs(rng.normal(0, 1, n))
        high = close * (1 + rng_frac)
        low = close * (1 - rng_frac)
        prev = np.concatenate([[close[0]], close[:-1]])
        openp = prev * (1 + rng.normal(0, 0.003, n))
        high = np.maximum.reduce([high, close, openp])
        low = np.minimum.reduce([low, close, openp])
        # volume: base level + slow drift + occasional spikes (lets breakout-volume trigger)
        base_vol = 5e5 + 5e7 * _unit(sym, "vol")
        drift = np.linspace(1.0, 1.0 + (_unit(sym, "vdrift") - 0.5) * 0.4, n)
        spikes = 1.0 + (rng.random(n) > 0.92) * rng.uniform(0.5, 1.8, n)
        volume = (base_vol * drift * spikes * (0.8 + 0.4 * rng.random(n))).round()
        # Deterministic final-bar volume surge for ~half of symbols, so near-high
        # sectors can trigger the volume-confirmed breakout path (PRD §5.5).
        if _unit(sym, "surge") > 0.5:
            volume[-1] *= 1.9
        df = pd.DataFrame(
            {
                "open": openp,
                "high": high,
                "low": low,
                "close": close,       # synthetic: already-adjusted, factor = 1
                "adj_close": close,
                "volume": volume,
            },
            index=dates,
        )
        return normalize_frame(df)
