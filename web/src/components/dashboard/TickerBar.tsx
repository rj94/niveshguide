"use client";

import { useEffect, useState } from "react";

import { formatNumber, formatPct } from "@/lib/format";
import { loadTickerItems } from "@/lib/load-dashboard";
import { cn } from "@/lib/utils";

export type TickerItem = {
  symbol: string;
  price: number;
  changePct: number;
};

type Props = {
  items?: TickerItem[];
};

export function TickerBar({ items: initialItems }: Props) {
  const [items, setItems] = useState<TickerItem[]>(initialItems ?? []);

  useEffect(() => {
    if (initialItems && initialItems.length > 0) {
      setItems(initialItems);
      return;
    }
    let cancelled = false;
    loadTickerItems()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      });
    return () => {
      cancelled = true;
    };
  }, [initialItems]);

  if (items.length === 0) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-40 flex h-[var(--ticker-h)] items-center border-t border-[var(--line)] bg-[#080a0f] px-3 text-xs text-[var(--ink-muted)] lg:left-[var(--sidebar-w)]">
        Waiting for live quotes…
      </div>
    );
  }

  const loop = [...items, ...items];

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 h-[var(--ticker-h)] overflow-hidden border-t border-[var(--line)] bg-[#080a0f] lg:left-[var(--sidebar-w)]">
      <div className="ticker-track flex h-full w-max items-center gap-8 px-3">
        {loop.map((item, i) => {
          const up = item.changePct >= 0;
          return (
            <div
              key={`${item.symbol}-${i}`}
              className="flex shrink-0 items-center gap-2 text-xs"
            >
              <span className="font-medium text-[var(--ink)]">{item.symbol}</span>
              <span className="tabular-nums text-[var(--ink-soft)]">
                {formatNumber(item.price, { maximumFractionDigits: 2 })}
              </span>
              <span
                className={cn(
                  "tabular-nums",
                  up ? "text-[var(--up)]" : "text-[var(--down)]",
                )}
              >
                {formatPct(item.changePct)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
