export type MarketQuoteCard = {
  id: string;
  symbol: string;
  name: string;
  kind: string;
  exchange: string | null;
  value: string | number | null;
  change: string | number | null;
  change_pct: number | null;
  sparkline: number[];
  as_of: string | null;
  sector_name?: string | null;
};

export type MarketsOverviewResponse = {
  indices: MarketQuoteCard[];
  sector_etfs: MarketQuoteCard[];
  commodities: MarketQuoteCard[];
  sectors: MarketQuoteCard[];
  as_of: string | null;
};

export type StockAnalysisRow = {
  id: number;
  symbol: string;
  company_name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  ltp: string | null;
  change_pct: number | null;
  market_cap: string | null;
  return_1m_pct: number | null;
  return_3m_pct: number | null;
  momentum_score: string | null;
  momentum_acceleration: string | null;
  momentum_category: string | null;
  volume_mover: boolean | null;
};

export type StockAnalysisResponse = {
  items: StockAnalysisRow[];
  total: number;
  scanned: number;
};

export type ScreenerQuery = {
  q?: string;
  exchange?: string;
  volume_mover?: boolean;
  min_return_3m?: number;
  min_momentum_score?: number;
  min_momentum_acceleration?: number;
  momentum_category?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  limit?: number;
  offset?: number;
  scan_limit?: number;
};

export type Quote = {
  price: string | null;
  change_pct: number | null;
  as_of: string | null;
  volume: number | null;
};

export type ScoreCard = {
  momentum: string | null;
  momentum_acceleration: string | null;
  momentum_category: string | null;
  return_score: string | null;
  dma_score: string | null;
  volume_score: string | null;
  result_score: string | null;
  sector_strength: string | null;
};

export type TechnicalsSnapshot = {
  return_1m_pct: number | null;
  return_3m_pct: number | null;
  return_6m_pct: number | null;
  return_1y_pct: number | null;
  momentum_score: number | null;
  momentum_acceleration: number | null;
  momentum_category: string | null;
  trend: string | null;
  trend_score: number | null;
};

export type StockDetail = {
  id: number;
  symbol: string;
  company_name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  market_cap: string | null;
  quote: Quote;
  scores: ScoreCard;
  technicals: TechnicalsSnapshot;
};

export type SectorScoreRow = {
  name: string;
  score?: string | number | null;
  return_3m?: number | null;
  constituents?: number | null;
};

export type SectorListResponse = {
  items: SectorScoreRow[];
};
