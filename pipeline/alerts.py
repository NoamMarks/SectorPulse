"""Telegram alerts (regime flips, breakouts, leadership rotation, daily digest).

Edge-triggered: each run is compared to the previously published payload, so an
alert fires only on an actual change (no spam from the ~15-min intraday cadence).
No-op when TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are unset, so local runs are silent.
"""
from __future__ import annotations

import html
import os

import requests

SITE = "https://noammarks.github.io/SectorPulse/"
_API = "https://api.telegram.org/bot{token}/sendMessage"


def _esc(x) -> str:
    return html.escape(str(x))


def _log(s: str) -> None:
    """Print without crashing on non-UTF-8 consoles (e.g. Windows cp1252)."""
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode())


def _send_telegram(text: str, token: str, chat_id: str, timeout: int = 15) -> None:
    r = requests.post(_API.format(token=token), timeout=timeout, json={
        "chat_id": chat_id, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    })
    r.raise_for_status()


def detect_events(new: dict, prev: dict | None) -> list[str]:
    """Instant, edge-triggered alerts comparing this payload to the previous one."""
    events: list[str] = []
    if not new or not new.get("sectors"):
        return events

    tag = "🟢 LIVE" if new.get("intraday") else "settled"

    # 1) regime flip
    ns = new["regime"]["state"]
    if prev and prev.get("regime", {}).get("state") and prev["regime"]["state"] != ns:
        reg = new["regime"]
        events.append(
            f"🔄 <b>Regime change</b>: {_esc(prev['regime']['state'])} → <b>{_esc(ns)}</b>\n"
            f"SPY {'above' if reg['spy_above_200sma'] else 'below'} 200-DMA · "
            f"{_esc(reg['pct_sectors_above_200sma'])}% of sectors above 200-DMA  <i>({tag})</i>"
        )

    # 2) newly-confirmed breakouts
    prev_bo = {s["ticker"]: s.get("breakout") for s in (prev.get("sectors") if prev else [])}
    for s in new["sectors"]:
        if s.get("breakout") and not prev_bo.get(s["ticker"]):
            events.append(
                f"🚀 <b>Breakout</b>: {_esc(s['ticker'])} ({_esc(s['name'])}) — "
                f"volume-confirmed near 52w high · RSS rank {_esc(s['rss_rank'])}  <i>({tag})</i>"
            )

    # 3) leadership rotation (#1 sector changed)
    new_top = new["sectors"][0]
    prev_top = prev["sectors"][0] if prev and prev.get("sectors") else None
    if prev_top and new_top["ticker"] != prev_top["ticker"]:
        events.append(
            f"👑 <b>New sector leader</b>: {_esc(new_top['ticker'])} ({_esc(new_top['name'])}) "
            f"overtakes {_esc(prev_top['ticker'])} · RSS rank {_esc(new_top['rss_rank'])}  <i>({tag})</i>"
        )
    return events


def build_digest(new: dict) -> str:
    """Once-a-day after-close summary."""
    reg = new["regime"]
    secs = new["sectors"]
    top3 = ", ".join(s["ticker"] for s in secs[:3])
    bos = [s["ticker"] for s in secs if s.get("breakout")]
    rally = [s["ticker"] for s in secs if s.get("rally_flag")]
    div = [s["ticker"] for s in secs if s.get("breadth_divergence")]
    lines = [
        f"📊 <b>SectorPulse</b> — {_esc(new['as_of_trading_date'])}",
        f"Regime: <b>{_esc(reg['state'])}</b> ({_esc(reg['pct_sectors_above_200sma'])}% sectors &gt; 200-DMA)",
        f"Leaders: {_esc(top3)}",
    ]
    if bos:
        lines.append(f"🚀 Breakouts: {_esc(', '.join(bos))}")
    if rally:
        lines.append(f"💪 High-participation rally: {_esc(', '.join(rally))}")
    if div:
        lines.append(f"⚠️ Breadth divergence: {_esc(', '.join(div))}")
    lines.append(f'<a href="{SITE}">Open dashboard</a>')
    return "\n".join(lines)


def notify(prev_payload: dict | None, new_payload: dict, *, digest: bool = False,
           verbose: bool = True) -> int:
    """Send all applicable alerts. Returns the number of messages sent. No-op if
    Telegram secrets are absent (so local/dev runs stay silent)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return 0
    msgs = detect_events(new_payload, prev_payload)
    if digest:
        msgs.append(build_digest(new_payload))
    sent = 0
    for m in msgs:
        try:
            _send_telegram(m, token, chat)
            sent += 1
            if verbose:
                _log(f"[alerts] sent: {m.splitlines()[0]}")
        except Exception as exc:  # non-fatal — never break the pipeline
            if verbose:
                _log(f"[alerts] send failed (non-fatal): {exc}")
    return sent
