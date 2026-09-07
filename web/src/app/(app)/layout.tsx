import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { loadTickerItems } from "@/lib/load-dashboard";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const tickerItems = await loadTickerItems().catch(() => []);

  return (
    <DashboardShell tickerItems={tickerItems}>{children}</DashboardShell>
  );
}
