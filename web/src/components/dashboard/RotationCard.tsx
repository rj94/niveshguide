import Link from "next/link";

import {
  ScoreCardShell,
  ScoreTileGrid,
  type ScoreTile,
} from "@/components/dashboard/ScoreTileGrid";
import type { RotationItem } from "@/lib/dashboard-data";
import { formatPct } from "@/lib/format";

type Props = {
  items: RotationItem[];
};

function sourceHint(source: RotationItem["return3mSource"]): string | null {
  if (source === "index") return "Idx";
  if (source === "cap_weight") return "CW";
  if (source === "equal_weight") return "EW";
  return null;
}

export function RotationCard({ items }: Props) {
  const tiles: ScoreTile[] = items.slice(0, 8).map((item) => {
    const hint = sourceHint(item.return3mSource);
    const showCwSecondary =
      item.return3mSource === "index" &&
      item.return3mCw !== null &&
      item.scoreChange !== null;
    const state = item.state?.replaceAll("_", " ") || "";
    const change =
      item.scoreChange === null
        ? null
        : `${hint ? `${hint} ` : ""}${formatPct(item.scoreChange, 1)} 3M`;
    return {
      id: item.id,
      name: item.name,
      href: `/sectors/sector/${encodeURIComponent(item.name)}`,
      score: item.score,
      secondary: [state, change].filter(Boolean).join(" · ") || null,
      tertiary: showCwSecondary
        ? `CW ${formatPct(item.return3mCw, 1)}`
        : null,
    };
  });

  return (
    <ScoreCardShell title="Sector Rotation" chip="Improving / Weakening">
      <ScoreTileGrid
        tiles={tiles}
        emptyText="No rotation movers yet. Need Improving / Weakening sector states from scores."
      />
      <Link
        href="/sectors"
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--accent-hover)] transition hover:text-white"
      >
        View Sector Analysis →
      </Link>
    </ScoreCardShell>
  );
}
