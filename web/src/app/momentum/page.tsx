import { MomentumWorkspace } from "@/components/momentum/MomentumWorkspace";

export const dynamic = "force-dynamic";

export default function MomentumPage() {
  return (
    <div className="page-shell pb-12 pt-4">
      <MomentumWorkspace />
    </div>
  );
}
