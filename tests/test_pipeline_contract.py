"""End-to-end: the synthetic pipeline produces a schema-valid, sane payload."""
import json

import pytest

from pipeline import assemble, calendar_utils, indicators
from pipeline.config import load_config
from pipeline.main import run


@pytest.fixture(scope="module")
def payload():
    res = run(provider_override="synthetic", force=True, mirror_web=False, verbose=False)
    return res["payload"]


def test_payload_validates_against_contract(payload):
    assemble.validate(payload)  # raises on any contract violation


def test_payload_is_json_serializable_without_nan(payload):
    # allow_nan=False raises if any NaN/Inf leaked (PRD §5.2/§14).
    json.dumps(payload, allow_nan=False)


def test_all_eleven_sectors_present(payload):
    assert len(payload["sectors"]) == 11
    cfg = load_config()
    assert {s["ticker"] for s in payload["sectors"]} == set(cfg["sectors"].keys())


def test_leaderboard_sorted_by_rank_desc(payload):
    ranks = [s["rss_rank"] for s in payload["sectors"]]
    assert ranks == sorted(ranks, reverse=True)


def test_trend_sign_matches_rss_sign(payload):
    for s in payload["sectors"]:
        if s["rss"] is None:
            continue
        if s["rss"] > 0:
            assert s["trend"] == "positive"
        elif s["rss"] < 0:
            assert s["trend"] == "negative"


def test_holdings_buckets_are_disjoint_and_typed(payload):
    for s in payload["sectors"]:
        assert all(h["classification"] == "LEADER" for h in s["leaders"])
        assert all(h["classification"] == "SETUP" for h in s["setups"])


def test_regime_and_coverage_shapes(payload):
    assert payload["regime"]["state"] in {"risk_on", "neutral", "risk_off"}
    cov = payload["coverage"]
    assert cov["symbols_ok"] + cov["symbols_skipped"] == cov["symbols_expected"]


def test_latest_trading_date_is_a_session():
    import datetime as dt
    d = calendar_utils.latest_trading_date()
    assert calendar_utils.is_trading_day(d)
    assert d.weekday() < 5


def test_atr_and_sma_basic_sanity():
    import numpy as np
    import pandas as pd
    s = pd.Series(np.linspace(100, 150, 60), index=pd.bdate_range("2025-01-01", periods=60))
    assert indicators.sma(s, 10).iloc[-1] > indicators.sma(s, 50).iloc[-1]  # uptrend
    hi = s * 1.01
    lo = s * 0.99
    atr = indicators.wilder_atr(hi, lo, s, 14)
    assert atr.iloc[-1] > 0
