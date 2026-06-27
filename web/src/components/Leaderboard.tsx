import type { Sector } from '../types';
import SectorRow from './SectorRow';

interface LeaderboardProps {
  sectors: Sector[];
  tradeAssist: boolean;
  dimLongs: boolean;
}

/**
 * Renders the pre-sorted sector list. Order is preserved exactly as delivered
 * in the JSON — no client-side re-sorting.
 */
export default function Leaderboard({
  sectors,
  tradeAssist,
  dimLongs,
}: LeaderboardProps) {
  if (sectors.length === 0) {
    return (
      <p className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-6 text-center text-sm text-slate-400">
        No sectors available in this dataset.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {sectors.map((sector) => (
        <SectorRow
          key={sector.ticker}
          sector={sector}
          tradeAssist={tradeAssist}
          dimLongs={dimLongs}
        />
      ))}
    </div>
  );
}
