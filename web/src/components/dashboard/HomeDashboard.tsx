"use client";

import { useEffect, useState } from "react";

import { PageAd } from "@/components/ads/PageAd";
import { IndexCards } from "@/components/dashboard/IndexCards";
import { IndicesOverview } from "@/components/dashboard/IndicesOverview";
import { MarketMovers } from "@/components/dashboard/MarketMovers";
import {
  MomentumLeadersCard,
  type MomentumLeader,
} from "@/components/dashboard/MomentumLeadersCard";
import { RotationCard } from "@/components/dashboard/RotationCard";
import { SectorEtfPanel } from "@/components/dashboard/SectorEtfPanel";
import { SectorStrengthCard } from "@/components/dashboard/SectorStrengthCard";
import { WatchlistCard } from "@/components/dashboard/WatchlistCard";
import type { SectorEtfRow } from "@/lib/load-dashboard";
import type { DashboardPayload } from "@/lib/load-dashboard";
import type { IndexCard } from "@/lib/dashboard-data";
import { getMarketsOverview, screenStocks } from "@/services/api";
import type { StockAnalysisRow } from "@/types/stock";

type Props = DashboardPayload;

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

function mapSectorEtfs(
  cards: {
    symbol: string;
    name: string;
    value: string | number | null;
    change_pct: number | null;
    sparkline?: number[];
    sector_name?: string | null;
  }[],
): SectorEtfRow[] {
  const out: SectorEtfRow[] = [];
  for (const c of cards) {
    const value = num(c.value);
    const changePct = c.change_pct;
    if (value === null || changePct === null) continue;
    out.push({
      symbol: c.symbol,
      name: c.name,
      value,
      changePct,
      sparkline: c.sparkline ?? [],
      kind: "sector_etf",
      sectorName: c.sector_name ?? null,
    });
  }
  return out;
}

function mapIndices(
  cards: {
    id: string;
    name: string;
    symbol: string;
    value: string | number | null;
    change: string | number | null;
    change_pct: number | null;
    sparkline?: number[];
    kind: string;
  }[],
): IndexCard[] {
  const out: IndexCard[] = [];
  for (const card of cards.slice(0, 5)) {
    const value = num(card.value);
    const change = num(card.change) ?? 0;
    const changePct = card.change_pct;
    if (value === null || changePct === null) continue;
    out.push({
      id: card.id,
      name: card.name,
      value,
      change,
      changePct,
      sparkline: card.sparkline ?? [],
      tone: changePct >= 0 ? "up" : "down",
      icon: "chart",
      kind: "index",
      subtitle: card.symbol,
    });
  }
  return out;
}

function mapMomentumLeaders(items: StockAnalysisRow[]): MomentumLeader[] {
  return items
    .map((row) => {
      const score = num(row.momentum_score ?? row.overall);
      if (score === null) return null;
      return {
        symbol: row.symbol,
        name: row.company_name,
        score,
        category: row.momentum_category,
        changePct: row.change_pct,
        ltp: num(row.ltp),
      };
    })
    .filter((x): x is MomentumLeader => x !== null)
    .slice(0, 12);
}

export function HomeDashboard(props: Props) {
  const [sectorEtfs, setSectorEtfs] = useState(props.sectorEtfs);
  const [indices, setIndices] = useState(props.indices);
  const [momentum, setMomentum] = useState(props.momentumLeaders);
  const [liveHint, setLiveHint] = useState<string | null>("Live NSE");
  const [momentumHint, setMomentumHint] = useState<string | null>(null);

  useEffect(() => {
    setSectorEtfs(props.sectorEtfs);
    setIndices(props.indices);
    setMomentum(props.momentumLeaders);
  }, [props.sectorEtfs, props.indices, props.momentumLeaders]);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const clock = () =>
        new Date().toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });

      try {
        const [overview, momentumRes] = await Promise.all([
          getMarketsOverview(),
          screenStocks({
            exchange: "NSE",
            sort_by: "momentum_score",
            sort_dir: "desc",
            limit: 12,
            scan_limit: 8000,
          }).catch(() => null),
        ]);
        if (cancelled) return;

        const etfs = mapSectorEtfs(overview.sector_etfs ?? []);
        if (etfs.length) setSectorEtfs(etfs);
        const idx = mapIndices(overview.indices ?? []);
        if (idx.length) setIndices(idx);
        setLiveHint(`Live · ${clock()}`);

        if (momentumRes?.items?.length) {
          const leaders = mapMomentumLeaders(momentumRes.items);
          if (leaders.length) {
            setMomentum(leaders);
            setMomentumHint(`Live · ${clock()}`);
          }
        }
      } catch {
        if (!cancelled) setLiveHint("Live · retrying");
      }
    };
    const id = window.setInterval(poll, 30_000);
    const boot = window.setTimeout(poll, 2_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
      window.clearTimeout(boot);
    };
  }, []);

  return (
    <div className="page-shell space-y-3">
      {indices.length > 0 ? (
        <IndexCards indices={indices} />
      ) : (
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-8 text-center text-sm text-[var(--ink-muted)]">
          No index quotes yet. Run{" "}
          <code className="text-xs">python -m cli scrape-indices</code>.
        </div>
      )}

      <PageAd page="dashboard" />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[260px_minmax(0,1.4fr)_minmax(0,0.9fr)]">
        <SectorEtfPanel items={sectorEtfs} liveHint={liveHint} />
        <MomentumLeadersCard items={momentum} liveHint={momentumHint} />
        <MarketMovers
          gainers={props.gainers}
          losers={props.losers}
          byVolume={props.byVolume}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <SectorStrengthCard sectors={props.sectors} />
        <IndicesOverview rows={props.indexRows} />
        <RotationCard items={props.rotation} />
        <WatchlistCard items={props.watchlist} />
      </div>
    </div>
  );
}
