import type { Holding, Sector } from '../types';
import { fmtNum, fmtSigned, fmtSignedPct } from '../lib/format';

interface HoldingsTablesProps {
  sector: Sector;
  tradeAssist: boolean;
  /** Dim leader markers when the regime suppresses longs. */
  dimLongs: boolean;
}

/** Check / cross indicator for boolean fields (not color-only). */
function BoolMark({ value }: { value: boolean | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-500">—</span>;
  }
  return value ? (
    <span className="text-emerald-400" title="Yes">
      ✓
    </span>
  ) : (
    <span className="text-red-400" title="No">
      ✗
    </span>
  );
}

function EmptyRow({ colSpan, message }: { colSpan: number; message: string }) {
  return (
    <tr>
      <td
        colSpan={colSpan}
        className="px-3 py-3 text-center text-sm italic text-slate-500"
      >
        {message}
      </td>
    </tr>
  );
}

/* ----------------------------- Leaders ----------------------------- */

function LeadersTable({
  sector,
  tradeAssist,
  dimLongs,
}: {
  sector: Sector;
  tradeAssist: boolean;
  dimLongs: boolean;
}) {
  const { leaders, name } = sector;
  const baseCols = 5;
  const colSpan = baseCols + (tradeAssist ? 2 : 0);
  const rowClass = dimLongs ? 'opacity-50' : '';

  return (
    <>
      {/* Desktop / tablet table */}
      <table className="hidden w-full border-collapse text-sm md:table">
        <caption className="sr-only">{`Leaders in ${name}`}</caption>
        <thead>
          <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-400">
            <th scope="col" className="px-3 py-2 font-medium">
              Ticker
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              RSS
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              % from 52w high
            </th>
            <th scope="col" className="px-3 py-2 text-center font-medium">
              &gt; 50-DMA
            </th>
            <th scope="col" className="px-3 py-2 text-center font-medium">
              &gt; 200-DMA
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              ATR(14)
            </th>
            {tradeAssist && (
              <>
                <th scope="col" className="px-3 py-2 text-right font-medium">
                  Sugg. stop
                </th>
                <th scope="col" className="px-3 py-2 text-right font-medium">
                  Sugg. shares
                </th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {leaders.length === 0 ? (
            <EmptyRow
              colSpan={colSpan + 1}
              message="No leaders within 5% of highs today"
            />
          ) : (
            leaders.map((h: Holding) => (
              <tr
                key={h.ticker}
                className={`border-b border-slate-800 last:border-0 ${rowClass}`}
              >
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-mono font-medium text-slate-100"
                >
                  {h.ticker}
                </th>
                <td className="px-3 py-2 text-right font-mono text-slate-200">
                  {fmtSigned(h.rss, 3)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-slate-200">
                  {fmtSignedPct(h.pct_from_52w_high)}
                </td>
                <td className="px-3 py-2 text-center">
                  <BoolMark value={h.above_sma50} />
                </td>
                <td className="px-3 py-2 text-center">
                  <BoolMark value={h.above_sma200} />
                </td>
                <td className="px-3 py-2 text-right font-mono text-slate-200">
                  {fmtNum(h.atr_14, 2)}
                </td>
                {tradeAssist && (
                  <>
                    <td className="px-3 py-2 text-right font-mono text-slate-200">
                      {fmtNum(h.suggested_stop, 2)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-slate-200">
                      {h.suggested_shares ?? '—'}
                    </td>
                  </>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Mobile stacked cards */}
      <div className="space-y-2 md:hidden">
        {leaders.length === 0 ? (
          <p className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-3 text-center text-sm italic text-slate-500">
            No leaders within 5% of highs today
          </p>
        ) : (
          leaders.map((h) => (
            <div
              key={h.ticker}
              className={`rounded-md border border-slate-800 bg-slate-900/60 p-3 ${rowClass}`}
            >
              <div className="mb-2 font-mono text-base font-semibold text-slate-100">
                {h.ticker}
              </div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <dt className="text-slate-400">RSS</dt>
                <dd className="text-right font-mono text-slate-200">
                  {fmtSigned(h.rss, 3)}
                </dd>
                <dt className="text-slate-400">% from 52w high</dt>
                <dd className="text-right font-mono text-slate-200">
                  {fmtSignedPct(h.pct_from_52w_high)}
                </dd>
                <dt className="text-slate-400">&gt; 50-DMA</dt>
                <dd className="text-right">
                  <BoolMark value={h.above_sma50} />
                </dd>
                <dt className="text-slate-400">&gt; 200-DMA</dt>
                <dd className="text-right">
                  <BoolMark value={h.above_sma200} />
                </dd>
                <dt className="text-slate-400">ATR(14)</dt>
                <dd className="text-right font-mono text-slate-200">
                  {fmtNum(h.atr_14, 2)}
                </dd>
                {tradeAssist && (
                  <>
                    <dt className="text-slate-400">Sugg. stop</dt>
                    <dd className="text-right font-mono text-slate-200">
                      {fmtNum(h.suggested_stop, 2)}
                    </dd>
                    <dt className="text-slate-400">Sugg. shares</dt>
                    <dd className="text-right font-mono text-slate-200">
                      {h.suggested_shares ?? '—'}
                    </dd>
                  </>
                )}
              </dl>
            </div>
          ))
        )}
      </div>
    </>
  );
}

/* ------------------------------ Setups ----------------------------- */

function SetupsTable({ sector }: { sector: Sector }) {
  const { setups, name } = sector;

  return (
    <>
      {/* Desktop / tablet table */}
      <table className="hidden w-full border-collapse text-sm md:table">
        <caption className="sr-only">{`Setups in ${name}`}</caption>
        <thead>
          <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-400">
            <th scope="col" className="px-3 py-2 font-medium">
              Ticker
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              % from SMA50
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              ATR ratio
            </th>
            <th scope="col" className="px-3 py-2 text-center font-medium">
              Contraction
            </th>
            <th scope="col" className="px-3 py-2 text-center font-medium">
              &gt; 200-DMA
            </th>
          </tr>
        </thead>
        <tbody>
          {setups.length === 0 ? (
            <EmptyRow colSpan={5} message="No setups forming today" />
          ) : (
            setups.map((h: Holding) => (
              <tr
                key={h.ticker}
                className="border-b border-slate-800 last:border-0"
              >
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-mono font-medium text-slate-100"
                >
                  {h.ticker}
                </th>
                <td className="px-3 py-2 text-right font-mono text-slate-200">
                  {fmtSignedPct(h.pct_from_sma50)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-slate-200">
                  {fmtNum(h.atr_ratio, 2)}
                </td>
                <td className="px-3 py-2 text-center">
                  {h.vol_contraction ? (
                    <span className="text-emerald-400" title="Volatility contraction">
                      ✓
                    </span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <BoolMark value={h.above_sma200} />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Mobile stacked cards */}
      <div className="space-y-2 md:hidden">
        {setups.length === 0 ? (
          <p className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-3 text-center text-sm italic text-slate-500">
            No setups forming today
          </p>
        ) : (
          setups.map((h) => (
            <div
              key={h.ticker}
              className="rounded-md border border-slate-800 bg-slate-900/60 p-3"
            >
              <div className="mb-2 font-mono text-base font-semibold text-slate-100">
                {h.ticker}
              </div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <dt className="text-slate-400">% from SMA50</dt>
                <dd className="text-right font-mono text-slate-200">
                  {fmtSignedPct(h.pct_from_sma50)}
                </dd>
                <dt className="text-slate-400">ATR ratio</dt>
                <dd className="text-right font-mono text-slate-200">
                  {fmtNum(h.atr_ratio, 2)}
                </dd>
                <dt className="text-slate-400">Contraction</dt>
                <dd className="text-right">
                  {h.vol_contraction ? (
                    <span className="text-emerald-400">✓</span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </dd>
                <dt className="text-slate-400">&gt; 200-DMA</dt>
                <dd className="text-right">
                  <BoolMark value={h.above_sma200} />
                </dd>
              </dl>
            </div>
          ))
        )}
      </div>
    </>
  );
}

/* ----------------------------- Wrapper ----------------------------- */

export default function HoldingsTables({
  sector,
  tradeAssist,
  dimLongs,
}: HoldingsTablesProps) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div>
        <h4 className="mb-2 text-sm font-semibold text-slate-300">
          Leaders{' '}
          <span className="font-normal text-slate-500">in {sector.name}</span>
        </h4>
        <LeadersTable
          sector={sector}
          tradeAssist={tradeAssist}
          dimLongs={dimLongs}
        />
        {tradeAssist && (
          <p className="mt-2 text-xs italic text-slate-500">
            Guidance only — not investment advice. Backtest before risking
            capital.
          </p>
        )}
        {sector.other_count > 0 && (
          <p className="mt-2 text-xs text-slate-500">
            +{sector.other_count} others
          </p>
        )}
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold text-slate-300">
          Setups{' '}
          <span className="font-normal text-slate-500">in {sector.name}</span>
        </h4>
        <SetupsTable sector={sector} />
      </div>
    </div>
  );
}
