"use client";

import { useEffect, useState } from "react";
import { Bell, Menu, Moon } from "lucide-react";

import { StockSearch } from "@/components/stock/StockSearch";
import { formatIstClock, isNseMarketOpen } from "@/lib/dashboard-data";

type Props = {
  onMenuClick: () => void;
};

export function TopHeader({ onMenuClick }: Props) {
  // Avoid SSR/client clock mismatches — only render live time after mount.
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);

  const marketOpen = now ? isNseMarketOpen(now) : false;
  const clockLabel = now ? formatIstClock(now) : "—";

  return (
    <header className="sticky top-0 z-30 flex h-[var(--header-h)] items-center gap-3 border-b border-[var(--line)] bg-[var(--background)]/90 px-3 backdrop-blur-md sm:px-4">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-lg p-2 text-[var(--ink-soft)] transition hover:bg-white/5 hover:text-[var(--ink)]"
        aria-label="Toggle sidebar"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="min-w-0 flex-1">
        <StockSearch className="w-full max-w-xl" />
      </div>

      <div className="hidden items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--ink-soft)] md:flex">
        <span
          className={
            marketOpen
              ? "h-2 w-2 rounded-full bg-[var(--up)]"
              : "h-2 w-2 rounded-full bg-[var(--ink-muted)]"
          }
          style={marketOpen ? { animation: "pulse-dot 2s ease-in-out infinite" } : undefined}
        />
        <span className="font-medium text-[var(--ink)]">
          NSE Market {now ? (marketOpen ? "Open" : "Closed") : "…"}
        </span>
        <span className="text-[var(--ink-muted)]">·</span>
        <span className="tabular-nums" suppressHydrationWarning>
          {clockLabel}
        </span>
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          className="rounded-lg p-2 text-[var(--ink-soft)] transition hover:bg-white/5 hover:text-[var(--ink)]"
          aria-label="Theme"
        >
          <Moon className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="relative rounded-lg p-2 text-[var(--ink-soft)] transition hover:bg-white/5 hover:text-[var(--ink)]"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
