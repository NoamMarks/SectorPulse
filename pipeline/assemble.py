"""Assemble + validate the dashboard contract (PRD §10)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contract" / "latest.schema.json"


def _sanitize(obj):
    """Recursively replace NaN/Inf with None (PRD §5.2 / §14)."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


def assemble(computed: dict, *, generated_at_utc: str, config_hash: str,
             provider: str, benchmark: str, status: str = "ok",
             intraday: bool = False, as_of_time_utc: str | None = None) -> dict:
    payload = {
        "schema_version": 1,
        "generated_at_utc": generated_at_utc,
        "as_of_trading_date": computed["as_of_trading_date"],
        "benchmark": benchmark,
        "status": status,
        "config_hash": config_hash,
        "provider": provider,
        "regime": computed["regime"],
        "coverage": computed["coverage"],
        "sectors": computed["sectors"],
    }
    # Only settled EOD payloads get downgraded to "partial"; intraday keeps its status.
    if computed["coverage"]["symbols_skipped"] > 0 and status == "ok":
        payload["status"] = "partial"
    if intraday:
        payload["intraday"] = True
        payload["as_of_time_utc"] = as_of_time_utc or generated_at_utc
    return _sanitize(payload)


def validate(payload: dict) -> None:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    jsonschema.validate(payload, schema)  # raises on contract violation
