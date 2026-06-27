"""Intraday overlay + cache + market-hours guard."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from pipeline import assemble, calendar_utils, compute, eod_cache, intraday
from pipeline.config import load_config
from pipeline.providers import build_provider

CFG = load_config()


def _frames():
    prov = build_provider("synthetic", benchmark=CFG["benchmark"], sector_of=CFG.sector_of())
    end = pd.Timestamp(calendar_utils.latest_trading_date())
    start = end - pd.Timedelta(days=CFG["history_lookback_days"])
    return prov.fetch(CFG.all_symbols(), start, end)


def test_eod_cache_round_trips(tmp_path):
    frames = _frames()
    path = tmp_path / "cache.json.gz"
    eod_cache.save_cache(frames, path)
    loaded = eod_cache.load_cache(path)
    assert set(loaded) == set(frames)
    a, b = frames["SPY"], loaded["SPY"]
    assert len(a) == len(b)
    assert abs(a["close"].iloc[-1] - b["close"].iloc[-1]) < 1e-6


def test_overlay_updates_todays_bar():
    frames = _frames()
    as_of = frames["SPY"].index[-1]            # update-in-place path
    live = {sym: float(df["close"].iloc[-1]) * 1.02 for sym, df in frames.items()}
    merged = intraday.overlay_live(frames, live, as_of)
    # SPY's last close should now equal the live price (1.02x), high lifted.
    assert abs(merged["SPY"]["close"].iloc[-1] - live["SPY"]) < 1e-6
    assert merged["SPY"]["high"].iloc[-1] >= live["SPY"] - 1e-6
    assert len(merged["SPY"]) == len(frames["SPY"])  # updated, not appended


def test_overlay_appends_new_session():
    frames = _frames()
    next_day = frames["SPY"].index[-1] + pd.tseries.offsets.BDay(1)
    live = {"SPY": float(frames["SPY"]["close"].iloc[-1]) * 0.97}
    merged = intraday.overlay_live(frames, live, next_day)
    assert len(merged["SPY"]) == len(frames["SPY"]) + 1
    assert abs(merged["SPY"]["close"].iloc[-1] - live["SPY"]) < 1e-6


def test_intraday_payload_is_valid_and_flagged():
    frames = _frames()
    as_of = frames["SPY"].index[-1]
    live = {sym: float(df["close"].iloc[-1]) * 1.01 for sym, df in frames.items()}
    merged = intraday.overlay_live(frames, live, as_of)
    computed = compute.compute(merged, CFG, None, as_of)
    payload = assemble.assemble(
        computed, generated_at_utc="2026-06-26T18:00:00Z", config_hash=CFG.hash,
        provider="tiingo-iex", benchmark=CFG["benchmark"],
        status="intraday", intraday=True, as_of_time_utc="2026-06-26T18:00:00Z",
    )
    assemble.validate(payload)                 # raises on contract violation
    assert payload["status"] == "intraday"
    assert payload["intraday"] is True
    assert payload["as_of_time_utc"]
    assert len(payload["sectors"]) == 11


def test_market_hours_guard():
    # 14:00 UTC on a Wednesday = 10:00 ET (June, EDT) -> open.
    wed_open = datetime(2026, 6, 24, 14, 0, tzinfo=ZoneInfo("UTC"))
    assert calendar_utils.is_market_open(wed_open) is True
    # 02:00 UTC = 22:00 ET prior day -> closed.
    night = datetime(2026, 6, 24, 2, 0, tzinfo=ZoneInfo("UTC"))
    assert calendar_utils.is_market_open(night) is False
    # Saturday -> closed regardless of time.
    sat = datetime(2026, 6, 27, 15, 0, tzinfo=ZoneInfo("UTC"))
    assert calendar_utils.is_market_open(sat) is False
