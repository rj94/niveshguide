import { Suspense } from "react";

import { ScreenerWorkspace } from "@/components/screener/ScreenerWorkspace";

export const dynamic = "force-dynamic";

export default function ScreenerPage() {
  return (
    <div className="page-shell pb-12 pt-4">
      <Suspense
        fallback={
          <div className="py-12 text-center text-sm text-[var(--ink-muted)]">Loading screener...</div>
        }
      >
        <ScreenerWorkspace />
      </Suspense>
    </div>
  );
}
