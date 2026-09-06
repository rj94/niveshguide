"use client";

import { AdUnit } from "@/components/ads/AdUnit";
import { getAdSenseSlot } from "@/lib/ads";

type Page = "dashboard" | "momentum" | "stock";

/** Page-scoped ad slot using env slot IDs. */
export function PageAd({ page, className }: { page: Page; className?: string }) {
  return <AdUnit slot={getAdSenseSlot(page)} className={className} />;
}
