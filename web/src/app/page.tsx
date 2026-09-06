import { HomeDashboard } from "@/components/dashboard/HomeDashboard";
import { loadDashboard } from "@/lib/load-dashboard";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const data = await loadDashboard();
  return <HomeDashboard {...data} />;
}
