// Pure formatting helpers. No quant math — just display formatting.

const EM_DASH = '—';

/** Render a possibly-null number to a fixed number of decimals, or em-dash. */
export function fmtNum(
  value: number | null | undefined,
  decimals = 2,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EM_DASH;
  }
  return value.toFixed(decimals);
}

/** Signed number, e.g. "+0.052" / "-0.045". */
export function fmtSigned(
  value: number | null | undefined,
  decimals = 3,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EM_DASH;
  }
  const s = value.toFixed(decimals);
  return value > 0 ? `+${s}` : s;
}

/** Percentage with a trailing %, e.g. "33.3%". */
export function fmtPct(
  value: number | null | undefined,
  decimals = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EM_DASH;
  }
  return `${value.toFixed(decimals)}%`;
}

/** Signed percentage, e.g. "-3.2%". */
export function fmtSignedPct(
  value: number | null | undefined,
  decimals = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EM_DASH;
  }
  const s = value.toFixed(decimals);
  return `${value > 0 ? '+' : ''}${s}%`;
}

/** Persistence as "9/10" given a count out of the sparkline window (10). */
export function fmtPersist(
  value: number | null | undefined,
  outOf = 10,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EM_DASH;
  }
  return `${value}/${outOf}`;
}

/**
 * Relative time like "3 hours ago" from an ISO-Z timestamp.
 * Returns em-dash if unparseable.
 */
export function relativeTime(
  iso: string | null | undefined,
  now: Date = new Date(),
): string {
  if (!iso) return EM_DASH;
  const then = new Date(iso);
  const ms = then.getTime();
  if (Number.isNaN(ms)) return EM_DASH;

  const diffSec = Math.round((now.getTime() - ms) / 1000);
  const abs = Math.abs(diffSec);
  const future = diffSec < 0;

  const units: Array<[number, string]> = [
    [60, 'second'],
    [60 * 60, 'minute'],
    [60 * 60 * 24, 'hour'],
    [60 * 60 * 24 * 7, 'day'],
    [60 * 60 * 24 * 30, 'week'],
    [60 * 60 * 24 * 365, 'month'],
    [Infinity, 'year'],
  ];

  let divisor = 1;
  let unit = 'second';
  let prevThreshold = 1;
  for (const [threshold, label] of units) {
    if (abs < threshold) {
      unit = label;
      divisor = prevThreshold;
      break;
    }
    prevThreshold = threshold;
  }

  const count = Math.max(1, Math.floor(abs / divisor));
  const plural = count === 1 ? '' : 's';
  return future
    ? `in ${count} ${unit}${plural}`
    : `${count} ${unit}${plural} ago`;
}

/**
 * Hours elapsed between an ISO-Z timestamp and `now`.
 * Returns null if unparseable.
 */
export function hoursSince(
  iso: string | null | undefined,
  now: Date = new Date(),
): number | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return null;
  return (now.getTime() - ms) / (1000 * 60 * 60);
}

/** True if `date` falls on Mon–Fri in the local timezone. */
export function isWeekday(date: Date = new Date()): boolean {
  const day = date.getDay();
  return day >= 1 && day <= 5;
}
