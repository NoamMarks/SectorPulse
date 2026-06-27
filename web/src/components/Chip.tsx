import type { ReactNode } from 'react';

type ChipTone = 'emerald' | 'red' | 'amber' | 'slate' | 'muted';

const TONE_CLASSES: Record<ChipTone, string> = {
  emerald: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/30',
  red: 'bg-red-400/10 text-red-300 border-red-400/30',
  amber: 'bg-amber-400/10 text-amber-300 border-amber-400/30',
  slate: 'bg-slate-700/40 text-slate-200 border-slate-600',
  muted: 'bg-slate-800/60 text-slate-400 border-slate-700',
};

interface ChipProps {
  tone?: ChipTone;
  children: ReactNode;
  /** Native title attribute — used for the divergence explanation tooltip. */
  title?: string;
  className?: string;
  /** When true, fade the chip (e.g. breakout markers when regime != risk_on). */
  dimmed?: boolean;
}

export default function Chip({
  tone = 'slate',
  children,
  title,
  className = '',
  dimmed = false,
}: ChipProps) {
  return (
    <span
      title={title}
      className={[
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium',
        TONE_CLASSES[tone],
        dimmed ? 'opacity-40' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </span>
  );
}
