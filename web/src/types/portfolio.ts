export type PortfolioHolding = {
  symbol: string;
  name: string;
  exchange: string;
  quantity: string | number;
  avg_price: string | number;
  last_price: string | number | null;
  day_change: string | number | null;
  day_change_pct: number | null;
  invested_value: string | number;
  current_value: string | number | null;
  pnl: string | number | null;
  pnl_pct: number | null;
  weight_pct: number | null;
  sector: string | null;
  isin: string | null;
  broker_symbol: string | null;
  as_of: string | null;
};

export type PortfolioImport = {
  id: number;
  broker: string;
  filename: string;
  row_count: number;
  matched_count: number;
  unmatched_symbols: string[];
  imported_at: string | null;
};

export type PortfolioSummary = {
  invested_value: string | number;
  current_value: string | number;
  total_pnl: string | number;
  total_pnl_pct: number | null;
  day_pnl: string | number;
  holdings_count: number;
};

export type PortfolioResponse = {
  id: number;
  name: string;
  client_key: string;
  broker: string | null;
  last_import_at: string | null;
  summary: PortfolioSummary;
  holdings: PortfolioHolding[];
  recent_imports: PortfolioImport[];
  as_of: string | null;
  refreshed_at: string | null;
};
