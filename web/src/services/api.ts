import type { MarketEtfsResponse, MarketsOverviewResponse } from "@/types/markets";
import type {
  NewsCategoriesResponse,
  NewsEventCard,
  NewsListResponse,
  NewsQuery,
  NewsRefreshResponse,
  SummarizeResponse,
  TrendingNewsResponse,
} from "@/types/news";
import type {
  IndustryScoreRow,
  SectorListResponse,
  SectorScoreRow,
} from "@/types/sector";
import type {
  ScreenerQuery,
  StockAnalysisResponse,
  StockDetail,
  StockListResponse,
} from "@/types/stock";
import type {
  StrategyListResponse,
  StrategyQuery,
  StrategyRunResponse,
  StrategySlug,
} from "@/types/strategy";
import type { WatchlistResponse } from "@/types/watchlist";
import type { PortfolioResponse } from "@/types/portfolio";

// 8010 by default: port 8000 is frequently blocked on Windows (WinError 10013).
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8010/api/v1";

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { revalidate?: number },
): Promise<T> {
  const { revalidate = 30, ...rest } = init ?? {};
  const isServer = typeof window === "undefined";
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(rest.headers ?? {}),
    },
    ...(isServer
      ? { next: { revalidate } }
      : { cache: "no-store" as RequestCache }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function clientHeaders(clientKey?: string): HeadersInit {
  if (!clientKey) return {};
  return { "X-Client-Key": clientKey };
}

function appendParams(search: URLSearchParams, params: Record<string, unknown>) {
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
}

export async function listStocks(params?: {
  q?: string;
  exchange?: string;
  symbols?: string[];
  limit?: number;
  offset?: number;
}): Promise<StockListResponse> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.exchange) search.set("exchange", params.exchange);
  if (params?.symbols?.length) search.set("symbols", params.symbols.join(","));
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.offset) search.set("offset", String(params.offset));
  const qs = search.toString();
  return apiFetch<StockListResponse>(`/stocks${qs ? `?${qs}` : ""}`);
}

export async function getStock(
  symbol: string,
  params?: { exchange?: string; price_limit?: number },
): Promise<StockDetail> {
  const search = new URLSearchParams();
  if (params?.exchange) search.set("exchange", params.exchange);
  if (params?.price_limit) search.set("price_limit", String(params.price_limit));
  const qs = search.toString();
  return apiFetch<StockDetail>(
    `/stocks/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ""}`,
  );
}

export async function listSectors(params?: {
  limit?: number;
  min_constituents?: number;
  gaining_only?: boolean;
}): Promise<SectorListResponse> {
  const search = new URLSearchParams();
  appendParams(search, {
    limit: params?.limit ?? 100,
    min_constituents: params?.min_constituents ?? 0,
    gaining_only: params?.gaining_only ?? false,
  });
  return apiFetch<SectorListResponse>(`/sectors?${search.toString()}`);
}

export async function getSector(name: string): Promise<SectorScoreRow> {
  return apiFetch<SectorScoreRow>(`/sectors/by-name/${encodeURIComponent(name)}`);
}

export async function getIndustry(name: string): Promise<IndustryScoreRow> {
  return apiFetch<IndustryScoreRow>(
    `/sectors/industries/by-name/${encodeURIComponent(name)}`,
  );
}

export async function listSectorStocks(
  name: string,
  params?: {
    exchange?: string;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
    limit?: number;
    offset?: number;
  },
): Promise<StockAnalysisResponse> {
  const search = new URLSearchParams();
  appendParams(search, {
    exchange: params?.exchange ?? "NSE",
    sort_by: params?.sort_by ?? "overall",
    sort_dir: params?.sort_dir ?? "desc",
    limit: params?.limit ?? 100,
    offset: params?.offset ?? 0,
  });
  return apiFetch<StockAnalysisResponse>(
    `/sectors/by-name/${encodeURIComponent(name)}/stocks?${search.toString()}`,
  );
}

export async function listIndustryStocks(
  name: string,
  params?: {
    exchange?: string;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
    limit?: number;
    offset?: number;
  },
): Promise<StockAnalysisResponse> {
  const search = new URLSearchParams();
  appendParams(search, {
    exchange: params?.exchange ?? "NSE",
    sort_by: params?.sort_by ?? "overall",
    sort_dir: params?.sort_dir ?? "desc",
    limit: params?.limit ?? 100,
    offset: params?.offset ?? 0,
  });
  return apiFetch<StockAnalysisResponse>(
    `/sectors/industries/by-name/${encodeURIComponent(name)}/stocks?${search.toString()}`,
  );
}

export async function screenStocks(
  params?: ScreenerQuery,
): Promise<StockAnalysisResponse> {
  const search = new URLSearchParams();
  appendParams(search, { ...(params ?? {}) });
  const qs = search.toString();
  return apiFetch<StockAnalysisResponse>(`/screener${qs ? `?${qs}` : ""}`);
}

export async function listStrategies(): Promise<StrategyListResponse> {
  return apiFetch<StrategyListResponse>("/strategies");
}

export async function runStrategy(
  slug: StrategySlug,
  params?: StrategyQuery,
): Promise<StrategyRunResponse> {
  const search = new URLSearchParams();
  appendParams(search, {
    exchange: params?.exchange ?? "NSE",
    q: params?.q,
    limit: params?.limit ?? 50,
    offset: params?.offset ?? 0,
    scan_limit: params?.scan_limit ?? 5000,
  });
  return apiFetch<StrategyRunResponse>(
    `/strategies/${encodeURIComponent(slug)}?${search.toString()}`,
  );
}

export async function getMarketsOverview(): Promise<MarketsOverviewResponse> {
  return apiFetch<MarketsOverviewResponse>("/markets/overview");
}

export async function listMarketEtfs(): Promise<MarketEtfsResponse> {
  return apiFetch<MarketEtfsResponse>("/markets/etfs");
}

export async function listNews(params?: NewsQuery): Promise<NewsListResponse> {
  const search = new URLSearchParams();
  appendParams(search, {
    category: params?.category,
    event_type: params?.event_type,
    symbol: params?.symbol,
    q: params?.q,
    date_from: params?.date_from,
    date_to: params?.date_to,
    important_only: params?.important_only ? "true" : undefined,
    sentiment: params?.sentiment,
    impact_band: params?.impact_band,
    sort: params?.sort,
    limit: params?.limit,
    offset: params?.offset,
  });
  const qs = search.toString();
  return apiFetch<NewsListResponse>(`/news${qs ? `?${qs}` : ""}`);
}

export async function getNewsCategories(): Promise<NewsCategoriesResponse> {
  return apiFetch<NewsCategoriesResponse>("/news/categories");
}

export async function getNewsTrending(params?: {
  days?: number;
  limit?: number;
}): Promise<TrendingNewsResponse> {
  const search = new URLSearchParams();
  appendParams(search, { days: params?.days, limit: params?.limit });
  const qs = search.toString();
  return apiFetch<TrendingNewsResponse>(`/news/trending${qs ? `?${qs}` : ""}`);
}

export async function getNewsEvent(id: number): Promise<NewsEventCard> {
  return apiFetch<NewsEventCard>(`/news/${id}`);
}

export async function summarizeNewsEvent(id: number): Promise<SummarizeResponse> {
  return apiFetch<SummarizeResponse>(`/news/${id}/summarize`, { method: "POST" });
}

export async function refreshNews(params?: {
  days?: number;
  limit?: number;
}): Promise<NewsRefreshResponse> {
  const search = new URLSearchParams();
  appendParams(search, { days: params?.days ?? 1, limit: params?.limit ?? 200 });
  return apiFetch<NewsRefreshResponse>(`/news/refresh?${search.toString()}`, {
    method: "POST",
  });
}

export async function getMyWatchlist(clientKey: string): Promise<WatchlistResponse> {
  return apiFetch<WatchlistResponse>("/watchlists/me", {
    headers: clientHeaders(clientKey),
  });
}

export async function replaceMyWatchlist(
  clientKey: string,
  symbols: string[],
): Promise<WatchlistResponse> {
  return apiFetch<WatchlistResponse>("/watchlists/me/items", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...clientHeaders(clientKey),
    },
    body: JSON.stringify({ symbols }),
  });
}

export async function addToMyWatchlist(
  clientKey: string,
  symbol: string,
  exchange?: string,
): Promise<WatchlistResponse> {
  return apiFetch<WatchlistResponse>("/watchlists/me/items", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...clientHeaders(clientKey),
    },
    body: JSON.stringify({ symbol, exchange }),
  });
}

export async function removeFromMyWatchlist(
  clientKey: string,
  symbol: string,
): Promise<WatchlistResponse> {
  return apiFetch<WatchlistResponse>(
    `/watchlists/me/items/${encodeURIComponent(symbol)}`,
    {
      method: "DELETE",
      headers: clientHeaders(clientKey),
    },
  );
}

export async function getMyPortfolio(clientKey: string): Promise<PortfolioResponse> {
  return apiFetch<PortfolioResponse>("/portfolio/me", {
    headers: clientHeaders(clientKey),
  });
}

export async function importMyPortfolio(
  clientKey: string,
  file: File,
): Promise<PortfolioResponse> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_BASE}/portfolio/me/import`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...clientHeaders(clientKey),
    },
    body,
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<PortfolioResponse>;
}

export async function clearMyPortfolio(clientKey: string): Promise<PortfolioResponse> {
  return apiFetch<PortfolioResponse>("/portfolio/me/holdings", {
    method: "DELETE",
    headers: clientHeaders(clientKey),
  });
}
