import { MarketingHome } from "@/components/marketing/MarketingHome";
import { loadDashboard } from "@/lib/load-dashboard";

export const dynamic = "force-dynamic";

export default async function MarketingPage() {
  const data = await loadDashboard();
  return <MarketingHome data={data} />;
}
