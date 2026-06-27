"""Compute core (PRD §5). Turns adjusted OHLCV into the dashboard payload pieces.

Pipeline order (PRD §5.0): regime gate -> corrected RSS + rank/slope/persist ->
MAP breadth -> volume confirmation -> Leader/Setup classification.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import indicators as ind


# --------------------------------------------------------------------------- #
# Per-asset latest-bar metrics
# --------------------------------------------------------------------------- #
def asset_metrics(adj: pd.DataFrame, cfg, D: pd.Timestamp) -> dict:
    """Latest scalar metrics for one adjusted-OHLC frame, as of date D."""
    s = adj.loc[:D]
    if len(s) == 0:
        return {}
    close = s["close"]
    last = close.iloc[-1]
    sma50 = ind.sma(close, 50).iloc[-1]
    sma200 = ind.sma(close, 200).iloc[-1] if len(close) >= 200 else float("nan")
    atr14 = ind.wilder_atr(s["high"], s["low"], close, 14)
    atr_last = atr14.iloc[-1]
    atr_med = atr14.tail(252).median()
    high52 = close.tail(252).max()
    vol = s["volume"].iloc[-1]
    vol_sma50 = s["volume"].rolling(50, min_periods=10).mean().iloc[-1]
    dollar_vol = (s["close_raw"] * s["volume"]).tail(20).median()
    return {
        "close": float(last),
        "close_raw": float(s["close_raw"].iloc[-1]),
        "sma50": float(sma50) if pd.notna(sma50) else float("nan"),
        "sma200": float(sma200) if pd.notna(sma200) else float("nan"),
        "above_sma50": bool(last > sma50) if pd.notna(sma50) else False,
        "above_sma200": bool(last > sma200) if pd.notna(sma200) else False,
        "atr_14": float(atr_last) if pd.notna(atr_last) else float("nan"),
        "atr_ratio": float(atr_last / atr_med) if pd.notna(atr_last) and atr_med else float("nan"),
        "pct_from_52w_high": ind.pct(last, high52),
        "pct_from_sma50": ind.pct(last, sma50),
        "volume": float(vol),
        "vol_sma50": float(vol_sma50) if pd.notna(vol_sma50) else float("nan"),
        "dollar_volume": float(dollar_vol) if pd.notna(dollar_vol) else 0.0,
        "ret": {h: float(ind.log_return(close, h).iloc[-1]) if len(close) > h else float("nan")
                for h in cfg.horizons},
    }


# --------------------------------------------------------------------------- #
# Relative strength (PRD §5.2 / §5.3)
# --------------------------------------------------------------------------- #
def rss_frame(adj_close: pd.DataFrame, sectors: list[str], benchmark: str, cfg) -> pd.DataFrame:
    """Excess-log-return RSS for every sector across all dates (vectorized).

    RSS = sum_h w_h * (R_h(asset) - R_h(SPY)),  R_h(x) = ln(P_t / P_{t-h}).
    Sign-stable, natural zero, no division by a return.
    """
    out = pd.DataFrame(0.0, index=adj_close.index, columns=sectors)
    have = pd.Series(False, index=adj_close.index)
    for h in cfg.horizons:
        r = np.log(adj_close / adj_close.shift(h))
        excess = r[sectors].sub(r[benchmark], axis=0)
        out = out.add(cfg.weight(h) * excess, fill_value=0.0)
        have = have | excess.notna().any(axis=1)
    return out.where(have)


def _row_at(frame: pd.DataFrame, D: pd.Timestamp):
    idx = frame.index
    if D in idx:
        return D
    prior = idx[idx <= D]
    return prior[-1] if len(prior) else idx[-1]


# --------------------------------------------------------------------------- #
# Classification (PRD §5.6)
# --------------------------------------------------------------------------- #
def classify(m: dict, regime_risk_on: bool, cfg) -> str:
    band = cfg["breakout_band"]
    leader = (
        m.get("pct_from_52w_high", float("nan")) >= -band
        and m.get("above_sma50") and m.get("above_sma200") and regime_risk_on
    )
    if leader:
        return "LEADER"
    pfs = m.get("pct_from_sma50", float("nan"))
    setup = (
        pd.notna(pfs) and abs(pfs) <= cfg["setup_sma50_band"]
        and m.get("atr_ratio", float("inf")) <= cfg["setup_atr_ratio_max"]
        and m.get("above_sma200")
    )
    return "SETUP" if setup else "OTHER"


def regime_label(spy_above: bool, pct_above: float, cfg) -> str:
    """Market-regime gate (PRD §5.1). Pure function for testability."""
    cond_breadth = pct_above >= cfg["regime_breadth_min"]
    if spy_above and cond_breadth:
        return "risk_on"
    if not spy_above and not cond_breadth:
        return "risk_off"
    return "neutral"


def _udvr(adj: pd.DataFrame, D: pd.Timestamp, window: int) -> float:
    s = adj.loc[:D].tail(window + 1)
    if len(s) < 3:
        return float("nan")
    chg = s["close"].diff()
    up = s["volume"][chg > 0].sum()
    down = s["volume"][chg < 0].sum()
    return float(up / down) if down > 0 else float("nan")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def compute(prices: dict[str, pd.DataFrame], cfg, prev_state: dict | None, D) -> dict:
    D = pd.Timestamp(D)
    benchmark = cfg["benchmark"]
    sector_tickers = list(cfg["sectors"].keys())
    prev_flags = {}
    if prev_state:
        for sec in prev_state.get("sectors", []):
            prev_flags[sec["ticker"]] = sec.get("rally_flag")

    # adjusted frames for every symbol present
    adj = {sym: ind.adjust_ohlc(df) for sym, df in prices.items() if df is not None and not df.empty}

    if benchmark not in adj:
        raise RuntimeError(f"benchmark {benchmark} missing from data")

    # --- metrics for sectors + benchmark ---
    metrics = {sym: asset_metrics(adj[sym], cfg, D) for sym in [benchmark, *sector_tickers] if sym in adj}
    spy_m = metrics[benchmark]
    spy_ret = spy_m.get("ret", {})

    # --- RSS frame + rank/slope/persist ---
    adj_close = pd.concat({sym: adj[sym]["close"] for sym in [benchmark, *sector_tickers] if sym in adj}, axis=1)
    present_sectors = [s for s in sector_tickers if s in adj]
    rssf = rss_frame(adj_close, present_sectors, benchmark, cfg)
    Drow = _row_at(rssf, D)
    rss_latest = rssf.loc[Drow]
    rss_rank = ind.rank_to_percentile(rss_latest)

    pwin = rssf.loc[:Drow].tail(cfg["persist_window"])
    pranks = pwin.apply(ind.rank_to_percentile, axis=1)
    persist = (pranks >= cfg["persist_rank_min"]).sum(axis=0)

    # --- regime (PRD §5.1) ---
    above200 = {s: metrics[s].get("above_sma200", False) for s in present_sectors}
    pct_above = 100.0 * (sum(above200.values()) / len(above200)) if above200 else 0.0
    spy_above = bool(spy_m.get("above_sma200", False))
    state = regime_label(spy_above, pct_above, cfg)
    risk_on = state == "risk_on"
    regime = {
        "state": state,
        "spy_above_200sma": spy_above,
        "pct_sectors_above_200sma": round(pct_above, 1),
    }

    # --- per-sector assembly ---
    sectors_out = []
    for sec in sector_tickers:
        meta = cfg["sectors"][sec]
        if sec not in adj:
            continue
        etf = metrics[sec]
        rss_val = rss_latest.get(sec, float("nan"))

        # universe selection by dollar volume (PRD §6.4)
        stock_metrics = {}
        for stk in meta["stocks"]:
            if stk in adj:
                stock_metrics[stk] = asset_metrics(adj[stk], cfg, D)
        ranked = sorted(stock_metrics.items(), key=lambda kv: kv[1].get("dollar_volume", 0), reverse=True)
        floored = [(t, m) for t, m in ranked if m.get("dollar_volume", 0) >= cfg["min_dollar_volume"]]
        chosen = (floored if len(floored) >= 3 else ranked)[: cfg["universe_size"]]

        # MAP breadth (PRD §5.4)
        valid = [m for _, m in chosen if pd.notna(m.get("sma50"))]
        valid200 = [m for _, m in chosen if pd.notna(m.get("sma200"))]
        map50 = 100.0 * sum(m["above_sma50"] for m in valid) / len(valid) if valid else float("nan")
        map200 = 100.0 * sum(m["above_sma200"] for m in valid200) / len(valid200) if valid200 else float("nan")
        n_used = len(valid)
        band = "high" if map50 >= cfg["map_high"] else ("mid" if map50 >= cfg["map_mid"] else "low")

        # rally flag with hysteresis (PRD §5.4)
        prev = prev_flags.get(sec)
        if prev:
            rally = map50 >= cfg["map_rally_off"]
        else:
            rally = map50 >= cfg["map_rally_on"]

        # breakout w/ volume (PRD §5.5)
        breakout = bool(
            etf.get("pct_from_52w_high", float("nan")) >= -cfg["breakout_band"]
            and pd.notna(etf.get("vol_sma50")) and etf.get("volume", 0) >= cfg["vol_mult"] * etf["vol_sma50"]
            and risk_on
        )
        trend = "positive" if rss_val > 0 else ("negative" if rss_val < 0 else "neutral")
        divergence = bool(trend == "positive" and pd.notna(map50) and map50 < cfg["map_mid"])

        # holdings classification
        leaders, setups, other = [], [], 0
        for stk, m in chosen:
            cls = classify(m, risk_on, cfg)
            stk_rss = _stock_rss(m.get("ret", {}), spy_ret, cfg)
            if cls == "LEADER":
                leaders.append({
                    "ticker": stk, "name": stk, "classification": cls,
                    "rss": _clean(stk_rss),
                    "pct_from_52w_high": _clean(m.get("pct_from_52w_high")),
                    "above_sma50": m.get("above_sma50"), "above_sma200": m.get("above_sma200"),
                    "atr_14": _clean(m.get("atr_14")),
                    "suggested_stop": _suggested_stop(m, cfg),
                    "suggested_shares": _suggested_shares(m, cfg),
                })
            elif cls == "SETUP":
                setups.append({
                    "ticker": stk, "name": stk, "classification": cls,
                    "pct_from_sma50": _clean(m.get("pct_from_sma50")),
                    "atr_ratio": _clean(m.get("atr_ratio")),
                    "vol_contraction": bool(m.get("atr_ratio", float("inf")) <= cfg["setup_atr_ratio_max"]),
                    "above_sma200": m.get("above_sma200"),
                })
            else:
                other += 1
        leaders.sort(key=lambda h: (h["rss"] if h["rss"] is not None else -9e9), reverse=True)
        setups.sort(key=lambda h: (h["atr_ratio"] if h["atr_ratio"] is not None else 9e9))

        spark = [
            _clean(v) for v in rssf[sec].loc[:Drow].tail(cfg["sparkline_window"]).tolist()
        ] if sec in rssf.columns else []

        sectors_out.append({
            "ticker": sec, "name": meta["name"],
            "rss": _clean(rss_val),
            "rss_rank": _int(rss_rank.get(sec)),
            "rss_slope": _clean(_slope(adj, sec, benchmark, D, cfg)),
            "rss_persist": int(persist.get(sec, 0)),
            "trend": trend,
            "breakout": breakout,
            "map_50": _clean(map50), "map_200": _clean(map200), "map_band": band,
            "rally_flag": bool(rally),
            "breadth_divergence": divergence,
            "udvr": _clean(_udvr(adj[sec], D, cfg["udvr_window"])),
            "map_granularity_pct": round(100.0 / n_used, 1) if n_used else None,
            "rss_sparkline": spark,
            "other_count": other,
            "leaders": leaders,
            "setups": setups,
        })

    # leaderboard order: rss_rank desc, slope as tiebreak
    sectors_out.sort(key=lambda s: ((s["rss_rank"] or 0), (s["rss_slope"] or 0)), reverse=True)

    expected = len(cfg.all_symbols())
    ok = len(adj)
    coverage = {"symbols_expected": expected, "symbols_ok": ok, "symbols_skipped": expected - ok}
    return {"sectors": sectors_out, "regime": regime, "coverage": coverage,
            "as_of_trading_date": str(Drow.date())}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _stock_rss(ret: dict, spy_ret: dict, cfg) -> float:
    total = 0.0
    for h in cfg.horizons:
        a, b = ret.get(h, float("nan")), spy_ret.get(h, float("nan"))
        if pd.isna(a) or pd.isna(b):
            return float("nan")
        total += cfg.weight(h) * (a - b)
    return total


def _slope(adj, sec, benchmark, D, cfg) -> float:
    a = adj[sec]["close"].loc[:D]
    b = adj[benchmark]["close"].loc[:D]
    rs = (a / b).tail(cfg["slope_window"])
    return ind.regression_slope(np.log(rs))


def _suggested_stop(m, cfg) -> float | None:
    c, atr = m.get("close"), m.get("atr_14")
    if c is None or pd.isna(atr):
        return None
    return round(c - cfg["atr_stop_mult"] * atr, 2)


def _suggested_shares(m, cfg) -> int | None:
    atr = m.get("atr_14")
    if pd.isna(atr) or atr <= 0:
        return None
    return int(cfg["risk_budget"] * cfg["equity"] / (cfg["atr_stop_mult"] * atr))


def _clean(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 4)


def _int(x):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return int(x)
