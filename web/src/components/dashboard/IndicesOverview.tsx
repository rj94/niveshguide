import { Sparkline } from "@/components/dashboard/Sparkline";
import type { IndexRow } from "@/lib/dashboard-data";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

type Props = {
  rows: IndexRow[];
};

export function IndicesOverview({ rows }: Props) {
  return (
    <article className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Commodities & FX</h2>
        <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--ink-muted)]">
          Yahoo proxies
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--ink-muted)]">
          No commodity quotes yet. Run{" "}
          <code className="text-xs">seed_commodities.py --with-history</code>.
        </p>
      ) : (
        <ul className="divide-y divide-[var(--line)]">
          {rows.map((row) => {
            const up = row.changePct >= 0;
            return (
              <li key={row.name} className="flex items-center gap-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-[var(--ink)]">{row.name}</p>
                  <p className="text-xs capitalize tabular-nums text-[var(--ink-muted)]">
                    {row.kind ?? "market"} ·{" "}
                    {formatNumber(row.value, { maximumFractionDigits: 2 })}
                  </p>
                </div>
                <Sparkline data={row.sparkline} positive={up} width={56} height={24} />
                <span
                  className={cn(
                    "w-16 text-right text-xs font-medium tabular-nums",
                    up ? "text-[var(--up)]" : "text-[var(--down)]",
                  )}
                >
                  {formatPct(row.changePct)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}
