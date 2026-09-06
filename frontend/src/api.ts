export type StockRow = {
  symbol: string;
  company_name: string | null;
  exchange: string;
  ltp: number | null;
  market_cap: number | null;
  day_high: number | null;
  prev_close: number | null;
  high_52_week: number | null;
  low_52_week: number | null;
  pe: number | null;
  eps: number | null;
  ma_3: number | null;
  ma_7: number | null;
  ma_21: number | null;
  ma_50: number | null;
  ma_200: number | null;
  crossover_3_7: boolean | null;
  above_ma_21: boolean | null;
  ma21_gt_ma50: boolean | null;
  above_ma_200: boolean | null;
  golden_cross: boolean | null;
  trend_score: number | null;
  trend: string | null;
  distance_from_52w_high: number | null;
  return_3m: number | null;
  return_6m: number | null;
  volume: number | null;
  avg_volume_3m: number | null;
  avg_volume_6m: number | null;
  avg_volume_1y: number | null;
  as_of: string | null;
  snapshot_date: string | null;
  source: string | null;
};

export type Dashboard = {
  as_of: string | null;
  total_active: number;
  strong_uptrend: number;
  uptrend: number;
  neutral: number;
  downtrend: number;
  strong_downtrend: number;
  fresh_bullish_crossovers: number;
  fresh_bearish_crossovers: number;
  new_52_week_highs: number;
  golden_crosses: number;
  by_trend: Record<string, number>;
  signals_today: Record<string, number>;
  batches: Array<{
    batch_name: string;
    spreadsheet_id: string;
    gid: number | null;
    sheet_name: string;
    status: string;
    last_successful_sync: string | null;
    last_attempted_sync: string | null;
    error_message: string | null;
    retry_count: number;
    url: string;
  }>;
  source_workbook: string;
};

export type SignalRow = {
  symbol: string;
  company_name: string | null;
  signal_type: string;
  direction: string | null;
  signal_date: string;
  metadata: Record<string, unknown> | null;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => getJson<Dashboard>("/dashboard"),
  screener: (params: Record<string, string | number | undefined>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    return getJson<{ count: number; total: number; screen: string | null; items: StockRow[] }>(
      `/screener?${query.toString()}`
    );
  },
  stock: (symbol: string) =>
    getJson<
      StockRow & {
        prices: Array<{ date: string; close: number | null; high: number | null; low: number | null; volume: number | null }>;
        signals: SignalRow[];
        trend_history: Array<{ date: string; trend: string | null; trend_score: number | null }>;
      }
    >(`/stocks/${encodeURIComponent(symbol)}`),
  signalsToday: () => getJson<{ as_of: string | null; count: number; items: SignalRow[] }>("/signals/today"),
  freshCrossover: () => getJson<{ as_of: string | null; count: number; items: SignalRow[] }>("/signals/fresh-crossover"),
};
