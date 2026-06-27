import type { Regime, RegimeState } from '../types';
import { fmtPct } from '../lib/format';

interface RegimeBannerProps {
  regime: Regime;
}

interface RegimeStyle {
  label: string;
  icon: string;
  container: string;
  iconWrap: string;
  text: string;
}

const STYLES: Record<RegimeState, RegimeStyle> = {
  risk_on: {
    label: 'Risk On',
    icon: '▲',
    container: 'border-emerald-400/40 bg-emerald-400/10',
    iconWrap: 'bg-emerald-400/20 text-emerald-300',
    text: 'text-emerald-300',
  },
  neutral: {
    label: 'Neutral',
    icon: '■',
    container: 'border-amber-400/40 bg-amber-400/10',
    iconWrap: 'bg-amber-400/20 text-amber-300',
    text: 'text-amber-300',
  },
  risk_off: {
    label: 'Risk Off',
    icon: '▼',
    container: 'border-red-400/40 bg-red-400/10',
    iconWrap: 'bg-red-400/20 text-red-300',
    text: 'text-red-300',
  },
};

export default function RegimeBanner({ regime }: RegimeBannerProps) {
  const style = STYLES[regime.state] ?? STYLES.neutral;
  const longsSuppressed = regime.state !== 'risk_on';

  return (
    <section
      aria-label="Market regime"
      className={`rounded-lg border p-4 ${style.container}`}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className={`flex h-9 w-9 items-center justify-center rounded-full text-lg font-bold ${style.iconWrap}`}
          >
            {style.icon}
          </span>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-400">
              Market Regime
            </div>
            <div className={`text-xl font-semibold leading-tight ${style.text}`}>
              {style.label}
            </div>
          </div>
        </div>

        <div className="hidden h-8 w-px self-center bg-slate-600/50 sm:block" />

        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div>
            <dt className="text-slate-400">SPY vs 200-DMA</dt>
            <dd className="font-medium text-slate-100">
              SPY {regime.spy_above_200sma ? 'above' : 'below'} 200-DMA
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">Breadth</dt>
            <dd className="font-medium text-slate-100">
              {fmtPct(regime.pct_sectors_above_200sma)} of sectors above 200-DMA
            </dd>
          </div>
        </dl>
      </div>

      {longsSuppressed && (
        <p className="mt-3 flex items-center gap-2 text-sm text-amber-300">
          <span aria-hidden="true">⚠</span>
          <span>
            Long signals are suppressed in this regime. Breakout and leader
            markers are dimmed below.
          </span>
        </p>
      )}
    </section>
  );
}
