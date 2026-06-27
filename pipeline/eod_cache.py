"""EOD history cache (intraday support).

The daily job writes the full trailing OHLCV window here; the intraday job loads
it instead of re-pulling a year of history every 15 minutes (which would blow the
free Tiingo rate limit). Stored as gzipped JSON on the `data` branch.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = ROOT / "data" / "eod_cache.json.gz"
_COLS = ["open", "high", "low", "close", "adj_close", "volume"]


def save_cache(prices: dict[str, pd.DataFrame], path: Path = DEFAULT_CACHE) -> Path:
    obj = {}
    for sym, df in prices.items():
        if df is None or df.empty:
            continue
        obj[sym] = {"index": [d.strftime("%Y-%m-%d") for d in df.index],
                    **{c: df[c].astype(float).round(6).tolist() for c in _COLS}}
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path


def load_cache(path: Path = DEFAULT_CACHE) -> dict[str, pd.DataFrame]:
    path = Path(path)
    if not path.exists():
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        obj = json.load(fh)
    out = {}
    for sym, d in obj.items():
        idx = pd.to_datetime(d["index"])
        out[sym] = pd.DataFrame({c: d[c] for c in _COLS}, index=idx)
    return out
