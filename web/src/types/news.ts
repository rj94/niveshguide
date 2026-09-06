export type NewsCategoryKey =
  | "all"
  | "result"
  | "award_order"
  | "press_release"
  | "monthly_update"
  | "shareholder"
  | "other";

export interface EventAttribute {
  key: string;
  value_text: string | null;
  value_number: string | number | null;
  unit: string | null;
  source_text: string | null;
  extraction_method: string;
  confidence: string | number | null;
}

export interface NewsMetrics {
  revenue_yoy_pct: number | null;
  revenue_qoq_pct: number | null;
  ebitda_yoy_pct: number | null;
  pat_yoy_pct: number | null;
  pat_qoq_pct: number | null;
  eps_yoy_pct: number | null;
  ocf_yoy_pct: number | null;
  revenue_cr: number | null;
  ebitda_cr: number | null;
  pat_cr: number | null;
  order_value_cr: number | null;
  order_to_revenue_pct: number | null;
  materiality_band: string | null;
}

export type SectorProfile = "bank" | "nbfc" | "it" | "pharma" | "general" | string;

export interface NewsEventCard {
  id: number;
  event_type: string;
  category: string;
  category_label: string;
  title: string;
  what_happened: string;
  summary_simple: string | null;
  impact_score: string | number | null;
  confidence: string | number | null;
  sentiment: string | null;
  published_at: string | null;
  price_reaction_pct: string | number | null;
  extraction_method: string | null;
  stock_id: number | null;
  symbol: string | null;
  company_name: string | null;
  exchange: string | null;
  sector?: string | null;
  last_price: string | number | null;
  change_pct: number | null;
  source_url: string | null;
  announcement_id: number;
  attributes: EventAttribute[];
  metrics?: NewsMetrics | null;
  sector_profile?: SectorProfile;
  sector_kpis?: Record<string, number | null>;
}

export interface NewsListResponse {
  items: NewsEventCard[];
  total: number;
  limit: number;
  offset: number;
}

export interface NewsCategoryCount {
  key: string;
  label: string;
  count: number;
}

export interface NewsCategoriesResponse {
  categories: NewsCategoryCount[];
  total: number;
}

export interface TrendingStock {
  rank: number;
  stock_id: number;
  symbol: string;
  company_name: string;
  exchange: string;
  event_count: number;
  last_price: string | number | null;
  change_pct: number | null;
}

export interface TrendingNewsResponse {
  items: TrendingStock[];
}

export interface SummarizeResponse {
  id: number;
  summary_simple: string | null;
  extraction_method: string | null;
  llm_used: boolean;
}

export interface NewsRefreshResponse {
  fetched: number;
  created: number;
  processed: number;
  skipped: number;
  days: number;
  exchanges: string[];
  used_seed: boolean;
  live_count: number;
  purged_seed: number;
  limit: number;
}

export interface NewsQuery {
  category?: string;
  event_type?: string;
  symbol?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  important_only?: boolean;
  sentiment?: string;
  impact_band?: string;
  sort?: "latest" | "impact";
  limit?: number;
  offset?: number;
}
