import { formatNumber, scoreToStars } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ScoreCard } from "@/types/stock";

type Props = {
  scores: ScoreCard;
};

const BREAKDOWN: { key: keyof ScoreCard; label: string; weight: string }[] = [
  { key: "return_score", label: "Returns", weight: "25%" },
  { key: "dma_score", label: "DMA / Trend", weight: "20%" },
  { key: "volume_score", label: "Volume", weight: "15%" },
  { key: "result_score", label: "Results", weight: "20%" },
  { key: "sector_strength", label: "Sector", weight: "20%" },
];

const ROWS: { key: keyof ScoreCard; label: string }[] = [
  { key: "technical", label: "Technical (trend 0–5×20)" },
  { key: "sector_strength", label: "Sector Strength" },
  { key: "industry_strength", label: "Industry Strength" },
  { key: "risk", label: "Risk" },
  { key: "quality", label: "Quality" },
  { key: "growth", label: "Growth" },
  { key: "value", label: "Value" },
  { key: "financial_health", label: "Financial Health" },
  { key: "ownership", label: "Ownership" },
  { key: "management", label: "Management" },
];

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

export function ScorePanel({ scores }: Props) {
  const overall = num(scores.overall);
  const momentum = num(scores.momentum) ?? overall;
  const accel = num(scores.momentum_acceleration);
  const hasMomentumV1 = scores.source === "momentum_v1" || BREAKDOWN.some((r) => num(scores[r.key]) != null);

  return (
    <section className="border border-[var(--line)] bg-[var(--surface)]/80 p-6 backdrop-blur-sm">
      <p className="text-xs uppercase tracking-[0.2em] text-[var(--ink-muted)]">
        Momentum Score
      </p>
      <div className="mt-2 flex items-end gap-3">
        <p className="font-[family-name:var(--font-display)] text-6xl leading-none tabular-nums text-[var(--ink)]">
          {momentum !== null ? Math.round(momentum) : "—"}
        </p>
        <p className="mb-1 text-sm text-[var(--ink-muted)]">/100</p>
      </div>
      <p className="mt-2 text-sm text-[var(--ink-soft)]">
        {scores.momentum_category ?? "—"}
        {accel != null ? (
          <span
            className={cn(
              "ml-2 tabular-nums",
              accel >= 0 ? "text-[var(--up)]" : "text-[var(--down)]",
            )}
          >
            Accel {accel > 0 ? "+" : ""}
            {formatNumber(accel, { maximumFractionDigits: 1 })}
          </span>
        ) : null}
      </p>
      <p className="mt-2 text-xs text-[var(--ink-muted)]">
        {scores.source === "momentum_v1"
          ? "V1: Returns 25% · DMA 20% · Volume 15% · Results 20% · Sector 20%"
          : scores.source === "engine"
            ? "Sector Strength Engine (price momentum, RS, breadth, risk)"
            : scores.source === "price_derived" || scores.source === "trade_trend_score"
              ? "Provisional from price & technicals — run calculate for full momentum"
              : "Awaiting momentum scoring"}
      </p>

      {hasMomentumV1 ? (
        <ul className="mt-6 space-y-3">
          {BREAKDOWN.map((row) => {
            const value = num(scores[row.key] as string | null);
            const display =
              value !== null ? formatNumber(value, { maximumFractionDigits: 0 }) : "—";
            const width = value != null ? Math.max(4, Math.min(100, value)) : 0;
            return (
              <li key={row.key} className="border-t border-[var(--line)] pt-3 first:border-t-0 first:pt-0">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-[var(--ink)]">{row.label}</p>
                    <p className="text-xs text-[var(--ink-muted)]">Weight {row.weight}</p>
                  </div>
                  <p className="font-[family-name:var(--font-display)] text-xl tabular-nums text-[var(--ink)]">
                    {display}
                  </p>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden bg-[var(--surface-muted)]">
                  <div
                    className="h-full bg-[var(--accent)]/80 transition-[width] duration-500"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <ul className="mt-6 space-y-3">
          {ROWS.map((row) => {
            const raw = scores[row.key];
            const value =
              typeof raw === "string" || typeof raw === "number" ? Number(raw) : null;
            const display =
              value !== null && !Number.isNaN(value)
                ? formatNumber(value, { maximumFractionDigits: 0 })
                : "—";
            return (
              <li
                key={row.key}
                className="flex items-center justify-between gap-4 border-t border-[var(--line)] pt-3 first:border-t-0 first:pt-0"
              >
                <div>
                  <p className="text-sm text-[var(--ink)]">{row.label}</p>
                  <p className="text-xs tracking-widest text-[var(--accent)]">
                    {scoreToStars(value)}
                  </p>
                </div>
                <p className="font-[family-name:var(--font-display)] text-xl tabular-nums text-[var(--ink)]">
                  {display}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
