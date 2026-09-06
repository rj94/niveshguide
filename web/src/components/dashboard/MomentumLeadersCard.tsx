"use client";

import Link from "next/link";

import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export type MomentumLeader = {
  symbol: string;
  name: string;
  score: number;
  category: string | null;
  changePct: number | null;
  ltp: number | null;
};

type Props = {
  items: MomentumLeader[];
  liveHint?: string | null;
};

export function MomentumLeadersCard({ items, liveHint }: Props) {
  return (
    <article className="flex h-full min-h-[360px] flex-col rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-[var(--ink)]">Top Momentum</h2>
          <p className="mt-0.5 text-[11px] text-[var(--ink-muted)]">
            Highest momentum scores
            {liveHint ? ` · ${liveHint}` : ""}
          </p>
        </div>
        <Link
          href="/momentum"
          className="text-xs font-medium text-[var(--accent-hover)] transition hover:text-white"
        >
          View all →
        </Link>
      </div>

      {items.length === 0 ? (
        <p className="flex flex-1 items-center justify-center text-sm text-[var(--ink-muted)]">
          No momentum scores yet. Run <code className="mx-1 text-xs">python -m cli calculate</code>.
        </p>
      ) : (
        <div className="dashboard-scroll flex-1 overflow-x-auto overflow-y-auto">
          <table className="w-full min-w-[420px] text-left text-sm">
            <thead className="sticky top-0 bg-[var(--surface)] text-[10px] uppercase tracking-[0.12em] text-[var(--ink-muted)]">
              <tr className="border-b border-[var(--line)]">
                <th className="px-1 py-2 font-medium">#</th>
                <th className="px-1 py-2 font-medium">Stock</th>
                <th className="px-1 py-2 text-right font-medium">Price</th>
                <th className="px-1 py-2 text-right font-medium">Change</th>
                <th className="px-1 py-2 text-right font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row, idx) => {
                const up = (row.changePct ?? 0) >= 0;
                return (
                  <tr
                    key={row.symbol}
                    className="border-b border-[var(--line)]/70 transition hover:bg-white/[0.02]"
                  >
                    <td className="px-1 py-2.5 text-xs tabular-nums text-[var(--ink-muted)]">
                      {idx + 1}
                    </td>
                    <td className="px-1 py-2.5">
                      <Link
                        href={`/stocks/${encodeURIComponent(row.symbol)}`}
                        className="block min-w-0"
                      >
                        <span className="block truncate font-medium text-[var(--ink)]">
                          {row.symbol}
                        </span>
                        <span className="block truncate text-[11px] text-[var(--ink-muted)]">
                          {row.category || row.name}
                        </span>
                      </Link>
                    </td>
                    <td className="px-1 py-2.5 text-right tabular-nums text-[var(--ink)]">
                      {row.ltp != null ? formatNumber(row.ltp) : "—"}
                    </td>
                    <td
                      className={cn(
                        "px-1 py-2.5 text-right tabular-nums",
                        row.changePct == null
                          ? "text-[var(--ink-muted)]"
                          : up
                            ? "text-[var(--up)]"
                            : "text-[var(--down)]",
                      )}
                    >
                      {row.changePct != null ? formatPct(row.changePct) : "—"}
                    </td>
                    <td className="px-1 py-2.5 text-right text-base font-semibold tabular-nums text-[var(--accent)]">
                      {Math.round(row.score)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}
