# SectorPulse

A **zero-cost, daily sector relative-strength dashboard**. Once per trading day after the US close, a GitHub Action computes the relative strength of the 11 GICS sector ETFs versus SPY — gated by a market-regime filter, confirmed by breadth and volume — and a static React dashboard renders the result from a CDN. No servers, no database, no paid APIs.

> **Research / screening tool — not investment advice, not an automated trader.** Signals must pass the backtest gate (PRD §12) before any capital is risked. See [PRD.md](PRD.md) for the full spec.

---

## Why v2.1

This is the corrected build. The original v2.0 spec defined relative strength as a **ratio of returns** (`asset_return / SPY_return`), which **inverts sign in down markets**, explodes when SPY is flat, and has no natural zero. v2.1 replaces it with a **weighted excess log return**:

```
RSS = 0.2·(R5_asset − R5_SPY) + 0.3·(R20_asset − R20_SPY) + 0.5·(R50_asset − R50_SPY)
      where R_h(x) = ln(P_t / P_{t−h})
```

Sign-stable in every regime, natural zero (0 = matched SPY), no division by a return. This and ~23 other corrections (regime gate, quantified setups, fixed scheduling/idempotency, flat-file storage, frozen data contract, accessibility) are tracked in [PRD.md §19](PRD.md).

The headline guarantee is enforced by a test — `tests/test_rss.py::test_rss_does_not_invert_in_down_market`.

---

## Architecture

```
GitHub Actions (22:30 UTC, Mon–Fri)
   → Python pipeline: provider chain → trailing-1y adjusted OHLCV
      → regime gate → RSS + rank/slope → MAP breadth → volume confirm → classify
      → validate against contract/latest.schema.json
   → publish data/latest.json (+ rolled history) to the orphan `data` branch
   → build & deploy the static React site (GitHub Pages)
React + Tailwind dashboard ← runtime-fetches /data/latest.json (no client math)
```

---

## Quickstart

```bash
# 1. Python deps
pip install -r requirements.txt

# 2. Run the pipeline with deterministic synthetic data (no keys, no network)
python -m pipeline.main --provider synthetic --force
#    → writes data/latest.json, data/history/<date>.json, web/public/data/latest.json

# 3. Run the test suite (18 tests incl. the RSS sign-stability guarantee)
python -m pytest -q

# 4. Run the dashboard locally
cd web && npm install && npm run dev   # http://localhost:5173
```

### Real market data

```bash
# Single provider:
python -m pipeline.main --provider yfinance --force

# Provider chain (priority order, falls through on failure/low coverage):
SECTORPULSE_PROVIDERS="tiingo,alpaca,stooq,yfinance" python -m pipeline.main --force
```

| Provider | Key? | Notes |
|---|---|---|
| **tiingo** (primary) | `TIINGO_TOKEN` | Best free split/dividend-adjusted EOD |
| **alpaca** | `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` | Official; IEX feed; `adjustment=all` |
| **stooq** | none | Keyless CSV fallback; rate-limited |
| **yfinance** | none | Last-resort; unofficial, fragile (`pip install yfinance`) |
| **synthetic** | none | Deterministic offline data for dev/CI |

`config.yml` lists `synthetic` first so `python -m pipeline.main` works offline out of the box; CI sets `SECTORPULSE_PROVIDERS` to the real chain.

---

## Configuration

Every quantitative parameter lives in [config.yml](config.yml) (PRD §17) — horizon weights, regime/breadth thresholds, MAP bands + hysteresis, breakout/volume rules, setup definitions, the universe (11 ETFs + constituents), and the trade-framework defaults. No magic numbers in code. A hash of the config is stamped into every payload (`config_hash`) for auditability.

---

## Live updates (daily + intraday)

SectorPulse updates itself on two cadences, both free:

| Workflow | When | What it does |
|---|---|---|
| **Daily** ([daily.yml](.github/workflows/daily.yml)) | Mon–Fri 22:30 UTC (after close) | Overlays the **settled** Tiingo IEX close on the cached history, **persists** today's bar, publishes `latest.json` to the `data` branch → **deploys the site**. |
| **Intraday** ([intraday.yml](.github/workflows/intraday.yml)) | ~every 15 min, market hours | One **Tiingo IEX** call for live prices → overlays on the cached history → recomputes → publishes a **provisional** `latest.json` (`status:"intraday"`). No rebuild. |

The deployed dashboard **runtime-fetches `latest.json` and polls it every 60 s** (and on tab focus), so an open tab shows fresh data — with a pulsing **● LIVE** badge and a "provisional until close" note during the session — without any redeploy.

### How "live" actually works (and its limits)
- **Why a seeded cache:** yfinance is blocked from cloud/CI IPs, and Tiingo's *daily* endpoint rate-limits a 177-symbol pull (~50 unique symbols/hour). So CI never bulk-fetches history — it overlays the **Tiingo IEX batch snapshot** (all tickers in ~1 request, no per-symbol cap) onto a history cache (`eod_cache.json.gz`) that is **seeded once locally** (where yfinance works) and then grows one bar per day. This keeps every CI run inside Tiingo's free limits.
- **Cron is best-effort.** GitHub schedules run late/skip under load, so intraday is "~every 15–30 min," not exact. For tighter cadence, point a free external pinger (e.g. cron-job.org) at the workflow's `workflow_dispatch`.
- **CDN cache.** The live site fetches `latest.json` from the `data` branch raw URL (`raw.githubusercontent.com`, ~5 min cache) — fine for a 15-min cadence. Intraday numbers are **provisional** (unsettled IEX prints) until the EOD run finalizes them.

### Deploy (one-time)
1. Push this repo to GitHub — **make it public** ⇒ unlimited free Actions minutes (PRD §4).
2. Add the secret (Settings → Secrets → Actions): **`TIINGO_TOKEN`** (free at tiingo.com — powers all live data via the IEX endpoint).
3. Enable **Pages** (Settings → Pages → Source: GitHub Actions).
4. **Seed the history cache locally** (CI can't bulk-fetch), then publish it to the `data` branch:
   ```bash
   python -m pipeline.main --provider yfinance --force   # builds data/eod_cache.json.gz + latest.json
   bash scripts/seed_data_branch.sh                       # pushes data/ to the `data` branch
   ```
5. Run the **Daily** workflow once (*Actions → SectorPulse Daily → Run workflow*) to deploy the site. Daily + intraday then maintain everything via Tiingo IEX. Re-seed only when you change the universe in `config.yml`.

Run locally during market hours: `TIINGO_TOKEN=... python -m pipeline.main --mode intraday`.

Hosting on Vercel/Netlify instead: connect the repo (build dir `web/`) and set `VITE_DATA_URL` to the `data`-branch raw `latest.json` URL so the live feed reaches the site.

Cron is UTC-only and **does not follow DST** — 22:30 UTC is safely after the 16:00 ET close year-round; the intraday window is wide and gated in-code to the real session (PRD §8).

---

## Project structure

```
PRD.md                     Product spec (v2.1, review-corrected)
config.yml                 All parameters + universe (PRD §17)
contract/latest.schema.json  Frozen JSON data contract (PRD §10)
pipeline/                  Python: providers, indicators, compute, assemble, publish, main
tests/                     pytest: RSS sign-stability, classification, regime, e2e contract
web/                       Vite + React + Tailwind dashboard (runtime-fetches the contract)
scripts/publish_data_branch.sh   Pushes data/ to the orphan `data` branch
.github/workflows/daily.yml      Scheduled compute + Pages deploy
data/                      Generated output (gitignored; lives on the `data` branch in CI)
```

---

## Validation status

The methodology is a **hypothesis** until it beats buy-and-hold SPY (net of costs) in the walk-forward backtest of PRD §12. The dashboard presents itself as a screening tool accordingly.
