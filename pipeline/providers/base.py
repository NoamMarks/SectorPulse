"""Provider interface and the normalized OHLCV contract (PRD §6.1).

Every provider returns ``dict[symbol -> DataFrame]`` where each DataFrame has an
ascending, tz-naive ``DatetimeIndex`` and exactly these columns:

    open, high, low, close, adj_close, volume

``close`` is the raw close; ``adj_close`` is split/dividend adjusted (PRD §6.2).
All downstream math uses ``adj_close`` (and OHLC scaled to the adjustment factor).
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


class PriceProvider:
    """Base class. Subclasses implement :meth:`fetch` and optionally :meth:`available`."""

    name = "base"

    def available(self) -> bool:
        """Return True if this provider can run (deps present, creds set)."""
        return True

    def fetch(self, symbols, start, end):  # -> dict[str, pd.DataFrame]
        raise NotImplementedError


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a raw provider frame into the normalized contract.

    Missing ``adj_close`` falls back to ``close``. Rows with no close are dropped.
    """
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    if "adj_close" not in df.columns:
        df["adj_close"] = df.get("close")
    if "close" not in df.columns:
        df["close"] = df["adj_close"]
    for col in ("open", "high", "low"):
        if col not in df.columns:
            df[col] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df[REQUIRED_COLUMNS]
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    df.index = idx
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["close", "adj_close"])
