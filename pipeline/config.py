"""Config loader (PRD §17). Single source of truth for every parameter."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.yml"


class Config(dict):
    """Dict with attribute access and a stable content hash for auditability."""

    __getattr__ = dict.get

    @property
    def hash(self) -> str:
        blob = json.dumps(self, sort_keys=True, default=str).encode()
        return hashlib.sha256(blob).hexdigest()[:8]

    @property
    def horizons(self) -> list[int]:
        return sorted(int(h) for h in self["horizon_weights"])

    def weight(self, h: int) -> float:
        return float(self["horizon_weights"][h if h in self["horizon_weights"] else str(h)])

    def sector_of(self) -> dict[str, str]:
        """ticker -> sector ETF (and ETF -> itself), for the synthetic factor model."""
        m = {}
        for etf, meta in self["sectors"].items():
            m[etf] = etf
            for s in meta["stocks"]:
                m[s] = etf
        return m

    def all_symbols(self) -> list[str]:
        syms = [self["benchmark"]]
        for etf, meta in self["sectors"].items():
            syms.append(etf)
            syms.extend(meta["stocks"])
        # de-dupe, preserve order
        seen, out = set(), []
        for s in syms:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path) if path else DEFAULT_PATH
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    # normalize horizon_weights keys to int
    raw["horizon_weights"] = {int(k): float(v) for k, v in raw["horizon_weights"].items()}
    return Config(raw)
