import { SiteHeader } from "@/components/layout/SiteHeader";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="marketing-root min-h-full">
      <SiteHeader />
      {children}
    </div>
  );
}
