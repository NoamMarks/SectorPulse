/** Small pulsing-green "LIVE" badge for provisional intraday payloads. */
export default function LiveBadge() {
  return (
    <span
      role="status"
      aria-label="Live intraday data, auto-refreshing"
      className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-400/10 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-emerald-300"
    >
      <span className="relative flex h-2 w-2" aria-hidden="true">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
      </span>
      LIVE
    </span>
  );
}
