import { Suspense } from "react";

import { AnalysisWorkspace } from "@/components/analysis/AnalysisWorkspace";

export const dynamic = "force-dynamic";

export default function AnalysisPage() {
  return (
    <Suspense
      fallback={
        <div className="px-6 py-16 text-sm text-[var(--ink-muted)]">Loading analysis…</div>
      }
    >
      <AnalysisWorkspace />
    </Suspense>
  );
}
