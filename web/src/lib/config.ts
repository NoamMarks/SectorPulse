// Runtime configuration.
//
// In production VITE_DATA_URL points at the live data-branch raw URL; locally
// it falls back to the static file served from /public.
export const DATA_URL: string =
  import.meta.env.VITE_DATA_URL ?? '/data/latest.json';

/** Auto-refresh interval for intraday/live polling (ms). */
export const REFRESH_MS = 60000;
