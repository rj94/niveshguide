import Link from "next/link";

import type { IndexRow } from "@/lib/dashboard-data";
import { changeHeatColor } from "@/lib/dashboard-data";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export type SectorEtfItem = IndexRow & {
  symbol: string;
  sectorName?: string | null;
};

function etfHref(item: SectorEtfItem): string {
  if (item.sectorName) {
    return `/sectors/sector/${encodeURIComponent(item.sectorName)}`;
  }
  return "/sectors";
}

type Props = {
  items: SectorEtfItem[];
  liveHint?: string | null;
};

function initials(name: string): string {
  const parts = name
    .replace(/[/Â·]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function SectorEtfPanel({ items, liveHint }: Props) {
  return (
    <aside className="flex h-full max-h-[520px] flex-col rounded-xl border border-[var(--line)] bg-[var(--surface)] xl:max-h-none">
      <div className="border-b border-[var(--line)] px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-[var(--ink)]">
              Sector ETFs
            </h2>
            <p className="mt-0.5 text-[11px] leading-snug text-[var(--ink-muted)]">
              Click a sector to view its stocks
            </p>
          </div>
          {liveHint ? (
            <span className="shrink-0 rounded-md border border-[var(--line)] px-1.5 py-0.5 text-[10px] text-[var(--accent)]">
              {liveHint}
            </span>
          ) : null}
        </div>
      </div>

      {items.length === 0 ? (
        <p className="px-4 py-10 text-center text-sm text-[var(--ink-muted)]">
          No sector ETF quotes yet. Waiting for NSE live quotes (or DB snapshot fallback).
        </p>
      ) : (
        <ul className="dashboard-scroll flex-1 divide-y divide-[var(--line)] overflow-y-auto">
          {items.map((item) => {
            const up = item.changePct >= 0;
            return (
              <li key={item.symbol}>
                <Link
                  href={etfHref(item)}
                  className="group flex items-start gap-3 px-3 py-3 transition hover:bg-white/[0.03]"
                >
                  <span
                    className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold tracking-wide text-white"
                    style={{ background: changeHeatColor(item.changePct) }}
                    aria-hidden
                  >
                    {initials(item.name)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] font-semibold leading-snug text-[var(--ink)] group-hover:text-white">
                      {item.name}
                    </span>
                    <span className="mt-0.5 block text-[11px] tabular-nums text-[var(--ink-muted)]">
                      {item.symbol}
                    </span>
                  </span>
                  <span className="w-[76px] shrink-0 pt-0.5 text-right">
                    <span className="block text-sm font-medium tabular-nums text-[var(--ink)]">
                      {formatNumber(item.value, { maximumFractionDigits: 2 })}
                    </span>
                    <span
                      className={cn(
                        "mt-0.5 inline-flex rounded-md px-1.5 py-0.5 text-[11px] font-medium tabular-nums",
                        up
                          ? "bg-[var(--up-soft)] text-[var(--up)]"
                          : "bg-[var(--down-soft)] text-[var(--down)]",
                      )}
                    >
                      {formatPct(item.changePct)}
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <div className="border-t border-[var(--line)] px-4 py-2.5 flex items-center justify-between gap-2">
        <Link
          href="/markets"
          className="text-xs font-medium text-[var(--accent-hover)] transition hover:text-white"
        >
          View all ETFs →
        </Link>
        <Link
          href="/sectors"
          className="text-xs font-medium text-[var(--ink-muted)] transition hover:text-white"
        >
          Sector analysis →
        </Link>
      </div>
    </aside>
  );
}
