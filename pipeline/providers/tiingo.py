"""Tiingo EOD provider (PRD §6.1 primary). High-quality adjusted EOD.

Requires env var ``TIINGO_TOKEN`` (stored as a GitHub Actions secret, PRD §8.5).
"""
from __future__ import annotations

import os
import time

import pandas as pd
import requests

from .base import PriceProvider, normalize_frame


class TiingoProvider(PriceProvider):
    name = "tiingo"

    def __init__(self, token: str | None = None, pause: float = 0.1, timeout: int = 20):
        self.token = token or os.environ.get("TIINGO_TOKEN")
        self.pause = pause
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.token)

    def fetch(self, symbols, start, end):
        s = pd.Timestamp(start).strftime("%Y-%m-%d")
        e = pd.Timestamp(end).strftime("%Y-%m-%d")
        headers = {"Content-Type": "application/json"}
        out: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            url = f"https://api.tiingo.com/tiingo/daily/{sym}/prices"
            params = {"startDate": s, "endDate": e, "format": "json", "token": self.token}
            try:
                r = requests.get(url, params=params, headers=headers, timeout=self.timeout)
                r.raise_for_status()
                rows = r.json()
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                df = df.set_index("date")
                norm = pd.DataFrame(
                    {
                        "open": df.get("adjOpen", df["open"]),
                        "high": df.get("adjHigh", df["high"]),
                        "low": df.get("adjLow", df["low"]),
                        "close": df["close"],
                        "adj_close": df.get("adjClose", df["close"]),
                        "volume": df.get("adjVolume", df["volume"]),
                    }
                )
                out[sym] = normalize_frame(norm)
            except Exception:
                continue  # graceful degradation
            time.sleep(self.pause)
        return out
