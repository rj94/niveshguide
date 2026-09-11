"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Crosshair,
  Funnel,
  LineChart,
  Search,
  Star,
  TrendingUp,
} from "lucide-react";

import { Sparkline } from "@/components/dashboard/Sparkline";
import { MarketingSearch } from "@/components/marketing/MarketingSearch";
import { avatarColor, type IndexCard, type IndexRow, type MoverRow, type RotationItem, type SectorCell } from "@/lib/dashboard-data";
import type { DashboardPayload, SectorEtfRow } from "@/lib/load-dashboard";
import { formatNumber, formatPct } from "@/lib/format";
import { filterMovers } from "@/lib/movers-filter";
import {
  buildRotationItems,
  rankSectorsForPerformance,
} from "@/lib/sector-rotation";
import { cn } from "@/lib/utils";
import { getMarketsOverview, listSectors, screenStocks } from "@/services/api";
import type { StockAnalysisRow } from "@/types/stock";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/screener", label: "Screener" },
  { href: "/momentum", label: "Momentum" },
  { href: "/volume-gainer", label: "Volume" },
  { href: "/analysis", label: "Strategies" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/news", label: "Learn" },
] as const;

const POPULAR = ["HDFC Bank", "Reliance", "TCS", "IRFC", "RVNL", "SBI", "Adani", "HAL"];

const FEATURES = [
  { href: "/screener", title: "Stock Screener", text: "Filter stocks with price, volume and strength.", icon: Funnel, tone: "text-emerald-300" },
  { href: "/momentum", title: "Momentum Stocks", text: "Discover high momentum stocks.", icon: TrendingUp, tone: "text-sky-300" },
  { href: "/volume-gainer", title: "Volume Breakouts", text: "Spot unusual volume activity.", icon: Activity, tone: "text-orange-300" },
  { href: "/analysis", title: "Strategies", text: "Explore proven investment strategies.", icon: Crosshair, tone: "text-indigo-300" },
  { href: "/watchlist", title: "Watchlist", text: "Track your favorite stocks.", icon: Star, tone: "text-amber-300" },
  { href: "/news", title: "Learning Hub", text: "Learn and follow market context.", icon: BookOpen, tone: "text-teal-300" },
] as const;

type HomeState = Pick<
  DashboardPayload,
  "indices" | "momentumLeaders" | "gainers" | "losers" | "byVolume" | "sectors" | "indexRows" | "sectorEtfs" | "rotation" | "asOf"
>;

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

function pctClass(value: number | null | undefined) {
  return (value ?? 0) >= 0 ? "text-emerald-300" : "text-red-300";
}

function mapMover(row: StockAnalysisRow): MoverRow | null {
  const price = num(row.ltp);
  if (price === null || row.change_pct === null) return null;
  return { symbol: row.symbol, name: row.company_name, price, changePct: row.change_pct, color: avatarColor(row.symbol) };
}

export function MarketingHome({ data }: { data: DashboardPayload }) {
  const [state, setState] = useState<HomeState>(data);
  const [liveLabel, setLiveLabel] = useState("Live");

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const [overview, sectorsRes, momentumRes, gainersRes, losersRes, volumeRes] = await Promise.all([
          getMarketsOverview(),
          listSectors({ limit: 80, min_constituents: 3 }).catch(() => null),
          screenStocks({ exchange: "NSE", sort_by: "momentum_score", sort_dir: "desc", limit: 12, scan_limit: 2000 }).catch(() => null),
          screenStocks({ exchange: "NSE", sort_by: "change_pct", sort_dir: "desc", limit: 24, scan_limit: 2000 }).catch(() => null),
          screenStocks({ exchange: "NSE", sort_by: "change_pct", sort_dir: "asc", limit: 24, scan_limit: 2000 }).catch(() => null),
          screenStocks({ exchange: "NSE", volume_mover: true, sort_by: "volume_ratio", sort_dir: "desc", limit: 16, scan_limit: 2000 }).catch(() => null),
        ]);
        if (cancelled) return;

        const indices: IndexCard[] = overview.indices
          .reduce<IndexCard[]>((acc, card) => {
            const value = num(card.value);
            if (value === null || card.change_pct === null) return acc;
            acc.push({
              id: card.id,
              name: card.name,
              value,
              change: num(card.change) ?? 0,
              changePct: card.change_pct,
              sparkline: card.sparkline ?? [],
              tone: card.change_pct >= 0 ? "up" : "down",
              icon: "chart",
              kind: "index",
              subtitle: card.symbol,
            });
            return acc;
          }, [])
          .slice(0, 6);

        const sectorEtfs: SectorEtfRow[] = overview.sector_etfs
          .reduce<SectorEtfRow[]>((acc, card) => {
            const value = num(card.value);
            if (value === null || card.change_pct === null) return acc;
            acc.push({
              symbol: card.symbol,
              name: card.name,
              value,
              changePct: card.change_pct,
              sparkline: card.sparkline ?? [],
              kind: "sector_etf",
              sectorName: card.sector_name ?? null,
            });
            return acc;
          }, []);

        const indexRows: IndexRow[] = overview.commodities
          .reduce<IndexRow[]>((acc, card) => {
            const value = num(card.value);
            if (value === null || card.change_pct === null) return acc;
            acc.push({ name: card.name, value, changePct: card.change_pct, sparkline: card.sparkline ?? [], kind: card.kind });
            return acc;
          }, [])
          .slice(0, 6);

        setState((current) => ({
          ...current,
          indices: indices.length ? indices : current.indices,
          sectorEtfs: sectorEtfs.length ? sectorEtfs : current.sectorEtfs,
          indexRows: indexRows.length ? indexRows : current.indexRows,
          sectors: sectorsRes
            ? (() => {
                const ranked = rankSectorsForPerformance(
                  (sectorsRes.industries?.length ? sectorsRes.industries : sectorsRes.items) ?? [],
                  12,
                );
                return ranked.length ? ranked : current.sectors;
              })()
            : current.sectors,
          rotation: sectorsRes
            ? buildRotationItems(
                (sectorsRes.industries?.length ? sectorsRes.industries : sectorsRes.items) ?? [],
                { max: 8 },
              )
            : current.rotation,
          momentumLeaders: momentumRes
            ? (momentumRes.items ?? [])
                .map((row) => {
                  const score = num(row.momentum_score ?? row.overall);
                  if (score === null) return null;
                  return { symbol: row.symbol, name: row.company_name, score, category: row.momentum_category, changePct: row.change_pct, ltp: num(row.ltp) };
                })
                .filter((x): x is HomeState["momentumLeaders"][number] => x !== null)
            : current.momentumLeaders,
          gainers: gainersRes
            ? filterMovers((gainersRes.items ?? []).map(mapMover).filter((x): x is MoverRow => x !== null), { softGainers: true, limit: 5 })
            : current.gainers,
          losers: losersRes
            ? filterMovers((losersRes.items ?? []).map(mapMover).filter((x): x is MoverRow => x !== null), { limit: 5 })
            : current.losers,
          byVolume: volumeRes
            ? filterMovers((volumeRes.items ?? []).map(mapMover).filter((x): x is MoverRow => x !== null), { volumeMover: true, limit: 5 })
            : current.byVolume,
          asOf: overview.as_of ?? sectorsRes?.as_of ?? current.asOf,
        }));
        setLiveLabel(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      } catch {
        if (!cancelled) setLiveLabel("retrying");
      }
    }

    const boot = window.setTimeout(refresh, 1500);
    const interval = window.setInterval(refresh, 30_000);
    return () => {
      cancelled = true;
      window.clearTimeout(boot);
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#080b0f] text-slate-100">
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#0b0f14]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 lg:px-6">
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-400 text-[#07110d]">
              <LineChart className="h-4 w-4" strokeWidth={2.4} />
            </span>
            <span className="text-base font-bold text-white">NiveshGuide</span>
          </Link>
          <nav className="hidden flex-1 items-center justify-center gap-1 lg:flex">
            {NAV_LINKS.map((link) => (
              <Link key={link.href} href={link.href} className={cn("rounded-md px-2.5 py-1.5 text-sm font-medium text-slate-400 transition hover:bg-white/5 hover:text-white", link.href === "/" && "text-emerald-300")}>
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <MarketingSearch size="nav" variant="dark" className="hidden w-56 md:block xl:w-72" placeholder="Search stocks (e.g. TCS)" />
            <Link href="/watchlist" className="rounded-md bg-emerald-500 px-3.5 py-2 text-sm font-semibold text-[#06110d] transition hover:bg-emerald-400">Login</Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-14 lg:px-6">
        <section className="grid min-h-[420px] gap-8 py-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(340px,0.9fr)] lg:items-center lg:py-14">
          <div>
            <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(52,211,153,0.9)]" />
              Live market dashboard
            </p>
            <h1 className="max-w-2xl text-4xl font-extrabold leading-tight tracking-normal text-slate-100 sm:text-6xl">
              Better Data.
              <span className="block text-emerald-400">Smarter Investing.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-300">
              Discover opportunities, analyse trends and make informed investment decisions - all in one place.
            </p>
            <div className="mt-8 max-w-xl">
              <MarketingSearch size="hero" variant="dark" />
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px]">
              <span className="text-slate-500">Popular</span>
              {POPULAR.map((label) => <span key={label} className="rounded-full border border-white/8 px-2.5 py-1 text-slate-400">{label}</span>)}
            </div>
          </div>
          <div className="relative min-h-[270px] overflow-hidden rounded-lg border border-white/8 bg-[#0f151d] p-7 shadow-2xl shadow-black/30">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_35%,rgba(16,185,129,0.14),transparent_32%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_55%)]" />
            <div className="relative flex h-full flex-col justify-between">
              <blockquote className="max-w-sm text-xl font-bold leading-snug text-slate-100">"A disciplined investor today, a wealthier tomorrow."</blockquote>
              <div className="mt-10 grid grid-cols-[1fr_auto] items-end gap-5">
                <div className="space-y-2 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                  {["Track", "Analyse", "Discover", "Invest", "Grow"].map((word) => <p key={word}>{word}</p>)}
                </div>
                <TrendingUp className="h-28 w-28 text-emerald-400" strokeWidth={1.5} />
              </div>
              <p className="mt-4 text-xs text-slate-500"><span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />Live · {liveLabel}</p>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {state.indices.slice(0, 6).map((card) => <IndexTile key={card.id} card={card} />)}
        </section>

        <section className="grid gap-5 py-9 md:grid-cols-3 lg:grid-cols-6">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link key={feature.href} href={feature.href} className="group min-h-28 rounded-lg border border-white/7 bg-[#0d1219] p-4 transition hover:border-emerald-400/30 hover:bg-[#111923]">
                <Icon className={cn("mb-4 h-5 w-5", feature.tone)} />
                <h2 className="text-sm font-bold text-slate-100">{feature.title}</h2>
                <p className="mt-1 text-[11px] leading-4 text-slate-500">{feature.text}</p>
              </Link>
            );
          })}
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <DataTable title="Top Momentum Stocks" href="/momentum" viewLabel="View momentum" score rows={state.momentumLeaders.slice(0, 5).map((r, i) => ({ rank: i + 1, symbol: r.symbol, price: r.ltp, changePct: r.changePct, score: r.score }))} />
          <DataTable title="Top Gainers" href="/screener?sort_by=change_pct&sort_dir=desc" viewLabel="View gainers" rows={state.gainers.slice(0, 5).map((r, i) => ({ rank: i + 1, symbol: r.symbol, price: r.price, changePct: r.changePct }))} />
          <DataTable title="Top Losers" href="/screener?sort_by=change_pct&sort_dir=asc" viewLabel="View losers" rows={state.losers.slice(0, 5).map((r, i) => ({ rank: i + 1, symbol: r.symbol, price: r.price, changePct: r.changePct }))} />
          <DataTable title="High Volume Stocks" href="/volume-gainer" viewLabel="View volume" rows={state.byVolume.slice(0, 5).map((r, i) => ({ rank: i + 1, symbol: r.symbol, price: r.price, changePct: r.changePct }))} />
        </section>

        <section className="grid gap-6 py-9 lg:grid-cols-2">
          <SectorBars sectors={state.sectors} />
          <RotationList items={state.rotation} />
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <MarketList title="Key ETFs" rows={state.sectorEtfs} href="/markets" viewLabel="View all ETFs" />
          <MarketList title="Commodities" rows={state.indexRows} href="/markets?tab=commodities" viewLabel="View commodities" />
        </section>

        <section className="grid gap-6 py-9 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <QuoteCard />
          <WatchlistCta />
        </section>
      </main>
    </div>
  );
}

function IndexTile({ card }: { card: IndexCard }) {
  return (
    <article className="rounded-lg border border-white/7 bg-[#0d1219] p-4">
      <p className="truncate text-[10px] font-bold uppercase tracking-wide text-slate-500">{card.name}</p>
      <p className="mt-2 text-lg font-bold tabular-nums text-slate-100">{formatNumber(card.value, { maximumFractionDigits: 2 })}</p>
      <div className="mt-2 flex items-center justify-between gap-2">
        <p className={cn("text-[11px] font-semibold tabular-nums", pctClass(card.changePct))}>{formatNumber(card.change, { maximumFractionDigits: 2 })} ({formatPct(card.changePct)})</p>
        {card.sparkline.length >= 5 ? (
          <Sparkline data={card.sparkline} positive={card.changePct >= 0} width={58} height={26} />
        ) : null}
      </div>
    </article>
  );
}

type DataRow = { rank: number; symbol: string; price: number | null | undefined; changePct: number | null | undefined; score?: number | null };

function DataTable({
  title,
  href,
  rows,
  score = false,
  viewLabel = "View all",
}: {
  title: string;
  href: string;
  rows: DataRow[];
  score?: boolean;
  viewLabel?: string;
}) {
  return (
    <article className="rounded-lg border border-white/7 bg-[#0d1219] p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-base font-bold text-slate-100">{title}</h2>
        <Link href={href} className="shrink-0 text-[11px] font-semibold text-emerald-300 hover:text-emerald-200">
          {viewLabel}
        </Link>
      </div>
      <table className="w-full table-fixed text-left text-xs">
        <thead className="text-[10px] uppercase tracking-wide text-slate-600">
          <tr>
            <th className="w-8 pb-3 font-semibold">#</th>
            <th className="pb-3 font-semibold">Stock</th>
            <th className="w-20 pb-3 text-right font-semibold">Price</th>
            <th className="w-16 pb-3 text-right font-semibold">1D %</th>
            <th className="w-14 pb-3 text-right font-semibold">{score ? "Score" : ""}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={5} className="py-8 text-center text-slate-500">
                No live data yet.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.symbol}>
                <td className="py-3 tabular-nums text-slate-600">{row.rank}</td>
                <td className="py-3">
                  <Link href={`/stocks/${row.symbol}`} className="font-bold text-emerald-300 hover:text-emerald-200">
                    {row.symbol}
                  </Link>
                </td>
                <td className="py-3 text-right font-semibold tabular-nums text-slate-200">
                  {formatNumber(row.price, { maximumFractionDigits: 2 })}
                </td>
                <td className={cn("py-3 text-right font-bold tabular-nums", pctClass(row.changePct))}>
                  {formatPct(row.changePct)}
                </td>
                <td className="py-3 text-right">
                  {score ? (
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-emerald-300/40 text-[11px] font-bold text-emerald-300">
                      {formatNumber(row.score, { maximumFractionDigits: 0 })}
                    </span>
                  ) : (
                    <span className="inline-block h-8 w-8" aria-hidden />
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </article>
  );
}

function SectorBars({ sectors }: { sectors: SectorCell[] }) {
  const display = sectors.filter((s) => s.scoreChange1w != null).slice(0, 8);
  const values = display.map((s) => Math.abs(s.scoreChange1w ?? 0));
  const maxAbs = Math.max(0.01, ...values);
  return (
    <article className="rounded-lg border border-white/7 bg-[#0d1219] p-5">
      <div className="mb-1 flex items-end justify-between gap-3">
        <h2 className="text-base font-bold text-slate-100">Sector Performance</h2>
        <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">1M return</p>
      </div>
      <p className="mb-4 text-[11px] text-slate-500">
        Top industries by 1-month return (group average of constituent stocks).
      </p>
      <div className="space-y-3">
        {display.length === 0 ? (
          <p className="text-xs text-slate-500">No sector returns available yet.</p>
        ) : (
          display.map((sector) => {
            const ret = sector.scoreChange1w ?? 0;
            const widthPct = Math.min(100, Math.max(8, (Math.abs(ret) / maxAbs) * 100));
            return (
              <div key={sector.name} className="grid grid-cols-[100px_1fr_52px] items-center gap-3 text-xs">
                <span className="truncate text-slate-400" title={sector.name}>
                  {sector.name}
                </span>
                <span className="h-2 overflow-hidden rounded-full bg-white/5">
                  <span
                    className={cn("block h-full rounded-full", ret >= 0 ? "bg-emerald-400" : "bg-red-400")}
                    style={{ width: `${widthPct}%` }}
                  />
                </span>
                <span className={cn("text-right font-bold tabular-nums", pctClass(ret))}>{formatPct(ret, 1)}</span>
              </div>
            );
          })
        )}
      </div>
    </article>
  );
}

function rotationTone(state: string | null | undefined) {
  const s = (state || "").toLowerCase();
  if (s === "improving") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-300";
  if (s === "weakening") return "border-amber-400/40 bg-amber-400/10 text-amber-300";
  if (s === "leading") return "border-sky-400/40 bg-sky-400/10 text-sky-300";
  if (s === "lagging") return "border-red-400/40 bg-red-400/10 text-red-300";
  return "border-white/10 bg-white/5 text-slate-400";
}

function RotationList({ items }: { items: RotationItem[] }) {
  const flowing = items.filter((i) => (i.state || "").toLowerCase() === "improving");
  const cooling = items.filter((i) => (i.state || "").toLowerCase() === "weakening");
  return (
    <article className="rounded-lg border border-white/7 bg-[#0d1219] p-5">
      <h2 className="mb-1 text-base font-bold text-slate-100">Smart Money Rotation</h2>
      <p className="mb-4 text-[11px] text-slate-500">
        Where money is flowing (Improving) vs cooling off (Weakening), then Leading/Lagging fill.
      </p>
      <div className="space-y-2.5">
        {items.slice(0, 8).map((item) => {
          const ret = item.scoreChange ?? item.return3mCw;
          const badge = item.state || "-";
          const hint =
            (item.state || "").toLowerCase() === "improving"
              ? "Where money is flowing"
              : (item.state || "").toLowerCase() === "weakening"
                ? "Cooling off"
                : null;
          return (
            <div
              key={item.id}
              className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-md border border-white/5 bg-[#0a0e14] px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-semibold text-slate-200">{item.name}</span>
                  <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide", rotationTone(item.state))}>
                    {badge}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-slate-500">
                  Strength {formatNumber(item.score, { maximumFractionDigits: 0 })}
                  {ret != null ? ` · 3M ${formatPct(ret, 1)}` : ""}
                  {hint ? ` · ${hint}` : ""}
                </p>
              </div>
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-wide text-slate-600">Score</p>
                <p className="text-sm font-bold tabular-nums text-slate-100">
                  {formatNumber(item.score, { maximumFractionDigits: 0 })}
                </p>
              </div>
            </div>
          );
        })}
        {items.length === 0 ? <p className="py-6 text-center text-xs text-slate-500">No rotation data yet.</p> : null}
      </div>
      {(flowing.length > 0 || cooling.length > 0) && (
        <p className="mt-3 text-[10px] text-slate-600">
          {flowing.length ? `${flowing.length} improving` : "No improving"}
          {" · "}
          {cooling.length ? `${cooling.length} weakening` : "No weakening"}
        </p>
      )}
    </article>
  );
}

function MarketList({
  title,
  rows,
  href,
  viewLabel = "View all",
}: {
  title: string;
  rows: Array<IndexRow | SectorEtfRow>;
  href: string;
  viewLabel?: string;
}) {
  return (
    <article className="rounded-lg border border-white/7 bg-[#0d1219] p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-base font-bold text-slate-100">{title}</h2>
        <Link href={href} className="shrink-0 text-[11px] font-semibold text-emerald-300 hover:text-emerald-200">
          {viewLabel}
        </Link>
      </div>
      <table className="w-full text-left text-xs">
        <thead className="text-[10px] uppercase tracking-wide text-slate-600">
          <tr>
            <th className="pb-3">Name</th>
            <th className="pb-3 text-right">Price</th>
            <th className="pb-3 text-right">1D %</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.slice(0, 6).map((row) => (
            <tr key={"symbol" in row ? row.symbol : row.name}>
              <td className="py-3">
                <p className="font-bold text-emerald-300">{"symbol" in row ? row.symbol : row.name}</p>
                {"symbol" in row && row.name && row.name !== row.symbol ? (
                  <p className="text-[10px] text-slate-500">{row.name}</p>
                ) : null}
              </td>
              <td className="py-3 text-right font-semibold tabular-nums text-slate-200">
                {formatNumber(row.value, { maximumFractionDigits: 2 })}
              </td>
              <td className={cn("py-3 text-right font-bold tabular-nums", pctClass(row.changePct))}>
                {formatPct(row.changePct)}
              </td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={3} className="py-8 text-center text-slate-500">
                No quotes yet.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </article>
  );
}

function QuoteCard() {
  return (
    <article className="flex min-h-52 items-center justify-center rounded-lg border border-white/7 bg-[#0d1219] p-8 text-center">
      <div><p className="text-xl font-extrabold leading-snug text-slate-100">"Investing is not about timing the market, but time in the market."</p><span className="mx-auto mt-5 block h-1 w-12 rounded-full bg-emerald-400" /></div>
    </article>
  );
}

function WatchlistCta() {
  return (
    <article className="relative min-h-52 overflow-hidden rounded-lg border border-white/7 bg-[#0d1219] p-8">
      <div className="absolute inset-y-0 right-0 flex w-1/2 items-center justify-center opacity-10"><BarChart3 className="h-36 w-36 text-emerald-300" /></div>
      <div className="relative max-w-xs"><Search className="mb-5 h-6 w-6 text-emerald-300" /><p className="text-2xl font-extrabold leading-tight text-slate-100">Build your watchlist. Track opportunities.<span className="block text-emerald-400">Stay ahead.</span></p></div>
    </article>
  );
}
