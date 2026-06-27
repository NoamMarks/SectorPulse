"""Interactive Telegram status bot — no extra hosting required.

Answers /status, /sectors, /sector <TICKER>, /help by reading the live latest.json.
Standalone (only needs `requests` + stdlib — no pandas), so it runs cheaply in CI.

Run modes:
  python -m pipeline.bot --watch   # long-poll forever; instant replies (run locally)
  python -m pipeline.bot --once    # process pending updates once and exit (for cron)

Env:
  TELEGRAM_BOT_TOKEN   (required)
  TELEGRAM_CHAT_ID     (optional) restrict replies to this chat
  SECTORPULSE_DATA_URL (optional) override the latest.json URL
"""
from __future__ import annotations

import argparse
import os
import time

import requests

DATA_URL = os.environ.get(
    "SECTORPULSE_DATA_URL",
    "https://raw.githubusercontent.com/NoamMarks/SectorPulse/data/latest.json",
)
SITE = "https://noammarks.github.io/SectorPulse/"
_TG = "https://api.telegram.org/bot{token}/{method}"


# --------------------------------------------------------------------------- #
# Data + formatting (mirrors bot/worker.js)
# --------------------------------------------------------------------------- #
def fetch_data() -> dict:
    r = requests.get(DATA_URL, params={"t": int(time.time())},
                     headers={"cache-control": "no-cache"}, timeout=15)
    r.raise_for_status()
    return r.json()


def _fmt(x) -> str:
    return "—" if x is None else (f"+{x:.3f}" if x >= 0 else f"{x:.3f}")


def _fresh(d: dict) -> str:
    return "🟢 LIVE (provisional)" if (d.get("status") == "intraday" or d.get("intraday")) else "settled"


def status_text(d: dict) -> str:
    r = d["regime"]
    top = "  ".join(f"{i+1}. {s['ticker']} (#{s['rss_rank']})" for i, s in enumerate(d["sectors"][:3]))
    bo = [s["ticker"] for s in d["sectors"] if s.get("breakout")]
    rally = [s["ticker"] for s in d["sectors"] if s.get("rally_flag")]
    div = [s["ticker"] for s in d["sectors"] if s.get("breadth_divergence")]
    lines = [
        f"📊 <b>SectorPulse</b> — {d['as_of_trading_date']} · {_fresh(d)}",
        f"Regime: <b>{r['state']}</b> ({r['pct_sectors_above_200sma']}% &gt; 200-DMA)",
        f"Top: {top}",
    ]
    if bo:
        lines.append(f"🚀 Breakouts: {', '.join(bo)}")
    if rally:
        lines.append(f"💪 Rally: {', '.join(rally)}")
    if div:
        lines.append(f"⚠️ Divergence: {', '.join(div)}")
    lines.append(f'<a href="{SITE}">Open dashboard</a>')
    return "\n".join(lines)


def sectors_text(d: dict) -> str:
    rows = [
        f"{i+1:>2}. <b>{s['ticker']}</b> #{s['rss_rank']}  rss {_fmt(s['rss'])}  "
        f"MAP {round(s['map_50'])}%" + (" 🚀" if s.get("breakout") else "")
        for i, s in enumerate(d["sectors"])
    ]
    return f"📊 <b>Leaderboard</b> — {d['as_of_trading_date']} · {_fresh(d)}\n" + "\n".join(rows)


def sector_detail(d: dict, tk: str) -> str:
    s = next((x for x in d["sectors"] if x["ticker"] == tk), None)
    if not s:
        return f'No sector "<b>{tk}</b>". Try /sectors.'
    lead = ", ".join(h["ticker"] for h in s.get("leaders", [])) or "none"
    setup = ", ".join(h["ticker"] for h in s.get("setups", [])) or "none"
    flags = " · ".join(f for f in [
        "breakout" if s.get("breakout") else None,
        "rally" if s.get("rally_flag") else None,
        "⚠️ divergence" if s.get("breadth_divergence") else None,
    ] if f) or "none"
    return "\n".join([
        f"<b>{s['ticker']}</b> — {s['name']}  (rank {s['rss_rank']})",
        f"RSS {_fmt(s['rss'])} · MAP50 {round(s['map_50'])}% ({s['map_band']}) · trend {s['trend']}",
        f"Flags: {flags}",
        f"Leaders ({len(s.get('leaders', []))}): {lead}",
        f"Setups ({len(s.get('setups', []))}): {setup}",
    ])


def help_text() -> str:
    return "\n".join([
        "🤖 <b>SectorPulse bot</b>",
        "/status — regime, top sectors, flags",
        "/sectors — full 11-sector leaderboard",
        "/sector XLK — one sector's detail + holdings",
        "/help — this message",
    ])


def handle(text: str) -> str:
    parts = text.strip().split()
    if not parts:
        return help_text()
    name = parts[0].lower().split("@")[0]
    arg = parts[1].upper() if len(parts) > 1 else ""
    if name in ("/help", "/start"):
        return help_text()
    if name == "/status":
        return status_text(fetch_data())
    if name == "/sectors":
        return sectors_text(fetch_data())
    if name == "/sector":
        return sector_detail(fetch_data(), arg) if arg else "Usage: <code>/sector XLK</code>"
    return "Unknown command.\n\n" + help_text()


# --------------------------------------------------------------------------- #
# Telegram polling
# --------------------------------------------------------------------------- #
def send(token: str, chat_id, text: str) -> None:
    requests.post(_TG.format(token=token, method="sendMessage"), timeout=15, json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True,
    })


def _get_updates(token: str, offset=None, timeout=0):
    params = {"timeout": timeout, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(_TG.format(token=token, method="getUpdates"),
                     params=params, timeout=timeout + 15)
    return r.json().get("result", [])


def _process(update: dict, token: str, allowed) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg or not msg.get("text"):
        return
    chat = msg["chat"]["id"]
    if allowed and str(chat) != str(allowed):
        send(token, chat, "⛔ Not authorized.")
        return
    try:
        reply = handle(msg["text"])
    except Exception:
        reply = "⚠️ Couldn't read SectorPulse data right now — try again shortly."
    send(token, chat, reply)


def run_once(token: str, allowed) -> int:
    """Process all pending updates and confirm them server-side, then exit."""
    ups = _get_updates(token, timeout=0)
    last = None
    for u in ups:
        _process(u, token, allowed)
        last = u["update_id"]
    if last is not None:
        _get_updates(token, offset=last + 1)  # confirm -> Telegram drops them next time
    return len(ups)


def run_watch(token: str, allowed) -> None:
    """Long-poll forever — instant replies. Ctrl+C to stop."""
    print("SectorPulse bot watching for messages (Ctrl+C to stop)...")
    offset = None
    while True:
        try:
            ups = _get_updates(token, offset=offset, timeout=30)
            for u in ups:
                _process(u, token, allowed)
                offset = u["update_id"] + 1
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"[bot] transient error: {exc}; retrying...")
            time.sleep(3)


def main(argv=None):
    p = argparse.ArgumentParser(description="SectorPulse Telegram status bot")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--watch", action="store_true", help="long-poll forever (instant)")
    g.add_argument("--once", action="store_true", help="process pending updates once (cron)")
    args = p.parse_args(argv)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set")
    allowed = os.environ.get("TELEGRAM_CHAT_ID")

    if args.watch:
        run_watch(token, allowed)
    else:
        n = run_once(token, allowed)
        print(f"[bot] processed {n} update(s)")


if __name__ == "__main__":
    main()
