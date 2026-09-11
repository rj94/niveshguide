import type { StrengthRow } from "@/types/sector";
import type { RotationItem, SectorCell } from "@/lib/dashboard-data";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

export function mapSectorCell(s: StrengthRow): SectorCell {
  return {
    name: s.name,
    score: num(s.strength_score) ?? 0,
    scoreChange1w: num(s.score_change_1w),
    return3m: num(s.return_3m),
    return3mCw: num(s.return_3m_cw),
    return3mSource: s.return_3m_source,
  };
}

export function mapRotationItem(s: StrengthRow): RotationItem {
  return {
    id: s.name,
    name: s.name,
    score: num(s.strength_score) ?? 0,
    scoreChange: num(s.return_3m),
    return3mCw: num(s.return_3m_cw),
    return3mSource: s.return_3m_source,
    state: s.rotation_state,
  };
}

/**
 * Desk mapping: Improving / Weakening first (by abs momentum), then Leading/Lagging fill.
 * Shared by SSR load-dashboard and MarketingHome live refresh.
 */
export function buildRotationItems(
  rows: StrengthRow[],
  opts?: { preferDistinctFrom?: SectorCell[]; max?: number },
): RotationItem[] {
  const max = opts?.max ?? 8;
  const preferDistinct = opts?.preferDistinctFrom ?? [];
  const byState = (state: string) =>
    rows
      .filter((s) => (s.rotation_state || "").toLowerCase() === state.toLowerCase())
      .sort((a, b) => {
        const ma = Math.abs(num(a.momentum_score) ?? 0);
        const mb = Math.abs(num(b.momentum_score) ?? 0);
        if (mb !== ma) return mb - ma;
        return (num(b.strength_score) ?? 0) - (num(a.strength_score) ?? 0);
      });

  const rotation: RotationItem[] = [];
  const seen = new Set<string>();
  for (const state of ["Improving", "Weakening"] as const) {
    for (const row of byState(state)) {
      if (seen.has(row.name)) continue;
      rotation.push(mapRotationItem(row));
      seen.add(row.name);
      if (rotation.length >= max) return rotation;
    }
  }
  if (rotation.length < 5) {
    for (const state of ["Leading", "Lagging"] as const) {
      for (const row of byState(state)) {
        if (seen.has(row.name)) continue;
        if (preferDistinct.some((c) => c.name === row.name) && rotation.length >= 3) continue;
        rotation.push(mapRotationItem(row));
        seen.add(row.name);
        if (rotation.length >= Math.max(5, max)) break;
      }
      if (rotation.length >= 5) break;
    }
  }
  return rotation.slice(0, max);
}

/** Top industries by |1W score change|, fallback strength. Clear % for Sector Performance. */
export function rankSectorsForPerformance(rows: StrengthRow[], limit = 8): SectorCell[] {
  const scored = rows
    .map(mapSectorCell)
    .filter((s) => s.name)
    .sort((a, b) => {
      const aHas = a.scoreChange1w != null;
      const bHas = b.scoreChange1w != null;
      if (aHas !== bHas) return aHas ? -1 : 1;
      const ca = Math.abs(a.scoreChange1w ?? 0);
      const cb = Math.abs(b.scoreChange1w ?? 0);
      if (cb !== ca) return cb - ca;
      return b.score - a.score;
    });
  return scored.slice(0, limit);
}
