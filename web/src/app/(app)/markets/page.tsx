"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Sparkline } from "@/components/dashboard/Sparkline";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { getMarketsOverview, listMarketEtfs } from "@/services/api";
import type { MarketQuoteCard, MarketsOverviewResponse } from "@/types/markets";

function num(value: string | number | null): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

function QuoteCard({ card, index }: { card: MarketQuoteCard; index: number }) {
  const changePct = card.change_pct ?? 0;
  const up = changePct >= 0;
  return (
    <article
      className="animate-[fade-up_0.45s_ease_both] rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3.5"
      style={{ animationDelay: `${Math.min(index, 20) * 20}ms` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--ink-muted)]">
            {card.symbol}
          </p>
          <p className="mt-0.5 truncate text-xs font-medium text-[var(--ink)]">
            {card.name}
          </p>
          {card.sector_name ? (
            <p className="mt-1 truncate text-[10px] text-[var(--ink-muted)]">
              {card.sector_name}
            </p>
          ) : null}
        </div>
        {card.exchange ? (
          <span className="shrink-0 rounded-md border border-[var(--line)] px-1.5 py-0.5 text-[10px] text-[var(--ink-muted)]">
            {card.exchange}
          </span>
        ) : null}
      </div>
      <div className="mt-2 flex items-end justify-between gap-2">
        <div>
          <p className="text-lg font-semibold tabular-nums tracking-tight text-[var(--ink)]">
            {formatNumber(num(card.value), { maximumFractionDigits: 2 })}
          </p>
          <p
            className={cn(
              "mt-1 text-xs tabular-nums",
              up ? "text-[var(--up)]" : "text-[var(--down)]",
            )}
          >
            {formatNumber(num(card.change), {
              maximumFractionDigits: 2,
              signDisplay: "always",
            })}{" "}
            ({formatPct(card.change_pct)})
          </p>
        </div>
        {card.sparkline.length > 1 ? (
          <Sparkline data={card.sparkline} positive={up} width={68} height={30} />
        ) : null}
      </div>
    </article>
  );
}

function SectorRow({ card }: { card: MarketQuoteCard }) {
  const change = num(card.score_change_1w) ?? 0;
  const up = change >= 0;
  return (
    <Link
      href={`/sectors/sector/${encodeURIComponent(card.symbol)}`}
      className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 transition hover:bg-[var(--surface-2,rgba(127,127,127,0.06))]"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-[var(--ink)]">{card.name}</p>
        <p className="text-xs text-[var(--ink-muted)]">
          {card.rotation_state ?? "-"} - 1M ret {formatPct(num(card.return_1m))}
        </p>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold tabular-nums text-[var(--ink)]">
          {formatNumber(num(card.score), { maximumFractionDigits: 0 })}
        </p>
        <p
          className={cn(
            "text-xs tabular-nums",
            up ? "text-[var(--up)]" : "text-[var(--down)]",
          )}
        >
          {formatNumber(change, { maximumFractionDigits: 1, signDisplay: "always" })} 1W
        </p>
      </div>
    </Link>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--ink-muted)]">
        {title}
      </h2>
      {children}
    </section>
  );
}

function MarketsPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const tab = (searchParams.get("tab") || "etfs").toLowerCase() === "commodities" ? "commodities" : "etfs";

  const [data, setData] = useState<MarketsOverviewResponse | null>(null);
  const [etfs, setEtfs] = useState<MarketQuoteCard[]>([]);
  const [etfTotal, setEtfTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [overview, etfRes] = await Promise.all([
          getMarketsOverview(),
          listMarketEtfs().catch(() => null),
        ]);
        if (cancelled) return;
        setData(overview);
        // Equity/sector ETFs only in ETF tab (exclude commodity kind if present)
        const items = (etfRes?.items ?? overview.sector_etfs).filter((c) => c.kind !== "commodity");
        setEtfs(items);
        setEtfTotal(etfRes?.total ?? items.length);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load markets overview");
        }
      }
    }

    load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const setTab = (next: "etfs" | "commodities") => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "etfs") params.delete("tab");
    else params.set("tab", "commodities");
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  const commodityCards = useMemo(() => data?.commodities ?? [], [data]);

  if (error) {
    return (
      <div className="page-shell mx-auto max-w-3xl py-12 text-center text-sm text-[var(--ink-muted)]">
        Markets overview unavailable: {error}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="page-shell mx-auto max-w-3xl py-12 text-center text-sm text-[var(--ink-muted)]">
        Loading markets...
      </div>
    );
  }

  return (
    <div className="page-shell space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">Markets</h1>
        {data.as_of ? (
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            Live from market DB - as of {data.as_of}
          </p>
        ) : null}
      </div>

      <Section title="Indices">
        {data.indices.length ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {data.indices.map((card, i) => (
              <QuoteCard key={card.id} card={card} index={i} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--ink-muted)]">
            No index quotes yet. Run <code>python -m cli scrape-indices</code>.
          </p>
        )}
      </Section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          <div className="flex items-center gap-2 border-b border-[var(--line)] pb-2">
            <button
              type="button"
              onClick={() => setTab("etfs")}
              className={
                tab === "etfs"
                  ? "rounded-md bg-[var(--surface)] px-3 py-1.5 text-sm font-semibold text-[var(--ink)]"
                  : "rounded-md px-3 py-1.5 text-sm font-medium text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }
            >
              ETFs
            </button>
            <button
              type="button"
              onClick={() => setTab("commodities")}
              className={
                tab === "commodities"
                  ? "rounded-md bg-[var(--surface)] px-3 py-1.5 text-sm font-semibold text-[var(--ink)]"
                  : "rounded-md px-3 py-1.5 text-sm font-medium text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }
            >
              Commodities
            </button>
          </div>

          {tab === "etfs" ? (
            <Section title={`Key ETFs${etfTotal ? ` (${etfs.length})` : ""}`}>
              {etfs.length ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {etfs.map((card, i) => (
                    <QuoteCard key={card.id} card={card} index={i} />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[var(--ink-muted)]">
                  No ETF quotes yet. Run <code>python -m cli scrape-etfs</code>.
                </p>
              )}
            </Section>
          ) : (
            <Section title={`Commodities${commodityCards.length ? ` (${commodityCards.length})` : ""}`}>
              <p className="mb-3 text-xs text-[var(--ink-muted)]">
                India ETFs (Gold ETF, Silver ETF) plus Yahoo futures proxies for oil, gas, and copper.
              </p>
              {commodityCards.length ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {commodityCards.map((card, i) => (
                    <QuoteCard key={card.id} card={card} index={i} />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[var(--ink-muted)]">
                  No commodity quotes yet. Run <code>python -m cli scrape-etfs</code>.
                </p>
              )}
            </Section>
          )}
        </div>

        <Section title="Sector strength movers">
          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-2">
            {data.sectors.length ? (
              data.sectors.map((card) => <SectorRow key={card.id} card={card} />)
            ) : (
              <p className="px-3 py-4 text-sm text-[var(--ink-muted)]">
                No sector scores yet.
              </p>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}

export default function MarketsPage() {
  return (
    <Suspense
      fallback={
        <div className="page-shell mx-auto max-w-3xl py-12 text-center text-sm text-[var(--ink-muted)]">
          Loading markets...
        </div>
      }
    >
      <MarketsPageInner />
    </Suspense>
  );
}
