"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { getIndustry, getSector } from "@/services/api";
import type { IndustryScoreRow, SectorScoreRow, StrengthRow } from "@/types/sector";

import { ConstituentsView } from "./ConstituentsView";
import {
  ChangeCell,
  ScoreBar,
  change21d,
  change5d,
  num,
  scoreOf,
  stateClass,
  strengthLabel,
} from "./sector-ui";

type Kind = "sector" | "industry";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[var(--line)] bg-[var(--surface)]/70 px-3 py-3">
      <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--ink-muted)]">{label}</p>
      <p className="mt-1 tabular-nums text-[var(--ink)]">{value}</p>
    </div>
  );
}

function pct(value: string | number | null | undefined): string {
  const n = num(value);
  return n == null ? "—" : `${Math.round(n)}%`;
}

export function GroupDetailWorkspace({ kind, name }: { kind: Kind; name: string }) {
  const [row, setRow] = useState<SectorScoreRow | IndustryScoreRow | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = kind === "sector" ? await getSector(name) : await getIndustry(name);
        if (!cancelled) {
          setRow(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load analysis");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [kind, name]);

  const score = row ? scoreOf(row) : null;
  const industries: StrengthRow[] = kind === "sector" ? ((row as SectorScoreRow | null)?.industries ?? []) : [];
  const parent = row?.parent_sector ?? null;

  return (
    <div className="page-shell py-6">
      <Link
        href="/sectors"
        className="text-sm text-[var(--accent)] underline-offset-4 hover:underline"
      >
        ← All sectors
      </Link>
      {parent && kind === "industry" ? (
        <p className="mt-3 text-sm text-[var(--ink-soft)]">
          Parent sector{" "}
          <Link
            href={`/sectors/sector/${encodeURIComponent(parent)}`}
            className="text-[var(--accent)] hover:underline"
          >
            {parent}
          </Link>
        </p>
      ) : null}

      <p className="mt-6 font-[family-name:var(--font-display)] text-sm uppercase tracking-[0.28em] text-[var(--accent)]">
        {kind === "sector" ? "Sector analysis" : "Industry analysis"}
      </p>
      <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-wide text-[var(--ink)] sm:text-5xl">
        {name}
      </h1>
      <p className="mt-2 text-[var(--ink-soft)]">
        <span className={cn("font-[family-name:var(--font-display)] text-3xl tabular-nums text-[var(--ink)]")}>
          {score != null ? formatNumber(score, { maximumFractionDigits: 0 }) : "—"}
        </span>
        <span className="ml-3">{strengthLabel(score)}</span>
        {row?.rotation_state ? (
          <span className={cn("ml-3", stateClass(row.rotation_state))}>{row.rotation_state}</span>
        ) : null}
        <span className="ml-3">
          5D <ChangeCell value={row ? change5d(row) : null} />
        </span>
        <span className="ml-3">
          21D <ChangeCell value={row ? change21d(row) : null} />
        </span>
      </p>
      {row?.alerts?.length ? (
        <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[var(--accent)]">
          {row.alerts.join(" · ")}
        </p>
      ) : null}
      {error ? <p className="mt-4 text-sm text-[var(--down)]">{error}</p> : null}

      <section className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-3 border border-[var(--line)] bg-[var(--surface)]/70 p-4">
          <h2 className="font-[family-name:var(--font-display)] text-lg tracking-wide text-[var(--ink)]">
            Component scores
          </h2>
          <ScoreBar label="Relative strength" value={num(row?.relative_strength_score)} />
          <ScoreBar label="Momentum" value={num(row?.momentum_score)} />
          <ScoreBar label="Breadth" value={num(row?.breadth_score)} />
          <ScoreBar label="Volume" value={num(row?.volume_score)} />
          <ScoreBar label="Breakouts" value={num(row?.breakout_score)} />
          {kind === "sector" ? <ScoreBar label="Trend quality" value={num(row?.trend_score)} /> : null}
          <ScoreBar label="Emerging" value={num(row?.emerging_score)} />
        </div>
        <div className="grid grid-cols-2 gap-3 content-start">
          <Stat label=">21 DMA" value={pct(row?.above_21dma_pct)} />
          <Stat label=">50 DMA" value={pct(row?.above_50dma_pct)} />
          <Stat label=">200 DMA" value={pct(row?.above_200dma_pct)} />
          <Stat label="20D highs" value={pct(row?.breakout_20d_pct)} />
          <Stat label="50D highs" value={pct(row?.breakout_50d_pct)} />
          <Stat label="52W highs" value={pct(row?.breakout_52w_pct)} />
          <Stat
            label="Vol expansion"
            value={
              num(row?.volume_expansion) == null
                ? "—"
                : `${Number(num(row?.volume_expansion)).toFixed(2)}x`
            }
          />
          <Stat label="Names" value={row?.constituent_count != null ? String(row.constituent_count) : "—"} />
        </div>
      </section>

      {kind === "sector" ? (
        <section className="mt-10">
          <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
            Top industries
          </h2>
          {industries.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--ink-muted)]">No nested industries for this sector yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-[var(--line)] border border-[var(--line)] bg-[var(--surface)]/70">
              {industries.slice(0, 12).map((ind) => (
                <li key={ind.name} className="flex items-baseline justify-between gap-3 px-4 py-3">
                  <Link
                    href={`/sectors/industry/${encodeURIComponent(ind.name)}`}
                    className="font-[family-name:var(--font-display)] tracking-wide hover:text-[var(--accent)]"
                  >
                    {ind.name}
                  </Link>
                  <span className="tabular-nums text-sm">
                    {scoreOf(ind) != null ? Math.round(scoreOf(ind) as number) : "—"}{" "}
                    <span className={stateClass(ind.rotation_state)}>{ind.rotation_state ?? ""}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <ConstituentsView kind={kind} name={name} embedded />
    </div>
  );
}
