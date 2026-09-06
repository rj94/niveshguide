import type { RatingBand, StrategySlug } from "@/types/strategy";

export const STRATEGY_SLUGS: StrategySlug[] = ["canslim", "garp", "darvas", "sepa"];

export const STRATEGY_LABELS: Record<StrategySlug, string> = {
  canslim: "CANSLIM",
  garp: "GARP",
  darvas: "DARVAS",
  sepa: "SEPA",
};

export const RATING_META: Record<
  RatingBand,
  { label: string; color: string; soft: string }
> = {
  strong_buy: {
    label: "Strong Buy",
    color: "text-[var(--up)]",
    soft: "bg-[var(--up-soft)] text-[var(--up)]",
  },
  buy: {
    label: "Buy",
    color: "text-emerald-300",
    soft: "bg-emerald-500/15 text-emerald-300",
  },
  watch: {
    label: "Watch",
    color: "text-[var(--warn)]",
    soft: "bg-amber-500/15 text-[var(--warn)]",
  },
  avoid: {
    label: "Avoid",
    color: "text-[var(--down)]",
    soft: "bg-[var(--down-soft)] text-[var(--down)]",
  },
};

export const SAVED_SCREENS_KEY = "niveshguide.analysis.savedScreens";
const LEGACY_SAVED_SCREENS_KEY = "stockinsight.analysis.savedScreens";

export type SavedScreen = {
  id: string;
  name: string;
  strategy: StrategySlug;
  createdAt: string;
};

export function loadSavedScreens(): SavedScreen[] {
  if (typeof window === "undefined") return [];
  try {
    let raw = localStorage.getItem(SAVED_SCREENS_KEY);
    if (!raw) {
      const legacy = localStorage.getItem(LEGACY_SAVED_SCREENS_KEY);
      if (legacy) {
        localStorage.setItem(SAVED_SCREENS_KEY, legacy);
        raw = legacy;
      }
    }
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedScreen[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveSavedScreens(screens: SavedScreen[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(SAVED_SCREENS_KEY, JSON.stringify(screens.slice(0, 20)));
}

export function parseStrategySlug(value: string | null | undefined): StrategySlug {
  if (value && STRATEGY_SLUGS.includes(value as StrategySlug)) {
    return value as StrategySlug;
  }
  return "canslim";
}

export function metricNumber(metrics: Record<string, unknown>, key: string): number | null {
  const v = metrics[key];
  if (v === null || v === undefined || v === "") return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

export function metricBool(metrics: Record<string, unknown>, key: string): boolean | null {
  const v = metrics[key];
  if (typeof v === "boolean") return v;
  return null;
}

export function metricString(metrics: Record<string, unknown>, key: string): string | null {
  const v = metrics[key];
  return typeof v === "string" ? v : null;
}
