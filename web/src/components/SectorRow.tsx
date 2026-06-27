import { useId, useState } from 'react';
import type { Sector, Trend, MapBand } from '../types';
import { fmtSigned, fmtPct, fmtPersist, fmtNum } from '../lib/format';
import Chip from './Chip';
import Sparkline from './Sparkline';
import HoldingsTables from './HoldingsTables';

interface SectorRowProps {
  sector: Sector;
  tradeAssist: boolean;
  /** When true (regime != risk_on), dim breakout/leader markers. */
  dimLongs: boolean;
}

const TREND_META: Record<
  Trend,
  { icon: string; label: string; className: string }
> = {
  positive: { icon: '▲', label: 'Leading', className: 'text-emerald-400' },
  negative: { icon: '▼', label: 'Lagging', className: 'text-red-400' },
  neutral: { icon: '■', label: 'Neutral', className: 'text-slate-400' },
};

const BAND_TONE: Record<MapBand, 'emerald' | 'slate' | 'muted'> = {
  high: 'emerald',
  mid: 'slate',
  low: 'muted',
};

function TrendIndicator({ trend }: { trend: Trend }) {
  const meta = TREND_META[trend] ?? TREND_META.neutral;
  return (
    <span className={`inline-flex items-center gap-1 font-medium ${meta.className}`}>
      <span aria-hidden="true">{meta.icon}</span>
      <span>{meta.label}</span>
    </span>
  );
}

function BreadthPill({ sector }: { sector: Sector }) {
  const tone = BAND_TONE[sector.map_band] ?? 'slate';
  const label =
    sector.map_band === 'high' ? 'High participation' : `${fmtPct(sector.map_50)}`;
  const title =
    sector.map_band === 'high'
      ? `${fmtPct(sector.map_50)} of holdings above their 50-DMA — high participation`
      : `${fmtPct(sector.map_50)} of holdings above their 50-DMA (${sector.map_band} band)`;
  return (
    <Chip tone={tone} title={title}>
      {label}
    </Chip>
  );
}

export default function SectorRow({
  sector,
  tradeAssist,
  dimLongs,
}: SectorRowProps) {
  const [expanded, setExpanded] = useState(false);
  const regionId = useId();
  const buttonId = useId();

  const trendMeta = TREND_META[sector.trend] ?? TREND_META.neutral;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
      <button
        type="button"
        id={buttonId}
        aria-expanded={expanded}
        aria-controls={regionId}
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-3 text-left transition-colors hover:bg-slate-800/60 focus-visible:ring-2 focus-visible:ring-sky-400 sm:gap-4 sm:px-4"
      >
        {/* Rank */}
        <div className="flex w-10 shrink-0 flex-col items-center">
          <span className="text-2xl font-bold leading-none tabular-nums text-slate-100">
            {sector.rss_rank ?? '—'}
          </span>
          <span className="text-[10px] uppercase tracking-wide text-slate-500">
            rank
          </span>
        </div>

        {/* Name + ticker */}
        <div className="min-w-0 flex-1">
          <div className="truncate font-semibold text-slate-100">
            {sector.name}
          </div>
          <div className="font-mono text-xs text-slate-400">{sector.ticker}</div>
        </div>

        {/* RSS */}
        <div className="w-20 shrink-0 text-right">
          <div className="font-mono text-sm font-medium tabular-nums text-slate-100">
            {fmtSigned(sector.rss, 3)}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            rss
          </div>
        </div>

        {/* Trend (always visible) */}
        <div className="w-24 shrink-0 text-sm">
          <TrendIndicator trend={sector.trend} />
        </div>

        {/* Breadth pill (always visible) */}
        <div className="hidden shrink-0 sm:block">
          <BreadthPill sector={sector} />
        </div>

        {/* Persist (md+) */}
        <div className="hidden w-16 shrink-0 text-right text-sm text-slate-300 md:block">
          <span className="tabular-nums">{fmtPersist(sector.rss_persist)}</span>
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            persist
          </div>
        </div>

        {/* UDVR (md+) */}
        <div className="hidden w-16 shrink-0 text-right text-sm text-slate-300 md:block">
          <span className="tabular-nums">{fmtNum(sector.udvr, 2)}</span>
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            udvr
          </div>
        </div>

        {/* Markers: breakout + divergence */}
        <div className="hidden shrink-0 items-center gap-1.5 lg:flex">
          {sector.breakout && (
            <Chip
              tone="emerald"
              dimmed={dimLongs}
              title="Breakout — relative strength breaking to new highs"
            >
              <span aria-hidden="true">⟲</span>
              <span>Breakout</span>
            </Chip>
          )}
          {sector.breadth_divergence && (
            <Chip
              tone="amber"
              title="Divergence — price leading but breadth weak"
            >
              Divergence
            </Chip>
          )}
        </div>

        {/* Sparkline (md+) */}
        <div className="hidden shrink-0 md:block">
          <Sparkline values={sector.rss_sparkline} />
        </div>

        {/* Expand chevron */}
        <div
          aria-hidden="true"
          className={`shrink-0 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
        >
          ▾
        </div>
      </button>

      {/* Markers row for small screens (breakout/divergence not shown above lg) */}
      {(sector.breakout || sector.breadth_divergence) && (
        <div className="flex flex-wrap items-center gap-1.5 px-3 pb-2 lg:hidden sm:px-4">
          {sector.breakout && (
            <Chip
              tone="emerald"
              dimmed={dimLongs}
              title="Breakout — relative strength breaking to new highs"
            >
              <span aria-hidden="true">⟲</span>
              <span>Breakout</span>
            </Chip>
          )}
          {sector.breadth_divergence && (
            <Chip tone="amber" title="Divergence — price leading but breadth weak">
              Divergence
            </Chip>
          )}
        </div>
      )}

      {/* Expandable region (View 2) */}
      <div
        id={regionId}
        role="region"
        aria-labelledby={buttonId}
        hidden={!expanded}
        className="border-t border-slate-800 bg-slate-950/40 px-3 py-4 sm:px-4"
      >
        {/* Inline summary chips visible inside the drill-down too */}
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-400">
          <span className="inline-flex items-center gap-1">
            <span aria-hidden="true">{trendMeta.icon}</span>
            {trendMeta.label}
          </span>
          <span aria-hidden="true">·</span>
          <BreadthPill sector={sector} />
          <span aria-hidden="true">·</span>
          <span>persist {fmtPersist(sector.rss_persist)}</span>
          <span aria-hidden="true">·</span>
          <span>udvr {fmtNum(sector.udvr, 2)}</span>
        </div>
        <HoldingsTables
          sector={sector}
          tradeAssist={tradeAssist}
          dimLongs={dimLongs}
        />
      </div>
    </div>
  );
}
