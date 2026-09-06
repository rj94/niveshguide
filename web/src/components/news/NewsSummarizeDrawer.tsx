"use client";

import Link from "next/link";
import {
  ArrowDownRight,
  ArrowUpRight,
  ExternalLink,
  FileText,
  LoaderCircle,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import { formatNumber, formatPct, formatPrice } from "@/lib/format";
import {
  KPI_LABELS,
  formatCr,
  formatGrowth,
  hasFinancialMetrics,
  hasOrderMetrics,
  metricsOf,
  sectorAnalysisBlurb,
  sectorAnalysisTitle,
  sectorKpisOf,
  sectorProfileOf,
} from "@/lib/news-metrics";
import { cn } from "@/lib/utils";
import { getNewsEvent, summarizeNewsEvent } from "@/services/api";
import type { NewsEventCard } from "@/types/news";

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

type Props = {
  eventId: number | null;
  onClose: () => void;
  onSummaryUpdated?: (eventId: number, summary: string, extractionMethod: string | null) => void;
};

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

function eventLabel(type: string): string {
  return type.replaceAll("_", " ");
}

function formatWhen(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function NewsSummarizeDrawer({ eventId, onClose, onSummaryUpdated }: Props) {
  const [detail, setDetail] = useState<NewsEventCard | null>(null);
  const [loading, setLoading] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (eventId == null) {
      setDetail(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const row = await getNewsEvent(eventId);
        if (!cancelled) setDetail(row);
      } catch (err) {
        if (!cancelled) {
          setDetail(null);
          setError(err instanceof Error ? err.message : "Failed to load event");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  useEffect(() => {
    if (eventId == null) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [eventId, onClose]);

  if (eventId == null) return null;

  const score = num(detail?.impact_score);
  const band = impactBand(score);
  const move = detail?.change_pct ?? num(detail?.price_reaction_pct);
  const summary = detail?.summary_simple || detail?.what_happened || null;

  async function onExplain() {
    if (eventId == null) return;
    setSummarizing(true);
    setError(null);
    try {
      const res = await summarizeNewsEvent(eventId);
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              summary_simple: res.summary_simple,
              extraction_method: res.extraction_method,
            }
          : prev,
      );
      if (res.summary_simple) {
        onSummaryUpdated?.(eventId, res.summary_simple, res.extraction_method);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Summarize failed");
    } finally {
      setSummarizing(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
        aria-label="Close summarize view"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="News summary"
        className="relative flex h-full w-full max-w-[440px] flex-col border-l border-[var(--line)] bg-[var(--surface)] shadow-2xl animate-[fade-up_0.25s_ease]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-[var(--line)] px-4 py-3">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
              Summarize view
            </div>
            <h2 className="mt-0.5 truncate text-base font-semibold text-[var(--ink)]">
              {detail?.company_name ?? detail?.symbol ?? "Event"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[var(--line)] p-1.5 text-[var(--ink-muted)] hover:text-[var(--ink)]"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--ink-muted)]">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Loading event…
            </div>
          ) : null}

          {!loading && error && !detail ? (
            <div className="rounded-lg border border-[var(--down)]/40 bg-[var(--down-soft)] px-3 py-3 text-sm text-[var(--down)]">
              {error}
            </div>
          ) : null}

          {!loading && detail ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "inline-flex rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                    EVENT_BADGE[detail.event_type] ??
                      "border-white/10 bg-white/5 text-[var(--ink-soft)]",
                  )}
                >
                  {eventLabel(detail.event_type)}
                </span>
                {detail.symbol ? (
                  <span className="text-xs font-medium text-[var(--ink-soft)]">{detail.symbol}</span>
                ) : null}
                <span className="text-xs text-[var(--ink-muted)]">
                  {formatWhen(detail.published_at)}
                </span>
              </div>

              <div className="rounded-xl border border-[var(--accent)]/30 bg-[var(--accent-soft)]/40 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--accent-hover)]">
                    <Sparkles className="h-3.5 w-3.5" />
                    Simple summary
                  </div>
                  <button
                    type="button"
                    onClick={onExplain}
                    disabled={summarizing}
                    className="rounded-md border border-[var(--line)] px-2 py-1 text-[11px] text-[var(--ink-soft)] hover:border-[var(--accent)] disabled:opacity-50"
                  >
                    {summarizing ? "Explaining…" : "Explain simply"}
                  </button>
                </div>
                <p className="text-[15px] leading-relaxed text-[var(--ink)]">
                  {summary ?? "No summary yet — click Explain simply."}
                </p>
                {detail.extraction_method ? (
                  <p className="mt-2 text-[11px] text-[var(--ink-muted)]">
                    Via {detail.extraction_method.replaceAll("_", " ")}
                  </p>
                ) : null}
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
                  What happened
                </div>
                <p className="mt-1 text-sm leading-relaxed text-[var(--ink-soft)]">
                  {detail.what_happened || detail.title}
                </p>
                {detail.title && detail.title !== detail.what_happened ? (
                  <p className="mt-2 text-xs text-[var(--ink-muted)]">{detail.title}</p>
                ) : null}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className={cn("rounded-lg border px-3 py-2", impactClass(band))}>
                  <div className="text-[10px] uppercase tracking-wide opacity-80">Impact</div>
                  <div className="mt-0.5 text-sm font-semibold">
                    {band}
                    {score != null ? ` · ${formatNumber(score, { maximumFractionDigits: 0 })}` : ""}
                  </div>
                </div>
                <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-[var(--ink-muted)]">
                    Confidence
                  </div>
                  <div className="mt-0.5 text-sm font-semibold text-[var(--ink)]">
                    {detail.confidence != null
                      ? formatPct((num(detail.confidence) ?? 0) * 100, 0)
                      : "—"}
                  </div>
                </div>
                <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-[var(--ink-muted)]">
                    Sentiment
                  </div>
                  <div className="mt-0.5 text-sm font-semibold capitalize text-[var(--ink)]">
                    {detail.sentiment ?? "—"}
                  </div>
                </div>
                <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-[var(--ink-muted)]">
                    Price move
                  </div>
                  <div
                    className={cn(
                      "mt-0.5 inline-flex items-center gap-0.5 text-sm font-semibold tabular-nums",
                      (move ?? 0) > 0
                        ? "text-[var(--up)]"
                        : (move ?? 0) < 0
                          ? "text-[var(--down)]"
                          : "text-[var(--ink)]",
                    )}
                  >
                    {(move ?? 0) > 0 ? (
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    ) : (move ?? 0) < 0 ? (
                      <ArrowDownRight className="h-3.5 w-3.5" />
                    ) : null}
                    {move == null ? "—" : formatPct(move)}
                  </div>
                </div>
              </div>

              {(() => {
                const m = metricsOf(detail);
                if (!hasFinancialMetrics(m)) return null;
                return (
                  <div>
                    <div className="mb-2 text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
                      Financial snapshot
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {(
                        [
                          ["Sales YoY", m.revenue_yoy_pct],
                          ["EBITDA YoY", m.ebitda_yoy_pct],
                          ["PAT YoY", m.pat_yoy_pct],
                          ["Cash flow YoY", m.ocf_yoy_pct],
                        ] as const
                      ).map(([label, value]) => (
                        <div
                          key={label}
                          className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2"
                        >
                          <div className="text-[10px] text-[var(--ink-muted)]">{label}</div>
                          <div
                            className={cn(
                              "mt-0.5 text-sm font-semibold tabular-nums",
                              value == null
                                ? "text-[var(--ink-muted)]"
                                : value > 0
                                  ? "text-[var(--up)]"
                                  : value < 0
                                    ? "text-[var(--down)]"
                                    : "text-[var(--ink)]",
                            )}
                          >
                            {formatGrowth(value)}
                          </div>
                        </div>
                      ))}
                    </div>
                    {(m.revenue_cr != null || m.pat_cr != null) && (
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-[var(--ink-soft)]">
                        {m.revenue_cr != null ? (
                          <span className="rounded-md bg-white/5 px-2 py-1">
                            Sales {formatCr(m.revenue_cr)}
                          </span>
                        ) : null}
                        {m.pat_cr != null ? (
                          <span className="rounded-md bg-white/5 px-2 py-1">
                            PAT {formatCr(m.pat_cr)}
                          </span>
                        ) : null}
                      </div>
                    )}
                  </div>
                );
              })()}

              {(() => {
                const m = metricsOf(detail);
                if (!hasOrderMetrics(m)) return null;
                return (
                  <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-3">
                    <div className="text-[11px] uppercase tracking-wide text-sky-300">Order</div>
                    <div className="mt-1 text-lg font-semibold text-[var(--ink)]">
                      {formatCr(m.order_value_cr)}
                    </div>
                    <div className="mt-1 text-xs text-[var(--ink-soft)]">
                      {m.order_to_revenue_pct != null
                        ? `${m.order_to_revenue_pct.toFixed(1)}% of annual revenue`
                        : "Order size extracted from filing"}
                      {m.materiality_band ? ` · Materiality ${m.materiality_band}` : ""}
                    </div>
                  </div>
                );
              })()}

              {(() => {
                const profile = sectorProfileOf(detail);
                const kpis = sectorKpisOf(detail);
                const entries = Object.entries(kpis).filter(([, v]) => v != null);
                if (!entries.length) return null;
                const blurb = sectorAnalysisBlurb(profile, kpis);
                return (
                  <div>
                    <div className="mb-2 text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
                      {sectorAnalysisTitle(profile)}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {entries.map(([key, value]) => (
                        <div
                          key={key}
                          className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2"
                        >
                          <div className="text-[10px] text-[var(--ink-muted)]">
                            {KPI_LABELS[key] ?? key}
                          </div>
                          <div className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--ink)]">
                            {value!.toFixed(2)}%
                          </div>
                        </div>
                      ))}
                    </div>
                    {blurb ? (
                      <p className="mt-2 text-xs leading-relaxed text-[var(--ink-soft)]">{blurb}</p>
                    ) : null}
                  </div>
                );
              })()}

              {(detail.last_price != null || detail.symbol) && (
                <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-2 text-sm">
                  <span className="text-[var(--ink-muted)]">Last price </span>
                  <span className="font-semibold tabular-nums text-[var(--ink)]">
                    {formatPrice(detail.last_price)}
                  </span>
                </div>
              )}

              {detail.attributes?.length ? (
                <div>
                  <div className="mb-2 text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
                    Extracted attributes
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {detail.attributes.map((attr) => (
                      <span
                        key={`${attr.key}-${attr.value_text}-${attr.value_number}`}
                        className="rounded-md border border-[var(--line)] bg-[var(--surface-muted)] px-2 py-1 text-xs text-[var(--ink-soft)]"
                      >
                        <span className="text-[var(--ink-muted)]">{attr.key}: </span>
                        {attr.value_text ??
                          (attr.value_number != null
                            ? formatNumber(attr.value_number, { maximumFractionDigits: 2 })
                            : "—")}
                        {attr.unit ? ` ${attr.unit}` : ""}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {error ? (
                <div className="rounded-lg border border-[var(--down)]/40 bg-[var(--down-soft)] px-3 py-2 text-xs text-[var(--down)]">
                  {error}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {detail ? (
          <div className="flex flex-wrap gap-2 border-t border-[var(--line)] px-4 py-3">
            {detail.symbol ? (
              <Link
                href={`/stocks/${encodeURIComponent(detail.symbol)}`}
                className="inline-flex items-center gap-1 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-hover)]"
              >
                View {detail.symbol}
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            ) : null}
            {detail.source_url ? (
              <a
                href={detail.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-lg border border-[var(--line)] px-3 py-2 text-sm text-[var(--ink-soft)] hover:border-[var(--line-strong)]"
              >
                <FileText className="h-3.5 w-3.5" />
                Original filing
              </a>
            ) : null}
          </div>
        ) : null}
      </aside>
    </div>
  );
}
