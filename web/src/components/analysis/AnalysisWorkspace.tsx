"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  BookmarkPlus,
  LineChart,
  LoaderCircle,
  Play,
  Star,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, useTransition } from "react";

import { Sparkline } from "@/components/dashboard/Sparkline";
import { formatNumber, formatPct, formatPrice } from "@/lib/format";
import {
  RATING_META,
  STRATEGY_LABELS,
  STRATEGY_SLUGS,
  loadSavedScreens,
  metricBool,
  metricNumber,
  metricString,
  parseStrategySlug,
  saveSavedScreens,
  type SavedScreen,
} from "@/lib/strategies";
import { cn } from "@/lib/utils";
import { runStrategy } from "@/services/api";
import type {
  RatingBand,
  StrategyRunResponse,
  StrategySlug,
  StrategyStockRow,
} from "@/types/strategy";

function avatarTone(symbol: string): string {
  const hues = [210, 160, 280, 20, 340, 190];
  let hash = 0;
  for (let i = 0; i < symbol.length; i += 1) hash = (hash + symbol.charCodeAt(i) * 17) % 360;
  const h = hues[hash % hues.length];
  return `hsl(${h} 55% 42%)`;
}

function ChangeCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-[var(--ink-muted)]">—</span>;
  }
  return (
    <span
      className={cn(
        "tabular-nums",
        value > 0 ? "text-[var(--up)]" : value < 0 ? "text-[var(--down)]" : "text-[var(--ink-muted)]",
      )}
    >
      {formatPct(value)}
    </span>
  );
}

function ScoreBadge({ score, rating }: { score: number; rating: RatingBand }) {
  return (
    <span
      className={cn(
        "inline-flex min-w-[2.5rem] items-center justify-center rounded-md px-2 py-0.5 text-sm font-semibold tabular-nums",
        RATING_META[rating].soft,
      )}
    >
      {Math.round(score)}
    </span>
  );
}

function InstLabel({ value }: { value: string | null }) {
  if (!value) return <span className="text-[var(--ink-muted)]">—</span>;
  return (
    <span className="inline-block whitespace-nowrap text-[var(--ink-soft)]">{value}</span>
  );
}

function metricCell(row: StrategyStockRow, key: string, kind: "pct" | "num" | "text" = "num") {
  if (kind === "text") {
    const s = metricString(row.metrics, key);
    return s ?? "—";
  }
  const n = metricNumber(row.metrics, key);
  if (n === null) return "—";
  if (kind === "pct") return formatPct(n);
  return formatNumber(n, { maximumFractionDigits: 2 });
}

export function AnalysisWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const strategy = parseStrategySlug(searchParams.get("strategy"));

  const [data, setData] = useState<StrategyRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [savedScreens, setSavedScreens] = useState<SavedScreen[]>([]);
  const [saveFlash, setSaveFlash] = useState(false);

  useEffect(() => {
    setSavedScreens(loadSavedScreens());
  }, []);

  const load = useCallback(
    (slug: StrategySlug) => {
      startTransition(async () => {
        try {
          const result = await runStrategy(slug, {
            exchange: "NSE",
            limit: 50,
            offset: 0,
            scan_limit: 5000,
          });
          setData(result);
          setSelectedSymbol(result.selected_symbol);
          setError(null);
        } catch (err) {
          const raw = err instanceof Error ? err.message : "Failed to run analysis";
          const unreachable =
            /Failed to fetch|NetworkError|ECONNREFUSED|fetch failed/i.test(raw);
          setError(
            unreachable
              ? `Cannot reach API at ${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}. Start the backend on that port (see frontend/.env.local) and retry.`
              : raw,
          );
          setData(null);
        }
      });
    },
    [],
  );

  useEffect(() => {
    load(strategy);
  }, [strategy, load]);

  const selectedRow = useMemo(() => {
    if (!data?.items.length) return null;
    return data.items.find((r) => r.symbol === selectedSymbol) ?? data.items[0] ?? null;
  }, [data, selectedSymbol]);

  function setStrategy(slug: StrategySlug) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("strategy", slug);
    router.replace(`/analysis?${params.toString()}`);
  }

  function onSaveScreen() {
    if (!data) return;
    const screen: SavedScreen = {
      id: `${Date.now()}`,
      name: `My ${data.strategy.short_name} Screen`,
      strategy: data.strategy.slug,
      createdAt: new Date().toISOString(),
    };
    const next = [screen, ...savedScreens].slice(0, 12);
    setSavedScreens(next);
    saveSavedScreens(next);
    setSaveFlash(true);
    window.setTimeout(() => setSaveFlash(false), 1600);
  }

  const counts = data?.summary.counts;
  const trend = data?.summary.market_trend;

  const advancePct =
    trend && trend.advances != null && trend.declines != null
      ? (trend.advances / Math.max(trend.advances + trend.declines, 1)) * 100
      : null;

  return (
    <div className="page-shell">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0 space-y-4">
          <header className="animate-[fade-up_0.35s_ease_both]">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-wide text-[var(--ink)] sm:text-4xl">
                  Strategies
                </h1>
                <p className="mt-1.5 max-w-2xl text-sm text-[var(--ink-soft)]">
                  Strategy-driven stock screening with explainable checklists for CANSLIM, GARP,
                  Darvas Box, and SEPA (Minervini).
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onSaveScreen}
                  disabled={!data}
                  className="inline-flex items-center gap-2 rounded-lg border border-[var(--accent)] bg-transparent px-3.5 py-2 text-sm font-medium text-[var(--accent)] transition hover:bg-[var(--accent-soft)] disabled:opacity-40"
                >
                  <BookmarkPlus className="h-4 w-4" />
                  {saveFlash ? "Saved" : "Save Screen"}
                </button>
                <button
                  type="button"
                  onClick={() => load(strategy)}
                  disabled={pending}
                  className="inline-flex items-center gap-2 rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-3.5 py-2 text-sm font-medium text-white shadow-[0_8px_20px_rgba(99,102,241,0.28)] transition hover:bg-[var(--accent-hover)] disabled:opacity-60"
                >
                  {pending ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4 fill-current" />
                  )}
                  Run Analysis
                </button>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-1 border-b border-[var(--line)] pb-px">
              {STRATEGY_SLUGS.map((slug) => {
                const active = slug === strategy;
                return (
                  <button
                    key={slug}
                    type="button"
                    onClick={() => setStrategy(slug)}
                    className={cn(
                      "relative px-3 py-2.5 text-sm transition",
                      active
                        ? "font-semibold text-[var(--accent)]"
                        : "text-[var(--ink-soft)] hover:text-[var(--ink)]",
                    )}
                  >
                    {STRATEGY_LABELS[slug]}
                    {active ? (
                      <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-[var(--accent)]" />
                    ) : null}
                  </button>
                );
              })}
            </div>
          </header>

          {error ? (
            <div className="rounded-xl border border-[var(--down)]/40 bg-[var(--down-soft)] px-4 py-3 text-sm text-[var(--down)]">
              {error}
            </div>
          ) : null}

          <section className="animate-[fade-up_0.4s_ease_both] rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-xl">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--accent)]">
                  {data?.strategy.name ?? STRATEGY_LABELS[strategy]}
                </p>
                <p className="mt-1 text-sm text-[var(--ink-soft)]">
                  {data?.strategy.description ??
                    "Run analysis to score the universe against this strategy."}
                </p>
              </div>
              <div
                className={cn(
                  "flex min-w-[200px] items-center gap-3 rounded-lg border px-3 py-2.5",
                  trend?.label === "Bullish"
                    ? "border-[var(--up)]/30 bg-[var(--up-soft)]"
                    : trend?.label === "Bearish"
                      ? "border-[var(--down)]/30 bg-[var(--down-soft)]"
                      : "border-[var(--line)] bg-[var(--surface-muted)]",
                )}
              >
                {trend?.label === "Bearish" ? (
                  <TrendingDown className="h-5 w-5 text-[var(--down)]" />
                ) : (
                  <TrendingUp
                    className={cn(
                      "h-5 w-5",
                      trend?.label === "Bullish" ? "text-[var(--up)]" : "text-[var(--warn)]",
                    )}
                  />
                )}
                <div>
                  <p
                    className={cn(
                      "text-sm font-semibold",
                      trend?.label === "Bullish"
                        ? "text-[var(--up)]"
                        : trend?.label === "Bearish"
                          ? "text-[var(--down)]"
                          : "text-[var(--warn)]",
                    )}
                  >
                    {trend?.label ?? "—"}
                  </p>
                  <p className="text-xs text-[var(--ink-soft)]">
                    {trend?.detail ?? "Loading market trend…"}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
              {[
                { label: "Total Stocks", value: counts?.total, tone: "text-[var(--ink)]" },
                {
                  label: "Strong Buy",
                  value: counts?.strong_buy,
                  tone: "text-[var(--up)]",
                },
                { label: "Buy", value: counts?.buy, tone: "text-emerald-300" },
                { label: "Watch", value: counts?.watch, tone: "text-[var(--warn)]" },
                { label: "Avoid", value: counts?.avoid, tone: "text-[var(--down)]" },
              ].map((card) => (
                <div
                  key={card.label}
                  className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2.5"
                >
                  <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--ink-muted)]">
                    {card.label}
                  </p>
                  <p className={cn("mt-1 text-xl font-semibold tabular-nums", card.tone)}>
                    {pending && !data ? "…" : (card.value ?? "—")}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="animate-[fade-up_0.45s_ease_both]">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--ink-muted)]">
                Strategy filters
              </p>
              {pending ? (
                <span className="inline-flex items-center gap-1.5 text-xs text-[var(--ink-muted)]">
                  <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                  Scoring universe…
                </span>
              ) : data ? (
                <span className="text-xs text-[var(--ink-muted)]">
                  Scanned {formatNumber(data.scanned)} · showing {data.items.length}
                </span>
              ) : null}
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
              {(data?.strategy.filters ?? []).map((f) => (
                <div
                  key={f.key}
                  className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-3 py-3 text-center"
                >
                  <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-[var(--accent-soft)] text-sm font-bold text-[var(--accent)]">
                    {f.label}
                  </div>
                  <p className="mt-2 text-[11px] leading-snug text-[var(--ink-soft)]">{f.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="animate-[fade-up_0.5s_ease_both] rounded-xl border border-[var(--line)] bg-[var(--surface)]">
            <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-3">
              <h2 className="text-sm font-semibold text-[var(--ink)]">
                Top {STRATEGY_LABELS[strategy]} Stocks
              </h2>
            </div>
            <div className="dashboard-scroll overflow-x-auto">
              <table className="w-max min-w-full text-left text-sm">
                <thead className="bg-[var(--surface-muted)] text-[11px] uppercase tracking-[0.12em] text-[var(--ink-muted)]">
                  <tr>
                    <th className="px-3 py-2.5 font-medium">#</th>
                    <th className="px-3 py-2.5 font-medium">Stock</th>
                    <th className="px-3 py-2.5 font-medium">Price</th>
                    <th className="px-3 py-2.5 font-medium">% Chg</th>
                    {strategy === "canslim" ? (
                      <>
                        <th className="px-3 py-2.5 font-medium">EPS QoQ</th>
                        <th className="px-3 py-2.5 font-medium">EPS YoY</th>
                        <th className="px-3 py-2.5 font-medium">RS</th>
                        <th className="px-3 py-2.5 font-medium">Rel Vol</th>
                      </>
                    ) : null}
                    {strategy === "garp" ? (
                      <>
                        <th className="px-3 py-2.5 font-medium">PEG</th>
                        <th className="px-3 py-2.5 font-medium">EPS Gr</th>
                        <th className="px-3 py-2.5 font-medium">ROE</th>
                        <th className="px-3 py-2.5 font-medium">D/E</th>
                        <th className="px-3 py-2.5 font-medium">P/E</th>
                      </>
                    ) : null}
                    {strategy === "darvas" ? (
                      <>
                        <th className="px-3 py-2.5 font-medium">Box Top</th>
                        <th className="px-3 py-2.5 font-medium">Box Bot</th>
                        <th className="px-3 py-2.5 font-medium">Breakout</th>
                        <th className="px-3 py-2.5 font-medium">Rel Vol</th>
                      </>
                    ) : null}
                    {strategy === "sepa" ? (
                      <>
                        <th className="px-3 py-2.5 font-medium">RS</th>
                        <th className="px-3 py-2.5 font-medium">vs 52W Hi</th>
                        <th className="px-3 py-2.5 font-medium">vs 52W Lo</th>
                        <th className="px-3 py-2.5 font-medium">VCP</th>
                        <th className="px-3 py-2.5 font-medium">Template</th>
                      </>
                    ) : null}
                    <th className="px-3 py-2.5 font-medium">Score</th>
                    {strategy === "canslim" ? (
                      <th className="px-3 py-2.5 font-medium">Inst.</th>
                    ) : null}
                    <th className="px-3 py-2.5 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {!data?.items.length && !pending ? (
                    <tr>
                      <td
                        colSpan={12}
                        className="px-4 py-10 text-center text-[var(--ink-muted)]"
                      >
                        No scored stocks yet. Ensure screener metrics are refreshed and try again.
                      </td>
                    </tr>
                  ) : null}
                  {data?.items.map((row) => {
                    const active = selectedRow?.symbol === row.symbol;
                    return (
                      <tr
                        key={row.id}
                        onClick={() => setSelectedSymbol(row.symbol)}
                        className={cn(
                          "cursor-pointer border-t border-[var(--line)] transition hover:bg-white/[0.03]",
                          active && "bg-[var(--accent-soft)]/40",
                        )}
                      >
                        <td className="px-3 py-2.5 tabular-nums text-[var(--ink-muted)]">
                          {row.rank}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2.5">
                            <span
                              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                              style={{ background: avatarTone(row.symbol) }}
                            >
                              {row.symbol.slice(0, 2)}
                            </span>
                            <div className="min-w-0">
                              <p className="truncate font-medium text-[var(--ink)]">{row.symbol}</p>
                              <p className="truncate text-xs text-[var(--ink-muted)]">
                                {row.company_name}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-[var(--ink)]">
                          {formatPrice(row.ltp)}
                        </td>
                        <td className="px-3 py-2.5">
                          <ChangeCell value={row.change_pct} />
                        </td>
                        {strategy === "canslim" ? (
                          <>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "eps_qoq", "pct")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "eps_yoy", "pct")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "rs_rating")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricNumber(row.metrics, "relative_volume") != null
                                ? `${metricNumber(row.metrics, "relative_volume")!.toFixed(2)}x`
                                : "—"}
                            </td>
                          </>
                        ) : null}
                        {strategy === "garp" ? (
                          <>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "peg")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "eps_growth", "pct")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "roe", "pct")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "debt_equity")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "pe_ttm")}
                            </td>
                          </>
                        ) : null}
                        {strategy === "darvas" ? (
                          <>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "box_top")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "box_bottom")}
                            </td>
                            <td className="px-3 py-2.5">
                              {metricBool(row.metrics, "breakout") ? (
                                <span className="text-[var(--up)]">Yes</span>
                              ) : metricBool(row.metrics, "inside_box") ? (
                                <span className="text-[var(--warn)]">Inside</span>
                              ) : (
                                <span className="text-[var(--ink-muted)]">No</span>
                              )}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricNumber(row.metrics, "relative_volume") != null
                                ? `${metricNumber(row.metrics, "relative_volume")!.toFixed(2)}x`
                                : "—"}
                            </td>
                          </>
                        ) : null}
                        {strategy === "sepa" ? (
                          <>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "rs_rating")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "dist_from_52w_high_pct", "pct")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricCell(row, "dist_from_52w_low_pct", "pct")}
                            </td>
                            <td className="px-3 py-2.5 tabular-nums">
                              {metricNumber(row.metrics, "vcp_range_pct") != null
                                ? `${metricNumber(row.metrics, "vcp_range_pct")!.toFixed(1)}%`
                                : "—"}
                            </td>
                            <td className="px-3 py-2.5">
                              {metricBool(row.metrics, "trend_template_pass") ? (
                                <span className="text-[var(--up)]">Pass</span>
                              ) : (
                                <span className="text-[var(--ink-muted)]">Partial</span>
                              )}
                            </td>
                          </>
                        ) : null}
                        <td className="px-3 py-2.5">
                          <ScoreBadge score={row.score} rating={row.rating} />
                        </td>
                        {strategy === "canslim" ? (
                          <td className="px-3 py-2.5 pr-4">
                            <InstLabel
                              value={metricString(row.metrics, "institutional_accumulation")}
                            />
                          </td>
                        ) : null}
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              className="rounded-md p-1.5 text-[var(--ink-muted)] hover:bg-white/5 hover:text-[var(--warn)]"
                              title="Watchlist"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Star className="h-4 w-4" />
                            </button>
                            <Link
                              href={`/stocks/${encodeURIComponent(row.symbol)}`}
                              className="rounded-md p-1.5 text-[var(--ink-muted)] hover:bg-white/5 hover:text-[var(--accent)]"
                              title="Chart"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <LineChart className="h-4 w-4" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
            <h3 className="text-sm font-semibold text-[var(--ink)]">Market Context</h3>
            <div className="mt-3 flex items-start justify-between gap-2">
              <div>
                <p className="text-xs text-[var(--ink-muted)]">
                  {trend?.proxy_symbol ?? "Nifty 50"}
                </p>
                <p className="mt-0.5 text-xl font-semibold tabular-nums text-[var(--ink)]">
                  {trend?.price != null ? formatNumber(trend.price, { maximumFractionDigits: 2 }) : "—"}
                </p>
                <ChangeCell value={trend?.change_pct} />
              </div>
              {trend?.change_pct != null ? (
                <Sparkline
                  data={[
                    100,
                    100 + (trend.change_pct || 0) * 0.4,
                    100 + (trend.change_pct || 0) * 0.7,
                    100 + (trend.change_pct || 0),
                  ]}
                  positive={(trend.change_pct || 0) >= 0}
                  width={88}
                  height={36}
                />
              ) : null}
            </div>

            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs text-[var(--ink-muted)]">
                <span>Advance / Decline</span>
                <span className="tabular-nums">
                  {trend?.advances ?? "—"} / {trend?.declines ?? "—"}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[var(--down-soft)]">
                <div
                  className="h-full rounded-full bg-[var(--up)] transition-all"
                  style={{ width: `${advancePct ?? 50}%` }}
                />
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2">
                <p className="text-[11px] text-[var(--ink-muted)]">New 52W Highs</p>
                <p className="mt-0.5 text-lg font-semibold tabular-nums text-[var(--up)]">
                  {trend?.new_highs ?? "—"}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2">
                <p className="text-[11px] text-[var(--ink-muted)]">New 52W Lows</p>
                <p className="mt-0.5 text-lg font-semibold tabular-nums text-[var(--down)]">
                  {trend?.new_lows ?? "—"}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
            <h3 className="text-sm font-semibold text-[var(--ink)]">Top Insights</h3>
            <ul className="mt-3 space-y-2.5">
              {(data?.summary.insights ?? []).map((insight, idx) => (
                <li key={`${insight.text}-${idx}`} className="flex gap-2 text-sm">
                  <span
                    className={cn(
                      "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                      insight.tone === "positive"
                        ? "bg-[var(--up)]"
                        : insight.tone === "warning"
                          ? "bg-[var(--warn)]"
                          : "bg-[var(--accent)]",
                    )}
                  />
                  <span className="text-[var(--ink-soft)]">{insight.text}</span>
                </li>
              ))}
              {!data?.summary.insights?.length ? (
                <li className="text-sm text-[var(--ink-muted)]">Insights appear after analysis.</li>
              ) : null}
            </ul>
          </div>

          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
            <h3 className="text-sm font-semibold text-[var(--ink)]">Saved Screens</h3>
            <ul className="mt-3 space-y-2">
              {savedScreens.length === 0 ? (
                <li className="text-sm text-[var(--ink-muted)]">
                  Save the current screen to pin it here.
                </li>
              ) : (
                savedScreens.map((screen) => (
                  <li key={screen.id}>
                    <button
                      type="button"
                      onClick={() => setStrategy(screen.strategy)}
                      className="flex w-full items-center justify-between rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2 text-left transition hover:border-[var(--accent)]"
                    >
                      <span>
                        <span className="block text-sm text-[var(--ink)]">{screen.name}</span>
                        <span className="text-[11px] text-[var(--ink-muted)]">
                          {STRATEGY_LABELS[screen.strategy]} ·{" "}
                          {new Date(screen.createdAt).toLocaleDateString("en-IN", {
                            day: "numeric",
                            month: "short",
                          })}
                        </span>
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
