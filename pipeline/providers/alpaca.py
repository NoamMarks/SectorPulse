"""Alpaca Market Data EOD provider (PRD §6.1). Official, adjusted daily bars.

Requires ``APCA_API_KEY_ID`` / ``APCA_API_SECRET_KEY`` (GitHub Actions secrets).
Free tier serves the IEX feed; adjustment=all gives split/dividend-adjusted bars.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

from .base import PriceProvider, normalize_frame

_URL = "https://data.alpaca.markets/v2/stocks/bars"


def _alpaca_symbol(sym: str) -> str:
    return sym.replace("-", ".")  # BRK-B -> BRK.B


class AlpacaProvider(PriceProvider):
    name = "alpaca"

    def __init__(self, key_id=None, secret=None, feed="iex", timeout=25):
        self.key_id = key_id or os.environ.get("APCA_API_KEY_ID")
        self.secret = secret or os.environ.get("APCA_API_SECRET_KEY")
        self.feed = feed
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.key_id and self.secret)

    def fetch(self, symbols, start, end):
        headers = {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret,
        }
        sym_map = {_alpaca_symbol(s): s for s in symbols}
        frames: dict[str, list] = {s: [] for s in symbols}
        params = {
            "symbols": ",".join(sym_map.keys()),
            "timeframe": "1Day",
            "start": pd.Timestamp(start).strftime("%Y-%m-%d"),
            "end": pd.Timestamp(end).strftime("%Y-%m-%d"),
            "adjustment": "all",
            "feed": self.feed,
            "limit": 10000,
        }
        page_token = None
        try:
            while True:
                if page_token:
                    params["page_token"] = page_token
                r = requests.get(_URL, params=params, headers=headers, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                for asym, bars in (data.get("bars") or {}).items():
                    orig = sym_map.get(asym, asym)
                    frames.setdefault(orig, []).extend(bars)
                page_token = data.get("next_page_token")
                if not page_token:
                    break
        except Exception:
            pass  # graceful degradation; return whatever paged in

        out: dict[str, pd.DataFrame] = {}
        for sym, bars in frames.items():
            if not bars:
                continue
            df = pd.DataFrame(bars)
            df["date"] = pd.to_datetime(df["t"]).dt.tz_localize(None)
            df = df.set_index("date")
            norm = pd.DataFrame(
                {
                    "open": df["o"], "high": df["h"], "low": df["l"],
                    "close": df["c"], "adj_close": df["c"], "volume": df["v"],
                }
            )
            out[sym] = normalize_frame(norm)
        return out
