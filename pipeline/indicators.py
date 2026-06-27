"""Technical indicators (PRD §5–§6). All operate on adjusted prices."""
from __future__ import annotations

import numpy as np
import pandas as pd


def adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Scale OHLC by the adjustment factor (adj_close/close) so every series is
    adjusted-consistent (PRD §6.2). Keeps raw close as ``close_raw``."""
    df = df.copy()
    factor = (df["adj_close"] / df["close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    out = pd.DataFrame(index=df.index)
    out["open"] = df["open"] * factor
    out["high"] = df["high"] * factor
    out["low"] = df["low"] * factor
    out["close"] = df["adj_close"]
    out["close_raw"] = df["close"]
    out["volume"] = df["volume"]
    return out


def log_return(close: pd.Series, h: int) -> pd.Series:
    return np.log(close / close.shift(h))


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    # Wilder smoothing
    return tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def rolling_max(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=1).max()


def pct(a: float, b: float) -> float:
    """(a/b - 1) * 100, NaN-safe."""
    if b in (0, None) or pd.isna(a) or pd.isna(b):
        return float("nan")
    return (a / b - 1.0) * 100.0


def rank_to_percentile(values: pd.Series) -> pd.Series:
    """Map cross-sectional values to an IBD-style 1–99 rank (PRD §5.3).
    Highest value -> 99, lowest -> 1. NaNs map to NaN."""
    valid = values.dropna()
    n = len(valid)
    if n == 0:
        return pd.Series(index=values.index, dtype="float")
    if n == 1:
        out = pd.Series(index=values.index, dtype="float")
        out[valid.index[0]] = 99.0
        return out
    ordinal = valid.rank(method="average")           # 1..n, ties averaged
    pctile = (ordinal - 1) / (n - 1)                  # 0..1
    mapped = (1 + 98 * pctile).round()
    return mapped.reindex(values.index)


def regression_slope(series: pd.Series) -> float:
    """Slope per step of a least-squares line through the series (PRD §5.3)."""
    y = series.dropna().to_numpy(dtype=float)
    if len(y) < 2:
        return float("nan")
    x = np.arange(len(y), dtype=float)
    slope = np.polyfit(x, y, 1)[0]
    return float(slope)
