"""The headline correctness test: the v2.1 RSS must NOT invert in down markets.

This is the exact failure mode that disqualified v2.0 (ratio of returns). With
constant log-drift prices, R_h(x) = slope_x * h, so for the corrected excess-return
formula sign(RSS_x) == sign(slope_x - slope_SPY) regardless of the market's sign.
"""
import numpy as np
import pandas as pd

from pipeline.compute import rss_frame
from pipeline.config import load_config
from pipeline.indicators import rank_to_percentile

CFG = load_config()


def _series(slope: float, n: int = 80, p0: float = 100.0) -> pd.Series:
    t = np.arange(n)
    return pd.Series(p0 * np.exp(slope * t), index=pd.bdate_range("2025-01-01", periods=n))


def test_rss_does_not_invert_in_down_market():
    # SPY falling; A rises (outperforms), B falls harder (underperforms), C matches SPY.
    spy = _series(-0.002)        # down market
    a = _series(+0.001)          # UP while market is DOWN — the v2.0 killer case
    b = _series(-0.004)          # falls twice as fast as SPY
    c = _series(-0.002)          # exactly matches SPY
    df = pd.concat({"SPY": spy, "XLA": a, "XLB": b, "XLC": c}, axis=1)

    rss = rss_frame(df, ["XLA", "XLB", "XLC"], "SPY", CFG).iloc[-1]

    # Corrected behavior: the genuine outperformer scores POSITIVE even though it
    # and the market are... it rose while SPY fell, so it MUST be positive.
    assert rss["XLA"] > 0, "asset up while SPY down must score positive (v2.0 inverted this)"
    assert rss["XLB"] < 0, "asset falling faster than SPY must score negative"
    assert abs(rss["XLC"]) < 1e-9, "asset matching SPY must score ~0 (natural zero)"
    # Ordering is monotonic in true relative performance.
    assert rss["XLA"] > rss["XLC"] > rss["XLB"]


def test_rss_has_natural_zero_and_is_finite():
    flat = _series(0.0)
    df = pd.concat({"SPY": flat, "X": flat}, axis=1)
    rss = rss_frame(df, ["X"], "SPY", CFG).iloc[-1]
    assert abs(rss["X"]) < 1e-9
    assert np.isfinite(rss["X"])


def test_rss_never_divides_by_zero_when_spy_flat():
    # SPY perfectly flat (the v2.0 divide-by-zero / explosion case) must stay finite.
    spy = _series(0.0)
    up = _series(0.001)
    df = pd.concat({"SPY": spy, "X": up}, axis=1)
    rss = rss_frame(df, ["X"], "SPY", CFG).iloc[-1]
    assert np.isfinite(rss["X"]) and rss["X"] > 0


def test_rank_maps_best_to_99_worst_to_1():
    vals = pd.Series({"a": 0.5, "b": 0.4, "c": 0.3, "d": 0.2, "e": 0.1})
    r = rank_to_percentile(vals)
    assert r["a"] == 99
    assert r["e"] == 1
    assert r["a"] > r["b"] > r["c"] > r["d"] > r["e"]
