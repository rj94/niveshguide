"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import { formatNumber, formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  listIndustryStocks,
  listSectorStocks,
} from "@/services/api";
import type { StockAnalysisRow } from "@/types/stock";

type Props = {
  kind: "sector" | "industry";
  name: string;
  parentSector?: string | null;
  strengthScore?: string | null;
  rotationState?: string | null;
  scoreChange1m?: string | null;
};

const SORT_OPTIONS = [
  { value: "momentum_score", label: "Momentum score" },
  { value: "overall", label: "Overall score" },
  { value: "symbol", label: "Symbol" },
  { value: "ltp", label: "Price" },
  { value: "return_1m_pct", label: "1M return" },
  { value: "return_3m_pct", label: "3M return" },
  { value: "company_strength", label: "Company strength" },
  { value: "industry_strength", label: "Industry strength" },
];

export function ConstituentsView({
  kind,
  name,
  parentSector,
  strengthScore,
  rotationState,
  scoreChange1m,
}: Props) {
  const [rows, setRows] = useState<StockAnalysisRow[]>([]);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState("momentum_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [exchange, setExchange] = useState("NSE");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    startTransition(async () => {
      try {
        const data =
          kind === "sector"
            ? await listSectorStocks(name, {
                exchange,
                sort_by: sortBy,
                sort_dir: sortDir,
                limit: 150,
              })
            : await listIndustryStocks(name, {
                exchange,
                sort_by: sortBy,
                sort_dir: sortDir,
                limit: 150,
              });
        setRows(data.items);
        setTotal(data.total);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load stocks");
        setRows([]);
        setTotal(0);
      }
    });
  }, [kind, name, exchange, sortBy, sortDir]);

  return (
    <div className="page-shell py-6">
      <Link
        href="/sectors"
        className="text-sm text-[var(--accent)] underline-offset-4 hover:underline"
      >
        ← All sectors
      </Link>

      <p className="mt-6 font-[family-name:var(--font-display)] text-sm uppercase tracking-[0.28em] text-[var(--accent)]">
        {kind === "sector" ? "Sector" : "Industry"}
      </p>
      <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-wide text-[var(--ink)] sm:text-5xl">
        {name}
      </h1>
      <p className="mt-2 text-[var(--ink-soft)]">
        {parentSector ? `${parentSector} · ` : ""}
        {strengthScore != null
          ? `Strength ${formatNumber(strengthScore, { maximumFractionDigits: 0 })}`
          : "Strength —"}
        {rotationState ? ` · ${rotationState}` : ""}
        {scoreChange1m != null
          ? ` · 1M ${Number(scoreChange1m) >= 0 ? "+" : ""}${formatNumber(scoreChange1m, { maximumFractionDigits: 1 })}`
          : ""}
        {` · ${total} stocks with recent prices`}
        {pending ? " · Loading…" : ""}
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <label className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
          Exchange
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="ml-2 border border-[var(--line)] bg-[var(--surface)] px-2 py-1.5 text-sm normal-case tracking-normal text-[var(--ink)]"
          >
            <option value="NSE">NSE</option>
            <option value="">All</option>
          </select>
        </label>
        <label className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
          Sort
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="ml-2 border border-[var(--line)] bg-[var(--surface)] px-2 py-1.5 text-sm normal-case tracking-normal text-[var(--ink)]"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
          Dir
          <select
            value={sortDir}
            onChange={(e) => setSortDir(e.target.value as "asc" | "desc")}
            className="ml-2 border border-[var(--line)] bg-[var(--surface)] px-2 py-1.5 text-sm normal-case tracking-normal text-[var(--ink)]"
          >
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </select>
        </label>
      </div>

      {error ? <p className="mt-4 text-sm text-[var(--down)]">{error}</p> : null}

      <div className="mt-6 overflow-x-auto border border-[var(--line)] bg-[var(--surface)]/70">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="border-b border-[var(--line)] text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
            <tr>
              <th className="px-4 py-3 font-medium">Stock</th>
              {kind === "sector" ? (
                <th className="px-4 py-3 font-medium">Industry</th>
              ) : null}
              <th className="px-4 py-3 font-medium text-right">LTP</th>
              <th className="px-4 py-3 font-medium text-right">Momentum</th>
              <th className="px-4 py-3 font-medium text-right">Overall</th>
              <th className="px-4 py-3 font-medium text-right">1M</th>
              <th className="px-4 py-3 font-medium text-right">3M</th>
              <th className="px-4 py-3 font-medium text-center">P&gt;50&gt;200</th>
              <th className="px-4 py-3 font-medium text-center">Vol mover</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${row.exchange}-${row.symbol}`}
                className="border-t border-[var(--line)]/80 hover:bg-[var(--surface-muted)]/60"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/stocks/${encodeURIComponent(row.symbol)}?exchange=${row.exchange}`}
                    className="font-[family-name:var(--font-display)] tracking-wide text-[var(--ink)] hover:text-[var(--accent)]"
                  >
                    {row.symbol}
                  </Link>
                  <div className="truncate text-xs text-[var(--ink-muted)]">
                    {row.company_name}
                  </div>
                </td>
                {kind === "sector" ? (
                  <td className="px-4 py-3 text-[var(--ink-soft)]">
                    {row.industry ? (
                      <Link
                        href={`/sectors/industry/${encodeURIComponent(row.industry)}`}
                        className="hover:text-[var(--accent)] hover:underline"
                      >
                        {row.industry}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                ) : null}
                <td className="px-4 py-3 text-right">
                  <div className="tabular-nums">{formatPrice(row.ltp)}</div>
                  <div
                    className={cn(
                      "text-xs tabular-nums",
                      (row.change_pct ?? 0) >= 0 ? "text-[var(--up)]" : "text-[var(--down)]",
                    )}
                  >
                    {formatPct(row.change_pct)}
                  </div>
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatNumber(row.momentum_score ?? row.overall ?? row.company_strength, {
                    maximumFractionDigits: 1,
                  })}
                  {row.momentum_category ? (
                    <div className="text-[10px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">
                      {row.momentum_category}
                    </div>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatNumber(row.overall ?? row.company_strength, {
                    maximumFractionDigits: 1,
                  })}
                </td>
                <td
                  className={cn(
                    "px-4 py-3 text-right tabular-nums",
                    (row.return_1m_pct ?? 0) >= 0 ? "text-[var(--up)]" : "text-[var(--down)]",
                  )}
                >
                  {formatPct(row.return_1m_pct)}
                </td>
                <td
                  className={cn(
                    "px-4 py-3 text-right tabular-nums",
                    (row.return_3m_pct ?? 0) >= 0 ? "text-[var(--up)]" : "text-[var(--down)]",
                  )}
                >
                  {formatPct(row.return_3m_pct)}
                </td>
                <td className="px-4 py-3 text-center text-xs uppercase tracking-[0.12em]">
                  {row.price_above_50_above_200 == null
                    ? "—"
                    : row.price_above_50_above_200
                      ? "Yes"
                      : "No"}
                </td>
                <td className="px-4 py-3 text-center text-xs uppercase tracking-[0.12em]">
                  {row.volume_mover == null ? "—" : row.volume_mover ? "Yes" : "No"}
                </td>
              </tr>
            ))}
            {rows.length === 0 && !pending ? (
              <tr>
                <td
                  colSpan={kind === "sector" ? 9 : 8}
                  className="px-4 py-8 text-center text-[var(--ink-muted)]"
                >
                  No priced constituents found for this filter.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
