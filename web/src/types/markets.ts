export type MarketQuoteCard = {
  id: string;
  symbol: string;
  name: string;
  kind: "index" | "commodity" | "fx" | "sector" | string;
  exchange: string | null;
  value: string | number | null;
  change: string | number | null;
  change_pct: number | null;
  sparkline: number[];
  as_of: string | null;
  score: string | number | null;
  score_change_1w: string | number | null;
  return_1m: string | number | null;
  rotation_state: string | null;
  /** Canonical sector for ETF → sector stocks click-through */
  sector_name?: string | null;
};

export type MarketsOverviewResponse = {
  indices: MarketQuoteCard[];
  sector_etfs: MarketQuoteCard[];
  commodities: MarketQuoteCard[];
  sectors: MarketQuoteCard[];
  as_of: string | null;
};

export type MarketEtfsResponse = {
  items: MarketQuoteCard[];
  total: number;
  as_of: string | null;
};
