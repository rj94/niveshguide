import {
  WATCHLIST_SYMBOLS,
  avatarColor,
  closesToSparkline,
  type ChartPoint,
  type ChartStats,
  type IndexCard,
  type IndexRow,
  type MarketCardKind,
  type MoverRow,
  type RotationItem,
  type SectorCell,
  type TickerItem,
  type WatchItem,
} from "@/lib/dashboard-data";
import {
  getMarketsOverview,
  getStock,
  listSectors,
  listStocks,
  screenStocks,
} from "@/services/api";
import type { MarketQuoteCard } from "@/types/markets";
import type { StrengthRow } from "@/types/sector";
import type { StockAnalysisRow, StockDetail, StockSummary } from "@/types/stock";
import type { MomentumLeader } from "@/components/dashboard/MomentumLeadersCard";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

function priceCloses(detail: StockDetail): number[] {
  return detail.prices
    .map((p) => num(p.close))
    .filter((v): v is number => v !== null);
}

function sparkFromDetail(detail: StockDetail, len = 20): number[] {
  return closesToSparkline(priceCloses(detail), len);
}

function chartFromDetail(detail: StockDetail): {
  title: string;
  symbol: string;
  price: number;
  change: number;
  changePct: number;
  points: ChartPoint[];
  stats: ChartStats;
} | null {
  const price = num(detail.quote.price);
  const change = num(detail.quote.change);
  const changePct = detail.quote.change_pct;
  if (price === null || change === null || changePct === null) return null;
  if (detail.prices.length < 2) return null;

  const points: ChartPoint[] = detail.prices
    .map((bar) => {
      const value = num(bar.close);
      if (value === null) return null;
      const d = new Date(`${bar.date}T00:00:00`);
      const time = Number.isNaN(d.getTime())
        ? bar.date
        : d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
      return { time, value, date: bar.date };
    })
    .filter((p): p is ChartPoint => p !== null);

  const closes = points.map((p) => p.value);
  const highs = detail.prices.map((p) => num(p.high)).filter((v): v is number => v !== null);
  const lows = detail.prices.map((p) => num(p.low)).filter((v): v is number => v !== null);
  const latest = detail.prices[detail.prices.length - 1]!;
  const open = num(detail.quote.open) ?? num(latest.open) ?? price;
  const high = num(detail.quote.high) ?? Math.max(...highs.slice(-1), price);
  const low = num(detail.quote.low) ?? Math.min(...lows.slice(-1), price);
  const prevClose = num(detail.quote.previous_close) ?? closes[closes.length - 2] ?? price;
  const high52w = num(detail.technicals.high_52w) ?? Math.max(...closes);
  const low52w = num(detail.technicals.low_52w) ?? Math.min(...closes);

  return {
    title: detail.symbol,
    symbol: detail.symbol,
    price,
    change,
    changePct,
    points,
    stats: { open, high, low, prevClose, high52w, low52w },
  };
}

async function fetchDetail(symbol: string): Promise<StockDetail | null> {
  try {
    return await getStock(symbol, { exchange: "NSE", price_limit: 400 });
  } catch {
    return null;
  }
}

function kindIcon(kind: string): IndexCard["icon"] {
  if (kind === "commodity") return "flame";
  if (kind === "fx") return "currency";
  if (kind === "sector") return "globe";
  return "chart";
}

function asKind(kind: string): MarketCardKind {
  if (kind === "commodity" || kind === "fx" || kind === "sector" || kind === "index") {
    return kind;
  }
  return "index";
}

function cardFromMarket(card: MarketQuoteCard): IndexCard | null {
  const value = num(card.value);
  const change = num(card.change) ?? 0;
  const changePct =
    card.kind === "sector"
      ? num(card.return_1m) ?? num(card.score_change_1w) ?? card.change_pct
      : card.change_pct;
  if (value === null || changePct === null) return null;
  return {
    id: card.id,
    name: card.name,
    value,
    change,
    changePct,
    sparkline: card.sparkline ?? [],
    tone: changePct >= 0 ? "up" : "down",
    icon: kindIcon(card.kind),
    kind: asKind(card.kind),
    subtitle:
      card.kind === "sector"
        ? card.rotation_state?.replaceAll("_", " ") ?? "Sector"
        : card.symbol,
  };
}

export type SectorEtfRow = IndexRow & {
  symbol: string;
  /** Canonical sector name; null for broad market ETFs */
  sectorName: string | null;
};

async function resolveMarketStrip(): Promise<{
  indices: IndexCard[];
  sectorEtfs: SectorEtfRow[];
  commodityRows: IndexRow[];
  chartDetail: StockDetail | null;
  asOf: string | null;
}> {
  const overview = await getMarketsOverview().catch(() => null);
  const strip: IndexCard[] = [];

  // Featured NSE index levels (from scrape-indices; ETF fallback if empty).
  for (const card of overview?.indices.slice(0, 5) ?? []) {
    const mapped = cardFromMarket(card);
    if (mapped) strip.push(mapped);
  }

  const sectorEtfs: SectorEtfRow[] = [];
  for (const c of overview?.sector_etfs ?? []) {
    const value = num(c.value);
    const changePct = c.change_pct;
    if (value === null || changePct === null) continue;
    sectorEtfs.push({
      symbol: c.symbol,
      name: c.name,
      value,
      changePct,
      sparkline: c.sparkline ?? [],
      kind: "sector_etf",
      sectorName: c.sector_name ?? null,
    });
  }

  const commodityRows: IndexRow[] = [];
  for (const c of overview?.commodities ?? []) {
    const value = num(c.value);
    const changePct = c.change_pct;
    if (value === null || changePct === null) continue;
    commodityRows.push({
      name: c.name,
      value,
      changePct,
      sparkline: c.sparkline ?? [],
      kind: c.kind,
    });
    if (commodityRows.length >= 6) break;
  }

  // Prefer liquid equities — index ETFs are often absent from the Sheets universe.
  let chartDetail: StockDetail | null = null;
  for (const symbol of ["RELIANCE", "TCS", "HDFCBANK", "NIFTYBEES"] as const) {
    chartDetail = await fetchDetail(symbol);
    if (chartDetail) break;
  }

  return {
    indices: strip.slice(0, 5),
    sectorEtfs,
    commodityRows,
    chartDetail,
    asOf: overview?.as_of ?? null,
  };
}

function moverFromAnalysis(row: StockAnalysisRow): MoverRow | null {
  const price = num(row.ltp);
  if (price === null || row.change_pct === null) return null;
  return {
    symbol: row.symbol,
    name: row.company_name,
    price,
    changePct: row.change_pct,
    color: avatarColor(row.symbol),
  };
}

async function loadMovers(): Promise<{
  gainers: MoverRow[];
  losers: MoverRow[];
  byVolume: MoverRow[];
}> {
  const [gainersRes, losersRes, volumeRes] = await Promise.all([
    screenStocks({
      exchange: "NSE",
      sort_by: "change_pct",
      sort_dir: "desc",
      limit: 8,
      scan_limit: 8000,
    }).catch(() => null),
    screenStocks({
      exchange: "NSE",
      sort_by: "change_pct",
      sort_dir: "asc",
      limit: 8,
      scan_limit: 8000,
    }).catch(() => null),
    screenStocks({
      exchange: "NSE",
      volume_mover: true,
      sort_by: "volume_ratio",
      sort_dir: "desc",
      limit: 8,
      scan_limit: 8000,
    }).catch(() => null),
  ]);

  const map = (rows: StockAnalysisRow[] | undefined) =>
    (rows ?? [])
      .map(moverFromAnalysis)
      .filter((x): x is MoverRow => x !== null)
      .slice(0, 5);

  return {
    gainers: map(gainersRes?.items),
    losers: map(losersRes?.items),
    byVolume: map(volumeRes?.items),
  };
}

/** SSR seed for watchlist; client heatmap hydrates from /watchlists/me. */
async function loadWatchlistSeed(): Promise<WatchItem[]> {
  const items: WatchItem[] = [];

  await Promise.all(
    WATCHLIST_SYMBOLS.map(async (symbol) => {
      const detail = await fetchDetail(symbol);
      if (!detail) return;
      const price = num(detail.quote.price);
      const changePct = detail.quote.change_pct;
      if (price === null || changePct === null) return;
      items.push({
        symbol: detail.symbol,
        name: detail.company_name,
        price,
        changePct,
        sparkline: sparkFromDetail(detail, 16),
        color: avatarColor(detail.symbol),
      });
    }),
  );

  const order = new Map(WATCHLIST_SYMBOLS.map((s, i) => [s, i]));
  return items.sort(
    (a, b) =>
      (order.get(a.symbol as (typeof WATCHLIST_SYMBOLS)[number]) ?? 99) -
      (order.get(b.symbol as (typeof WATCHLIST_SYMBOLS)[number]) ?? 99),
  );
}

export async function loadTickerItems(): Promise<TickerItem[]> {
  const items: TickerItem[] = [];
  const seen = new Set<string>();

  await Promise.all(
    [
      "RELIANCE",
      "TCS",
      "HDFCBANK",
      "INFY",
      "ICICIBANK",
      "SBIN",
      "ITC",
      "BHARTIARTL",
    ].map(async (symbol) => {
      try {
        const res = await listStocks({ q: symbol, limit: 6 });
        const hit = res.items.find(
          (s: StockSummary) =>
            s.symbol === symbol && s.exchange === "NSE" && s.has_prices,
        );
        const price = num(hit?.last_price);
        if (!hit || price === null || hit.change_pct === null || seen.has(symbol)) return;
        seen.add(symbol);
        items.push({ symbol, price, changePct: hit.change_pct });
      } catch {
        /* skip */
      }
    }),
  );

  return items;
}

export type DashboardPayload = {
  indices: IndexCard[];
  sectorEtfs: SectorEtfRow[];
  momentumLeaders: MomentumLeader[];
  gainers: MoverRow[];
  losers: MoverRow[];
  byVolume: MoverRow[];
  sectors: SectorCell[];
  indexRows: IndexRow[];
  rotation: RotationItem[];
  watchlist: WatchItem[];
  ticker: TickerItem[];
  asOf: string | null;
};

export async function loadDashboard(): Promise<DashboardPayload> {
  const [strip, movers, sectorsRes, watchlist, ticker, momentumRes] = await Promise.all([
    resolveMarketStrip(),
    loadMovers(),
    listSectors({ limit: 80, min_constituents: 3 }).catch(() => null),
    loadWatchlistSeed(),
    loadTickerItems(),
    screenStocks({
      exchange: "NSE",
      sort_by: "momentum_score",
      sort_dir: "desc",
      limit: 12,
      offset: 0,
      scan_limit: 8000,
    }).catch(() => null),
  ]);

  const mapSectorCell = (s: StrengthRow): SectorCell => ({
    name: s.name,
    score: num(s.strength_score) ?? 0,
    scoreChange1w: num(s.score_change_1w),
    return3m: num(s.return_3m),
    return3mCw: num(s.return_3m_cw),
    return3mSource: s.return_3m_source,
  });

  const mapRotation = (s: StrengthRow): RotationItem => ({
    id: s.name,
    name: s.name,
    score: num(s.strength_score) ?? 0,
    scoreChange: num(s.return_3m),
    return3mCw: num(s.return_3m_cw),
    return3mSource: s.return_3m_source,
    state: s.rotation_state,
  });

  const sectors: SectorCell[] = (sectorsRes?.items ?? []).slice(0, 12).map(mapSectorCell);

  // Rotation = transition movers (Improving / Weakening), not the same top-strength list
  const allSectorRows = sectorsRes?.items ?? [];
  const byState = (state: string) =>
    allSectorRows
      .filter((s) => (s.rotation_state || "").toLowerCase() === state.toLowerCase())
      .sort((a, b) => {
        const ma = Math.abs(num(a.momentum_score) ?? 0);
        const mb = Math.abs(num(b.momentum_score) ?? 0);
        if (mb !== ma) return mb - ma;
        return (num(b.strength_score) ?? 0) - (num(a.strength_score) ?? 0);
      });

  const rotation: RotationItem[] = [];
  const seen = new Set<string>();
  for (const state of ["Improving", "Weakening"] as const) {
    for (const row of byState(state)) {
      if (seen.has(row.name)) continue;
      rotation.push(mapRotation(row));
      seen.add(row.name);
      if (rotation.length >= 8) break;
    }
    if (rotation.length >= 8) break;
  }
  if (rotation.length < 5) {
    for (const state of ["Leading", "Lagging"] as const) {
      for (const row of byState(state)) {
        if (seen.has(row.name)) continue;
        if (sectors.some((c) => c.name === row.name) && rotation.length >= 3) continue;
        rotation.push(mapRotation(row));
        seen.add(row.name);
        if (rotation.length >= 5) break;
      }
      if (rotation.length >= 5) break;
    }
  }

  const momentumLeaders: MomentumLeader[] = (momentumRes?.items ?? [])
    .map((row: StockAnalysisRow) => {
      const score = num(row.momentum_score ?? row.overall);
      if (score === null) return null;
      return {
        symbol: row.symbol,
        name: row.company_name,
        score,
        category: row.momentum_category,
        changePct: row.change_pct,
        ltp: num(row.ltp),
      };
    })
    .filter((x): x is MomentumLeader => x !== null)
    .slice(0, 12);

  return {
    indices: strip.indices,
    sectorEtfs: strip.sectorEtfs,
    momentumLeaders,
    gainers: movers.gainers,
    losers: movers.losers,
    byVolume: movers.byVolume,
    sectors,
    indexRows: strip.commodityRows,
    rotation,
    watchlist,
    ticker,
    asOf: strip.asOf ?? sectorsRes?.as_of ?? null,
  };
}
