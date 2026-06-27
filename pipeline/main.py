"""SectorPulse daily entrypoint (PRD §4, §8).

    python -m pipeline.main [--provider NAME] [--date YYYY-MM-DD] [--force] [--no-web]

Resolves the latest completed trading date, fetches a trailing adjusted-OHLCV
window via the provider chain, computes the contract, validates it, and publishes
latest.json + history. Idempotent and self-healing (PRD §8.2/§8.3).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import pandas as pd

from . import assemble, calendar_utils, compute, eod_cache, intraday, publish
from .config import load_config
from .providers import ProviderChain, build_provider


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(provider_override=None, on_date=None, force=False, mirror_web=True,
        config_path=None, verbose=True) -> dict:
    cfg = load_config(config_path)

    if on_date:
        D = pd.Timestamp(on_date).date()
    else:
        D = calendar_utils.latest_trading_date()

    as_of = str(D)
    if not force and publish.already_published(as_of):
        if verbose:
            print(f"[skip] {as_of} already published (idempotent no-op).")
        return {"status": "skipped", "as_of": as_of}

    # provider chain. Priority: explicit arg > SECTORPULSE_PROVIDERS env > config.
    # CI/production sets the env (e.g. "tiingo,alpaca,stooq,yfinance") so the
    # config can keep "synthetic" first for offline/local runs.
    if provider_override:
        names = [provider_override]
    elif os.environ.get("SECTORPULSE_PROVIDERS"):
        names = [s.strip() for s in os.environ["SECTORPULSE_PROVIDERS"].split(",") if s.strip()]
    else:
        names = cfg["providers"]
    chain = ProviderChain([
        build_provider(n, **_provider_kwargs(n, cfg)) for n in names
    ])
    if not chain.providers:
        raise RuntimeError("no providers available (missing deps/credentials)")

    start = pd.Timestamp(D) - pd.Timedelta(days=cfg["history_lookback_days"])
    symbols = cfg.all_symbols()
    if verbose:
        print(f"[fetch] {len(symbols)} symbols via chain "
              f"{[p.name for p in chain.providers]} for window {start.date()}..{D}")
    prices = chain.fetch(symbols, start, pd.Timestamp(D))
    if not prices:
        raise RuntimeError("provider chain returned no data")
    if verbose:
        print(f"[fetch] provider used: {chain.used}; symbols with data: {len(prices)}/{len(symbols)}")

    # Cache the EOD history so the intraday job can overlay live prices without
    # re-pulling a year of data every 15 minutes (PRD §6.3 / intraday design).
    eod_cache.save_cache(prices)

    prev = publish.load_previous()
    computed = compute.compute(prices, cfg, prev, D)

    payload = assemble.assemble(
        computed,
        generated_at_utc=_now_iso(),
        config_hash=cfg.hash,
        provider=chain.used or "unknown",
        benchmark=cfg["benchmark"],
    )
    assemble.validate(payload)  # raises if contract violated -> nothing published

    written = publish.publish(payload, keep_days=cfg["history_days"], mirror_web=mirror_web)
    if verbose:
        reg = payload["regime"]
        print(f"[ok] {payload['as_of_trading_date']} status={payload['status']} "
              f"regime={reg['state']} ({reg['pct_sectors_above_200sma']}% sectors>200SMA)")
        top = payload["sectors"][0]
        print(f"     leader: {top['ticker']} ({top['name']}) rank={top['rss_rank']} "
              f"map50={top['map_50']} rally={top['rally_flag']}")
        print(f"     wrote: {', '.join(str(p) for p in written)}")
    return {"status": payload["status"], "as_of": payload["as_of_trading_date"], "payload": payload}


def run_intraday(config_path=None, mirror_web=True, verbose=True, force=False) -> dict:
    """Intraday refresh (PRD intraday design): overlay live Tiingo IEX prices on the
    cached EOD history and recompute. No-op outside market hours."""
    cfg = load_config(config_path)

    if not force and not calendar_utils.is_market_open():
        if verbose:
            print("[intraday] market closed - no-op (EOD run is authoritative).")
        return {"status": "closed"}

    token = os.environ.get("TIINGO_TOKEN")
    if not token:
        raise RuntimeError("intraday mode requires TIINGO_TOKEN (Tiingo IEX live prices)")

    D = calendar_utils.current_session_date()
    frames = eod_cache.load_cache()
    if not frames:
        # Cold start: seed the cache with a full EOD fetch via the normal chain.
        if verbose:
            print("[intraday] no EOD cache found — seeding via full EOD run first.")
        run(on_date=str(D), force=True, mirror_web=False, config_path=config_path, verbose=verbose)
        frames = eod_cache.load_cache()
        if not frames:
            raise RuntimeError("could not seed EOD cache")

    live = intraday.fetch_live_tiingo(cfg.all_symbols(), token)
    if not live:
        raise RuntimeError("Tiingo IEX returned no live prices")
    if verbose:
        print(f"[intraday] {len(live)} live prices; overlaying on cached history as of {D}")

    frames = intraday.overlay_live(frames, live, D)
    prev = publish.load_previous()
    computed = compute.compute(frames, cfg, prev, D)
    now = _now_iso()
    payload = assemble.assemble(
        computed, generated_at_utc=now, config_hash=cfg.hash,
        provider="tiingo-iex", benchmark=cfg["benchmark"],
        status="intraday", intraday=True, as_of_time_utc=now,
    )
    assemble.validate(payload)
    written = publish.publish(payload, keep_days=cfg["history_days"], mirror_web=mirror_web)
    if verbose:
        top = payload["sectors"][0]
        print(f"[intraday-ok] {payload['as_of_trading_date']} @ {now} "
              f"regime={payload['regime']['state']} top={top['ticker']} rank={top['rss_rank']}")
        print(f"     wrote: {', '.join(str(p) for p in written)}")
    return {"status": "intraday", "as_of": payload["as_of_trading_date"], "payload": payload}


def _provider_kwargs(name: str, cfg) -> dict:
    if name == "synthetic":
        return {"benchmark": cfg["benchmark"], "sector_of": cfg.sector_of()}
    return {}


def main(argv=None):
    p = argparse.ArgumentParser(description="SectorPulse pipeline")
    p.add_argument("--mode", choices=["eod", "intraday"], default="eod",
                   help="eod (settled, after close) or intraday (live overlay)")
    p.add_argument("--provider", help="force a single provider (e.g. synthetic, tiingo)")
    p.add_argument("--date", help="compute as-of this trading date (YYYY-MM-DD)")
    p.add_argument("--force", action="store_true",
                   help="ignore idempotency guard (eod) / market-hours guard (intraday)")
    p.add_argument("--no-web", action="store_true", help="don't mirror to web/public/data")
    p.add_argument("--config", help="path to config.yml")
    args = p.parse_args(argv)
    try:
        if args.mode == "intraday":
            run_intraday(config_path=args.config, mirror_web=not args.no_web, force=args.force)
        else:
            run(provider_override=args.provider, on_date=args.date, force=args.force,
                mirror_web=not args.no_web, config_path=args.config)
    except Exception as exc:  # fail loud (PRD §8.5) — non-zero exit alerts the owner
        print(f"[error] pipeline failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
