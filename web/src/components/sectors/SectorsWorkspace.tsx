"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useTransition } from "react";

import { formatNumber, formatPct } from "@/lib/format";
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

function strengthLabel(score: number | null): string {
  if (score === null) return "—";
  if (score >= 91) return "Exceptional";
  if (score >= 76) return "Very Strong";
  if (score >= 61) return "Strong";
  if (score >= 41) return "Neutral";
  if (score >= 21) return "Weak";
  return "Very Weak";
}

function num(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function ChangeCell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-[var(--ink-muted)]">—</span>;
  return (
    <span
      className={cn(
        "tabular-nums",
        value > 0 ? "text-[var(--up)]" : value < 0 ? "text-[var(--down)]" : "text-[var(--ink-muted)]",
      )}
    >
      {value > 0 ? "↑ " : value < 0 ? "↓ " : ""}
      {formatNumber(Math.abs(value), { maximumFractionDigits: 1 })}
    </span>
  );
}

function sortRows(rows: StrengthRow[], prefs: SectorPrefs): StrengthRow[] {
  const dir = prefs.sortDir === "asc" ? 1 : -1;
  const scoreOf = (row: StrengthRow) =>
    num(row.strength_score ?? row.sector_strength_score ?? row.industry_strength_score) ?? -1;
  return [...rows].sort((a, b) => {
    let av = 0;
    let bv = 0;
    switch (prefs.sortBy) {
      case "score":
        av = scoreOf(a);
        bv = scoreOf(b);
        break;
      case "change_1m":
        av = num(a.score_change_1m) ?? -999;
        bv = num(b.score_change_1m) ?? -999;
        break;
      case "change_1w":
        av = num(a.score_change_1w) ?? -999;
        bv = num(b.score_change_1w) ?? -999;
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

  return (
    <section className="mt-12">
      <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
        {title}
      </h2>
      <div className="mt-4 overflow-x-auto border border-[var(--line)] bg-[var(--surface)]/70">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-[var(--line)] text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
            <tr>
              {visible.has("rank") ? <th className="px-4 py-3 font-medium">Rank</th> : null}
              {visible.has("name") ? <th className="px-4 py-3 font-medium">{nameHeader}</th> : null}
              {visible.has("parent") && showParent ? (
                <th className="px-4 py-3 font-medium">Sector</th>
              ) : null}
              {visible.has("score") ? <th className="px-4 py-3 font-medium">Score</th> : null}
              {visible.has("state") ? <th className="px-4 py-3 font-medium">State</th> : null}
              {visible.has("change_1w") ? <th className="px-4 py-3 font-medium">1W Δ</th> : null}
              {visible.has("change_1m") ? <th className="px-4 py-3 font-medium">1M Δ</th> : null}
              {visible.has("change_3m") ? <th className="px-4 py-3 font-medium">3M Δ</th> : null}
              {visible.has("momentum") ? <th className="px-4 py-3 font-medium">Momentum</th> : null}
              {visible.has("breadth") ? <th className="px-4 py-3 font-medium">Breadth</th> : null}
              {visible.has("return_1m") ? <th className="px-4 py-3 font-medium">1M Ret</th> : null}
              {visible.has("names") ? <th className="px-4 py-3 font-medium">Names</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const score = num(
                row.strength_score ?? row.sector_strength_score ?? row.industry_strength_score,
              );
              const ret1m = num(row.return_1m);
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
                      {row.is_gaining_strength ? (
                        <span className="ml-2 text-xs uppercase tracking-[0.12em] text-[var(--accent)]">
                          Gaining
                        </span>
                      ) : null}
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
                    <td className="px-4 py-3 text-[var(--ink-soft)]">
                      {row.rotation_state ?? "—"}
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
                  {visible.has("change_3m") ? (
                    <td className="px-4 py-3">
                      <ChangeCell value={num(row.score_change_3m)} />
                    </td>
                  ) : null}
                  {visible.has("momentum") ? (
                    <td className="px-4 py-3 tabular-nums">
                      {formatNumber(row.momentum_score, { maximumFractionDigits: 0 })}
                    </td>
                  ) : null}
                  {visible.has("breadth") ? (
                    <td className="px-4 py-3 tabular-nums">
                      {formatNumber(row.breadth_score, { maximumFractionDigits: 0 })}
                    </td>
                  ) : null}
                  {visible.has("return_1m") ? (
                    <td
                      className={cn(
                        "px-4 py-3 tabular-nums",
                        (ret1m ?? 0) >= 0 ? "text-[var(--up)]" : "text-[var(--down)]",
                      )}
                    >
                      {formatPct(ret1m)}
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
  const [gaining, setGaining] = useState<StrengthRow[]>([]);
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
        setGaining(data.gaining);
        setAsOf(data.as_of);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load sectors");
      }
    });
  }, [hydrated, prefs.minConstituents, prefs.gainingOnly]);

  const sortedSectors = useMemo(() => sortRows(sectors, prefs), [sectors, prefs]);
  const sortedIndustries = useMemo(() => sortRows(industries, prefs), [industries, prefs]);

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
            Sector Strength Engine
          </p>
          <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl tracking-wide text-[var(--ink)] sm:text-5xl">
            Sector & industry map
          </h1>
          <p className="mt-3 max-w-2xl text-[var(--ink-soft)]">
            Sectors and industries come from screener.in classifications linked
            to each stock. Strength blends constituent momentum scores,
            relative 3M return rank, and breadth (0–100).
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
                <option value="change_1m">1M change</option>
                <option value="change_1w">1W change</option>
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
                  checked={prefs.gainingOnly}
                  onChange={(e) => patch({ gainingOnly: e.target.checked })}
                />
                Gaining only
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.showGaining}
                  onChange={(e) => patch({ showGaining: e.target.checked })}
                />
                Show gaining cards
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

      {prefs.showGaining && gaining.length > 0 ? (
        <section className="mt-10">
          <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
            Gaining strength
          </h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {gaining.map((row) => {
              const score = num(row.strength_score ?? row.sector_strength_score);
              const ch = num(row.score_change_1m);
              return (
                <li key={row.name}>
                  <Link
                    href={`/sectors/sector/${encodeURIComponent(row.name)}`}
                    className="block border border-[var(--line)] bg-[var(--surface)]/80 px-4 py-4 transition hover:border-[var(--accent)]"
                  >
                    <p className="text-xs uppercase tracking-[0.16em] text-[var(--accent)]">
                      {row.rotation_state ?? "Improving"}
                    </p>
                    <p className="mt-1 font-[family-name:var(--font-display)] text-xl tracking-wide text-[var(--ink)]">
                      {row.name}
                    </p>
                    <div className="mt-3 flex items-end justify-between gap-3">
                      <p className="font-[family-name:var(--font-display)] text-3xl tabular-nums text-[var(--ink)]">
                        {score !== null
                          ? formatNumber(score, { maximumFractionDigits: 0 })
                          : "—"}
                      </p>
                      <p className="text-sm text-[var(--ink-soft)]">
                        1M <ChangeCell value={ch} />
                      </p>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

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
