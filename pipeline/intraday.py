"""Intraday overlay (live prices on cached EOD history).

During market hours the intraday job makes ONE batched Tiingo IEX request for the
latest price of every symbol, then overlays those prices as today's (provisional)
bar on top of the cached EOD history. The full RSS / breadth / classification
stack is then recomputed exactly as for EOD — the only difference is today's bar
is a live, unsettled print.
"""
from __future__ import annotations

import pandas as pd
import requests

_IEX_URL = "https://api.tiingo.com/iex/"


def fetch_live_tiingo(symbols, token: str, timeout: int = 20, batch: int = 90) -> dict[str, float]:
    """Latest price per symbol via the Tiingo IEX endpoint (batched, ~1 call)."""
    syms = list(symbols)
    out: dict[str, float] = {}
    for i in range(0, len(syms), batch):
        chunk = syms[i:i + batch]
        params = {"tickers": ",".join(chunk), "token": token}
        try:
            r = requests.get(_IEX_URL, params=params, timeout=timeout)
            r.raise_for_status()
            for row in r.json():
                t = (row.get("ticker") or "").upper()
                px = row.get("tngoLast") or row.get("last") or row.get("prevClose")
                if t and px is not None:
                    out[t] = float(px)
        except Exception:
            continue  # graceful degradation; other batches still count
    return out


def overlay_live(frames: dict[str, pd.DataFrame], live: dict[str, float], as_of) -> dict[str, pd.DataFrame]:
    """Set/append today's bar from the live price, preserving adjusted continuity.

    Today's adj_close = live_price * (last_adj_close / last_close), so the live
    point sits on the same adjusted scale as the historical series (no split/div
    discontinuity in the 5/20/50-day returns).
    """
    as_of = pd.Timestamp(as_of).normalize()
    upper = {k.upper(): v for k, v in live.items()}
    merged: dict[str, pd.DataFrame] = {}
    for sym, df in frames.items():
        px = upper.get(sym.upper())
        if px is None or df is None or df.empty:
            merged[sym] = df
            continue
        df = df.copy()
        last_close = df["close"].iloc[-1]
        factor = (df["adj_close"].iloc[-1] / last_close) if last_close else 1.0
        adj_px = px * factor
        if df.index[-1].normalize() == as_of:                 # update today's bar
            i = df.index[-1]
            df.at[i, "close"] = px
            df.at[i, "adj_close"] = adj_px
            df.at[i, "high"] = max(df.at[i, "high"], px)
            df.at[i, "low"] = min(df.at[i, "low"], px)
        else:                                                  # append a fresh bar
            row = pd.DataFrame(
                {"open": px, "high": px, "low": px, "close": px,
                 "adj_close": adj_px, "volume": 0.0},
                index=[as_of],
            )
            df = pd.concat([df, row])
        merged[sym] = df
    return merged
