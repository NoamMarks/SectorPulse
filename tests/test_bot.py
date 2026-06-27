"""Bot command formatting (no network — fetch_data is monkeypatched)."""
from pipeline import bot


def _data():
    return {
        "as_of_trading_date": "2026-06-26", "status": "intraday", "intraday": True,
        "regime": {"state": "risk_on", "spy_above_200sma": True, "pct_sectors_above_200sma": 82.0},
        "sectors": [
            {"ticker": "XLV", "name": "Health Care", "rss": 0.0704, "rss_rank": 99, "trend": "positive",
             "map_50": 80.0, "map_band": "high", "breakout": True, "rally_flag": True,
             "breadth_divergence": False,
             "leaders": [{"ticker": "LLY"}, {"ticker": "UNH"}], "setups": []},
            {"ticker": "XLK", "name": "Technology", "rss": 0.066, "rss_rank": 66, "trend": "positive",
             "map_50": 40.0, "map_band": "low", "breakout": False, "rally_flag": False,
             "breadth_divergence": True, "leaders": [], "setups": [{"ticker": "MSFT"}]},
        ],
    }


def test_status(monkeypatch):
    monkeypatch.setattr(bot, "fetch_data", _data)
    out = bot.handle("/status")
    assert "SectorPulse" in out and "risk_on" in out and "XLV" in out
    assert "LIVE" in out            # intraday flagged
    assert "🚀 Breakouts: XLV" in out


def test_status_with_botname_suffix(monkeypatch):
    monkeypatch.setattr(bot, "fetch_data", _data)
    assert "SectorPulse" in bot.handle("/status@SectorPulseBot")


def test_sectors(monkeypatch):
    monkeypatch.setattr(bot, "fetch_data", _data)
    out = bot.handle("/sectors")
    assert "Leaderboard" in out and "XLV" in out and "XLK" in out


def test_sector_detail(monkeypatch):
    monkeypatch.setattr(bot, "fetch_data", _data)
    out = bot.handle("/sector XLK")
    assert "Technology" in out and "divergence" in out and "MSFT" in out


def test_sector_unknown(monkeypatch):
    monkeypatch.setattr(bot, "fetch_data", _data)
    assert "No sector" in bot.handle("/sector ZZZ")


def test_sector_requires_arg():
    assert "Usage" in bot.handle("/sector")


def test_help_and_unknown():
    assert "SectorPulse bot" in bot.handle("/help")
    assert "Unknown command" in bot.handle("/wat")
