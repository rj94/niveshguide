"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Briefcase,
  LoaderCircle,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";

import { getClientKey } from "@/lib/client-key";
import { formatNumber, formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  clearMyPortfolio,
  getMyPortfolio,
  importMyPortfolio,
} from "@/services/api";
import type { PortfolioHolding, PortfolioResponse } from "@/types/portfolio";

const REFRESH_MS = 60_000;

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function money(value: string | number | null | undefined): string {
  const n = num(value);
  if (n == null) return "—";
  return `₹${formatNumber(n, { maximumFractionDigits: 2 })}`;
}

function PnlText({
  value,
  pct,
  className,
}: {
  value: string | number | null | undefined;
  pct?: number | null;
  className?: string;
}) {
  const n = num(value);
  const up = (n ?? 0) > 0;
  const down = (n ?? 0) < 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 tabular-nums font-semibold",
        up ? "text-[var(--up)]" : down ? "text-[var(--down)]" : "text-[var(--ink-muted)]",
        className,
      )}
    >
      {up ? <ArrowUpRight className="h-3.5 w-3.5" /> : null}
      {down ? <ArrowDownRight className="h-3.5 w-3.5" /> : null}
      {money(value)}
      {pct != null ? (
        <span className="ml-1 text-xs font-medium opacity-80">({formatPct(pct)})</span>
      ) : null}
    </span>
  );
}

function brokerLabel(broker: string | null | undefined): string {
  if (!broker) return "Not linked";
  if (broker === "zerodha") return "Zerodha";
  if (broker === "angelone") return "Angel One";
  return broker;
}

export function PortfolioWorkspace() {
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const key = getClientKey();
    const res = await getMyPortfolio(key);
    setData(res);
    setLastRefresh(res.refreshed_at ?? new Date().toISOString());
    setError(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await refresh();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load portfolio");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void refresh().catch(() => {
        /* keep last good snapshot */
      });
    }, REFRESH_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  async function onUpload(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const key = getClientKey();
      const res = await importMyPortfolio(key, file);
      setData(res);
      setLastRefresh(res.refreshed_at ?? new Date().toISOString());
      const unmatched = res.recent_imports[0]?.unmatched_symbols ?? [];
      if (unmatched.length) {
        setError(`Imported with unmatched symbols: ${unmatched.join(", ")}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onClear() {
    if (!data?.holdings.length) return;
    if (!window.confirm("Clear all holdings from this portfolio?")) return;
    setBusy(true);
    try {
      const key = getClientKey();
      const res = await clearMyPortfolio(key);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear portfolio");
    } finally {
      setBusy(false);
    }
  }

  const holdings = useMemo(() => data?.holdings ?? [], [data]);
  const summary = data?.summary;

  if (loading) {
    return (
      <div className="page-shell flex items-center gap-2 py-16 text-[var(--ink-muted)]">
        <LoaderCircle className="h-4 w-4 animate-spin" />
        Loading portfolio…
      </div>
    );
  }

  return (
    <div className="page-shell mx-auto flex max-w-6xl flex-col gap-4 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 text-[var(--accent-hover)]">
            <Briefcase className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-[0.18em]">Portfolio</span>
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)]">
            {data?.name ?? "My Portfolio"}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--ink-soft)]">
            Upload holdings CSV/XLSX from Zerodha or Angel One. Prices refresh every minute from
            stored market data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink-soft)] hover:text-[var(--ink)]"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", busy && "animate-spin")} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            <Upload className="h-3.5 w-3.5" />
            Import holdings
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls,.txt,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="hidden"
            onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: "Invested", value: money(summary?.invested_value) },
          { label: "Current value", value: money(summary?.current_value) },
          {
            label: "Total P&L",
            node: (
              <PnlText value={summary?.total_pnl} pct={summary?.total_pnl_pct ?? null} />
            ),
          },
          {
            label: "Day P&L",
            node: <PnlText value={summary?.day_pnl} />,
          },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3"
          >
            <div className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)]">
              {card.label}
            </div>
            <div className="mt-1 text-lg font-semibold text-[var(--ink)]">
              {"node" in card ? card.node : card.value}
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink-soft)]">
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <span>
            Broker: <strong className="text-[var(--ink)]">{brokerLabel(data?.broker)}</strong>
          </span>
          <span>
            Holdings:{" "}
            <strong className="text-[var(--ink)]">{summary?.holdings_count ?? 0}</strong>
          </span>
          <span>
            Last import:{" "}
            <strong className="text-[var(--ink)]">
              {data?.last_import_at
                ? new Date(data.last_import_at).toLocaleString("en-IN")
                : "—"}
            </strong>
          </span>
          <span>
            Prices as of:{" "}
            <strong className="text-[var(--ink)]">{data?.as_of ?? "—"}</strong>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--ink-muted)]">
            Auto-refresh {Math.round(REFRESH_MS / 1000)}s
            {lastRefresh
              ? ` · ${new Date(lastRefresh).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`
              : ""}
          </span>
          {holdings.length ? (
            <button
              type="button"
              onClick={() => void onClear()}
              disabled={busy}
              className="inline-flex items-center gap-1 text-xs text-[var(--down)] hover:underline"
            >
              <Trash2 className="h-3 w-3" />
              Clear
            </button>
          ) : null}
        </div>
      </div>

      <section className="overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)]">
        <div className="border-b border-[var(--line)] px-4 py-3">
          <h2 className="text-sm font-semibold text-[var(--ink)]">Holdings</h2>
        </div>
        {holdings.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-[var(--ink-muted)]">
            <p>No holdings yet.</p>
            <p className="mt-2">
              Download holdings from{" "}
              <span className="text-[var(--ink-soft)]">Zerodha Console → Holdings → Download</span>{" "}
              or{" "}
              <span className="text-[var(--ink-soft)]">Angel One → Portfolio → Export</span>, then
              import the CSV/XLSX here.
            </p>
            <p className="mt-3 text-xs">
              For automatic folder sync, run{" "}
              <code className="rounded bg-white/5 px-1.5 py-0.5 text-[11px]">
                python scripts/import_broker_holdings.py --watch DIR --client-key …
              </code>
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[var(--surface-muted)] text-[10px] uppercase tracking-wide text-[var(--ink-muted)]">
                <tr>
                  <th className="px-3 py-2 font-medium">Stock</th>
                  <th className="px-3 py-2 font-medium text-right">Qty</th>
                  <th className="px-3 py-2 font-medium text-right">Avg</th>
                  <th className="px-3 py-2 font-medium text-right">LTP</th>
                  <th className="px-3 py-2 font-medium text-right">Invested</th>
                  <th className="px-3 py-2 font-medium text-right">Current</th>
                  <th className="px-3 py-2 font-medium text-right">P&amp;L</th>
                  <th className="px-3 py-2 font-medium text-right">Weight</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((row: PortfolioHolding) => (
                  <tr key={`${row.exchange}-${row.symbol}`} className="border-t border-[var(--line)]">
                    <td className="px-3 py-2.5">
                      <Link
                        href={`/stocks/${encodeURIComponent(row.symbol)}`}
                        className="font-medium text-[var(--ink)] hover:text-[var(--accent-hover)]"
                      >
                        {row.symbol}
                      </Link>
                      <div className="text-[11px] text-[var(--ink-muted)]">{row.name}</div>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--ink-soft)]">
                      {formatNumber(num(row.quantity) ?? 0, { maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--ink-soft)]">
                      {formatPrice(num(row.avg_price))}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--ink)]">
                      {formatPrice(num(row.last_price))}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--ink-soft)]">
                      {money(row.invested_value)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--ink)]">
                      {money(row.current_value)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <PnlText value={row.pnl} pct={row.pnl_pct} />
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--ink-muted)]">
                      {row.weight_pct != null ? `${row.weight_pct.toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {data?.recent_imports?.length ? (
        <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
          <h2 className="mb-2 text-sm font-semibold text-[var(--ink)]">Recent imports</h2>
          <ul className="space-y-2 text-sm text-[var(--ink-soft)]">
            {data.recent_imports.map((imp) => (
              <li key={imp.id} className="flex flex-wrap justify-between gap-2 border-b border-[var(--line)] py-2 last:border-0">
                <span>
                  {imp.filename} · {brokerLabel(imp.broker)} · matched {imp.matched_count}/
                  {imp.row_count}
                </span>
                <span className="text-xs text-[var(--ink-muted)]">
                  {imp.imported_at ? new Date(imp.imported_at).toLocaleString("en-IN") : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
