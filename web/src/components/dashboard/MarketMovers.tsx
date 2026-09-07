"use client";

import Link from "next/link";
import { useState } from "react";

import type { MoverRow } from "@/lib/dashboard-data";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

type Props = {
  gainers: MoverRow[];
  losers: MoverRow[];
  byVolume: MoverRow[];
};

const TABS = [
  { id: "gainers", label: "Top Gainers" },
  { id: "losers", label: "Top Losers" },
  { id: "volume", label: "Active By Volume" },
] as const;

function displayName(name: string): string {
  if (name.length > 3 && name === name.toUpperCase()) {
    return name
      .toLowerCase()
      .split(/\s+/)
      .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
      .join(" ");
  }
  return name;
}

export function MarketMovers({ gainers, losers, byVolume }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("gainers");
  const rows = tab === "gainers" ? gainers : tab === "losers" ? losers : byVolume;

  const footer =
    tab === "gainers"
      ? { href: "/screener", label: "View All Gainers" }
      : tab === "losers"
        ? { href: "/screener?sort=losers", label: "View All Losers" }
        : { href: "/screener?sort=volume", label: "View Active By Volume" };

  return (
    <article className="flex h-full flex-col rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
      <div className="flex flex-wrap gap-1 border-b border-[var(--line)] pb-3">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={cn(
              "shrink-0 rounded-md px-2.5 py-1.5 text-xs font-medium transition",
              tab === item.id
                ? "bg-[var(--accent-soft)] text-[var(--accent-hover)]"
                : "text-[var(--ink-muted)] hover:text-[var(--ink)]",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="flex flex-1 items-center justify-center py-10 text-sm text-[var(--ink-muted)]">
          No movers from the screener yet.
        </p>
      ) : (
        <ul className="mt-2 flex-1 divide-y divide-[var(--line)]">
          {rows.map((row) => {
            const up = row.changePct >= 0;
            return (
              <li key={row.symbol}>
                <Link
                  href={`/stocks/${row.symbol}`}
                  className="flex items-center gap-3 py-3 transition hover:bg-white/[0.02]"
                >
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold text-white"
                    style={{ background: row.color }}
                  >
                    {row.symbol.slice(0, 2)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-[var(--ink)]">
                      {row.symbol}
                    </span>
                    <span className="block truncate text-xs text-[var(--ink-muted)]">
                      {displayName(row.name)}
                    </span>
                  </span>
                  <span className="text-right">
                    <span className="block text-sm tabular-nums text-[var(--ink)]">
                      {formatNumber(row.price, { maximumFractionDigits: 2 })}
                    </span>
                    <span
                      className={cn(
                        "block text-xs tabular-nums",
                        up ? "text-[var(--up)]" : "text-[var(--down)]",
                      )}
                    >
                      {formatPct(row.changePct)}
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <Link
        href={footer.href}
        className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-[var(--accent-hover)] transition hover:text-white"
      >
        {footer.label} →
      </Link>
    </article>
  );
}