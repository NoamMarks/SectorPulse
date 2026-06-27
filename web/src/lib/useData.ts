import { useCallback, useEffect, useRef, useState } from 'react';
import type { LatestData } from '../types';
import { DATA_URL, REFRESH_MS } from './config';

const CACHE_KEY = 'sectorpulse:last';

export type DataSource = 'network' | 'cache';

export interface DataState {
  /** The data to render, or null when nothing is available at all. */
  data: LatestData | null;
  /** Where the rendered data came from. */
  source: DataSource | null;
  /** True only during the INITIAL load. Background refetches never set this. */
  loading: boolean;
  /**
   * True when the network fetch failed but we are showing cached data.
   * Drives the "Showing last available data" notice.
   */
  usingFallback: boolean;
  /** Hard error: fetch failed AND there is no cache to fall back to. */
  error: string | null;
  /** When the last SUCCESSFUL network fetch landed (null until first success). */
  lastUpdated: Date | null;
  /** Manually re-trigger a fetch. */
  refetch: () => void;
}

function readCache(): LatestData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LatestData;
    if (!parsed || !Array.isArray(parsed.sectors)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeCache(data: LatestData): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  } catch {
    // Storage unavailable / quota exceeded — non-fatal, just skip caching.
  }
}

/** Lightweight runtime shape guard so a malformed payload doesn't crash render. */
function isLatestData(value: unknown): value is LatestData {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return Array.isArray(v.sectors) && typeof v.regime === 'object' && v.regime !== null;
}

export function useData(): DataState {
  const [data, setData] = useState<LatestData | null>(null);
  const [source, setSource] = useState<DataSource | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // True until the first fetch (success or fallback) resolves. While true a
  // failure surfaces a hard error/loading screen; afterwards, background
  // refetch failures are swallowed so the displayed data is never blanked.
  const initialLoadRef = useRef<boolean>(true);
  // Guards against overlapping fetches (e.g. interval + focus firing together).
  const inFlightRef = useRef<boolean>(false);
  const mountedRef = useRef<boolean>(true);

  const runFetch = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    // `cache: 'no-cache'` forces revalidation; the timestamp buster defeats any
    // intermediary that ignores the header so intraday updates land promptly.
    const url = `${DATA_URL}?t=${Date.now()}`;

    try {
      const res = await fetch(url, { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: unknown = await res.json();
      if (!isLatestData(json)) throw new Error('Malformed data payload');

      if (!mountedRef.current) return;
      // Only on SUCCESS do we replace the displayed payload.
      writeCache(json);
      setData(json);
      setSource('network');
      setUsingFallback(false);
      setError(null);
      setLastUpdated(new Date());
      initialLoadRef.current = false;
      setLoading(false);
    } catch {
      if (!mountedRef.current) return;

      if (initialLoadRef.current) {
        // First load failed — try the cache, else surface a hard error.
        const cached = readCache();
        if (cached) {
          setData(cached);
          setSource('cache');
          setUsingFallback(true);
          setError(null);
        } else {
          setData(null);
          setSource(null);
          setUsingFallback(false);
          setError('Unable to load sector data, and no cached copy is available.');
        }
        initialLoadRef.current = false;
        setLoading(false);
      }
      // Background refetch failure: keep the current data on screen untouched.
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  const refetch = useCallback(() => {
    void runFetch();
  }, [runFetch]);

  useEffect(() => {
    mountedRef.current = true;

    // Initial load.
    void runFetch();

    // Poll on an interval.
    const intervalId = window.setInterval(() => {
      void runFetch();
    }, REFRESH_MS);

    // Refetch when the user returns to the tab/window.
    const onFocus = () => {
      void runFetch();
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void runFetch();
      }
    };

    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      mountedRef.current = false;
      window.clearInterval(intervalId);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [runFetch]);

  return { data, source, loading, usingFallback, error, lastUpdated, refetch };
}
