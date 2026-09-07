"use client";

import Link from "next/link";
import { LoaderCircle, RotateCcw, Search } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useTransition,
  type FormEvent,
} from "react";

import { PageAd } from "@/components/ads/PageAd";
import { formatCompact, formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listSectors, screenStocks } from "@/services/api";
import type { StockAnalysisRow } from "@/types/stock";

type CapBucket = "" | "large" | "mid" | "small" | "micro";

type Filters = {
  q: string;
  exchange: string;
  marketCap: CapBucket;
  sector: string;
  category: string;
  minMomentum: string;
  minReturn3m: string;
  volumeMover: "any" | "yes" | "no";
  minAccel: string;
};

const INITIAL: Filters = {
  q: "",
  exchange: "NSE",
  marketCap: "",
  sector: "",
  category: "",
  minMomentum: "",
  minReturn3m: "",
  volumeMover: "any",
  minAccel: "",
};

const CAP_OPTIONS: { id: CapBucket; label: string }[] = [
  { id: "", label: "All market caps" },
  { id: "large", label: "Large (> ₹20,000 Cr)" },
  { id: "mid", label: "Mid (₹5,000–20,000 Cr)" },
  { id: "small", label: "Small (₹500–5,000 Cr)" },
  { id: "micro", label: "Micro (< ₹500 Cr)" },
];

const CATEGORIES = [
  { id: "", label: "All categories" },
  { id: "Strong Momentum", label: "Strong (≥85)" },
  { id: "Positive Momentum", label: "Positive (70–85)" },
  { id: "Emerging Momentum", label: "Emerging (55–70)" },
  { id: "Neutral", label: "Neutral (40–55)" },
  { id: "Weak", label: "Weak (20–40)" },
  { id: "Negative", label: "Negative (<20)" },
];

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

/** Market cap stored as Cr on analysis rows. */
function inCapBucket(mcapCr: number | null, bucket: CapBucket): boolean {
  if (!bucket) return true;
  if (mcapCr === null) return false;
  if (bucket === "large") return mcapCr > 20_000;
  if (bucket === "mid") return mcapCr > 5_000 && mcapCr <= 20_000;
  if (bucket === "small") return mcapCr >= 500 && mcapCr <= 5_000;
  if (bucket === "micro") return mcapCr < 500;
  return true;
}

function tonePct(value: number | null): string {
  if (value === null) return "text-[var(--ink-muted)]";
  if (value > 0) return "text-[var(--up)]";
  if (value < 0) return "text-[var(--down)]";
  return "text-[var(--ink-muted)]";
}

export function MomentumWorkspace() {
  const [draft, setDraft] = useState<Filters>(INITIAL);
  const [filters, setFilters] = useState<Filters>(INITIAL);
  const [rows, setRows] = useState<StockAnalysisRow[]>([]);
  const [scanned, setScanned] = useState(0);
  const [sectors, setSectors] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const load = useCallback((next: Filters) => {
    startTransition(async () => {
      try {
        const [data, sectorData] = await Promise.all([
          screenStocks({
            q: next.q.trim() || undefined,
            exchange: next.exchange || undefined,
            min_momentum_score: num(next.minMomentum) ?? undefined,
            min_momentum_acceleration: num(next.minAccel) ?? undefined,
            min_return_3m: num(next.minReturn3m) ?? undefined,
            momentum_category: next.category || undefined,
            volume_mover:
              next.volumeMover === "any" ? undefined : next.volumeMover === "yes",
            sort_by: "momentum_score",
            sort_dir: "desc",
            limit: 400,
            offset: 0,
            scan_limit: 2000,
          }),
          listSectors({ limit: 80, min_constituents: 3 }).catch(() => null),
        ]);
        setRows(data.items);
        setScanned(data.scanned);
        setSectors((sectorData?.items ?? []).map((s) => s.name).filter(Boolean));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load momentum");
        setRows([]);
        setScanned(0);
      }
    });
  }, []);

  useEffect(() => {
    load(filters);
  }, [filters, load]);

  const filtered = useMemo(() => {
    return rows.filter((row) => {
      if (filters.sector && (row.sector || "") !== filters.sector) return false;
      const mcap = num(row.market_cap);
      if (!inCapBucket(mcap, filters.marketCap)) return false;
      return true;
    });
  }, [rows, filters.sector, filters.marketCap]);

  const pageRows = filtered.slice(page * pageSize, page * pageSize + pageSize);
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

  function apply(event: FormEvent) {
    event.preventDefault();
    setPage(0);
    setFilters(draft);
  }

  function reset() {
    setDraft(INITIAL);
    setFilters(INITIAL);
    setPage(0);
  }

  const selectClass =
    "rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] px-2.5 py-2 text-sm text-[var(--ink)]";

  return (
    <div className="space-y-5">
      <header>
        <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-wide text-[var(--ink)] sm:text-4xl">
          Momentum
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Stocks ranked by momentum score (high → low). Filter by market cap, sector, and more.
        </p>
      </header>

      <form
        onSubmit={apply}
        className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4"
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
          <label className="block text-xs text-[var(--ink-muted)]">
            Search
            <div className="relative mt-1">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--ink-muted)]" />
              <input
                value={draft.q}
                onChange={(e) => setDraft((d) => ({ ...d, q: e.target.value }))}
                placeholder="Symbol or name"
                className={cn(selectClass, "w-full pl-8")}
              />
            </div>
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Market cap
            <select
              value={draft.marketCap}
              onChange={(e) =>
                setDraft((d) => ({ ...d, marketCap: e.target.value as CapBucket }))
              }
              className={cn(selectClass, "mt-1 w-full")}
            >
              {CAP_OPTIONS.map((o) => (
                <option key={o.id || "all"} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Sector
            <select
              value={draft.sector}
              onChange={(e) => setDraft((d) => ({ ...d, sector: e.target.value }))}
              className={cn(selectClass, "mt-1 w-full")}
            >
              <option value="">All sectors</option>
              {sectors.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Category
            <select
              value={draft.category}
              onChange={(e) => setDraft((d) => ({ ...d, category: e.target.value }))}
              className={cn(selectClass, "mt-1 w-full")}
            >
              {CATEGORIES.map((o) => (
                <option key={o.id || "all"} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Min momentum
            <input
              type="number"
              min={0}
              max={100}
              value={draft.minMomentum}
              onChange={(e) => setDraft((d) => ({ ...d, minMomentum: e.target.value }))}
              placeholder="e.g. 70"
              className={cn(selectClass, "mt-1 w-full")}
            />
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Min 3M return %
            <input
              type="number"
              value={draft.minReturn3m}
              onChange={(e) => setDraft((d) => ({ ...d, minReturn3m: e.target.value }))}
              placeholder="e.g. 5"
              className={cn(selectClass, "mt-1 w-full")}
            />
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Min acceleration
            <input
              type="number"
              value={draft.minAccel}
              onChange={(e) => setDraft((d) => ({ ...d, minAccel: e.target.value }))}
              placeholder="e.g. 0"
              className={cn(selectClass, "mt-1 w-full")}
            />
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Volume mover
            <select
              value={draft.volumeMover}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  volumeMover: e.target.value as Filters["volumeMover"],
                }))
              }
              className={cn(selectClass, "mt-1 w-full")}
            >
              <option value="any">Any</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </label>

          <label className="block text-xs text-[var(--ink-muted)]">
            Exchange
            <select
              value={draft.exchange}
              onChange={(e) => setDraft((d) => ({ ...d, exchange: e.target.value }))}
              className={cn(selectClass, "mt-1 w-full")}
            >
              <option value="NSE">NSE</option>
              <option value="">All</option>
            </select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="submit"
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:brightness-110"
          >
            Apply filters
          </button>
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] px-3 py-2 text-sm text-[var(--ink-soft)] transition hover:bg-white/[0.04]"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </button>
          <span className="ml-auto text-xs text-[var(--ink-muted)]">
            {pending ? (
              <span className="inline-flex items-center gap-1.5">
                <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                Loading…
              </span>
            ) : (
              `${filtered.length} shown · scanned ${scanned.toLocaleString("en-IN")}`
            )}
          </span>
        </div>
      </form>

      <PageAd page="momentum" />

      {error ? (
        <p className="rounded-lg border border-[var(--down)]/40 bg-[var(--down-soft)] px-4 py-3 text-sm text-[var(--down)]">
          {error}
        </p>
      ) : null}

      <div className="overflow-x-auto rounded-xl border border-[var(--line)] bg-[var(--surface)]">
        <table className="w-full min-w-[920px] text-left text-sm">
          <thead className="border-b border-[var(--line)] text-[11px] uppercase tracking-[0.12em] text-[var(--ink-muted)]">
            <tr>
              <th className="px-3 py-3 font-medium">#</th>
              <th className="px-3 py-3 font-medium">Stock</th>
              <th className="px-3 py-3 font-medium">Sector</th>
              <th className="px-3 py-3 font-medium">Mcap</th>
              <th className="px-3 py-3 font-medium">Score</th>
              <th className="px-3 py-3 font-medium">Category</th>
              <th className="px-3 py-3 font-medium">Accel</th>
              <th className="px-3 py-3 font-medium">1M</th>
              <th className="px-3 py-3 font-medium">3M</th>
              <th className="px-3 py-3 font-medium">LTP</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 && !pending ? (
              <tr>
                <td colSpan={10} className="px-3 py-10 text-center text-[var(--ink-muted)]">
                  No stocks match these filters.
                </td>
              </tr>
            ) : (
              pageRows.map((row, idx) => {
                const rank = page * pageSize + idx + 1;
                const score = num(row.momentum_score ?? row.overall);
                const accel = num(row.momentum_acceleration);
                const r1 = row.return_1m_pct;
                const r3 = row.return_3m_pct;
                return (
                  <tr
                    key={row.symbol}
                    className="border-b border-[var(--line)]/70 transition hover:bg-white/[0.02]"
                  >
                    <td className="px-3 py-2.5 tabular-nums text-[var(--ink-muted)]">{rank}</td>
                    <td className="px-3 py-2.5">
                      <Link
                        href={`/stocks/${encodeURIComponent(row.symbol)}`}
                        className="font-medium text-[var(--ink)] hover:text-[var(--accent-hover)]"
                      >
                        {row.symbol}
                      </Link>
                      <p className="max-w-[180px] truncate text-xs text-[var(--ink-muted)]">
                        {row.company_name}
                      </p>
                    </td>
                    <td className="px-3 py-2.5 text-[var(--ink-soft)]">{row.sector || "—"}</td>
                    <td className="px-3 py-2.5 tabular-nums text-[var(--ink-soft)]">
                      {row.market_cap != null ? `₹${formatCompact(row.market_cap)} Cr` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-lg font-semibold tabular-nums text-[var(--ink)]">
                      {score != null ? Math.round(score) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-[var(--ink-muted)]">
                      {row.momentum_category || "—"}
                    </td>
                    <td className={cn("px-3 py-2.5 tabular-nums", tonePct(accel))}>
                      {accel != null
                        ? `${accel > 0 ? "+" : ""}${formatNumber(accel, { maximumFractionDigits: 1 })}`
                        : "—"}
                    </td>
                    <td className={cn("px-3 py-2.5 tabular-nums", tonePct(r1))}>
                      {formatPct(r1)}
                    </td>
                    <td className={cn("px-3 py-2.5 tabular-nums", tonePct(r3))}>
                      {formatPct(r3)}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-[var(--ink)]">
                      {row.ltp != null ? formatNumber(row.ltp) : "—"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          disabled={page <= 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          className="rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--ink-soft)] disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-xs text-[var(--ink-muted)]">
          Page {page + 1} / {totalPages}
        </span>
        <button
          type="button"
          disabled={page + 1 >= totalPages}
          onClick={() => setPage((p) => p + 1)}
          className="rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--ink-soft)] disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
