"""Alert event detection + digest (no network)."""
from pipeline import alerts


def _payload(regime="risk_on", top="XLK", breakout=None, intraday=False):
    sectors = [
        {"ticker": "XLK", "name": "Technology", "rss_rank": 99, "breakout": False,
         "rally_flag": False, "breadth_divergence": False},
        {"ticker": "XLV", "name": "Health Care", "rss_rank": 80, "breakout": False,
         "rally_flag": True, "breadth_divergence": False},
        {"ticker": "XLF", "name": "Financials", "rss_rank": 60, "breakout": False,
         "rally_flag": False, "breadth_divergence": False},
    ]
    # reorder so `top` is first (leaderboard is sorted by rank)
    sectors.sort(key=lambda s: 0 if s["ticker"] == top else 1)
    if breakout:
        for s in sectors:
            if s["ticker"] == breakout:
                s["breakout"] = True
    return {
        "as_of_trading_date": "2026-06-29", "intraday": intraday,
        "regime": {"state": regime, "spy_above_200sma": regime == "risk_on",
                   "pct_sectors_above_200sma": 82.0},
        "sectors": sectors,
    }


def test_regime_flip_detected_once():
    prev = _payload(regime="risk_on")
    new = _payload(regime="risk_off")
    ev = alerts.detect_events(new, prev)
    assert any("Regime change" in e and "risk_off" in e for e in ev)
    # no flip -> no regime event
    assert not any("Regime change" in e for e in alerts.detect_events(new, new))


def test_breakout_is_edge_triggered():
    prev = _payload(breakout=None)
    new = _payload(breakout="XLK")
    ev = alerts.detect_events(new, prev)
    assert any("Breakout" in e and "XLK" in e for e in ev)
    # already broken out last run -> no repeat
    assert not any("Breakout" in e for e in alerts.detect_events(new, new))


def test_leadership_rotation_detected():
    prev = _payload(top="XLK")
    new = _payload(top="XLV")
    ev = alerts.detect_events(new, prev)
    assert any("New sector leader" in e and "XLV" in e for e in ev)


def test_no_events_without_prev():
    new = _payload()
    assert alerts.detect_events(new, None) == []


def test_digest_has_key_fields():
    d = alerts.build_digest(_payload(regime="risk_on", breakout="XLV"))
    assert "SectorPulse" in d and "2026-06-29" in d and "risk_on" in d
    assert "XLV" in d  # breakout listed


def test_notify_is_noop_without_secrets(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert alerts.notify(_payload(), _payload(regime="risk_off")) == 0
