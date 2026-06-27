"""Provider registry and priority chain (PRD §6.1, §8.4).

The chain tries providers in configured priority order, skipping unavailable ones
(missing deps/creds) and falling through on hard failure or insufficient coverage.
"""
from __future__ import annotations

from .alpaca import AlpacaProvider
from .base import PriceProvider, normalize_frame
from .stooq import StooqProvider
from .synthetic import SyntheticProvider
from .tiingo import TiingoProvider
from .yfinance_provider import YFinanceProvider

REGISTRY = {
    "synthetic": SyntheticProvider,
    "tiingo": TiingoProvider,
    "alpaca": AlpacaProvider,
    "stooq": StooqProvider,
    "yfinance": YFinanceProvider,
}


def build_provider(name: str, **kwargs) -> PriceProvider:
    try:
        return REGISTRY[name](**kwargs)
    except KeyError as exc:
        raise ValueError(f"unknown provider: {name!r}") from exc


class ProviderChain:
    """Fetch with fallthrough. Accepts a coverage floor: if a provider returns
    fewer than ``min_coverage`` of the requested symbols, fall through."""

    def __init__(self, providers, min_coverage: float = 0.5):
        self.providers = [p for p in providers if p.available()]
        self.min_coverage = min_coverage
        self.used = None

    def fetch(self, symbols, start, end):
        symbols = list(symbols)
        last = {}
        for prov in self.providers:
            try:
                data = prov.fetch(symbols, start, end)
            except Exception:
                continue
            data = {k: v for k, v in (data or {}).items() if v is not None and not v.empty}
            if len(data) >= max(1, int(self.min_coverage * len(symbols))):
                self.used = prov.name
                return data
            if len(data) > len(last):
                last = data
                self.used = prov.name
        return last  # best effort even if below floor
