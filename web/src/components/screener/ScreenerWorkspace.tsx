"use client";

import {
  Columns3,
  Filter,
  LoaderCircle,
  RotateCcw,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useTransition,
  type FormEvent,
} from "react";
import { useSearchParams } from "next/navigation";

import {
  COLUMN_STORAGE_KEY,
  defaultVisibleColumns,
  loadVisibleColumns,
  saveVisibleColumns,
  SCREENER_COLUMNS,
  type ColumnId,
} from "@/lib/screener-columns";
import { cn } from "@/lib/utils";
import { screenStocks } from "@/services/api";
import type { ScreenerQuery, StockAnalysisRow } from "@/types/stock";

type TriState = "any" | "yes" | "no";

type FilterState = {
  q: string;
  exchange: string;
  trend: string;
  minScore: string;
  priceStack: TriState;
  dmaCross: TriState;
  volumeMover: TriState;
  minReturn1m: string;
  minReturn3m: string;
  minReturn6m: string;
  minStrength: string;
  minMomentum: string;
  minAcceleration: string;
  momentumCategory: string;
};

const TREND_SCREENS = [
  { id: "", label: "All scored" },
  { id: "strong-momentum", label: "Strong momentum" },
  { id: "fresh-uptrend", label: "Fresh uptrend" },
  { id: "long-term-uptrend", label: "Long-term uptrend" },
  { id: "breakout-watchlist", label: "Breakout watchlist" },
  { id: "weak-avoid", label: "Weak / avoid" },
] as const;

const MOMENTUM_CATEGORIES = [
  { id: "", label: "All categories" },
  { id: "Strong Momentum", label: "Strong (≥85)" },
  { id: "Positive Momentum", label: "Positive (70–85)" },
  { id: "Emerging Momentum", label: "Emerging (55–70)" },
  { id: "Neutral", label: "Neutral (40–55)" },
  { id: "Weak", label: "Weak (20–40)" },
  { id: "Negative", label: "Negative (<20)" },
] as const;

const INITIAL_FILTERS: FilterState = {
  q: "",
  exchange: "NSE",
  trend: "",
  minScore: "",
  priceStack: "any",
  dmaCross: "any",
  volumeMover: "any",
  minReturn1m: "",
  minReturn3m: "",
  minReturn6m: "",
  minStrength: "",
  minMomentum: "",
  minAcceleration: "",
  momentumCategory: "",
};

function triToBool(value: TriState): boolean | undefined {
  if (value === "yes") return true;
  if (value === "no") return false;
  return undefined;
}

function parseOptionalNumber(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const num = Number(trimmed);
  return Number.isFinite(num) ? num : undefined;
}

function buildQuery(
  filters: FilterState,
  sortBy: string,
  sortDir: "asc" | "desc",
  page: number,
  pageSize: number,
): ScreenerQuery {
  return {
    q: filters.q.trim() || undefined,
    exchange: filters.exchange || undefined,
    price_above_50_above_200: triToBool(filters.priceStack),
    sma_50_above_200: triToBool(filters.dmaCross),
    volume_mover: triToBool(filters.volumeMover),
    min_return_1m: parseOptionalNumber(filters.minReturn1m),
    min_return_3m: parseOptionalNumber(filters.minReturn3m),
    min_return_6m: parseOptionalNumber(filters.minReturn6m),
    min_company_strength: parseOptionalNumber(filters.minStrength),
    min_momentum_score: parseOptionalNumber(filters.minMomentum),
    min_momentum_acceleration: parseOptionalNumber(filters.minAcceleration),
    momentum_category: filters.momentumCategory || undefined,
    trend: filters.trend || undefined,
    min_score: parseOptionalNumber(filters.minScore),
    sort_by: sortBy,
    sort_dir: sortDir,
    limit: pageSize,
    offset: page * pageSize,
    // Cover the NSE ≥ 50 Cr universe so the table stays in sync with DB.
    scan_limit: 2000,
  };
}

export function ScreenerWorkspace() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [draft, setDraft] = useState<FilterState>(INITIAL_FILTERS);
  const [visible, setVisible] = useState<ColumnId[]>(defaultVisibleColumns);
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [sortBy, setSortBy] = useState(() => searchParams.get("sort_by") || "momentum_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">(() => {
    const raw = searchParams.get("sort_dir");
    if (raw === "asc" || raw === "desc") return raw;
    return searchParams.get("sort_by") === "change_pct" && raw !== "desc" ? "desc" : "desc";
  });
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const [rows, setRows] = useState<StockAnalysisRow[]>([]);
  const [total, setTotal] = useState(0);
  const [scanned, setScanned] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    setVisible(loadVisibleColumns());
    const urlSort = searchParams.get("sort_by");
    const urlDir = searchParams.get("sort_dir");
    if (urlSort) {
      setSortBy(urlSort === "trend_score" || urlSort === "score" ? "momentum_score" : urlSort);
    } else {
      setSortBy((prev) => (prev === "trend_score" || prev === "score" ? "momentum_score" : prev));
    }
    if (urlDir === "asc" || urlDir === "desc") setSortDir(urlDir);
  }, [searchParams]);

  const activeColumns = useMemo(() => {
    const order = new Map(SCREENER_COLUMNS.map((c, i) => [c.id, i]));
    return SCREENER_COLUMNS.filter((c) => visible.includes(c.id)).sort(
      (a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0),
    );
  }, [visible]);

  const load = useCallback(
    (nextFilters: FilterState, nextSortBy: string, nextSortDir: "asc" | "desc", nextPage: number) => {
      startTransition(async () => {
        try {
          const data = await screenStocks(
            buildQuery(nextFilters, nextSortBy, nextSortDir, nextPage, pageSize),
          );
          setRows(data.items);
          setTotal(data.total);
          setScanned(data.scanned);
          setError(null);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load screener");
          setRows([]);
          setTotal(0);
          setScanned(0);
        }
      });
    },
    [],
  );

  useEffect(() => {
    load(filters, sortBy, sortDir, page);
  }, [filters, sortBy, sortDir, page, load]);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setPage(0);
    setFilters(draft);
  }

  function resetFilters() {
    setDraft(INITIAL_FILTERS);
    setPage(0);
    setFilters(INITIAL_FILTERS);
    setSortBy("momentum_score");
    setSortDir("desc");
  }

  function toggleColumn(id: ColumnId) {
    if (id === "stock") return;
    setVisible((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      const ensured = next.includes("stock") ? next : (["stock", ...next] as ColumnId[]);
      saveVisibleColumns(ensured);
      return ensured;
    });
  }

  function resetColumns() {
    const defaults = defaultVisibleColumns();
    setVisible(defaults);
    saveVisibleColumns(defaults);
  }

  function onSort(columnId: ColumnId) {
    const col = SCREENER_COLUMNS.find((c) => c.id === columnId);
    if (!col?.sortable || !col.sortKey) return;
    if (sortBy === col.sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col.sortKey);
      setSortDir(col.sortKey === "symbol" ? "asc" : "desc");
    }
    setPage(0);
  }

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent)]">
            Market table
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl tracking-wide text-[var(--ink)] sm:text-4xl">
            Stock Screener
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-[var(--ink-soft)]">
            {total} matching names. Strong momentum requires all five trend
            conditions; breakout is within 5% of the 52-week high.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setFiltersOpen((v) => !v)}
            className={cn(
              "inline-flex items-center gap-2 border px-3 py-2 text-sm transition",
              filtersOpen
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]"
                : "border-[var(--line)] bg-[var(--surface)]/80 text-[var(--ink-soft)] hover:border-[var(--accent)]",
            )}
          >
            <Filter className="h-4 w-4" />
            Filters
          </button>
          <button
            type="button"
            onClick={() => setColumnsOpen((v) => !v)}
            className={cn(
              "inline-flex items-center gap-2 border px-3 py-2 text-sm transition",
              columnsOpen
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]"
                : "border-[var(--line)] bg-[var(--surface)]/80 text-[var(--ink-soft)] hover:border-[var(--accent)]",
            )}
          >
            <Columns3 className="h-4 w-4" />
            Columns
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {TREND_SCREENS.map((screen) => (
          <button
            key={screen.id || "all"}
            type="button"
            onClick={() => {
              setFilters((f) => ({ ...f, trend: screen.id }));
              setDraft((f) => ({ ...f, trend: screen.id }));
              setPage(0);
            }}
            className={cn(
              "border px-3 py-1.5 text-xs uppercase tracking-[0.12em] transition",
              filters.trend === screen.id
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]"
                : "border-[var(--line)] text-[var(--ink-muted)] hover:border-[var(--accent)]",
            )}
          >
            {screen.label}
          </button>
        ))}
        <select
          value={filters.minScore}
          onChange={(e) => {
            const minScore = e.target.value;
            setFilters((f) => ({ ...f, minScore }));
            setDraft((f) => ({ ...f, minScore }));
            setPage(0);
          }}
          className="border border-[var(--line)] bg-[var(--background)] px-2 py-1.5 text-sm text-[var(--ink)]"
        >
          <option value="">Min trend 0–5</option>
          {[5, 4, 3, 2, 1, 0].map((score) => (
            <option key={score} value={score}>
              ≥ {score}
            </option>
          ))}
        </select>
        <select
          value={filters.minMomentum}
          onChange={(e) => {
            const minMomentum = e.target.value;
            setFilters((f) => ({ ...f, minMomentum }));
            setDraft((f) => ({ ...f, minMomentum }));
            setPage(0);
          }}
          className="border border-[var(--line)] bg-[var(--background)] px-2 py-1.5 text-sm text-[var(--ink)]"
        >
          <option value="">Min momentum</option>
          {[85, 70, 55, 40].map((score) => (
            <option key={score} value={score}>
              ≥ {score}
            </option>
          ))}
        </select>
        <select
          value={filters.minAcceleration}
          onChange={(e) => {
            const minAcceleration = e.target.value;
            setFilters((f) => ({ ...f, minAcceleration }));
            setDraft((f) => ({ ...f, minAcceleration }));
            setPage(0);
          }}
          className="border border-[var(--line)] bg-[var(--background)] px-2 py-1.5 text-sm text-[var(--ink)]"
        >
          <option value="">Min accel</option>
          {[15, 5, 0, -5].map((score) => (
            <option key={score} value={score}>
              ≥ {score}
            </option>
          ))}
        </select>
        <select
          value={filters.momentumCategory}
          onChange={(e) => {
            const momentumCategory = e.target.value;
            setFilters((f) => ({ ...f, momentumCategory }));
            setDraft((f) => ({ ...f, momentumCategory }));
            setPage(0);
          }}
          className="border border-[var(--line)] bg-[var(--background)] px-2 py-1.5 text-sm text-[var(--ink)]"
        >
          {MOMENTUM_CATEGORIES.map((cat) => (
            <option key={cat.id || "all-cat"} value={cat.id}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>

      {filtersOpen ? (
        <form
          onSubmit={applyFilters}
          className="animate-[fade-up_0.35s_ease_both] border border-[var(--line)] bg-[var(--surface)]/75 p-4"
        >
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[var(--ink-muted)]">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filter rows
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="block text-sm">
              <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
                Search
              </span>
              <span className="relative block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--ink-muted)]" />
                <input
                  value={draft.q}
                  onChange={(e) => setDraft((f) => ({ ...f, q: e.target.value }))}
                  placeholder="Symbol or company"
                  className="w-full border border-[var(--line)] bg-[var(--background)] py-2 pl-9 pr-3 text-[var(--ink)] outline-none focus:border-[var(--accent)]"
                />
              </span>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
                Exchange
              </span>
              <select
                value={draft.exchange}
                onChange={(e) => setDraft((f) => ({ ...f, exchange: e.target.value }))}
                className="w-full border border-[var(--line)] bg-[var(--background)] px-3 py-2 text-[var(--ink)] outline-none focus:border-[var(--accent)]"
              >
                <option value="NSE">NSE</option>
                <option value="">All</option>
              </select>
            </label>
            <TriSelect
              label="Price > 50 > 200"
              value={draft.priceStack}
              onChange={(priceStack) => setDraft((f) => ({ ...f, priceStack }))}
            />
            <TriSelect
              label="50 > 200 DMA"
              value={draft.dmaCross}
              onChange={(dmaCross) => setDraft((f) => ({ ...f, dmaCross }))}
            />
            <TriSelect
              label="Volume mover"
              value={draft.volumeMover}
              onChange={(volumeMover) => setDraft((f) => ({ ...f, volumeMover }))}
            />
            <NumberField
              label="Min 1M return %"
              value={draft.minReturn1m}
              onChange={(minReturn1m) => setDraft((f) => ({ ...f, minReturn1m }))}
            />
            <NumberField
              label="Min 3M return %"
              value={draft.minReturn3m}
              onChange={(minReturn3m) => setDraft((f) => ({ ...f, minReturn3m }))}
            />
            <NumberField
              label="Min 6M return %"
              value={draft.minReturn6m}
              onChange={(minReturn6m) => setDraft((f) => ({ ...f, minReturn6m }))}
            />
            <NumberField
              label="Min company strength"
              value={draft.minStrength}
              onChange={(minStrength) => setDraft((f) => ({ ...f, minStrength }))}
            />
            <NumberField
              label="Min momentum score"
              value={draft.minMomentum}
              onChange={(minMomentum) => setDraft((f) => ({ ...f, minMomentum }))}
            />
            <NumberField
              label="Min acceleration"
              value={draft.minAcceleration}
              onChange={(minAcceleration) => setDraft((f) => ({ ...f, minAcceleration }))}
            />
            <label className="block text-sm">
              <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
                Momentum category
              </span>
              <select
                value={draft.momentumCategory}
                onChange={(e) => setDraft((f) => ({ ...f, momentumCategory: e.target.value }))}
                className="w-full border border-[var(--line)] bg-[var(--background)] px-3 py-2 text-[var(--ink)] outline-none focus:border-[var(--accent)]"
              >
                {MOMENTUM_CATEGORIES.map((cat) => (
                  <option key={cat.id || "all-cat-draft"} value={cat.id}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="submit"
              className="border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-sm text-white transition hover:opacity-90"
            >
              Apply filters
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="inline-flex items-center gap-2 border border-[var(--line)] bg-[var(--background)] px-4 py-2 text-sm text-[var(--ink-soft)] transition hover:border-[var(--accent)]"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </button>
          </div>
        </form>
      ) : null}

      {columnsOpen ? (
        <div className="animate-[fade-up_0.35s_ease_both] border border-[var(--line)] bg-[var(--surface)]/75 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--ink-muted)]">
              Customize columns
            </p>
            <button
              type="button"
              onClick={resetColumns}
              className="text-xs uppercase tracking-[0.14em] text-[var(--accent)] hover:underline"
            >
              Restore defaults
            </button>
          </div>
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {SCREENER_COLUMNS.map((col) => {
              const checked = visible.includes(col.id);
              const locked = col.id === "stock";
              return (
                <li key={col.id}>
                  <label
                    className={cn(
                      "flex cursor-pointer items-start gap-3 border px-3 py-2 transition",
                      checked
                        ? "border-[var(--accent)]/50 bg-[var(--accent-soft)]/40"
                        : "border-[var(--line)] bg-[var(--background)]/60",
                      locked && "opacity-80",
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={locked}
                      onChange={() => toggleColumn(col.id)}
                      className="mt-1 accent-[var(--accent)]"
                    />
                    <span>
                      <span className="block text-sm text-[var(--ink)]">{col.label}</span>
                      {col.description ? (
                        <span className="mt-0.5 block text-xs text-[var(--ink-muted)]">
                          {col.description}
                        </span>
                      ) : null}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-[var(--ink-muted)]">
            Preferences saved in local storage ({COLUMN_STORAGE_KEY}). New
            metrics register in <code className="text-[var(--ink-soft)]">screener-columns.tsx</code>.
          </p>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-[var(--ink-muted)]">
        <p>
          {pending ? (
            <span className="inline-flex items-center gap-2">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Computing metrics…
            </span>
          ) : (
            <>
              Showing {rows.length} of {total} stocks
              {rows[0]?.as_of ? ` · as of ${rows[0].as_of}` : null}
              {scanned && scanned !== total ? ` · scanned ${scanned}` : null}
            </>
          )}
        </p>
        <p className="text-xs uppercase tracking-[0.14em]">
          Sort: {sortBy} · {sortDir}
        </p>
      </div>

      {error ? (
        <div className="border border-[var(--down)]/30 bg-[var(--surface)] px-4 py-3 text-sm text-[var(--down)]">
          {error}
        </div>
      ) : null}

      <div className="overflow-x-auto border border-[var(--line)] bg-[var(--surface)]/80">
        <table className="min-w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] bg-[var(--surface-muted)]/70">
              {activeColumns.map((col) => {
                const active = col.sortKey === sortBy;
                return (
                  <th
                    key={col.id}
                    style={col.minWidth ? { minWidth: col.minWidth } : undefined}
                    className={cn(
                      "whitespace-nowrap px-3 py-3 text-xs font-medium uppercase tracking-[0.12em] text-[var(--ink-muted)]",
                      col.align === "right" && "text-right",
                      col.align === "center" && "text-center",
                      col.align === "left" && "text-left",
                      !col.align && "text-left",
                    )}
                  >
                    {col.sortable ? (
                      <button
                        type="button"
                        onClick={() => onSort(col.id)}
                        className={cn(
                          "inline-flex items-center gap-1 transition hover:text-[var(--ink)]",
                          active && "text-[var(--ink)]",
                        )}
                      >
                        {col.shortLabel ?? col.label}
                        {active ? (
                          <span aria-hidden>{sortDir === "asc" ? "↑" : "↓"}</span>
                        ) : null}
                      </button>
                    ) : (
                      (col.shortLabel ?? col.label)
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !pending ? (
              <tr>
                <td
                  colSpan={activeColumns.length}
                  className="px-4 py-10 text-center text-[var(--ink-muted)]"
                >
                  No stocks match these filters.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={`${row.exchange}-${row.symbol}`}
                  className="border-b border-[var(--line)]/70 transition hover:bg-[var(--accent-soft)]/25"
                >
                  {activeColumns.map((col) => (
                    <td
                      key={col.id}
                      className={cn(
                        "px-3 py-3 align-middle",
                        col.align === "right" && "text-right",
                        col.align === "center" && "text-center",
                      )}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          disabled={page <= 0 || pending}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          className="border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink-soft)] transition enabled:hover:border-[var(--accent)] disabled:opacity-40"
        >
          Previous
        </button>
        <p className="text-sm text-[var(--ink-muted)]">
          Page {page + 1} of {pageCount}
        </p>
        <button
          type="button"
          disabled={page + 1 >= pageCount || pending}
          onClick={() => setPage((p) => p + 1)}
          className="border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink-soft)] transition enabled:hover:border-[var(--accent)] disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function TriSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: TriState;
  onChange: (value: TriState) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as TriState)}
        className="w-full border border-[var(--line)] bg-[var(--background)] px-3 py-2 text-[var(--ink)] outline-none focus:border-[var(--accent)]"
      >
        <option value="any">Any</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
        {label}
      </span>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-[var(--line)] bg-[var(--background)] px-3 py-2 text-[var(--ink)] outline-none focus:border-[var(--accent)]"
      />
    </label>
  );
}
