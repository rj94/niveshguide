import { cn } from "@/lib/utils";
import type { StrengthRow } from "@/types/sector";

export function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

export function scoreOf(row: StrengthRow): number | null {
  return num(
    row.strength_score ?? row.sector_strength_score ?? row.industry_strength_score,
  );
}

export function change5d(row: StrengthRow): number | null {
  return num(row.score_change_5d ?? row.score_change_1w);
}

export function change21d(row: StrengthRow): number | null {
  return num(row.score_change_21d ?? row.score_change_1m);
}

export function strengthLabel(score: number | null): string {
  if (score === null) return "—";
  if (score >= 91) return "Exceptional";
  if (score >= 76) return "Very Strong";
  if (score >= 61) return "Strong";
  if (score >= 41) return "Neutral";
  if (score >= 21) return "Weak";
  return "Very Weak";
}

export function stateClass(state: string | null | undefined): string {
  const key = (state || "").toLowerCase();
  if (key === "leading") return "text-[var(--up)]";
  if (key === "improving") return "text-[var(--accent)]";
  if (key === "weakening") return "text-[var(--ink-soft)]";
  if (key === "lagging") return "text-[var(--down)]";
  return "text-[var(--ink-muted)]";
}

export function ChangeCell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-[var(--ink-muted)]">—</span>;
  return (
    <span
      className={cn(
        "tabular-nums",
        value > 0 ? "text-[var(--up)]" : value < 0 ? "text-[var(--down)]" : "text-[var(--ink-muted)]",
      )}
    >
      {value > 0 ? "↑ " : value < 0 ? "↓ " : ""}
      {Math.abs(value).toFixed(1)}
    </span>
  );
}

export function ScoreBar({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  const pct = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-xs uppercase tracking-[0.12em] text-[var(--ink-muted)]">
        <span>{label}</span>
        <span className="tabular-nums text-[var(--ink)]">
          {value == null ? "—" : Math.round(value)}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden bg-[var(--surface-muted)]">
        <div
          className="h-full bg-[var(--accent)]"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
