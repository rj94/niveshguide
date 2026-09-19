export type AiQueryFilter = {
  field: string;
  operator: string;
  value: string | number | boolean | null | Array<string | number | boolean>;
};

export type AiQueryRow = {
  symbol: string;
  company_name?: string | null;
  sector?: string | null;
  industry?: string | null;
  ltp?: number | null;
  market_cap?: number | null;
  pe?: number | null;
  trend_score?: number | null;
  trend?: string | null;
  momentum_score?: number | null;
  momentum_acceleration?: number | null;
  return_1m?: number | null;
  return_3m?: number | null;
  return_6m?: number | null;
  volume_ratio?: number | null;
  distance_from_52w_high?: number | null;
};

export type AiQueryResponse = {
  answer: string;
  interpreted_query: string;
  filters: AiQueryFilter[];
  rows: AiQueryRow[];
  total: number;
  warnings: string[];
};

export type AiStatusResponse = {
  enabled: boolean;
  provider?: string | null;
  model?: string | null;
};
