# SectorPulse — Product Requirements & Technical Specification

| | |
|---|---|
| **Project** | SectorPulse |
| **Author** | Noam Marks |
| **Version** | 2.1 — *Zero-Cost Serverless, Review-Corrected* |
| **Date** | June 2026 |
| **Supersedes** | v2.0 (June 2026) |
| **Status** | Approved for build |
| **Target users** | Swing traders, position traders, portfolio managers |

> **What changed from v2.0 and why** — see the [Changelog](#19-changelog-v20--v21) at the end. v2.1 is a direct response to a multi-dimension technical review of v2.0. Every change traces to a verified finding (math correctness, data integrity, scheduling, storage, frontend contract, methodology soundness).

---

## 1. Executive Summary & Positioning

SectorPulse is a lightweight, **zero-cost, decision-support dashboard** that implements a **top-down market-leadership** workflow. Once per trading day, after the US close, it ranks the **11 GICS sector ETFs** by their **relative strength versus SPY**, confirms each ranking with **breadth and volume**, gates the whole picture behind a **market-regime filter**, and drills into each sector's holdings to surface **Leaders** (extended, in-trend) and **Setups** (low-volatility consolidations).

**Honest positioning (important).** SectorPulse is a **research / screening tool**, not an automated trading system and not investment advice. It surfaces ranked, confirmed candidates and a structured trade-management *framework*; it does **not** place orders, and its signals **must be backtested** (§12) before any capital is risked. This framing is deliberate: v2.0 described itself as "a quantitative trading methodology" while specifying no entry/sizing/exit rules and no validation. v2.1 either supplies those rules explicitly (§7) or labels their absence.

The system runs entirely on free infrastructure: a scheduled GitHub Action computes everything in Python, writes a small pre-computed JSON payload to a data branch, and a static React dashboard renders it from a CDN. No servers, no databases, no API costs.

---

## 2. Goals & Non-Goals

### 2.1 Goals
- **G1.** Correctly rank the 11 sector ETFs by regime-aware relative strength every trading day.
- **G2.** Confirm leadership with breadth (MAP) and volume, not price alone.
- **G3.** Drill into each sector to classify holdings into **Leaders** and **Setups** using *quantified, reproducible* rules.
- **G4.** Display a fast, accessible, mobile-responsive dark dashboard with explicit data-freshness and never-blank guarantees.
- **G5.** Operate at **$0** with no always-on infrastructure and no manual steps.
- **G6.** Be auditable: every displayed number is reproducible from stored inputs.

### 2.2 Non-Goals (v2.1)
- **True real-time / streaming** tick data and an always-on backend. *(v2.1 adds an optional **intraday provisional** mode — live Tiingo IEX prices overlaid on the cached EOD history, refreshed ~every 15 min and clearly flagged `status:"intraday"` until the close settles them. The core metrics remain EOD-defined; intraday is a provisional view, not a re-architecture to streaming.)*
- Order execution, brokerage integration, or portfolio accounting.
- Per-user accounts, auth, or persistence of user state.
- Options, futures, crypto, or non-US equities.
- A proven alpha claim. The methodology is a *hypothesis* until §12 validation passes.

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. SCHEDULER — GitHub Actions cron (UTC), Mon–Fri ~22:30 UTC          │
│    Public repo ⇒ UNLIMITED free minutes. In-code market-calendar gate. │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ workflow_dispatch + schedule
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2. INGESTION — Python. Pluggable provider (Tiingo→Alpaca→Stooq).       │
│    Batched download of a TRAILING ~1y adjusted-OHLCV window per run.    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ pandas DataFrame (in-memory)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3. COMPUTE — regime gate → RSS (excess log return) → RS rank →         │
│    MAP breadth → volume confirm → Leader/Setup classification.         │
│    All magic numbers come from config.yml (§17).                       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ validate against JSON schema
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 4. PUBLISH — write latest.json + history/ to an orphan `data` branch.  │
│    No DB. Daily churn kept OUT of main code history.                   │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ runtime fetch (no-cache/revalidate)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 5. DASHBOARD — Vite + React + Tailwind, static, CDN-hosted (free).     │
│    No client-side math. Renders the pre-computed contract only.        │
└──────────────────────────────────────────────────────────────────────┘
```

**Key architectural decisions (locked):**
- Frontend/host: **Vite + React + Tailwind**, static, on Vercel/Netlify/GitHub Pages. *(Streamlit and live-DB-read options dropped.)*
- Storage: **flat-file hybrid** (`latest.json` + capped history). *(Hosted Postgres dropped — see §9.)*
- The dashboard performs **zero quantitative computation**; it is a pure renderer of the §10 contract.

---

## 4. Tech Stack & Rationale

| Layer | Choice | Why (and corrected rationale) |
|---|---|---|
| Automation | **GitHub Actions** (cron + `workflow_dispatch`) | **Public repo ⇒ unlimited free minutes.** The "2,000 min/mo" figure is a *private-repo* cap; a ~3-min daily job is ~60 min/mo regardless. Zero-cost holds. |
| Language | **Python 3.12+**, pandas, numpy | In-memory compute; rich market-calendar + data libraries. |
| Market calendar | **`exchange_calendars`** (or `pandas_market_calendars`) | Correctly resolves the latest *trading* date, holidays, half-days — fixes the idempotency bug (§8.3). |
| Data source | **Tiingo** primary → **Alpaca** → **Stooq/yfinance** fallback | Pluggable provider behind one interface. Official, properly split/dividend-**adjusted** EOD with graceful degradation. (§6) |
| Storage | **Flat JSON on an orphan `data` branch** | No server, no cold-start, no inactivity pause, no DB credentials; data is ~hundreds of KB/yr. (§9) |
| Frontend | **Vite + React + TypeScript + Tailwind** | Static SSG, dark theme, accessible components, CDN-cacheable. |
| Hosting | **Vercel / Netlify / GitHub Pages** (free tier) | Static asset hosting; runtime-fetched JSON ⇒ no rebuild on data change. |
| Charts | **lightweight-charts** or inline SVG sparklines | Pre-baked series from the contract; no client aggregation. |

---

## 5. Quantitative Model

> All parameters below are **defaults in `config.yml`** (§17), documented as assumptions, and **must pass the sensitivity study in §12** before being trusted. Nothing here is a hard-coded magic number in application logic.

### 5.0 Computation order (each run)
1. Resolve **latest completed trading date** `D` (market calendar).
2. Compute the **market-regime gate** (§5.1). If risk-off, long signals are flagged suppressed (not hidden).
3. For every asset, compute **excess-return RSS** (§5.2) and **cross-sectional RS rank** (§5.3).
4. For each sector, compute **MAP breadth** (§5.4).
5. For each holding, compute **volume confirmation** (§5.5) and **Leader/Setup classification** (§5.6).
6. Assemble and validate the JSON contract (§10).

### 5.1 Market-Regime Gate (NEW — blocker fix)
A top-down system must first ask *"is the market in an uptrend?"* before acting on relative strength.

```
regime_risk_on =  (SPY_close > SMA_200(SPY))
              AND (pct_sectors_above_200SMA >= regime_breadth_min)   # default 50%
```

- `regime` ∈ `{ "risk_on", "neutral", "risk_off" }` (neutral = exactly one condition met).
- When not `risk_on`, the UI **dims/labels long signals as suppressed**; breakouts are not presented as actionable. The regime flag is stored and shown prominently.

### 5.2 Relative Strength Score — RSS (CORRECTED — the core fix)

> **v2.0 was mathematically broken.** It divided asset return by SPY return, which inverts sign in down markets, explodes when SPY ≈ 0, and has no natural zero (neutral was 1.0, so "positive = green" mislabeled underperformers). v2.1 replaces the ratio with a **weighted excess log return**.

For each horizon `h ∈ {5, 20, 50}` trading days, using **adjusted** close `P`:

$$R_h(x) = \ln\!\left(\frac{P_{x,t}}{P_{x,t-h}}\right) \qquad \text{(log return of asset } x\text{ over } h\text{ days)}$$

$$\boxed{\;RSS = 0.2\big(R_{5}^{\text{asset}}-R_{5}^{\text{SPY}}\big) + 0.3\big(R_{20}^{\text{asset}}-R_{20}^{\text{SPY}}\big) + 0.5\big(R_{50}^{\text{asset}}-R_{50}^{\text{SPY}}\big)\;}$$

**Properties (all verified):**
- **Sign-stable:** `RSS > 0` ⇔ outperformed SPY, in *every* regime including down markets. Makes "positive = green" literally correct.
- **Natural zero:** `0` = matched SPY.
- **Additive & same-unit:** all three terms are log-return points, so the `0.2/0.3/0.5` weights are coherent and sum to 1.
- **No division by a return:** never undefined, never explodes.
- **Bounded:** fits storage; sanitize any residual NaN/Inf → `null` before serialization.

### 5.3 Cross-Sectional RS Rank & Slope (NEW)
Daily RSS *level* is noisy; leadership lives in **persistence and slope**.
- **`rss_rank`** = percentile rank of `RSS` across the 11 sectors that day, mapped to **1–99** (IBD-style). Regime-independent ordering for the leaderboard.
- **`rss_slope`** = linear-regression slope of the **RS line** `RS(t) = P_asset(t)/P_SPY(t)` over the trailing `slope_window` (default 20d). Positive slope = strengthening.
- **`rss_persist`** = number of the last `persist_window` (default 10) days that `rss_rank ≥ persist_rank_min` (default 70). Used to flag *confirmed* vs *emerging* leadership.

The leaderboard sorts by **`rss_rank`** (primary) with `rss_slope` as tiebreak.

### 5.4 Sector Breadth — MAP (retained, de-binarized)
For a sector of `n` components (the §6.4 universe):

$$MAP_{50} = \frac{1}{n}\sum_{i=1}^{n}\mathbb{I}\big(P_i > SMA_{50,i}\big)\times 100 \qquad MAP_{200}\ \text{defined analogously}$$

- Stored and displayed as a **continuous value** (not a single boolean).
- **Band:** `high` (≥ `map_high`, default 80), `mid` (≥ `map_mid`, default 50), `low` otherwise.
- **Rally flag with hysteresis** to stop flip-flopping: turns **on** at `MAP_50 ≥ 80`, **off** only below `70`.
- Reported with a **small-sample caveat**: with n≈15 each name is ~6.7%, so the value carries a `±` granularity note in the contract.
- **Used as a confirmation gate**, not a parallel artifact: a *confirmed leader* requires high `rss_rank` **AND** rising/high breadth. Rising price with falling breadth is surfaced as a **divergence warning**.

### 5.5 Volume Confirmation (NEW)
Price-only breakouts have high false-positive rates; "institutional participation" *is* volume.

```
breakout = (pct_from_52w_high >= -breakout_band)        # default within 5% of high
       AND (volume >= vol_mult * SMA_50(volume))         # default 1.5×
       AND regime_risk_on
```

A sector-level **up/down volume ratio** (`udvr`) is also computed and stored for context.

### 5.6 Holding Classification (QUANTIFIED — was undefined in v2.0)
Each holding in a sector's universe is assigned exactly one `classification` ∈ `{LEADER, SETUP, OTHER}` so the buckets are **exhaustive** (no holding silently vanishes):

| Class | Definition (all from `config.yml`) |
|---|---|
| **LEADER** | `pct_from_52w_high ≥ -5%` **AND** `P > SMA_50` **AND** `P > SMA_200` **AND** `regime_risk_on` |
| **SETUP** | `|pct_from_SMA_50| ≤ 3%` over the last 10 days **AND** `ATR_14 / ATR_14_median_1y ≤ 0.75` (volatility contraction) **AND** `P > SMA_200` (still in a longer uptrend) |
| **OTHER** | anything else (counted, not displayed in detail) |

- `pct_from_52w_high` uses the 52-week high computed from bars **strictly prior to `D`** on **adjusted** prices (no look-ahead — §6.3).
- All decision inputs (`pct_from_52w_high`, `pct_from_sma50`, `atr_ratio`, `above_sma50`, `above_sma200`, `rss`) are **persisted** so the classification is reproducible and auditable.

---

## 6. Data Sourcing

### 6.1 Provider strategy (best-practice answer)
A single **`PriceProvider` interface** with a priority chain; on failure, fall through:

1. **Tiingo** *(primary)* — high-quality split/dividend-adjusted EOD; official token. Best free adjusted-EOD fidelity.
2. **Alpaca Market Data** *(alternative/primary-eligible)* — official, stable; request daily bars with `adjustment=all`.
3. **Stooq** *(keyless fallback)* — free CSV EOD, decent coverage.
4. **yfinance** *(last-resort fallback)* — keyless but unofficial Yahoo scraping; fragile and rate-limited. Acceptable only as a backstop.

> Verify each provider's *current* free-tier symbol/day and rate limits at implementation time (limits drift). ~176 symbols once daily is small, but pace requests to stay within the active provider's caps.

### 6.2 Adjusted vs raw close
- All returns, SMAs, ATR, and 52-week highs use **adjusted** close consistently to avoid split/dividend false breakouts.
- **Store both** `close_raw` and `close_adj` so figures are auditable and re-adjustable.

### 6.3 Trailing-window fetch (fixes cold-start & look-ahead)
- Each run fetches a **trailing ~1-year (260 trading-day) window** of OHLCV per symbol. This is what makes `SMA_200`, `ATR_14`, and the 52-week high computable **on day 1** (no empty-DB bootstrap problem).
- The 52-week high and all moving averages are computed from bars **strictly prior to / including `D`** as appropriate, never from future bars.

### 6.4 Universe selection (fixes survivorship/look-ahead)
- Per sector, select the top `universe_size` (default 15) constituents by **trailing 20-day median dollar volume**, subject to a hard **liquidity floor** (`min_dollar_volume`, default $20M/day).
- The selected universe is **snapshotted with `effective_date`** so any historical view is point-in-time reproducible. Delisted names are retained in history; today's winners are **not** retro-projected into the past.

### 6.5 Batched download (replaces the v2.0 sleep loop)
- Use the provider's **multi-symbol batch** endpoint (one request for many tickers), not a per-ticker loop with `time.sleep(1)`. Apply provider-appropriate pacing only if a batch endpoint is unavailable.

### 6.6 Missing-data handling
- NaN/holiday/partial-session rows are dropped per symbol; if a symbol's history is insufficient for a metric, that metric is `null` (never fabricated).
- A `coverage` object records how many symbols succeeded vs were skipped (surfaced in the UI as a "partial data" note — §11).

---

## 7. Trade-Management Framework (explicit, optional, clearly labeled)

> v2.0 ended at "render tables," which is a screen, not a system. v2.1 specifies a framework so the output is *actionable*, while §1/§12 keep it honest: **these are guidelines pending backtest validation, not advice.**

- **Entry trigger:** a `SETUP` resolving upward (close back above the consolidation high) **or** a `LEADER` breakout (§5.5) — only while `regime_risk_on`.
- **Position sizing (volatility-normalized):** `shares = (risk_budget × equity) / (atr_stop_mult × ATR_14 × price_per_share)`; default `risk_budget = 0.5%`, `atr_stop_mult = 2`.
- **Initial stop:** `entry − atr_stop_mult × ATR_14`. **Trailing stop:** raise to `max(prior_stop, close − atr_stop_mult × ATR_14)`.
- **Exit / rotation:** exit when sector `rss_rank` falls below `exit_rank` (default 50) **or** price closes below `SMA_50` on above-average volume.
- **Rebalance cadence:** evaluate daily; act on confirmed signals only.

This framework is **displayed as guidance** (e.g., suggested stop/size columns) and is **off by default** behind a "Trade Assist" toggle; the core product is the screen.

---

## 8. Automation & Pipeline

### 8.1 Schedule (fixes the DST/timezone bug)
- **Cron is UTC-only and does not follow DST.** v2.0's "21:30 UTC = 16:30 EST" is only true in winter.
- **Schedule:** `30 22 * * 1-5` (**22:30 UTC**). This is comfortably after the 16:00 ET close in **both** EST (17:30 ET) and EDT (18:30 ET), giving settled/adjusted prints time to finalize.
- **Correctness is decoupled from firing time:** the job derives "today's ET trading date" in-code via the market calendar and proceeds only if the session is complete; a delayed/dropped cron run is harmless.
- Also expose **`workflow_dispatch`** for manual/backfill runs. Optionally drive the trigger from an external scheduler (`cron-job.org`/Cloud Scheduler → `workflow_dispatch`) to sidestep both cron jitter and the 60-day auto-disable.

### 8.2 Robustness
- **Self-healing backfill:** each run checks whether the *previous* expected trading date is also missing and backfills it.
- **Keepalive:** the daily commit to the `data` branch counts as repo activity, preventing the **60-day scheduled-workflow auto-disable**. (If a no-commit variant is ever used, add an explicit keepalive.)
- **Retries** with backoff around each provider call; fall through the provider chain on hard failure.

### 8.3 Idempotency (fixes `date == current_date`)
- Key on the **latest trading date `D`**, not the wall-clock calendar date.
- Before publishing, check whether `latest.json.as_of_trading_date == D`; if so, exit cleanly (no-op).
- History files are written idempotently (overwrite-by-date), so a re-run can never duplicate or corrupt a day.

### 8.4 Graceful degradation
- A failed *symbol* is logged and skipped; the run proceeds. `coverage` records the shortfall.
- A failed *provider* falls through the chain. Only if **all** providers fail does the run abort **without** overwriting the last good `latest.json` (the dashboard keeps showing the last valid day with a staleness banner).

### 8.5 Observability & secrets
- **Secrets** (Tiingo/Alpaca tokens) live in **encrypted GitHub Actions Secrets**, never in the repo. On public repos, **logs are world-readable** — never print secret-derived values; use `::add-mask::`.
- **Least privilege:** workflow `permissions:` is `contents: write` only on the publish job (to push the `data` branch), else `contents: read`.
- **Commit identity:** the publish uses the default **`GITHUB_TOKEN`** (which does **not** retrigger workflows — no infinite loop). **Do not** switch to a PAT for this push, which *would* create a loop.
- **Alerting:** the job **exits non-zero on hard failure** so GitHub emails the owner; per-symbol failure counts are emitted as a metric so silent partial data is visible.

---

## 9. Storage Design (best-practice answer: flat-file hybrid, no DB)

**Decision: do not use hosted Postgres.** Data volume is ~hundreds of KB/year, the access pattern is single-writer/read-mostly, and the free Postgres tiers add failure modes a static file does not (Supabase **pauses after ~7 days idle**; Neon **cold-starts** on every visit), plus DB credentials the static site otherwise never needs.

**Layout (on an orphan `data` branch, separate from code history):**
```
data/                      ← orphan branch, periodically squashed to bound size
├── latest.json            ← current snapshot ONLY; the sole file the dashboard fetches to boot
├── history/
│   ├── 2026-Q2.json       ← per-quarter rolled history (lazy-loaded for sparklines/backtests)
│   └── ...
└── universe.json          ← point-in-time sector membership with effective_date
```
- `latest.json` stays small and cache-friendly; the dashboard boots from it alone.
- History is **capped/rolled** (default: keep `history_days` = 365 trading days hot; older quarters archived) and **lazy-loaded** only when a user opens a chart.
- Keeping daily churn on an orphan branch (squashed periodically) prevents main-repo git bloat. *(A naive daily commit to `main` was reviewed and found low-impact over a few years, but the orphan-branch pattern is cleaner.)*
- **Escalation path only if needed:** SQLite committed in-repo (if multi-dimension filtering exceeds what JSON serves); hosted Postgres only if multi-user writes/auth are ever added — neither is in scope.
- The publisher **validates every payload against the §10 JSON Schema before writing**, so a bad fetch cannot publish a broken dashboard.

---

## 10. Data Contract (the boundary that enforces "no client math")

The dashboard renders **only** these pre-computed fields. Versioned via `schema_version`.

```jsonc
{
  "schema_version": 1,
  "generated_at_utc": "2026-06-26T22:35:11Z",
  "as_of_trading_date": "2026-06-26",
  "benchmark": "SPY",
  "status": "ok",                       // "ok" | "stale" | "no_trading_day" | "partial" | "error"
  "regime": {
    "state": "risk_on",                 // "risk_on" | "neutral" | "risk_off"
    "spy_above_200sma": true,
    "pct_sectors_above_200sma": 72.7
  },
  "coverage": { "symbols_expected": 176, "symbols_ok": 174, "symbols_skipped": 2 },
  "config_hash": "a1b2c3",              // hash of config.yml used for this run (auditability)
  "sectors": [
    {
      "ticker": "XLK",
      "name": "Technology",
      "rss": 0.0184,                    // excess log-return score (§5.2)
      "rss_rank": 96,                   // 1–99 cross-sectional (§5.3)
      "rss_slope": 0.0012,              // RS-line regression slope
      "rss_persist": 9,                 // days of last 10 with rank≥70
      "trend": "positive",             // "positive" | "neutral" | "negative" (from sign of rss)
      "breakout": true,                 // price+volume confirmed (§5.5)
      "map_50": 83.3,
      "map_200": 75.0,
      "map_band": "high",              // "high" | "mid" | "low"
      "rally_flag": true,               // hysteresis-stabilized (§5.4)
      "breadth_divergence": false,
      "udvr": 1.8,                      // up/down volume ratio
      "map_granularity_pct": 6.7,       // small-sample caveat (1/n)
      "rss_sparkline": [/* last 20 daily rss values */],
      "leaders": [
        { "ticker": "NVDA", "name": "NVIDIA", "rss": 0.031, "pct_from_52w_high": -1.2,
          "above_sma50": true, "above_sma200": true, "atr_14": 4.10,
          "suggested_stop": 118.4, "suggested_shares": 42 }
      ],
      "setups": [
        { "ticker": "MSFT", "name": "Microsoft", "pct_from_sma50": 0.6,
          "atr_ratio": 0.61, "vol_contraction": true, "above_sma200": true }
      ],
      "other_count": 3                  // holdings in neither bucket (so nothing vanishes silently)
    }
    // … 10 more sectors
  ]
}
```

**Contract rules:** every visual encoding (rank, color, marker, sparkline, suggested stop) maps to a field above. The client **formats and toggles disclosure only** — it computes nothing. NaN/Inf are serialized as `null`.

---

## 11. Frontend Specification

**Stack:** Vite + React + TypeScript + Tailwind (dark). Background `#0F172A`. Static build; **runtime-fetches** `/data/latest.json` (never bundle-imports it, so a data change needs no rebuild).

### 11.1 View 1 — Sector Leaderboard
- 11 sectors sorted by **`rss_rank`** (slope as tiebreak).
- Each row: rank number, sector name, `rss`, a **breadth pill** (`map_50` with band color + "High participation" at ≥80), `udvr`, a **breakout marker** (icon **+ text**, not color alone), and a 20-day **sparkline**.
- A prominent **regime banner** at the top (`risk_on/neutral/risk_off`); when not risk-on, long signals are visibly **dimmed/labeled "suppressed."**
- **`breadth_divergence`** sectors get a small warning chip.

### 11.2 View 2 — Sector Drill-Down
- Clicking a sector expands a disclosure region with **Table A — Leaders** and **Table B — Setups**, plus an "N others" count so users see nothing was dropped.
- Optional **"Trade Assist"** columns (suggested stop/size) behind a toggle (§7), off by default.

### 11.3 Cross-cutting UX requirements
- **Freshness:** header always shows `As of {as_of_trading_date} (updated {relative time})`. If `generated_at_utc` is >28h old on a weekday, show a non-blocking **"Data may be stale"** banner.
- **Never blank:** on missing/404/`error` JSON, render the **last good payload from `localStorage`** with a "showing last available data" notice. Empty Leaders/Setups render an inline empty-state row, never a missing table.
- **Caching:** fetch with `Cache-Control: no-cache` / revalidate (or `?v={as_of_trading_date}` bust); the daily JSON is **never** marked immutable. Document per-host headers (Netlify `_headers`, Vercel config).
- **Accessibility:** expand triggers are real `<button>`s with `aria-expanded`/`aria-controls`, keyboard-operable (Enter/Space), visible focus; nested tables have captions ("Leaders in Technology"). Status uses **color + text + icon** (color-blind safe); verify green/red ≥ 4.5:1 contrast on `#0F172A` (prefer Tailwind `emerald-400`/`red-400`).
- **Mobile:** below `md`, nested tables **reflow to stacked cards** (or sticky-ticker horizontal scroll showing the 2–3 priority columns).

---

## 12. Validation & Backtesting (gate before trusting any signal)

The methodology is a **hypothesis until this passes.** Required before promoting v2.1 from "build" to "trusted":

- **Walk-forward backtest** of the full ruleset (regime gate → corrected RSS/rank → MAP/volume confirm → Leader/Setup → §7 sizing/exits) across multiple regimes, **including 2018-Q4, 2020, 2022**.
- **Point-in-time universe** with delisted names included (no survivorship).
- **Net of transaction costs.**
- **Benchmarks (must beat to be validated):** buy-and-hold **SPY** and **equal-weight 11 sectors**.
- **Report:** CAGR, max drawdown, Sharpe/Sortino, hit rate, turnover, net return.
- **Parameter sensitivity:** show results are stable across nearby values of the §17 parameters (horizons, weights, MAP threshold, ATR multiples). If results hinge on exact values, that is overfit.

> If the system does not beat buy-and-hold SPY net of costs, it is **not** validated and the UI must continue to present itself as a screening tool only.

---

## 13. Security & Operations
- Public repo: world-readable logs ⇒ mask all secrets; no secret-derived output.
- Least-privilege workflow permissions; `GITHUB_TOKEN` only (no PAT).
- No PII, no user data, no auth surface.
- Frontend reads only the public JSON — **no API keys ever reach the browser.**
- Owner alerted by email on any failed scheduled run; coverage metric surfaces silent partial data.

---

## 14. QA & Safeguards (superset of v2.0)
- **Idempotent** by trading date (§8.3); re-runs are no-ops.
- **Graceful degradation** at symbol and provider level (§8.4); dashboard never goes blank (§11.3).
- **Schema validation** of the payload before publish (§9).
- **Self-healing backfill** of a missed prior day (§8.2).
- **Sanitize** NaN/Inf → `null` before serialization.
- **Sanity checks** reject implausible single-day SPY/asset moves before they reorder the board.

---

## 15. Milestones
1. **M1 — Pipeline skeleton:** provider interface (Tiingo + one fallback), trailing-window batched fetch, market-calendar date resolution, `config.yml`.
2. **M2 — Compute core:** regime gate, corrected RSS + rank/slope, MAP, volume confirm, Leader/Setup classification; emit & schema-validate `latest.json`.
3. **M3 — Publish:** orphan `data` branch writer, history rolling, idempotency + backfill, secrets/alerting.
4. **M4 — Dashboard:** React+Tailwind, View 1/2, freshness/empty/never-blank, accessibility, mobile, caching headers.
5. **M5 — Validation:** walk-forward backtest harness + sensitivity study (§12).

## 16. Out of Scope (v2.1)
Intraday data, order execution, accounts/auth, non-US/other asset classes, ML signal generation, a proven-alpha claim.

---

## 17. Configuration Parameters (centralized — `config.yml`)

| Param | Default | Used in | Note |
|---|---|---|---|
| `horizon_weights` | `{5:0.2, 20:0.3, 50:0.5}` | §5.2 | sum=1; sensitivity-test |
| `regime_sma` | 200 | §5.1 | SPY trend filter |
| `regime_breadth_min` | 50 (%) | §5.1 | % sectors > 200SMA |
| `slope_window` | 20 | §5.3 | RS-line slope |
| `persist_window` / `persist_rank_min` | 10 / 70 | §5.3 | confirmed vs emerging |
| `map_high` / `map_mid` | 80 / 50 | §5.4 | breadth bands |
| `map_rally_on` / `map_rally_off` | 80 / 70 | §5.4 | hysteresis |
| `breakout_band` | 5 (%) | §5.5/5.6 | distance to 52w high |
| `vol_mult` | 1.5 | §5.5 | breakout volume |
| `setup_sma50_band` | 3 (%) | §5.6 | consolidation tightness |
| `setup_atr_ratio_max` | 0.75 | §5.6 | volatility contraction |
| `universe_size` | 15 | §6.4 | names per sector |
| `min_dollar_volume` | 20,000,000 | §6.4 | liquidity floor |
| `risk_budget` / `atr_stop_mult` / `exit_rank` | 0.5% / 2 / 50 | §7 | trade framework |
| `history_days` | 365 | §9 | hot history window |
| `schedule_utc` | `30 22 * * 1-5` | §8.1 | 22:30 UTC |

---

## 18. Appendix — Optional SQLite Schema (escalation path only)

Only if/when JSON can no longer serve the read patterns. Note the corrected types and the sector-level metrics table that gives MAP/classification a home (the v2.0 schema had nowhere to store them):

```sql
CREATE TABLE assets (
  id           INTEGER PRIMARY KEY,
  ticker       TEXT UNIQUE NOT NULL,
  name         TEXT,
  asset_type   TEXT NOT NULL CHECK (asset_type IN ('SECTOR','STOCK')),
  sector_id    INTEGER REFERENCES assets(id)        -- real FK, not a VARCHAR ticker
);

CREATE TABLE sector_metrics (
  sector_id    INTEGER NOT NULL REFERENCES assets(id),
  date         TEXT NOT NULL,
  rss          REAL,            -- double; bounded by §5.2, no overflow risk
  rss_rank     INTEGER,
  rss_slope    REAL,
  map_50       REAL,
  map_200      REAL,
  rally_flag   INTEGER,
  breakout     INTEGER,
  PRIMARY KEY (sector_id, date)
);

CREATE TABLE stock_metrics (
  stock_id           INTEGER NOT NULL REFERENCES assets(id),
  sector_id          INTEGER NOT NULL REFERENCES assets(id),
  date               TEXT NOT NULL,
  close_raw          REAL NOT NULL,
  close_adj          REAL NOT NULL,
  sma_50             REAL,
  sma_200            REAL,
  atr_14             REAL,
  atr_ratio          REAL,
  pct_from_52w_high  REAL,
  pct_from_sma50     REAL,
  above_sma50        INTEGER NOT NULL,
  above_sma200       INTEGER NOT NULL,
  classification     TEXT CHECK (classification IN ('LEADER','SETUP','OTHER')),
  PRIMARY KEY (stock_id, date)
);

CREATE INDEX idx_sector_metrics_date ON sector_metrics(date DESC);
CREATE INDEX idx_stock_metrics_date  ON stock_metrics(date DESC);
-- UNIQUE(asset_id,date) is the PK above ⇒ idempotent upserts via ON CONFLICT.
```

---

## 19. Changelog (v2.0 → v2.1)

| # | v2.0 problem | v2.1 fix | §ref |
|---|---|---|---|
| 1 | **RSS = ratio of returns** — sign-inverts in down markets, explodes near SPY≈0, no natural zero | **Weighted excess log return** + cross-sectional rank/slope | 5.2, 5.3 |
| 2 | No market-regime filter (surfaced "leaders" in bear markets) | **Regime gate** (SPY>200SMA + breadth) gates all long signals | 5.1 |
| 3 | No entry/sizing/stop/exit rules ("dashboard, not a system") | Explicit **trade framework** (optional, labeled) + honest positioning | 1, 7 |
| 4 | No backtest/benchmark/validation | **Walk-forward validation** required vs SPY net of costs | 12 |
| 5 | Schema stored only 2 of ~8 metrics; MAP/classification homeless | Full **data contract** + sector/stock metrics tables | 10, 18 |
| 6 | "21:30 UTC = 16:30 EST" wrong 8 months/yr; cron ignores DST | **22:30 UTC** + in-code market-calendar gate | 8.1 |
| 7 | 16:30 ET too early for settled adjusted EOD | Run after close in both EST/EDT; validate final bar | 8.1 |
| 8 | `date == current_date` idempotency conflated calendar/trade date | Key on **latest trading date**; idempotent overwrite | 8.3 |
| 9 | Couldn't compute SMA50/52w-high from "daily close" (cold start) | **Trailing ~1y window** fetched each run | 6.3 |
| 10 | Adjusted/raw close mixing; coarse `NUMERIC(10,2)` | **Adjusted consistently**, store both, REAL/`NUMERIC(14,6)` | 6.2, 18 |
| 11 | Survivorship/look-ahead in "top-15" & 52w-high | **Point-in-time universe** + strictly-prior highs | 6.4 |
| 12 | "Setups" never quantified | Numeric ATR/SMA50 definitions; exhaustive buckets | 5.6 |
| 13 | No volume confirmation despite "institutional rally" | **Volume gate** + liquidity floor + udvr | 5.5, 6.4 |
| 14 | JSON contract undefined ("no client math" unenforceable) | **Frozen, versioned contract** | 10 |
| 15 | No freshness signal; CDN could serve stale JSON | `generated_at`/`status` + no-cache/revalidate | 10, 11.3 |
| 16 | Deploy trigger unspecified | Runtime-fetched static asset; no rebuild on data change | 11 |
| 17 | `NUMERIC(6,2)` RSS overflow could crash inserts | Bounded metric + `REAL`/sanitized NaN/Inf | 5.2, 18 |
| 18 | Postgres free-tier pause/cold-start hazards | **Flat-file hybrid**, orphan data branch, no DB | 9 |
| 19 | "1-second sleep" per query | **Batched** multi-symbol download | 6.5 |
| 20 | 60-day workflow auto-disable; best-effort cron | Daily commit keepalive + self-healing backfill + dispatch | 8.1, 8.2 |
| 21 | Secrets/observability unspecified (logs public!) | Encrypted secrets, masking, least-privilege, fail-loud alerts | 8.5, 13 |
| 22 | "2,000 min/mo" framed as a constraint | **Public repo ⇒ unlimited**; rationale corrected | 4 |
| 23 | Accessibility/mobile/empty-states absent | ARIA disclosure, card reflow, never-blank states | 11.3 |
| 24 | Arbitrary 80% MAP / 0.2-0.3-0.5 weights as constants | Centralized `config.yml` + sensitivity study | 17, 12 |
```
