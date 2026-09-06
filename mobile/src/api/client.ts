import { getApiBase } from "./config";
import type {
  MarketsOverviewResponse,
  ScreenerQuery,
  SectorListResponse,
  StockAnalysisResponse,
  StockDetail,
} from "../types/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await getApiBase();
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function appendParams(search: URLSearchParams, params: Record<string, unknown>) {
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
}

export async function getMarketsOverview(): Promise<MarketsOverviewResponse> {
  return apiFetch<MarketsOverviewResponse>("/markets/overview");
}

export async function screenStocks(
  params?: ScreenerQuery,
): Promise<StockAnalysisResponse> {
  const search = new URLSearchParams();
  appendParams(search, { ...(params ?? {}) });
  const qs = search.toString();
  return apiFetch<StockAnalysisResponse>(`/screener${qs ? `?${qs}` : ""}`);
}

export async function getStock(
  symbol: string,
  params?: { exchange?: string; price_limit?: number },
): Promise<StockDetail> {
  const search = new URLSearchParams();
  appendParams(search, {
    exchange: params?.exchange,
    price_limit: params?.price_limit ?? 120,
  });
  const qs = search.toString();
  return apiFetch<StockDetail>(
    `/stocks/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ""}`,
  );
}

export async function listSectors(params?: {
  limit?: number;
  min_constituents?: number;
}): Promise<SectorListResponse> {
  const search = new URLSearchParams();
  appendParams(search, {
    limit: params?.limit ?? 40,
    min_constituents: params?.min_constituents ?? 3,
  });
  return apiFetch<SectorListResponse>(`/sectors?${search.toString()}`);
}
