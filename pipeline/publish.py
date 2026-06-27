"""Publish the payload (PRD §9). Writes latest.json + rolled history.

In CI this directory is pushed to the orphan ``data`` branch; the static site
also reads a copy under ``web/public/data/`` for local dev.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
WEB_DATA_DIR = ROOT / "web" / "public" / "data"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, allow_nan=False)


def already_published(as_of: str, data_dir: Path = DATA_DIR) -> bool:
    """Idempotency guard keyed on the *trading* date (PRD §8.3)."""
    latest = data_dir / "latest.json"
    if not latest.exists():
        return False
    try:
        with open(latest, "r", encoding="utf-8") as fh:
            return json.load(fh).get("as_of_trading_date") == as_of
    except Exception:
        return False


def load_previous(data_dir: Path = DATA_DIR) -> dict | None:
    latest = data_dir / "latest.json"
    if not latest.exists():
        return None
    try:
        with open(latest, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _prune_history(hist_dir: Path, keep_days: int) -> None:
    cutoff = date.today() - timedelta(days=int(keep_days * 1.6) + 30)
    for f in hist_dir.glob("*.json"):
        try:
            d = date.fromisoformat(f.stem)
            if d < cutoff:
                f.unlink()
        except ValueError:
            continue


def publish(payload: dict, *, keep_days: int = 365,
            data_dir: Path = DATA_DIR, web_dir: Path = WEB_DATA_DIR,
            mirror_web: bool = True) -> list[Path]:
    written = []
    _write_json(data_dir / "latest.json", payload)
    written.append(data_dir / "latest.json")

    hist_dir = data_dir / "history"
    hist_path = hist_dir / f"{payload['as_of_trading_date']}.json"
    _write_json(hist_path, payload)          # idempotent overwrite-by-date
    written.append(hist_path)
    _prune_history(hist_dir, keep_days)

    if mirror_web:
        _write_json(web_dir / "latest.json", payload)
        written.append(web_dir / "latest.json")
    return written
