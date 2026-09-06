export type StrategySlug = "canslim" | "garp" | "darvas" | "sepa";
export type RatingBand = "strong_buy" | "buy" | "watch" | "avoid";
export type CriterionState = "pass" | "partial" | "fail" | "unknown";

export type StrategyFilterDef = {
  key: string;
  label: string;
  detail: string;
};

export type StrategyMeta = {
  slug: StrategySlug;
  name: string;
  short_name: string;
  description: string;
  filters: StrategyFilterDef[];
};

export type CriterionStatus = {
  key: string;
  label: string;
  state: CriterionState;
  detail: string | null;
  value: number | null;
};

export type StrategyStockRow = {
  id: number;
  symbol: string;
  company_name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  ltp: string | null;
  change_pct: number | null;
  score: number;
  rating: RatingBand;
  rank: number;
  metrics: Record<string, unknown>;
  checklist: CriterionStatus[];
  as_of: string | null;
};

export type RatingCounts = {
  strong_buy: number;
  buy: number;
  watch: number;
  avoid: number;
  total: number;
};

export type MarketTrend = {
  label: "Bullish" | "Neutral" | "Bearish";
  detail: string;
  proxy_symbol: string | null;
  price: string | null;
  change_pct: number | null;
  advances: number | null;
  declines: number | null;
  new_highs: number | null;
  new_lows: number | null;
};

export type DistributionSlice = {
  key: RatingBand;
  label: string;
  count: number;
  pct: number;
};

export type TrendPoint = {
  label: string;
  strong_buy: number;
  buy: number;
  watch: number;
  avoid: number;
};

export type InsightItem = {
  text: string;
  tone: "positive" | "neutral" | "warning";
};

export type DataCoverage = {
  scanned: number;
  with_fundamentals: number;
  with_ownership: number;
  with_momentum: number;
  with_peg: number;
  with_eps_cagr: number;
  notes: string[];
};

export type StrategySummary = {
  market_trend: MarketTrend;
  counts: RatingCounts;
  distribution: DistributionSlice[];
  trend: TrendPoint[];
  insights: InsightItem[];
  data_coverage?: DataCoverage | null;
};

export type StrategyRunResponse = {
  strategy: StrategyMeta;
  summary: StrategySummary;
  items: StrategyStockRow[];
  total: number;
  scanned: number;
  selected_symbol: string | null;
};

export type StrategyListResponse = {
  items: StrategyMeta[];
};

export type StrategyQuery = {
  exchange?: string;
  q?: string;
  limit?: number;
  offset?: number;
  scan_limit?: number;
};
