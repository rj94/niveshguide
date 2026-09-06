"use client";

import { Suspense, useState } from "react";

import { Sidebar, SidebarFallback } from "@/components/dashboard/Sidebar";
import { TickerBar, type TickerItem } from "@/components/dashboard/TickerBar";
import { TopHeader } from "@/components/dashboard/TopHeader";

type Props = {
  children: React.ReactNode;
  tickerItems?: TickerItem[];
};

export function DashboardShell({ children, tickerItems }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--ink)]">
      <Suspense fallback={<SidebarFallback open={sidebarOpen} />}>
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      </Suspense>

      <div className="lg:pl-[var(--sidebar-w)]">
        <TopHeader onMenuClick={() => setSidebarOpen((v) => !v)} />
        <main className="dashboard-scroll min-h-[calc(100vh-var(--header-h)-var(--ticker-h))] overflow-x-hidden pb-[calc(var(--ticker-h)+1.25rem)]">
          {children}
        </main>
      </div>

      <TickerBar items={tickerItems} />
    </div>
  );
}
