interface TradeAssistToggleProps {
  enabled: boolean;
  onChange: (next: boolean) => void;
}

/** Accessible switch controlling the global Trade Assist columns. */
export default function TradeAssistToggle({
  enabled,
  onChange,
}: TradeAssistToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className="group inline-flex items-center gap-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 transition-colors hover:border-slate-600 focus-visible:ring-2 focus-visible:ring-sky-400"
    >
      <span
        aria-hidden="true"
        className={[
          'relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors',
          enabled ? 'bg-emerald-500/80' : 'bg-slate-700',
        ].join(' ')}
      >
        <span
          className={[
            'inline-block h-4 w-4 transform rounded-full bg-slate-100 shadow transition-transform',
            enabled ? 'translate-x-4' : 'translate-x-0.5',
          ].join(' ')}
        />
      </span>
      <span className="font-medium">Trade Assist</span>
    </button>
  );
}
