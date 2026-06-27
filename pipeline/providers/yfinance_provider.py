"""yfinance last-resort fallback (PRD §6.1). Keyless but unofficial; optional dep."""
from __future__ import annotations

import pandas as pd

from .base import PriceProvider, normalize_frame


class YFinanceProvider(PriceProvider):
    name = "yfinance"

    def available(self) -> bool:
        try:
            import yfinance  # noqa: F401
            return True
        except Exception:
            return False

    def fetch(self, symbols, start, end):
        import yfinance as yf

        raw = yf.download(
            list(symbols),
            start=pd.Timestamp(start).strftime("%Y-%m-%d"),
            end=(pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            auto_adjust=False,
            group_by="ticker",
            threads=True,
            progress=False,
        )
        out: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            try:
                sub = raw[sym] if isinstance(raw.columns, pd.MultiIndex) else raw
                df = pd.DataFrame(
                    {
                        "open": sub["Open"],
                        "high": sub["High"],
                        "low": sub["Low"],
                        "close": sub["Close"],
                        "adj_close": sub.get("Adj Close", sub["Close"]),
                        "volume": sub["Volume"],
                    }
                )
                out[sym] = normalize_frame(df)
            except Exception:
                continue
        return out
