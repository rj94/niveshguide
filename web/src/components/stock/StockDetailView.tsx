import Link from "next/link";

import { PageAd } from "@/components/ads/PageAd";
import { MetricGrid } from "@/components/stock/MetricGrid";
import { PriceChart } from "@/components/stock/PriceChart";
import { ScorePanel } from "@/components/stock/ScorePanel";
import { StockSearch } from "@/components/stock/StockSearch";
import {
  formatCompact,
  formatNumber,
  formatPct,
  formatPrice,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { StockDetail } from "@/types/stock";

type Props = {
  stock: StockDetail;
};

function toneFromSignal(signal: string | null): "up" | "down" | "default" {
  if (signal === "Bullish") return "up";
  if (signal === "Bearish") return "down";
  return "default";
}

function toneFromPct(value: number | null): "up" | "down" | "default" {
  if (value === null) return "default";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "default";
}

function pctMetric(value: string | null): string {
  return value ? `${formatNumber(value)}%` : "—";
}

function yesNo(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "Yes" : "No";
}

function toneFromBool(value: boolean | null | undefined): "up" | "down" | "default" {
  if (value === true) return "up";
  if (value === false) return "down";
  return "default";
}

export function StockDetailView({ stock }: Props) {
  const changePct = stock.quote.change_pct;
  const positive = (changePct ?? 0) >= 0;
  const t = stock.technicals;

  return (
    <div className="page-shell py-5">
      <header className="relative z-50 mb-8 flex flex-col gap-4 animate-[fade-up_0.55s_ease_both]">
        <p className="font-[family-name:var(--font-display)] text-sm uppercase tracking-[0.28em] text-[var(--accent)]">
          Stock Intelligence
        </p>
        <StockSearch initialQuery={stock.symbol} />
      </header>

      <div className="relative z-0 grid gap-8 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="animate-[fade-up_0.65s_ease_both]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0">
              <h1 className="font-[family-name:var(--font-display)] text-4xl tracking-wide text-[var(--ink)] sm:text-5xl">
                {stock.symbol}
              </h1>
              <p className="mt-2 max-w-xl text-base text-[var(--ink-soft)] sm:text-lg">
                {stock.company_name}
              </p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[var(--ink-muted)]">
                {stock.exchange}
                {t.trend ? ` · ${t.trend}` : ""}
                {t.trend_score != null ? ` · score ${t.trend_score}/5` : ""}
                {stock.sector ? (
                  <>
                    {" · "}
                    <Link
                      href={`/sectors/sector/${encodeURIComponent(stock.sector)}`}
                      className="hover:text-[var(--accent)]"
                    >
                      {stock.sector}
                    </Link>
                  </>
                ) : null}
                {(stock.industries?.length ? stock.industries : stock.industry ? [stock.industry] : []).map(
                  (ind) => (
                    <span key={ind}>
                      {" · "}
                      <Link
                        href={`/sectors/industry/${encodeURIComponent(ind)}`}
                        className="hover:text-[var(--accent)]"
                      >
                        {ind}
                      </Link>
                    </span>
                  ),
                )}
              </p>
              {stock.index_memberships && stock.index_memberships.length > 0 ? (
                <p className="mt-2 max-w-2xl text-[11px] leading-relaxed text-[var(--ink-muted)]">
                  Indices:{" "}
                  {stock.index_memberships.slice(0, 12).join(" · ")}
                  {stock.index_memberships.length > 12
                    ? ` · +${stock.index_memberships.length - 12} more`
                    : ""}
                </p>
              ) : null}
            </div>
            <div className="text-right">
              <p className="font-[family-name:var(--font-display)] text-4xl tabular-nums text-[var(--ink)] sm:text-5xl">
                {formatPrice(stock.quote.price)}
              </p>
              <p
                className={cn(
                  "mt-1 text-lg tabular-nums",
                  positive ? "text-[var(--up)]" : "text-[var(--down)]",
                )}
              >
                {formatPct(changePct)}
                {stock.quote.as_of ? (
                  <span className="ml-2 text-sm text-[var(--ink-muted)]">
                    as of {stock.quote.as_of}
                  </span>
                ) : null}
              </p>
            </div>
          </div>

          <PageAd page="stock" className="mt-6" />

          <div className="mt-8 border border-[var(--line)] bg-[var(--surface)]/70 p-3 backdrop-blur-sm animate-[fade-up_0.75s_ease_both]">
            <PriceChart prices={stock.prices} />
          </div>
        </div>

        <div className="animate-[fade-up_0.8s_ease_both]">
          <ScorePanel scores={stock.scores} />
        </div>
      </div>

      <div className="mt-10 space-y-2 animate-[fade-up_0.9s_ease_both]">
        <MetricGrid
          title="Sheet snapshot"
          subtitle="Values synced from the StockFilter Google Sheet"
          metrics={[
            { label: "LTP", value: formatPrice(stock.quote.price) },
            { label: "Day high", value: formatPrice(t.day_high ?? stock.quote.high) },
            { label: "Prev close", value: formatPrice(t.prev_close ?? stock.quote.previous_close) },
            { label: "Market cap (Cr)", value: formatNumber(stock.market_cap) },
            { label: "Volume", value: formatCompact(stock.quote.volume) },
            { label: "3M avg vol", value: formatCompact(t.avg_volume_3m) },
            { label: "6M avg vol", value: formatCompact(t.avg_volume_6m) },
            { label: "1Y avg vol", value: formatCompact(t.avg_volume_1y) },
            { label: "PE", value: formatNumber(t.pe ?? stock.fundamental_metrics.pe_ttm) },
            { label: "EPS", value: formatNumber(t.eps ?? stock.fundamentals.eps) },
            { label: "52W high", value: formatPrice(t.high_52w) },
            { label: "52W low", value: formatPrice(t.low_52w) },
            { label: "vs 52W high", value: formatPct(t.distance_from_52w_high_pct), tone: toneFromPct(t.distance_from_52w_high_pct) },
            { label: "Trend", value: t.trend ?? "—" },
            { label: "Trend score", value: t.trend_score != null ? `${t.trend_score} / 5` : "—" },
          ]}
        />

        <MetricGrid
          title="Moving averages & conditions"
          subtitle="3/7/21/50/200-day averages and StockFilter crossover flags"
          metrics={[
            { label: "3D MA", value: formatPrice(t.sma_3) },
            { label: "7D MA", value: formatPrice(t.sma_7) },
            { label: "21D MA", value: formatPrice(t.sma_21), tone: toneFromSignal(t.sma_21_signal) },
            { label: "50D MA", value: formatPrice(t.sma_50), tone: toneFromSignal(t.sma_50_signal) },
            { label: "200D MA", value: formatPrice(t.sma_200), tone: toneFromSignal(t.sma_200_signal) },
            { label: "3D > 7D", value: yesNo(t.crossover_3_7), tone: toneFromBool(t.crossover_3_7) },
            { label: "LTP > 21D", value: yesNo(t.above_ma_21), tone: toneFromBool(t.above_ma_21) },
            { label: "21D > 50D", value: yesNo(t.ma21_gt_ma50), tone: toneFromBool(t.ma21_gt_ma50) },
            { label: "LTP > 200D", value: yesNo(t.above_ma_200), tone: toneFromBool(t.above_ma_200) },
            { label: "50D > 200D", value: yesNo(t.golden_cross), tone: toneFromBool(t.golden_cross) },
          ]}
        />

        <MetricGrid
          title="Returns"
          subtitle="Computed from synced daily closes"
          metrics={[
            { label: "1M Return", value: formatPct(t.return_1m_pct), tone: toneFromPct(t.return_1m_pct) },
            { label: "3M Return", value: formatPct(t.return_3m_pct), tone: toneFromPct(t.return_3m_pct) },
            { label: "6M Return", value: formatPct(t.return_6m_pct), tone: toneFromPct(t.return_6m_pct) },
            { label: "1Y Return", value: formatPct(t.return_1y_pct), tone: toneFromPct(t.return_1y_pct) },
          ]}
        />

        <MetricGrid
          title="Ownership"
          subtitle={
            stock.ownership.period
              ? `Shareholding · as of ${stock.ownership.period}`
              : undefined
          }
          emptyMessage="No shareholding data for this symbol yet."
          metrics={[
            {
              label: "Promoter",
              value: pctMetric(stock.ownership.promoter_pct),
            },
            {
              label: "FII",
              value: pctMetric(stock.ownership.fii_pct),
            },
            {
              label: "DII",
              value: pctMetric(stock.ownership.dii_pct),
            },
            {
              label: "Public",
              value: pctMetric(stock.ownership.public_pct),
            },
            {
              label: "Pledge",
              value: pctMetric(stock.ownership.promoter_pledge_pct),
            },
          ]}
        />

        {stock.annual_history.length > 0 ? (
          <section className="border-t border-[var(--line)] pt-8">
            <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
              Annual history
            </h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">
              Latest years from screener.in for {stock.symbol}
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
                  <tr className="border-b border-[var(--line)]">
                    <th className="py-2 pr-3 font-medium">Period</th>
                    <th className="py-2 pr-3 font-medium">Revenue</th>
                    <th className="py-2 pr-3 font-medium">PAT</th>
                    <th className="py-2 pr-3 font-medium">EPS</th>
                    <th className="py-2 pr-3 font-medium">FCF</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.annual_history.map((row) => (
                    <tr
                      key={`${row.period_label || row.period}`}
                      className="border-b border-[var(--line)]/70 text-[var(--ink)]"
                    >
                      <td className="py-2.5 pr-3">
                        {row.period_label || row.period}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatCompact(row.revenue)}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatCompact(row.pat)}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatNumber(row.eps)}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatCompact(row.free_cashflow)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {stock.quarterly_history.length > 0 ? (
          <section className="border-t border-[var(--line)] pt-8">
            <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
              Quarterly history
            </h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">
              Recent quarters from screener.in for {stock.symbol}
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
                  <tr className="border-b border-[var(--line)]">
                    <th className="py-2 pr-3 font-medium">Period</th>
                    <th className="py-2 pr-3 font-medium">Revenue</th>
                    <th className="py-2 pr-3 font-medium">PAT</th>
                    <th className="py-2 pr-3 font-medium">EPS</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.quarterly_history.map((row) => (
                    <tr
                      key={`q-${row.period_label || row.period}`}
                      className="border-b border-[var(--line)]/70 text-[var(--ink)]"
                    >
                      <td className="py-2.5 pr-3">
                        {row.period_label || row.period}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatCompact(row.revenue)}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatCompact(row.pat)}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">
                        {formatNumber(row.eps)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        <section className="border-t border-[var(--line)] pt-8 pb-4">
          <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
            AI Research
          </h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Coming in Phase 3 — ask about concalls, risks, and valuation.
          </p>
          <div className="mt-4 border border-dashed border-[var(--line)] bg-[var(--surface)]/50 px-4 py-5 text-sm text-[var(--ink-soft)]">
            Ask anything about {stock.symbol}…
            <ul className="mt-3 space-y-1 text-[var(--ink-muted)]">
              <li>“What changed in the latest concall?”</li>
              <li>“What are the major risks?”</li>
              <li>“Is valuation justified?”</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
