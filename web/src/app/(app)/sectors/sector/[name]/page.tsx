import { GroupDetailWorkspace } from "@/components/sectors/GroupDetailWorkspace";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ name: string }>;
};

export default async function SectorDetailPage({ params }: PageProps) {
  const { name: raw } = await params;
  const name = decodeURIComponent(raw);
  return <GroupDetailWorkspace kind="sector" name={name} />;
}
