// Contract types mirroring contract/latest.schema.json.
// The frontend renders only these pre-computed fields and computes no quant math.

export type Status =
  | 'ok'
  | 'stale'
  | 'no_trading_day'
  | 'partial'
  | 'error'
  | 'intraday';
export type RegimeState = 'risk_on' | 'neutral' | 'risk_off';
export type Trend = 'positive' | 'neutral' | 'negative';
export type MapBand = 'high' | 'mid' | 'low';
export type Classification = 'LEADER' | 'SETUP' | 'OTHER';

export interface Regime {
  state: RegimeState;
  spy_above_200sma: boolean;
  pct_sectors_above_200sma: number;
}

export interface Coverage {
  symbols_expected: number;
  symbols_ok: number;
  symbols_skipped: number;
}

/** A leader holding row. Numeric fields may be null. */
export interface Holding {
  ticker: string;
  name?: string;
  classification: Classification;
  rss?: number | null;
  // Leader fields
  pct_from_52w_high?: number | null;
  above_sma50?: boolean | null;
  above_sma200?: boolean | null;
  atr_14?: number | null;
  suggested_stop?: number | null;
  suggested_shares?: number | null;
  // Setup fields
  pct_from_sma50?: number | null;
  atr_ratio?: number | null;
  vol_contraction?: boolean | null;
}

export interface Sector {
  ticker: string;
  name: string;
  rss: number | null;
  rss_rank: number | null;
  rss_slope?: number | null;
  rss_persist?: number | null;
  trend: Trend;
  breakout: boolean;
  map_50: number | null;
  map_200?: number | null;
  map_band: MapBand;
  rally_flag: boolean;
  breadth_divergence: boolean;
  udvr?: number | null;
  map_granularity_pct?: number | null;
  rss_sparkline: Array<number | null>;
  other_count: number;
  leaders: Holding[];
  setups: Holding[];
}

export interface LatestData {
  schema_version: number;
  generated_at_utc: string;
  as_of_trading_date: string;
  /** ISO timestamp of the intraday snapshot (present when intraday). */
  as_of_time_utc?: string | null;
  /** True for provisional intraday payloads. */
  intraday?: boolean;
  benchmark: string;
  status: Status;
  config_hash?: string;
  provider?: string;
  regime: Regime;
  coverage: Coverage;
  sectors: Sector[];
}
