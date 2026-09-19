"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useTransition } from "react";

import { formatNumber } from "@/lib/format";
import {
  DEFAULT_SECTOR_PREFS,
  SECTOR_COLUMN_DEFS,
  loadSectorPrefs,
  saveSectorPrefs,
  type SectorColumnId,
  type SectorPrefs,
} from "@/lib/sector-columns";
import { cn } from "@/lib/utils";
import { listSectors } from "@/services/api";
import type { StrengthRow } from "@/types/sector";

import {
  ChangeCell,
  change21d,
  change5d,
  num,
  scoreOf,
  stateClass,
  strengthLabel,
} from "./sector-ui";

const ROTATION_COLUMNS = [
  { key: "Leading", hint: "Strong RS, momentum and breadth" },
  { key: "Improving", hint: "Emerging — ranked by acceleration" },
  { key: "Weakening", hint: "High RS, internals rolling over" },
  { key: "Lagging", hint: "Weak RS and momentum" },
] as const;

function sortRows(rows: StrengthRow[], prefs: SectorPrefs): StrengthRow[] {
  const dir = prefs.sortDir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    let av = 0;
    let bv = 0;
    switch (prefs.sortBy) {
      case "score":
        av = scoreOf(a) ?? -1;
        bv = scoreOf(b) ?? -1;
        break;
      case "change_5d":
        av = change5d(a) ?? -999;
        bv = change5d(b) ?? -999;
        break;
      case "change_21d":
        av = change21d(a) ?? -999;
        bv = change21d(b) ?? -999;
        break;
      case "change_1m":
        av = change21d(a) ?? num(a.return_1m) ?? -999;
        bv = change21d(b) ?? num(b.return_1m) ?? -999;
        break;
      case "change_1w":
        av = change5d(a) ?? -999;
        bv = change5d(b) ?? -999;
        break;
      case "breadth":
        av = num(a.breadth_score) ?? -1;
        bv = num(b.breadth_score) ?? -1;
        break;
      case "names":
        av = a.constituent_count ?? -1;
        bv = b.constituent_count ?? -1;
        break;
      case "rank":
      default:
        av = a.rank ?? 999;
        bv = b.rank ?? 999;
        break;
    }
    return (av - bv) * dir;
  });
}

function rotationBuckets(rows: StrengthRow[]) {
  const buckets: Record<(typeof ROTATION_COLUMNS)[number]["key"], StrengthRow[]> = {
    Leading: [],
    Improving: [],
    Weakening: [],
    Lagging: [],
  };
  for (const row of rows) {
    const state = (row.rotation_state || "") as keyof typeof buckets;
    if (state in buckets) buckets[state].push(row);
  }
  buckets.Improving.sort((a, b) => (num(b.emerging_score) ?? 0) - (num(a.emerging_score) ?? 0));
  for (const key of ["Leading", "Weakening", "Lagging"] as const) {
    buckets[key].sort((a, b) => (scoreOf(b) ?? 0) - (scoreOf(a) ?? 0));
  }
  return buckets;
}

function RsMomentumScatter({ rows }: { rows: StrengthRow[] }) {
  const points = rows
    .map((row) => ({
      name: row.name,
      rs: num(row.relative_strength_score),
      mom: num(row.momentum_score),
      state: row.rotation_state,
    }))
    .filter((p): p is { name: string; rs: number; mom: number; state: string | null } => p.rs != null && p.mom != null)
    .slice(0, 40);
  const w = 320;
  const h = 240;
  const pad = 28;
  return (
    <section className="mt-10 border border-[var(--line)] bg-[var(--surface)]/70 p-4">
      <h2 className="font-[family-name:var(--font-display)] text-xl tracking-wide text-[var(--ink)]">
        RS vs momentum
      </h2>
      <p className="mt-1 text-xs text-[var(--ink-muted)]">
        Upper-right is leadership. Points colored by rotation state.
      </p>
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-4 w-full max-w-md" role="img" aria-label="RS versus momentum scatter">
        <line x1={pad} y1={h - pad} x2={w - 8} y2={h - pad} stroke="currentColor" className="text-[var(--line)]" />
        <line x1={pad} y1={8} x2={pad} y2={h - pad} stroke="currentColor" className="text-[var(--line)]" />
        <text x={w / 2} y={h - 6} textAnchor="middle" className="fill-[var(--ink-muted)] text-[10px]">
          Relative strength
        </text>
        <text
          x={12}
          y={h / 2}
          textAnchor="middle"
          transform={`rotate(-90 12 ${h / 2})`}
          className="fill-[var(--ink-muted)] text-[10px]"
        >
          Momentum
        </text>
        {points.map((p) => {
          const x = pad + (p.rs / 100) * (w - pad - 12);
          const y = h - pad - (p.mom / 100) * (h - pad - 12);
          const fill =
            p.state === "Leading"
              ? "var(--up)"
              : p.state === "Improving"
                ? "var(--accent)"
                : p.state === "Lagging"
                  ? "var(--down)"
                  : "var(--ink-muted)";
          return (
            <circle key={p.name} cx={x} cy={y} r={4} fill={fill}>
              <title>{`${p.name} · RS ${Math.round(p.rs)} · Mom ${Math.round(p.mom)}`}</title>
            </circle>
          );
        })}
      </svg>
    </section>
  );
}

function StrengthTable({
  title,
  rows,
  nameHeader,
  hrefFor,
  showParent,
  columns,
}: {
  title: string;
  rows: StrengthRow[];
  nameHeader: string;
  hrefFor: (row: StrengthRow) => string;
  showParent?: boolean;
  columns: SectorColumnId[];
}) {
  const visible = new Set(columns);
  if (showParent === false) visible.delete("parent");
  const scoreCol = (row: StrengthRow, id: SectorColumnId) => {
    switch (id) {
      case "rs":
        return num(row.relative_strength_score);
      case "momentum":
        return num(row.momentum_score);
      case "breadth":
        return num(row.breadth_score);
      case "volume":
        return num(row.volume_score);
      case "breakout":
        return num(row.breakout_score);
      case "trend":
        return num(row.trend_score);
      default:
        return null;
    }
  };

  return (
    <section className="mt-12">
      <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
        {title}
      </h2>
      <div className="mt-4 overflow-x-auto border border-[var(--line)] bg-[var(--surface)]/70">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead className="border-b border-[var(--line)] text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
            <tr>
              {visible.has("rank") ? <th className="px-4 py-3 font-medium">Rank</th> : null}
              {visible.has("name") ? <th className="px-4 py-3 font-medium">{nameHeader}</th> : null}
              {visible.has("parent") && showParent ? (
                <th className="px-4 py-3 font-medium">Sector</th>
              ) : null}
              {visible.has("score") ? <th className="px-4 py-3 font-medium">Score</th> : null}
              {visible.has("state") ? <th className="px-4 py-3 font-medium">State</th> : null}
              {visible.has("rs") ? <th className="px-4 py-3 font-medium">RS</th> : null}
              {visible.has("momentum") ? <th className="px-4 py-3 font-medium">Mom</th> : null}
              {visible.has("breadth") ? <th className="px-4 py-3 font-medium">Breadth</th> : null}
              {visible.has("volume") ? <th className="px-4 py-3 font-medium">Vol</th> : null}
              {visible.has("breakout") ? <th className="px-4 py-3 font-medium">Break</th> : null}
              {visible.has("trend") ? <th className="px-4 py-3 font-medium">Trend</th> : null}
              {visible.has("change_5d") ? <th className="px-4 py-3 font-medium">5D Δ</th> : null}
              {visible.has("change_21d") ? <th className="px-4 py-3 font-medium">21D Δ</th> : null}
              {visible.has("change_1w") ? <th className="px-4 py-3 font-medium">1W Δ</th> : null}
              {visible.has("change_1m") ? <th className="px-4 py-3 font-medium">1M Δ</th> : null}
              {visible.has("return_1m") ? <th className="px-4 py-3 font-medium">1M Ret</th> : null}
              {visible.has("names") ? <th className="px-4 py-3 font-medium">Names</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const score = scoreOf(row);
              return (
                <tr
                  key={`${row.parent_sector ?? ""}-${row.name}`}
                  className={cn(
                    "border-t border-[var(--line)]/80 hover:bg-[var(--surface-muted)]/60",
                    row.is_gaining_strength && "bg-[var(--accent-soft)]/25",
                  )}
                >
                  {visible.has("rank") ? (
                    <td className="px-4 py-3 tabular-nums text-[var(--ink-muted)]">
                      {row.rank ?? "—"}
                    </td>
                  ) : null}
                  {visible.has("name") ? (
                    <td className="px-4 py-3">
                      <Link
                        href={hrefFor(row)}
                        className="font-[family-name:var(--font-display)] text-base tracking-wide text-[var(--ink)] underline-offset-4 hover:text-[var(--accent)] hover:underline"
                      >
                        {row.name}
                      </Link>
                    </td>
                  ) : null}
                  {visible.has("parent") && showParent ? (
                    <td className="px-4 py-3 text-[var(--ink-soft)]">
                      {row.parent_sector ? (
                        <Link
                          href={`/sectors/sector/${encodeURIComponent(row.parent_sector)}`}
                          className="hover:text-[var(--accent)] hover:underline"
                        >
                          {row.parent_sector}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  ) : null}
                  {visible.has("score") ? (
                    <td className="px-4 py-3 font-[family-name:var(--font-display)] text-xl tabular-nums text-[var(--ink)]">
                      {score !== null
                        ? formatNumber(score, { maximumFractionDigits: 0 })
                        : "—"}
                      <div className="text-xs text-[var(--ink-muted)]">
                        {strengthLabel(score)}
                      </div>
                    </td>
                  ) : null}
                  {visible.has("state") ? (
                    <td className={cn("px-4 py-3", stateClass(row.rotation_state))}>
                      {row.rotation_state ?? "—"}
                    </td>
                  ) : null}
                  {(["rs", "momentum", "breadth", "volume", "breakout", "trend"] as const).map(
                    (id) =>
                      visible.has(id) ? (
                        <td key={id} className="px-4 py-3 tabular-nums">
                          {formatNumber(scoreCol(row, id), { maximumFractionDigits: 0 })}
                        </td>
                      ) : null,
                  )}
                  {visible.has("change_5d") ? (
                    <td className="px-4 py-3">
                      <ChangeCell value={change5d(row)} />
                    </td>
                  ) : null}
                  {visible.has("change_21d") ? (
                    <td className="px-4 py-3">
                      <ChangeCell value={change21d(row)} />
                    </td>
                  ) : null}
                  {visible.has("change_1w") ? (
                    <td className="px-4 py-3">
                      <ChangeCell value={num(row.score_change_1w)} />
                    </td>
                  ) : null}
                  {visible.has("change_1m") ? (
                    <td className="px-4 py-3">
                      <ChangeCell value={num(row.score_change_1m)} />
                    </td>
                  ) : null}
                  {visible.has("return_1m") ? (
                    <td className="px-4 py-3 tabular-nums">
                      {formatNumber(row.return_1m, { maximumFractionDigits: 1 })}
                    </td>
                  ) : null}
                  {visible.has("names") ? (
                    <td className="px-4 py-3 tabular-nums text-[var(--ink-muted)]">
                      {row.constituent_count ?? "—"}
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function SectorsWorkspace() {
  const [prefs, setPrefs] = useState<SectorPrefs>(DEFAULT_SECTOR_PREFS);
  const [hydrated, setHydrated] = useState(false);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [sectors, setSectors] = useState<StrengthRow[]>([]);
  const [industries, setIndustries] = useState<StrengthRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [customizeOpen, setCustomizeOpen] = useState(false);

  useEffect(() => {
    setPrefs(loadSectorPrefs());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    saveSectorPrefs(prefs);
  }, [prefs, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    startTransition(async () => {
      try {
        const data = await listSectors({
          limit: 200,
          min_constituents: prefs.minConstituents,
          gaining_only: prefs.gainingOnly,
        });
        setSectors(data.items);
        setIndustries(data.industries);
        setAsOf(data.as_of);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load sectors");
      }
    });
  }, [hydrated, prefs.minConstituents, prefs.gainingOnly]);

  const sortedSectors = useMemo(() => sortRows(sectors, prefs), [sectors, prefs]);
  const sortedIndustries = useMemo(() => sortRows(industries, prefs), [industries, prefs]);
  const buckets = useMemo(() => rotationBuckets(sectors), [sectors]);

  function patch(partial: Partial<SectorPrefs>) {
    setPrefs((prev) => ({ ...prev, ...partial }));
  }

  function toggleColumn(id: SectorColumnId) {
    setPrefs((prev) => {
      const has = prev.columns.includes(id);
      if (has && id === "name") return prev;
      const columns = has
        ? prev.columns.filter((c) => c !== id)
        : [...prev.columns, id];
      return { ...prev, columns };
    });
  }

  return (
    <div className="page-shell py-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-[family-name:var(--font-display)] text-sm uppercase tracking-[0.28em] text-[var(--accent)]">
            Sector Rotation
          </p>
          <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl tracking-wide text-[var(--ink)] sm:text-5xl">
            Sector strength dashboard
          </h1>
          <p className="mt-3 max-w-2xl text-[var(--ink-soft)]">
            Six-component score versus NIFTY 500: relative strength, momentum,
            breadth, volume flow, breakouts, and trend quality.
            {asOf ? ` As of ${asOf}.` : ""}
            {pending ? " Updating…" : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCustomizeOpen((v) => !v)}
          className="border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
        >
          {customizeOpen ? "Hide options" : "Customize"}
        </button>
      </div>

      {customizeOpen ? (
        <section className="mt-6 border border-[var(--line)] bg-[var(--surface)]/80 p-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <label className="block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
              Sort by
              <select
                value={prefs.sortBy}
                onChange={(e) =>
                  patch({ sortBy: e.target.value as SectorPrefs["sortBy"] })
                }
                className="mt-1 w-full border border-[var(--line)] bg-[var(--surface)] px-2 py-2 text-sm normal-case tracking-normal text-[var(--ink)]"
              >
                <option value="rank">Rank</option>
                <option value="score">Score</option>
                <option value="change_5d">5D change</option>
                <option value="change_21d">21D change</option>
                <option value="breadth">Breadth</option>
                <option value="names">Constituents</option>
              </select>
            </label>
            <label className="block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
              Direction
              <select
                value={prefs.sortDir}
                onChange={(e) =>
                  patch({ sortDir: e.target.value as SectorPrefs["sortDir"] })
                }
                className="mt-1 w-full border border-[var(--line)] bg-[var(--surface)] px-2 py-2 text-sm normal-case tracking-normal text-[var(--ink)]"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </label>
            <label className="block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
              Min constituents
              <input
                type="number"
                min={0}
                max={100}
                value={prefs.minConstituents}
                onChange={(e) =>
                  patch({ minConstituents: Number(e.target.value) || 0 })
                }
                className="mt-1 w-full border border-[var(--line)] bg-[var(--surface)] px-2 py-2 text-sm normal-case tracking-normal text-[var(--ink)]"
              />
            </label>
            <div className="space-y-2 text-sm text-[var(--ink-soft)]">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.showScatter}
                  onChange={(e) => patch({ showScatter: e.target.checked })}
                />
                Show RS scatter
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.showSectors}
                  onChange={(e) => patch({ showSectors: e.target.checked })}
                />
                Show sectors
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.showIndustries}
                  onChange={(e) => patch({ showIndustries: e.target.checked })}
                />
                Show industries
              </label>
            </div>
          </div>
          <div className="mt-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
              Columns
            </p>
            <div className="mt-2 flex flex-wrap gap-3">
              {SECTOR_COLUMN_DEFS.map((col) => (
                <label
                  key={col.id}
                  className="flex items-center gap-2 text-sm text-[var(--ink-soft)]"
                >
                  <input
                    type="checkbox"
                    checked={prefs.columns.includes(col.id)}
                    disabled={col.id === "name"}
                    onChange={() => toggleColumn(col.id)}
                  />
                  {col.label}
                </label>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {error ? (
        <p className="mt-6 text-sm text-[var(--down)]">
          {/Failed to fetch|NetworkError|ECONNREFUSED/i.test(error)
            ? `Cannot reach API at ${process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8010/api/v1"}. Start the backend and retry.`
            : error}
        </p>
      ) : null}

      <section className="mt-10 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {ROTATION_COLUMNS.map((col) => {
          const list = buckets[col.key].slice(0, 8);
          return (
            <div key={col.key} className="border border-[var(--line)] bg-[var(--surface)]/80 p-4">
              <p className={cn("text-xs uppercase tracking-[0.16em]", stateClass(col.key))}>
                {col.key === "Improving" ? "Improving · Emerging" : col.key}
              </p>
              <p className="mt-1 text-xs text-[var(--ink-muted)]">{col.hint}</p>
              <ul className="mt-3 space-y-2">
                {list.map((row) => {
                  const score = scoreOf(row);
                  return (
                    <li key={row.name}>
                      <Link
                        href={`/sectors/sector/${encodeURIComponent(row.name)}`}
                        className="flex items-baseline justify-between gap-2 hover:text-[var(--accent)]"
                      >
                        <span className="truncate font-[family-name:var(--font-display)] tracking-wide">
                          {row.name}
                        </span>
                        <span className="shrink-0 tabular-nums text-sm">
                          {score != null ? Math.round(score) : "—"}{" "}
                          <ChangeCell value={change5d(row)} />
                        </span>
                      </Link>
                    </li>
                  );
                })}
                {list.length === 0 ? (
                  <li className="text-sm text-[var(--ink-muted)]">No names yet.</li>
                ) : null}
              </ul>
            </div>
          );
        })}
      </section>

      {prefs.showScatter ? <RsMomentumScatter rows={sectors} /> : null}

      {prefs.showSectors ? (
        <StrengthTable
          title="All sectors"
          rows={sortedSectors}
          nameHeader="Sector"
          hrefFor={(row) => `/sectors/sector/${encodeURIComponent(row.name)}`}
          columns={prefs.columns}
        />
      ) : null}

      {prefs.showIndustries ? (
        <StrengthTable
          title="All industries"
          rows={sortedIndustries}
          nameHeader="Industry"
          showParent
          hrefFor={(row) => `/sectors/industry/${encodeURIComponent(row.name)}`}
          columns={prefs.columns}
        />
      ) : null}
    </div>
  );
}
