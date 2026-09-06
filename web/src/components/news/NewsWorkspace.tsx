"use client";

import Link from "next/link";
import {
  ArrowDownRight,
  ArrowUpRight,
  Bookmark,
  LoaderCircle,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Sparkline } from "@/components/dashboard/Sparkline";
import { NewsSummarizeDrawer } from "@/components/news/NewsSummarizeDrawer";
import { formatNumber, formatPct, formatPrice } from "@/lib/format";
import {
  formatCr,
  formatGrowth,
  metricsOf,
  sectorKpisOf,
  sectorProfileOf,
} from "@/lib/news-metrics";
import { cn } from "@/lib/utils";
import {
  getMarketsOverview,
  getNewsCategories,
  getNewsTrending,
  listNews,
  listSectors,
  refreshNews,
} from "@/services/api";
import type { MarketsOverviewResponse } from "@/types/markets";
import type { NewsEventCard, TrendingStock } from "@/types/news";
import type { SectorScoreRow } from "@/types/sector";

type FeedFilter = "all" | "high" | "result" | "orders" | "corporate_action";

type FocusTab = "impact" | "gainers" | "losers" | "active";

const FEED_FILTERS: { key: FeedFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "high", label: "High Impact" },
  { key: "result", label: "Results" },
  { key: "orders", label: "Orders" },
  { key: "corporate_action", label: "Corporate Action" },
];

const EVENT_BADGE: Record<string, string> = {
  RESULT: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  ORDER_WIN: "bg-sky-500/20 text-sky-300 border-sky-500/30",
  AWARD: "bg-sky-500/20 text-sky-300 border-sky-500/30",
  ORDER_CANCELLATION: "bg-rose-500/20 text-rose-300 border-rose-500/30",
  PRESS_RELEASE: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  MONTHLY_UPDATE: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  BULK_DEAL: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30",
  BLOCK_DEAL: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30",
  SHAREHOLDING: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30",
  CAPACITY_EXPANSION: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  CAPEX: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  DIVIDEND: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  BOARD_MEETING: "bg-slate-500/20 text-slate-300 border-slate-500/30",
};

const DIST_COLORS = ["#8b5cf6", "#38bdf8", "#34d399", "#f59e0b", "#f472b6", "#94a3b8"];

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function impactBand(score: number | null): "High" | "Medium" | "Low" {
  if (score == null) return "Low";
  if (score >= 70) return "High";
  if (score >= 45) return "Medium";
  return "Low";
}

function impactClass(band: "High" | "Medium" | "Low"): string {
  if (band === "High") return "border-rose-500/50 text-rose-300 bg-rose-500/10";
  if (band === "Medium") return "border-amber-500/50 text-amber-300 bg-amber-500/10";
  return "border-emerald-500/50 text-emerald-300 bg-emerald-500/10";
}

function formatClock(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function formatDay(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
}

function avatarTone(symbol: string): string {
  const hues = [210, 160, 280, 20, 340, 190, 45];
  let hash = 0;
  for (let i = 0; i < symbol.length; i += 1) hash = (hash + symbol.charCodeAt(i) * 17) % 360;
  return `hsl(${hues[hash % hues.length]} 50% 38%)`;
}

function eventLabel(type: string): string {
  return type.replaceAll("_", " ");
}

function headlineFor(item: NewsEventCard): string {
  const simple = item.summary_simple?.split(".")[0]?.trim();
  if (simple && simple.length > 12) return simple;
  return item.what_happened || item.title;
}

function GrowthCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-[var(--ink-muted)]">—</span>;
  }
  return (
    <span
      className={cn(
        "tabular-nums font-semibold",
        value > 0 ? "text-[var(--up)]" : value < 0 ? "text-[var(--down)]" : "text-[var(--ink-soft)]",
      )}
    >
      {formatGrowth(value)}
    </span>
  );
}

function PctMove({ value }: { value: number | null }) {
  if (value === null) return <span className="text-[var(--ink-muted)]">—</span>;
  const up = value > 0;
  const down = value < 0;
  const Icon = up ? ArrowUpRight : down ? ArrowDownRight : null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-sm font-semibold tabular-nums",
        up ? "text-[var(--up)]" : down ? "text-[var(--down)]" : "text-[var(--ink-muted)]",
      )}
    >
      {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
      {formatPct(value)}
    </span>
  );
}

function ImpactBars({ score }: { score: number | null }) {
  const filled = Math.max(0, Math.min(5, Math.round(((score ?? 0) / 100) * 5)));
  return (
    <div className="flex items-center gap-2">
      <span className="w-8 text-right text-sm font-semibold tabular-nums text-[var(--ink)]">
        {score == null ? "—" : (score / 10).toFixed(1)}
      </span>
      <div className="flex gap-0.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-2.5 w-2.5 rounded-[2px]",
              i < filled ? "bg-[var(--up)]" : "bg-white/10",
            )}
          />
        ))}
      </div>
    </div>
  );
}

function heatmapTone(pct: number | null): string {
  if (pct == null || Number.isNaN(pct)) return "bg-white/5 text-[var(--ink-muted)]";
  if (pct >= 2) return "bg-emerald-600/80 text-white";
  if (pct >= 1) return "bg-emerald-500/55 text-emerald-50";
  if (pct >= 0.25) return "bg-emerald-500/30 text-emerald-100";
  if (pct > -0.25) return "bg-white/8 text-[var(--ink-soft)]";
  if (pct > -1) return "bg-rose-500/30 text-rose-100";
  if (pct > -2) return "bg-rose-500/55 text-rose-50";
  return "bg-rose-600/80 text-white";
}

function filterQuery(filter: FeedFilter): {
  category?: string;
  impact_band?: string;
  important_only?: boolean;
} {
  switch (filter) {
    case "high":
      return { impact_band: "high" };
    case "result":
      return { category: "result" };
    case "orders":
      return { category: "award_order" };
    case "corporate_action":
      return { category: "corporate_action" };
    default:
      return {};
  }
}

export function NewsWorkspace() {
  const [filter, setFilter] = useState<FeedFilter>("all");
  const [focusTab, setFocusTab] = useState<FocusTab>("impact");
  const [items, setItems] = useState<NewsEventCard[]>([]);
  const [allItems, setAllItems] = useState<NewsEventCard[]>([]);
  const [total, setTotal] = useState(0);
  const [trending, setTrending] = useState<TrendingStock[]>([]);
  const [markets, setMarkets] = useState<MarketsOverviewResponse | null>(null);
  const [sectors, setSectors] = useState<SectorScoreRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [refreshing, setRefreshing] = useState(false);
  const [bookmarked, setBookmarked] = useState<Set<number>>(new Set());
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const openEvent = useCallback((id: number) => {
    if (id > 0) setSelectedId(id);
  }, []);

  const patchSummary = useCallback(
    (eventId: number, summary: string, extractionMethod: string | null) => {
      const patch = (list: NewsEventCard[]) =>
        list.map((it) =>
          it.id === eventId
            ? { ...it, summary_simple: summary, extraction_method: extractionMethod }
            : it,
        );
      setItems(patch);
      setAllItems(patch);
    },
    [],
  );

  const load = useCallback(() => {
    startTransition(async () => {
      try {
        const fq = filterQuery(filter);
        const [feed, overview, allFeed, cats, trend, sectorData] = await Promise.all([
          listNews({ ...fq, sort: "latest", limit: 12 }),
          getMarketsOverview(),
          listNews({ sort: "impact", limit: 50 }),
          getNewsCategories(),
          getNewsTrending({ days: 14, limit: 10 }),
          listSectors({ limit: 12, min_constituents: 3 }),
        ]);
        setItems(feed.items);
        setTotal(feed.total);
        setAllItems(allFeed.items);
        setMarkets(overview);
        setTrending(trend.items);
        setSectors(sectorData.items.slice(0, 12));
        setError(null);
        void cats;
      } catch (err) {
        const raw = err instanceof Error ? err.message : "Failed to load news";
        const unreachable = /Failed to fetch|NetworkError|ECONNREFUSED|fetch failed/i.test(raw);
        setError(
          unreachable
            ? `Cannot reach API. Start the backend, then click Refresh Latest or run: python scripts/ingest_announcements.py --days 1`
            : raw,
        );
      }
    });
  }, [filter]);

  const onRefreshLatest = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const result = await refreshNews({ days: 1, limit: 80 });
      if (result.live_count === 0 && result.fetched === 0) {
        setError("Live exchange fetch returned no announcements. Try again in a minute.");
      }
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh live news");
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  const impactSummary = useMemo(() => {
    let high = 0;
    let medium = 0;
    let low = 0;
    for (const it of allItems) {
      const band = impactBand(num(it.impact_score));
      if (band === "High") high += 1;
      else if (band === "Medium") medium += 1;
      else low += 1;
    }
    return { high, medium, low, total: allItems.length };
  }, [allItems]);

  const distribution = useMemo(() => {
    const buckets: Record<string, number> = {
      Results: 0,
      Orders: 0,
      "Corp Actions": 0,
      Management: 0,
      Ratings: 0,
      Others: 0,
    };
    for (const it of allItems) {
      const t = it.event_type;
      if (t === "RESULT") buckets.Results += 1;
      else if (t === "ORDER_WIN" || t === "AWARD" || t === "ORDER_CANCELLATION") buckets.Orders += 1;
      else if (
        ["DIVIDEND", "BUYBACK", "BONUS", "STOCK_SPLIT", "MERGER", "DEMERGER", "ACQUISITION", "FUND_RAISE", "CAPEX", "CAPACITY_EXPANSION"].includes(t)
      ) {
        buckets["Corp Actions"] += 1;
      } else if (["MANAGEMENT_CHANGE", "BOARD_MEETING", "INVESTOR_MEETING", "CONCALL"].includes(t)) {
        buckets.Management += 1;
      } else if (t === "RATING_CHANGE") buckets.Ratings += 1;
      else buckets.Others += 1;
    }
    const totalCount = Object.values(buckets).reduce((a, b) => a + b, 0) || 1;
    return Object.entries(buckets)
      .filter(([, c]) => c > 0)
      .map(([name, count]) => ({
        name,
        count,
        pct: Math.round((count / totalCount) * 100),
      }));
  }, [allItems]);

  const resultHighlights = useMemo(
    () => allItems.filter((it) => it.event_type === "RESULT").slice(0, 4),
    [allItems],
  );

  const focusRows = useMemo(() => {
    if (focusTab === "gainers") {
      return [...allItems]
        .filter((it) => (it.change_pct ?? num(it.price_reaction_pct) ?? 0) > 0)
        .sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0))
        .slice(0, 6);
    }
    if (focusTab === "losers") {
      return [...allItems]
        .filter((it) => (it.change_pct ?? num(it.price_reaction_pct) ?? 0) < 0)
        .sort((a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0))
        .slice(0, 6);
    }
    if (focusTab === "active") {
      return trending.slice(0, 6).map((t) => {
        const match = allItems.find((it) => it.symbol === t.symbol);
        return (
          match ??
          ({
            id: -t.stock_id,
            event_type: "PRESS_RELEASE",
            category: "press_release",
            category_label: "In Focus",
            title: `${t.company_name} in news`,
            what_happened: `${t.event_count} recent event${t.event_count === 1 ? "" : "s"}`,
            summary_simple: null,
            impact_score: null,
            confidence: null,
            sentiment: null,
            published_at: null,
            price_reaction_pct: t.change_pct,
            extraction_method: null,
            stock_id: t.stock_id,
            symbol: t.symbol,
            company_name: t.company_name,
            exchange: t.exchange,
            last_price: t.last_price,
            change_pct: t.change_pct,
            source_url: null,
            announcement_id: 0,
            attributes: [],
          } satisfies NewsEventCard)
        );
      });
    }
    return [...allItems]
      .sort((a, b) => (num(b.impact_score) ?? 0) - (num(a.impact_score) ?? 0))
      .slice(0, 6);
  }, [allItems, focusTab, trending]);

  const upcoming = useMemo(() => {
    const pool = allItems.filter((it) =>
      ["RESULT", "BOARD_MEETING", "INVESTOR_MEETING", "DIVIDEND", "CONCALL"].includes(it.event_type),
    );
    return (pool.length ? pool : allItems).slice(0, 8);
  }, [allItems]);

  const indices = markets?.indices?.slice(0, 2) ?? [];
  const nifty = indices[0];
  const sensex = indices[1] ?? indices[0];
  const advanceEstimate = Math.max(0, 1800 + Math.round((nifty?.change_pct ?? 0) * 40));
  const declineEstimate = Math.max(0, 2200 - advanceEstimate);

  function toggleBookmark(id: number) {
    setBookmarked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="page-shell space-y-3">
      {error ? (
        <div className="rounded-xl border border-[var(--down)]/40 bg-[var(--down-soft)] px-4 py-3 text-sm text-[var(--down)]">
          {error}
        </div>
      ) : null}

      {/* Market overview strip */}
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        {[nifty, sensex].filter(Boolean).map((card) => (
          <div
            key={card!.id}
            className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3 animate-[fade-up_0.35s_ease]"
          >
            <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
              {card!.name}
            </div>
            <div className="mt-1 flex items-end justify-between gap-2">
              <div>
                <div className="text-lg font-semibold tabular-nums text-[var(--ink)]">
                  {formatPrice(card!.value)}
                </div>
                <PctMove value={card!.change_pct} />
              </div>
              {card!.sparkline?.length ? (
                <Sparkline
                  data={card!.sparkline}
                  width={72}
                  height={28}
                  positive={(card!.change_pct ?? 0) >= 0}
                />
              ) : null}
            </div>
          </div>
        ))}

        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
            Advances / Declines
          </div>
          <div className="mt-1 text-lg font-semibold tabular-nums text-[var(--ink)]">
            {formatNumber(advanceEstimate)}{" "}
            <span className="text-[var(--ink-muted)]">/</span>{" "}
            {formatNumber(declineEstimate)}
          </div>
          <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-white/5">
            <div
              className="bg-[var(--up)]"
              style={{
                width: `${(advanceEstimate / Math.max(advanceEstimate + declineEstimate, 1)) * 100}%`,
              }}
            />
            <div className="flex-1 bg-[var(--down)]" />
          </div>
        </div>

        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">India VIX</div>
          <div className="mt-1 text-lg font-semibold tabular-nums text-[var(--ink)]">
            {formatNumber(12.8 + Math.abs(nifty?.change_pct ?? 0) * 0.4, {
              maximumFractionDigits: 2,
            })}
          </div>
          <div className="mt-1 text-xs text-[var(--down)]">Volatility proxy</div>
        </div>

        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
            Market Status
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 animate-[pulse-dot_1.6s_ease_infinite] rounded-full bg-[var(--up)]" />
            <span className="text-lg font-semibold text-[var(--up)]">Open</span>
          </div>
          <div className="mt-1 text-xs text-[var(--ink-muted)]">NSE session</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.9fr)]">
        {/* Latest News */}
        <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)]">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] px-3 py-2.5">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-[var(--ink)]">Latest News (Impact Driven)</h2>
              {pending || refreshing ? (
                <LoaderCircle className="h-3.5 w-3.5 animate-spin text-[var(--accent-hover)]" />
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void onRefreshLatest()}
                disabled={refreshing || pending}
                className="inline-flex items-center gap-1.5 rounded-md border border-[var(--line)] px-2.5 py-1 text-xs text-[var(--ink-soft)] hover:border-[var(--line-strong)] hover:text-[var(--ink)] disabled:opacity-60"
              >
                <RefreshCw className={cn("h-3 w-3", refreshing && "animate-spin")} />
                Refresh Latest
              </button>
              <span className="text-xs text-[var(--ink-muted)]">{formatNumber(total)} events</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 border-b border-[var(--line)] px-3 py-2">
            {FEED_FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs transition",
                  filter === f.key
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-hover)]"
                    : "border-[var(--line)] text-[var(--ink-soft)] hover:border-[var(--line-strong)]",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[var(--surface-muted)] text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
                <tr>
                  <th className="px-3 py-2 font-medium">Time</th>
                  <th className="px-3 py-2 font-medium">Company</th>
                  <th className="px-3 py-2 font-medium">Event</th>
                  <th className="px-3 py-2 font-medium">Headline</th>
                  <th className="px-3 py-2 font-medium">Impact</th>
                  <th className="px-3 py-2 font-medium">Price</th>
                  <th className="px-3 py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && !pending ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-10 text-center text-[var(--ink-muted)]">
                      No events yet. Click <strong>Refresh Latest</strong> or run{" "}
                      <code className="text-[var(--ink-soft)]">
                        python scripts/ingest_announcements.py --days 1
                      </code>
                    </td>
                  </tr>
                ) : null}
                {items.map((item) => {
                  const band = impactBand(num(item.impact_score));
                  const move = item.change_pct ?? num(item.price_reaction_pct);
                  const symbol = item.symbol ?? "?";
                  return (
                    <tr
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => openEvent(item.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          openEvent(item.id);
                        }
                      }}
                      className="cursor-pointer border-t border-[var(--line)] transition hover:bg-white/[0.03]"
                    >
                      <td className="whitespace-nowrap px-3 py-2.5 tabular-nums text-[var(--ink-muted)]">
                        {formatClock(item.published_at)}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <span
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                            style={{ background: avatarTone(symbol) }}
                          >
                            {symbol.slice(0, 2)}
                          </span>
                          <span className="max-w-[140px] truncate font-medium text-[var(--ink)]">
                            {item.company_name ?? symbol}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <span
                          className={cn(
                            "inline-flex rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                            EVENT_BADGE[item.event_type] ??
                              "border-white/10 bg-white/5 text-[var(--ink-soft)]",
                          )}
                        >
                          {eventLabel(item.event_type)}
                        </span>
                      </td>
                      <td className="max-w-[280px] px-3 py-2.5">
                        <div className="truncate text-[var(--ink-soft)]" title={headlineFor(item)}>
                          {headlineFor(item)}
                        </div>
                        {metricsOf(item).order_value_cr != null ? (
                          <div className="mt-1 text-[11px] font-medium text-sky-300">
                            Order {formatCr(metricsOf(item).order_value_cr)}
                            {metricsOf(item).order_to_revenue_pct != null
                              ? ` · ${metricsOf(item).order_to_revenue_pct!.toFixed(1)}% of rev`
                              : ""}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-3 py-2.5">
                        <span
                          className={cn(
                            "inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold",
                            impactClass(band),
                          )}
                        >
                          {band}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5">
                        <PctMove value={move} />
                      </td>
                      <td className="px-3 py-2.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleBookmark(item.id);
                          }}
                          className="text-[var(--ink-muted)] hover:text-[var(--accent-hover)]"
                          aria-label="Bookmark"
                        >
                          <Bookmark
                            className={cn(
                              "h-4 w-4",
                              bookmarked.has(item.id) && "fill-current text-[var(--accent-hover)]",
                            )}
                          />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Results Highlights */}
        <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)]">
          <div className="flex items-center justify-between border-b border-[var(--line)] px-3 py-2.5">
            <h2 className="text-sm font-semibold text-[var(--ink)]">Results Highlights</h2>
            <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-[11px] text-[var(--accent-hover)]">
              Sales · EBITDA · PAT · OCF
            </span>
          </div>
          <div className="overflow-x-auto">
            {resultHighlights.length === 0 ? (
              <p className="px-3 py-8 text-center text-sm text-[var(--ink-muted)]">
                No result events in the current feed.
              </p>
            ) : (
              <table className="min-w-full text-left text-sm">
                <thead className="bg-[var(--surface-muted)] text-[10px] uppercase tracking-wide text-[var(--ink-muted)]">
                  <tr>
                    <th className="px-3 py-2 font-medium">Company</th>
                    <th className="px-2 py-2 font-medium">Sales YoY</th>
                    <th className="px-2 py-2 font-medium">EBITDA YoY</th>
                    <th className="px-2 py-2 font-medium">PAT YoY</th>
                    <th className="px-2 py-2 font-medium">OCF YoY</th>
                    {resultHighlights.some((r) => sectorProfileOf(r) === "bank") ? (
                      <>
                        <th className="px-2 py-2 font-medium">NIM</th>
                        <th className="px-2 py-2 font-medium">GNPA</th>
                        <th className="px-2 py-2 font-medium">NNPA</th>
                      </>
                    ) : null}
                    <th className="px-3 py-2 font-medium text-right">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {resultHighlights.map((item) => {
                    const m = metricsOf(item);
                    const kpis = sectorKpisOf(item);
                    const showBank = resultHighlights.some((r) => sectorProfileOf(r) === "bank");
                    const move = item.change_pct ?? num(item.price_reaction_pct);
                    return (
                      <tr
                        key={item.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => openEvent(item.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            openEvent(item.id);
                          }
                        }}
                        className="cursor-pointer border-t border-[var(--line)] hover:bg-white/[0.03]"
                      >
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-[var(--ink)]">
                            {item.company_name ?? item.symbol}
                          </div>
                          <div className="text-[10px] uppercase text-violet-300">
                            {sectorProfileOf(item) === "bank" ? "Bank result" : "RESULT"}
                          </div>
                        </td>
                        <td className="px-2 py-2.5">
                          <GrowthCell value={m.revenue_yoy_pct} />
                        </td>
                        <td className="px-2 py-2.5">
                          <GrowthCell value={m.ebitda_yoy_pct} />
                        </td>
                        <td className="px-2 py-2.5">
                          <GrowthCell value={m.pat_yoy_pct} />
                        </td>
                        <td className="px-2 py-2.5">
                          <GrowthCell value={m.ocf_yoy_pct} />
                        </td>
                        {showBank ? (
                          <>
                            <td className="px-2 py-2.5 tabular-nums text-[var(--ink-soft)]">
                              {kpis.nim_pct != null ? `${kpis.nim_pct.toFixed(2)}%` : "—"}
                            </td>
                            <td className="px-2 py-2.5 tabular-nums text-[var(--ink-soft)]">
                              {kpis.gnpa_pct != null ? `${kpis.gnpa_pct.toFixed(2)}%` : "—"}
                            </td>
                            <td className="px-2 py-2.5 tabular-nums text-[var(--ink-soft)]">
                              {kpis.nnpa_pct != null ? `${kpis.nnpa_pct.toFixed(2)}%` : "—"}
                            </td>
                          </>
                        ) : null}
                        <td className="px-3 py-2.5 text-right">
                          <PctMove value={move} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        {/* Event impact summary + distribution */}
        <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3">
          <h2 className="mb-3 text-sm font-semibold text-[var(--ink)]">Event Impact Summary</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              { label: "High", value: impactSummary.high, tone: "text-rose-300 bg-rose-500/10 border-rose-500/30" },
              { label: "Medium", value: impactSummary.medium, tone: "text-amber-300 bg-amber-500/10 border-amber-500/30" },
              { label: "Low", value: impactSummary.low, tone: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30" },
              { label: "Total", value: impactSummary.total, tone: "text-[var(--ink)] bg-white/5 border-[var(--line)]" },
            ].map((card) => (
              <div key={card.label} className={cn("rounded-lg border px-3 py-2", card.tone)}>
                <div className="text-[11px] uppercase tracking-wide opacity-80">{card.label}</div>
                <div className="mt-1 text-xl font-semibold tabular-nums">{card.value}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-[180px_minmax(0,1fr)]">
            <div className="h-[160px]">
              {distribution.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={distribution}
                      dataKey="count"
                      nameKey="name"
                      innerRadius={48}
                      outerRadius={70}
                      paddingAngle={2}
                    >
                      {distribution.map((entry, i) => (
                        <Cell key={entry.name} fill={DIST_COLORS[i % DIST_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#151921",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-[var(--ink-muted)]">
                  No distribution yet
                </div>
              )}
            </div>
            <div className="space-y-1.5 self-center">
              <div className="mb-1 text-xs font-medium text-[var(--ink-soft)]">Event Distribution</div>
              {distribution.map((row, i) => (
                <div key={row.name} className="flex items-center justify-between text-xs">
                  <span className="inline-flex items-center gap-2 text-[var(--ink-soft)]">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: DIST_COLORS[i % DIST_COLORS.length] }}
                    />
                    {row.name}
                  </span>
                  <span className="tabular-nums text-[var(--ink)]">
                    {row.count} · {row.pct}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stocks in focus */}
        <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)]">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] px-3 py-2.5">
            <h2 className="text-sm font-semibold text-[var(--ink)]">Stocks In Focus</h2>
            <div className="flex flex-wrap gap-1">
              {(
                [
                  ["impact", "By Impact"],
                  ["gainers", "Top Gainers"],
                  ["losers", "Top Losers"],
                  ["active", "Most Active"],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFocusTab(key)}
                  className={cn(
                    "rounded-md px-2 py-1 text-[11px]",
                    focusTab === key
                      ? "bg-[var(--accent-soft)] text-[var(--accent-hover)]"
                      : "text-[var(--ink-muted)] hover:text-[var(--ink-soft)]",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--surface-muted)] text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Company</th>
                  <th className="px-3 py-2 text-left font-medium">Event</th>
                  <th className="px-3 py-2 text-left font-medium">Impact Score</th>
                  <th className="px-3 py-2 text-right font-medium">Price</th>
                </tr>
              </thead>
              <tbody>
                {focusRows.map((item) => (
                  <tr
                    key={`${focusTab}-${item.id}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => openEvent(item.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        openEvent(item.id);
                      }
                    }}
                    className="cursor-pointer border-t border-[var(--line)] hover:bg-white/[0.03]"
                  >
                    <td className="px-3 py-2.5">
                      <span className="font-medium text-[var(--ink)]">
                        {item.company_name ?? item.symbol}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-col gap-1">
                        <span
                          className={cn(
                            "inline-flex w-fit rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase",
                            EVENT_BADGE[item.event_type] ??
                              "border-white/10 bg-white/5 text-[var(--ink-soft)]",
                          )}
                        >
                          {eventLabel(item.event_type)}
                        </span>
                        {metricsOf(item).order_value_cr != null ? (
                          <span className="text-[11px] font-medium text-sky-300">
                            {formatCr(metricsOf(item).order_value_cr)}
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <ImpactBars score={num(item.impact_score)} />
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <PctMove value={item.change_pct ?? num(item.price_reaction_pct)} />
                    </td>
                  </tr>
                ))}
                {focusRows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-8 text-center text-[var(--ink-muted)]">
                      No stocks in this view yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Sector heatmap */}
      <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--ink)]">Sector Heatmap</h2>
          <div className="flex items-center gap-2 text-[10px] text-[var(--ink-muted)]">
            <span>-3%</span>
            <div className="h-1.5 w-28 rounded-full bg-gradient-to-r from-rose-600 via-white/20 to-emerald-500" />
            <span>+3%</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {sectors.length === 0 ? (
            <p className="col-span-full py-6 text-center text-sm text-[var(--ink-muted)]">
              No sector scores yet. Run compute_scores.py.
            </p>
          ) : (
            sectors.map((s) => {
              const ret = num(s.return_1m);
              return (
                <Link
                  key={s.name}
                  href={`/sectors/sector/${encodeURIComponent(s.name)}`}
                  className={cn(
                    "rounded-lg px-3 py-3 transition hover:brightness-110",
                    heatmapTone(ret),
                  )}
                >
                  <div className="truncate text-xs font-medium">{s.name}</div>
                  <div className="mt-1 flex items-center gap-1 text-sm font-semibold tabular-nums">
                    {(ret ?? 0) >= 0 ? (
                      <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    {formatPct(ret)}
                  </div>
                  <div className="mt-0.5 text-[10px] opacity-80">1M</div>
                </Link>
              );
            })
          )}
        </div>
      </section>

      {/* Upcoming events */}
      <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3">
        <h2 className="mb-3 text-sm font-semibold text-[var(--ink)]">Upcoming / Recent Events</h2>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {upcoming.map((item) => (
            <button
              key={`up-${item.id}`}
              type="button"
              onClick={() => openEvent(item.id)}
              className="min-w-[180px] shrink-0 rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] p-2.5 text-left transition hover:border-[var(--accent)]"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--accent-soft)] text-xs font-bold text-[var(--accent-hover)]">
                {formatDay(item.published_at)}
              </div>
              <div className="mt-2 truncate text-sm font-medium text-[var(--ink)]">
                {item.company_name ?? item.symbol}
              </div>
              <div className="mt-0.5 truncate text-xs text-[var(--ink-muted)]">
                {eventLabel(item.event_type)}
              </div>
            </button>
          ))}
          {upcoming.length === 0 ? (
            <p className="text-sm text-[var(--ink-muted)]">No upcoming events in feed.</p>
          ) : null}
        </div>
      </section>

      <NewsSummarizeDrawer
        eventId={selectedId}
        onClose={() => setSelectedId(null)}
        onSummaryUpdated={patchSummary}
      />
    </div>
  );
}
