import { ScreenerWorkspace } from "@/components/screener/ScreenerWorkspace";

export const dynamic = "force-dynamic";

export default function ScreenerPage() {
  return (
    <div className="page-shell pb-12 pt-4">
      <ScreenerWorkspace />
    </div>
  );
}
