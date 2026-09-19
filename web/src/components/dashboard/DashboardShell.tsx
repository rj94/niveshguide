"use client";

import { SiteHeader } from "@/components/layout/SiteHeader";
import { TickerBar, type TickerItem } from "@/components/dashboard/TickerBar";

type Props = {
  children: React.ReactNode;
  tickerItems?: TickerItem[];
};

export function DashboardShell({ children, tickerItems }: Props) {
  return (
    <div className="app-canvas min-h-screen">
      <SiteHeader />
      <main className="dashboard-scroll mx-auto min-h-[calc(100vh-4.5rem)] max-w-7xl px-4 pb-[calc(var(--ticker-h)+1.5rem)] lg:px-6">
        {children}
      </main>
      <TickerBar items={tickerItems} />
    </div>
  );
}
