import type { LatestData } from '../types';
import { relativeTime } from '../lib/format';
import LiveBadge from './LiveBadge';

interface FreshnessHeaderProps {
  data: LatestData;
  now: Date;
}

/** True when the payload represents a provisional intraday snapshot. */
export function isIntraday(data: LatestData): boolean {
  return data.status === 'intraday' || data.intraday === true;
}

function Separator() {
  return (
    <span aria-hidden="true" className="text-slate-600">
      ·
    </span>
  );
}

function ContextBits({ data }: { data: LatestData }) {
  return (
    <>
      {data.benchmark && (
        <>
          <Separator />
          <span>
            benchmark{' '}
            <span className="font-mono text-slate-300">{data.benchmark}</span>
          </span>
        </>
      )}
      <Separator />
      <span>
        coverage{' '}
        <span className="text-slate-300">
          {data.coverage.symbols_ok}/{data.coverage.symbols_expected}
        </span>
      </span>
    </>
  );
}

/**
 * Freshness header.
 * - Intraday: LIVE badge + "Intraday · provisional · auto-refreshing" with the
 *   intraday snapshot clock.
 * - Settled EOD: "As of {date} · updated {relative}".
 */
export default function FreshnessHeader({ data, now }: FreshnessHeaderProps) {
  if (isIntraday(data)) {
    const snapshot = data.as_of_time_utc ?? data.generated_at_utc;
    return (
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-400">
        <LiveBadge />
        <span className="text-slate-300">Intraday</span>
        <Separator />
        <span className="text-amber-300">provisional</span>
        <Separator />
        <span>auto-refreshing</span>
        <Separator />
        <span>
          snapshot{' '}
          <time dateTime={snapshot} className="text-slate-300">
            {relativeTime(snapshot, now)}
          </time>
        </span>
        <ContextBits data={data} />
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm text-slate-400">
      <span>
        As of{' '}
        <span className="font-medium text-slate-200">
          {data.as_of_trading_date}
        </span>
      </span>
      <Separator />
      <span>
        updated{' '}
        <time dateTime={data.generated_at_utc} className="text-slate-300">
          {relativeTime(data.generated_at_utc, now)}
        </time>
      </span>
      <ContextBits data={data} />
    </div>
  );
}
