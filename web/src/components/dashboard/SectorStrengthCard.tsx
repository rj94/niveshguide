import Link from "next/link";

import {
  ScoreCardShell,
  ScoreTileGrid,
  type ScoreTile,
} from "@/components/dashboard/ScoreTileGrid";
import type { SectorCell } from "@/lib/dashboard-data";
import { formatPct } from "@/lib/format";

type Props = {
  sectors: SectorCell[];
};

function sourceHint(source: SectorCell["return3mSource"]): string | null {
  if (source === "index") return "Idx";
  if (source === "cap_weight") return "CW";
  if (source === "equal_weight") return "EW";
  return null;
}

export function SectorStrengthCard({ sectors }: Props) {
  const tiles: ScoreTile[] = sectors.slice(0, 8).map((sector) => {
    const ret = sector.return3m;
    const hint = sourceHint(sector.return3mSource);
    const showCwSecondary =
      sector.return3mSource === "index" &&
      sector.return3mCw !== null &&
      ret !== null;
    return {
      id: sector.name,
      name: sector.name,
      href: `/sectors/sector/${encodeURIComponent(sector.name)}`,
      score: sector.score,
      secondary:
        ret !== null
          ? `${hint ? `${hint} ` : ""}${formatPct(ret)} 3M`
          : null,
      tertiary: showCwSecondary
        ? `CW ${formatPct(sector.return3mCw)}`
        : null,
    };
  });

  return (
    <ScoreCardShell title="Sector Strength" chip="Nifty · CW">
      <ScoreTileGrid
        tiles={tiles}
        emptyText="No sector scores yet. Run score computation to populate this."
      />
      <div className="mt-4">
        <div
          className="h-2 rounded-full"
          style={{
            background:
              "linear-gradient(90deg, #ef4444 0%, #f97316 20%, #fbbf24 40%, #a3e635 60%, #10b981 80%, #059669 100%)",
          }}
        />
        <div className="mt-1.5 flex justify-between text-[11px] text-[var(--ink-muted)]">
          <span>Weak</span>
          <span>Strong</span>
        </div>
      </div>
      <Link
        href="/sectors"
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--accent-hover)] transition hover:text-white"
      >
        View Sector Analysis →
      </Link>
    </ScoreCardShell>
  );
}
