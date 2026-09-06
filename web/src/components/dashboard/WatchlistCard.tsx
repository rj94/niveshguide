"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MoreHorizontal, Plus } from "lucide-react";

import type { WatchItem } from "@/lib/dashboard-data";
import { changeHeatColor } from "@/lib/dashboard-data";
import { getClientKey } from "@/lib/client-key";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { getMyWatchlist } from "@/services/api";

type Props = {
  items: WatchItem[];
};

function toWatchItems(
  rows: {
    symbol: string;
    name: string;
    price: string | number | null;
    change_pct: number | null;
    sparkline: number[];
  }[],
): WatchItem[] {
  return rows
    .map((row) => {
      const price = row.price === null || row.price === "" ? null : Number(row.price);
      if (price === null || Number.isNaN(price) || row.change_pct === null) return null;
      return {
        symbol: row.symbol,
        name: row.name,
        price,
        changePct: row.change_pct,
        sparkline: row.sparkline ?? [],
        color: changeHeatColor(row.change_pct),
      } satisfies WatchItem;
    })
    .filter((x): x is WatchItem => x !== null);
}

export function WatchlistCard({ items: seed }: Props) {
  const [items, setItems] = useState<WatchItem[]>(seed);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const key = getClientKey();
        const res = await getMyWatchlist(key);
        if (cancelled) return;
        const mapped = toWatchItems(res.items);
        if (mapped.length > 0) setItems(mapped);
      } catch {
        /* keep SSR seed */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <article className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[var(--ink)]">My Watchlist</h2>
        <div className="flex items-center gap-1">
          <Link
            href="/watchlist"
            className="rounded-md p-1.5 text-[var(--ink-muted)] transition hover:bg-white/5 hover:text-[var(--ink)]"
            aria-label="Add to watchlist"
          >
            <Plus className="h-4 w-4" />
          </Link>
          <Link
            href="/watchlist"
            className="rounded-md p-1.5 text-[var(--ink-muted)] transition hover:bg-white/5 hover:text-[var(--ink)]"
            aria-label="Watchlist options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {items.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--ink-muted)]">
          {loading ? "Loading watchlist…" : "Watchlist empty. Add symbols on the Watchlist page."}
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {items.map((item) => {
            const up = item.changePct >= 0;
            return (
              <Link
                key={item.symbol}
                href={`/stocks/${encodeURIComponent(item.symbol)}`}
                className="flex min-h-[88px] flex-col justify-between rounded-lg p-2.5 transition hover:brightness-110"
                style={{ background: changeHeatColor(item.changePct) }}
              >
                <span className="text-[11px] font-semibold tracking-wide text-white">
                  {item.symbol}
                </span>
                <span>
                  <span className="block text-sm font-semibold tabular-nums text-white">
                    {formatNumber(item.price, { maximumFractionDigits: 2 })}
                  </span>
                  <span
                    className={cn(
                      "block text-xs tabular-nums text-white/95",
                      up ? "" : "",
                    )}
                  >
                    {formatPct(item.changePct)}
                  </span>
                </span>
              </Link>
            );
          })}
        </div>
      )}

      <Link
        href="/watchlist"
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--accent-hover)] transition hover:text-white"
      >
        Manage Watchlist →
      </Link>
    </article>
  );
}
