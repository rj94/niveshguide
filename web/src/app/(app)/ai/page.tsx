import { AiQueryWorkspace } from "@/components/ai/AiQueryWorkspace";

export const dynamic = "force-dynamic";

export default function AiSearchPage() {
  return (
    <div className="page-shell pb-12 pt-4">
      <AiQueryWorkspace />
    </div>
  );
}
