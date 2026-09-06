/** AdSense env helpers — ads render only when client + slot are set. */

export function getAdSenseClient(): string {
  return process.env.NEXT_PUBLIC_ADSENSE_CLIENT?.trim() ?? "";
}

export function getAdSenseSlot(
  page: "dashboard" | "momentum" | "stock",
): string {
  const map = {
    dashboard: process.env.NEXT_PUBLIC_ADSENSE_SLOT_DASHBOARD,
    momentum: process.env.NEXT_PUBLIC_ADSENSE_SLOT_MOMENTUM,
    stock: process.env.NEXT_PUBLIC_ADSENSE_SLOT_STOCK,
  } as const;
  return map[page]?.trim() ?? "";
}

export function adsenseEnabled(): boolean {
  return Boolean(getAdSenseClient());
}
