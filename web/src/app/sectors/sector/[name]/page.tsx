import { ConstituentsView } from "@/components/sectors/ConstituentsView";
import { getSector } from "@/services/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ name: string }>;
};

export default async function SectorDetailPage({ params }: PageProps) {
  const { name: raw } = await params;
  const name = decodeURIComponent(raw);
  let meta: {
    strength_score?: string | null;
    rotation_state?: string | null;
    score_change_1m?: string | null;
  } = {};
  try {
    meta = await getSector(name);
  } catch {
    meta = {};
  }

  return (
    <ConstituentsView
      kind="sector"
      name={name}
      strengthScore={meta.strength_score ?? null}
      rotationState={meta.rotation_state ?? null}
      scoreChange1m={meta.score_change_1m ?? null}
    />
  );
}
