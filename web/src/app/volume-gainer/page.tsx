import { VolumeGainerWorkspace } from "@/components/volume/VolumeGainerWorkspace";

export const dynamic = "force-dynamic";

export default function VolumeGainerPage() {
  return (
    <div className="page-shell pb-12 pt-4">
      <VolumeGainerWorkspace />
    </div>
  );
}
