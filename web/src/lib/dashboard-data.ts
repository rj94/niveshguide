export type MarketCardKind = "index" | "commodity" | "fx" | "sector";

export type IndexCard = {
  id: string;
  name: string;
  value: number;
  change: number;
  changePct: number;
  sparkline: number[];
  tone: "up" | "down" | "neutral";
  icon: "chart" | "bank" | "flame" | "currency" | "globe";
  kind: MarketCardKind;
  subtitle?: string | null;
};

export type MoverRow = {
  symbol: string;
  name: string;
  price: number;
  changePct: number;
  color: string;
};

export type SectorCell = {
  name: string;
  score: number;
  scoreChange1w: number | null;
  /** Display 3M return % (official index when available, else CW) */
  return3m: number | null;
  return3mCw: number | null;
  return3mSource: "index" | "cap_weight" | "equal_weight" | string | null;
  state: string | null;
};

export type IndexRow = {
  name: string;
  value: number;
  changePct: number;
  sparkline: number[];
  kind?: MarketCardKind | string;
};

export type RotationItem = {
  id: string;
  name: string;
  score: number;
  scoreChange: number | null;
  return3mCw: number | null;
  return3mSource: "index" | "cap_weight" | "equal_weight" | string | null;
  state: string | null;
};

export type WatchItem = {
  symbol: string;
  name: string;
  price: number;
  changePct: number;
  sparkline: number[];
  color: string;
};

export type ChartPoint = {
  time: string;
  value: number;
  date: string;
};

export type ChartStats = {
  open: number;
  high: number;
  low: number;
  prevClose: number;
  high52w: number;
  low52w: number;
};

export type TickerItem = {
  symbol: string;
  price: number;
  changePct: number;
};

/** Featured NSE index keys / legacy ETF symbols used as dashboard fallbacks. */
export const BENCHMARK_SYMBOLS = [
  { symbol: "NIFTY 50", label: "Nifty 50", icon: "chart" as const },
  { symbol: "NIFTY BANK", label: "Bank Nifty", icon: "bank" as const },
  { symbol: "NIFTY NEXT 50", label: "Nifty Next 50", icon: "chart" as const },
  { symbol: "NIFTY 500", label: "Nifty 500", icon: "globe" as const },
  { symbol: "NIFTY 100", label: "Nifty 100", icon: "globe" as const },
];

export const WATCHLIST_SYMBOLS = [
  "RELIANCE",
  "TCS",
  "HDFCBANK",
  "INFY",
  "ICICIBANK",
] as const;

export const TICKER_SYMBOLS = [
  "NIFTYBEES",
  "BANKBEES",
  "RELIANCE",
  "TCS",
  "HDFCBANK",
  "INFY",
  "ICICIBANK",
  "SBIN",
  "ITC",
  "BHARTIARTL",
] as const;

export const LIQUID_FALLBACK_SYMBOLS = [
  "RELIANCE",
  "TCS",
  "HDFCBANK",
  "INFY",
  "ICICIBANK",
  "SBIN",
  "ITC",
  "BHARTIARTL",
  "LT",
  "AXISBANK",
] as const;

export function sectorColor(score: number): string {
  if (score >= 80) return "#059669";
  if (score >= 70) return "#10b981";
  if (score >= 60) return "#34d399";
  if (score >= 50) return "#a3e635";
  if (score >= 40) return "#fbbf24";
  if (score >= 30) return "#f97316";
  return "#ef4444";
}

/** Heat color for watchlist % change (clamped). */
export function changeHeatColor(changePct: number): string {
  const mag = Math.min(Math.abs(changePct), 8) / 8;
  if (changePct >= 0) {
    return `rgba(16, 185, 129, ${0.25 + mag * 0.55})`;
  }
  const r = Math.round(180 + mag * 40);
  return `rgba(${r}, 68, 68, ${0.25 + mag * 0.55})`;
}

export function avatarColor(symbol: string): string {
  const palette = ["#3b82f6", "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#14b8a6", "#8b5cf6"];
  let hash = 0;
  for (let i = 0; i < symbol.length; i += 1) hash = (hash + symbol.charCodeAt(i) * (i + 1)) % 997;
  return palette[hash % palette.length]!;
}

export function closesToSparkline(closes: number[], len = 20): number[] {
  if (closes.length === 0) return [];
  return closes.slice(-len);
}

export function isNseMarketOpen(now = new Date()): boolean {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(now);

  const weekday = parts.find((p) => p.type === "weekday")?.value ?? "";
  if (weekday === "Sat" || weekday === "Sun") return false;

  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? "0");
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? "0");
  const mins = hour * 60 + minute;
  return mins >= 9 * 60 + 15 && mins < 15 * 60 + 30;
}

export function formatIstClock(now = new Date()): string {
  return (
    new Intl.DateTimeFormat("en-IN", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "Asia/Kolkata",
    }).format(now) + " IST"
  );
}
