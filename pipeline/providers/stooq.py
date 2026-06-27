"""Stooq keyless EOD provider (PRD §6.1 fallback). Split-adjusted CSV, no API key.

Note: Stooq daily data is split-adjusted but dividend adjustment is best-effort;
treated as the fallback after Tiingo/Alpaca for that reason.
"""
from __future__ import annotations

import io
import time

import pandas as pd
import requests

from .base import PriceProvider, normalize_frame

_BASE = "https://stooq.com/q/d/l/"


def _stooq_symbol(sym: str) -> str:
    return sym.lower().replace(".", "-") + ".us"


class StooqProvider(PriceProvider):
    name = "stooq"

    def __init__(self, pause: float = 0.15, timeout: int = 20):
        self.pause = pause
        self.timeout = timeout

    def fetch(self, symbols, start, end):
        d1 = pd.Timestamp(start).strftime("%Y%m%d")
        d2 = pd.Timestamp(end).strftime("%Y%m%d")
        out: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            params = {"s": _stooq_symbol(sym), "d1": d1, "d2": d2, "i": "d"}
            try:
                r = requests.get(_BASE, params=params, timeout=self.timeout)
                r.raise_for_status()
                df = pd.read_csv(io.StringIO(r.text))
                if df.empty or "Close" not in df.columns:
                    continue
                df = df.rename(columns=str.lower).set_index("date")
                # Stooq has no separate adjusted column; use close for both.
                df["adj_close"] = df["close"]
                out[sym] = normalize_frame(df)
            except Exception:
                continue  # graceful degradation (PRD §8.4)
            time.sleep(self.pause)
        return out
