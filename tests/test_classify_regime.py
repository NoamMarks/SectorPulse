"""Classification (PRD §5.6) and regime gate (PRD §5.1)."""
import pandas as pd

from pipeline.compute import classify, regime_label
from pipeline.config import load_config

CFG = load_config()


def _m(**kw):
    base = dict(pct_from_52w_high=-50.0, pct_from_sma50=50.0, atr_ratio=2.0,
                above_sma50=False, above_sma200=False)
    base.update(kw)
    return base


def test_leader_requires_near_high_uptrend_and_risk_on():
    m = _m(pct_from_52w_high=-2.0, above_sma50=True, above_sma200=True)
    assert classify(m, regime_risk_on=True, cfg=CFG) == "LEADER"
    # Same stock, risk-off regime => not a leader (regime gate suppresses it).
    assert classify(m, regime_risk_on=False, cfg=CFG) != "LEADER"


def test_setup_requires_consolidation_contraction_uptrend():
    m = _m(pct_from_52w_high=-15.0, pct_from_sma50=1.0, atr_ratio=0.6, above_sma200=True)
    assert classify(m, regime_risk_on=True, cfg=CFG) == "SETUP"
    # Not contracted -> not a setup.
    assert classify(_m(pct_from_52w_high=-15.0, pct_from_sma50=1.0, atr_ratio=1.1,
                       above_sma200=True), True, CFG) == "OTHER"
    # Not near SMA50 -> not a setup.
    assert classify(_m(pct_from_52w_high=-15.0, pct_from_sma50=9.0, atr_ratio=0.6,
                       above_sma200=True), True, CFG) == "OTHER"


def test_other_bucket_is_the_catch_all():
    assert classify(_m(), regime_risk_on=True, cfg=CFG) == "OTHER"


def test_nan_inputs_never_raise_and_fall_through_to_other():
    m = _m(pct_from_52w_high=float("nan"), pct_from_sma50=float("nan"),
           atr_ratio=float("nan"), above_sma200=True)
    assert classify(m, regime_risk_on=True, cfg=CFG) == "OTHER"


def test_regime_gate_truth_table():
    assert regime_label(spy_above=True, pct_above=80.0, cfg=CFG) == "risk_on"
    assert regime_label(spy_above=False, pct_above=10.0, cfg=CFG) == "risk_off"
    assert regime_label(spy_above=True, pct_above=10.0, cfg=CFG) == "neutral"
    assert regime_label(spy_above=False, pct_above=80.0, cfg=CFG) == "neutral"
    # Boundary: exactly at the breadth threshold counts as meeting it.
    assert regime_label(spy_above=True, pct_above=CFG["regime_breadth_min"], cfg=CFG) == "risk_on"
