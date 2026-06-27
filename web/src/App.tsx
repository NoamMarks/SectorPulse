import { useMemo, useState } from 'react';
import { useData } from './lib/useData';
import { hoursSince, isWeekday } from './lib/format';
import RegimeBanner from './components/RegimeBanner';
import FreshnessHeader, { isIntraday } from './components/FreshnessHeader';
import Leaderboard from './components/Leaderboard';
import TradeAssistToggle from './components/TradeAssistToggle';

const STALE_THRESHOLD_HOURS = 28;

function Notice({
  tone,
  children,
}: {
  tone: 'amber' | 'slate';
  children: React.ReactNode;
}) {
  const toneClass =
    tone === 'amber'
      ? 'border-amber-400/40 bg-amber-400/10 text-amber-200'
      : 'border-slate-700 bg-slate-800/60 text-slate-300';
  return (
    <div
      role="status"
      className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${toneClass}`}
    >
      <span aria-hidden="true">ⓘ</span>
      <span>{children}</span>
    </div>
  );
}

function ErrorState({
  onRetry,
  message,
}: {
  onRetry: () => void;
  message?: string | null;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="max-w-md rounded-lg border border-slate-800 bg-slate-900 p-8 text-center">
        <div className="mb-3 text-3xl" aria-hidden="true">
          📡
        </div>
        <h1 className="mb-2 text-lg font-semibold text-slate-100">
          Couldn&apos;t load sector data
        </h1>
        <p className="mb-5 text-sm text-slate-400">
          {message ??
            "We weren't able to reach the data feed, and there's no cached copy on this device yet. Please check your connection and try again."}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-sky-400"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="flex items-center gap-3 text-slate-400">
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-slate-200"
          aria-hidden="true"
        />
        <span>Loading SectorPulse…</span>
      </div>
    </div>
  );
}

export default function App() {
  const { data, loading, usingFallback, error, lastUpdated, refetch } = useData();
  const [tradeAssist, setTradeAssist] = useState(false);

  // Anchor "now" to the last successful fetch so relative times re-derive on
  // each refresh (and stay consistent within a render).
  const now = useMemo(
    () => new Date(),
    [lastUpdated],
  );

  if (loading && !data) {
    return <LoadingState />;
  }

  if (!data) {
    return <ErrorState onRetry={refetch} message={error} />;
  }

  const dimLongs = data.regime.state !== 'risk_on';
  const intraday = isIntraday(data);

  const elapsedHours = hoursSince(data.generated_at_utc, now);
  // The >28h stale banner only applies to settled EOD payloads — intraday
  // snapshots are expected to be fresh and are flagged provisional instead.
  const showStaleBanner =
    !intraday &&
    elapsedHours !== null &&
    elapsedHours > STALE_THRESHOLD_HOURS &&
    isWeekday(now);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
        {/* Header */}
        <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Sector<span className="text-emerald-400">Pulse</span>
            </h1>
            <div className="mt-1">
              <FreshnessHeader data={data} now={now} />
            </div>
          </div>
          <div className="shrink-0">
            <TradeAssistToggle enabled={tradeAssist} onChange={setTradeAssist} />
          </div>
        </header>

        {/* Non-blocking notices */}
        <div className="mb-4 space-y-2">
          {usingFallback && (
            <Notice tone="slate">
              Showing last available data — we couldn&apos;t fetch a fresh copy.
            </Notice>
          )}
          {showStaleBanner && (
            <Notice tone="amber">
              Data may be stale — the latest update is over {STALE_THRESHOLD_HOURS}{' '}
              hours old.
            </Notice>
          )}
          {intraday && (
            <Notice tone="amber">
              Intraday numbers are provisional and may revise until the market
              close. Auto-refreshing every minute.
            </Notice>
          )}
          {data.status !== 'ok' && data.status !== 'intraday' && (
            <Notice tone="amber">
              Pipeline status: <span className="font-medium">{data.status}</span>.
              Some figures may be incomplete.
            </Notice>
          )}
        </div>

        {/* Regime banner */}
        <div className="mb-6">
          <RegimeBanner regime={data.regime} />
        </div>

        {/* Leaderboard (View 1) */}
        <section aria-label="Sector leaderboard">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
              Sector Leaderboard
            </h2>
            <span className="text-xs text-slate-500">
              {data.sectors.length} sectors · expand a row for holdings
            </span>
          </div>
          <Leaderboard
            sectors={data.sectors}
            tradeAssist={tradeAssist}
            dimLongs={dimLongs}
          />
        </section>

        {/* Footer */}
        <footer className="mt-10 border-t border-slate-800 pt-4 text-xs text-slate-500">
          <p>
            SectorPulse renders pre-computed signals only. Guidance is
            informational and not investment advice.
            {data.provider ? ` · provider: ${data.provider}` : ''}
            {data.config_hash ? ` · config ${data.config_hash}` : ''}
          </p>
        </footer>
      </div>
    </div>
  );
}
