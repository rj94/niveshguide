import Link from "next/link";
import type { ReactNode } from "react";

import { formatCompact, formatNumber, formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { StockAnalysisRow } from "@/types/stock";

/**
 * Extensible screener column registry.
 *
 * To add a column:
 * 1. Add the field on StockAnalysisRow (backend schema + service + frontend type)
 * 2. Append a ColumnDef here with id, label, accessor/render, filter, defaultVisible
 * 3. Optionally map sort_by on the /screener API
 */
export type ColumnId =
  | "stock"
  | "sector"
  | "industry"
  | "ltp"
  | "momentum_score"
  | "momentum_category"
  | "momentum_acceleration"
  | "return_score"
  | "dma_score"
  | "volume_score"
  | "result_score"
  | "trend_score"
  | "sma_3"
  | "sma_7"
  | "sma_21"
  | "sma_50"
  | "sma_200"
  | "crossover_3_7"
  | "above_ma_21"
  | "above_ma_200"
  | "price_stack"
  | "dma_cross"
  | "volume_mover"
  | "return_1m"
  | "return_3m"
  | "return_6m"
  | "distance_52w"
  | "pe"
  | "eps"
  | "market_cap"
  | "trend"
  | "company_strength";

export type ColumnDef = {
  id: ColumnId;
  label: string;
  shortLabel?: string;
  description?: string;
  defaultVisible: boolean;
  align?: "left" | "right" | "center";
  sortable?: boolean;
  sortKey?: string;
  minWidth?: string;
  render: (row: StockAnalysisRow) => ReactNode;
};

function BoolCell({ value }: { value: boolean | null }) {
  if (value === null) {
    return <span className="text-[var(--ink-muted)]">—</span>;
  }
  return (
    <span
      className={cn(
        "text-xs font-medium uppercase tracking-[0.12em]",
        value ? "text-[var(--up)]" : "text-[var(--ink-muted)]",
      )}
    >
      {value ? "Yes" : "No"}
    </span>
  );
}

function PctCell({ value }: { value: number | null }) {
  return (
    <span
      className={cn(
        "tabular-nums",
        value == null
          ? "text-[var(--ink-muted)]"
          : value >= 0
            ? "text-[var(--up)]"
            : "text-[var(--down)]",
      )}
    >
      {formatPct(value)}
    </span>
  );
}

export const SCREENER_COLUMNS: ColumnDef[] = [
  {
    id: "stock",
    label: "Stock",
    description: "Symbol and company",
    defaultVisible: true,
    align: "left",
    sortable: true,
    sortKey: "symbol",
    minWidth: "11rem",
    render: (row) => (
      <Link
        href={`/stocks/${encodeURIComponent(row.symbol)}?exchange=${row.exchange}`}
        className="group block min-w-0"
      >
        <span className="font-[family-name:var(--font-display)] tracking-wide text-[var(--ink)] group-hover:text-[var(--accent)]">
          {row.symbol}
        </span>
        <span className="mt-0.5 block truncate text-xs text-[var(--ink-muted)]">
          {row.company_name}
          <span className="ml-1 text-[var(--ink-muted)]/80">· {row.exchange}</span>
        </span>
      </Link>
    ),
  },
  {
    id: "sector",
    label: "Sector",
    description: "Screener.in sector classification",
    defaultVisible: true,
    align: "left",
    sortable: true,
    sortKey: "sector",
    minWidth: "9rem",
    render: (row) =>
      row.sector ? (
        <Link
          href={`/sectors/sector/${encodeURIComponent(row.sector)}`}
          className="text-[var(--ink-soft)] hover:text-[var(--accent)]"
        >
          {row.sector}
        </Link>
      ) : (
        <span className="text-[var(--ink-muted)]">—</span>
      ),
  },
  {
    id: "industry",
    label: "Industry",
    description: "Screener.in industry classification",
    defaultVisible: false,
    align: "left",
    sortable: true,
    sortKey: "industry",
    minWidth: "10rem",
    render: (row) =>
      row.industry ? (
        <Link
          href={`/sectors/industry/${encodeURIComponent(row.industry)}`}
          className="text-[var(--ink-soft)] hover:text-[var(--accent)]"
        >
          {row.industry}
        </Link>
      ) : (
        <span className="text-[var(--ink-muted)]">—</span>
      ),
  },
  {
    id: "ltp",
    label: "LTP",
    description: "Last traded price",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "ltp",
    render: (row) => (
      <div className="text-right">
        <div className="tabular-nums text-[var(--ink)]">{formatPrice(row.ltp)}</div>
        <div
          className={cn(
            "text-xs tabular-nums",
            (row.change_pct ?? 0) >= 0 ? "text-[var(--up)]" : "text-[var(--down)]",
          )}
        >
          {formatPct(row.change_pct)}
        </div>
      </div>
    ),
  },
  {
    id: "momentum_score",
    label: "Score",
    shortLabel: "Score",
    description: "Momentum score 0–100 (returns + DMA + volume + results)",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "momentum_score",
    render: (row) => {
      const score =
        row.momentum_score != null
          ? Number(row.momentum_score)
          : row.overall != null
            ? Number(row.overall)
            : null;
      return (
        <div className="text-right">
          <span className="font-[family-name:var(--font-display)] tabular-nums text-[var(--accent)]">
            {score != null && !Number.isNaN(score)
              ? formatNumber(score, { maximumFractionDigits: 0 })
              : "—"}
          </span>
          {row.momentum_category ? (
            <span className="mt-0.5 block text-[10px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">
              {row.momentum_category}
            </span>
          ) : null}
        </div>
      );
    },
  },
  {
    id: "momentum_category",
    label: "Category",
    description: "Momentum classification band",
    defaultVisible: false,
    align: "left",
    sortable: false,
    render: (row) => (
      <span className="text-[var(--ink-soft)]">{row.momentum_category ?? "—"}</span>
    ),
  },
  {
    id: "momentum_acceleration",
    label: "Accel",
    shortLabel: "Accel",
    description: "Momentum score change vs 20 sessions ago",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "momentum_acceleration",
    render: (row) => {
      const n = row.momentum_acceleration != null ? Number(row.momentum_acceleration) : null;
      return (
        <span
          className={cn(
            "tabular-nums",
            n == null
              ? "text-[var(--ink-muted)]"
              : n >= 0
                ? "text-[var(--up)]"
                : "text-[var(--down)]",
          )}
        >
          {n == null
            ? "—"
            : `${n > 0 ? "+" : ""}${formatNumber(n, { maximumFractionDigits: 1 })}`}
        </span>
      );
    },
  },
  {
    id: "return_score",
    label: "Return score",
    description: "Returns momentum component 0–100",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "return_score",
    render: (row) => (
      <span className="tabular-nums">
        {row.return_score != null
          ? formatNumber(row.return_score, { maximumFractionDigits: 0 })
          : "—"}
      </span>
    ),
  },
  {
    id: "dma_score",
    label: "DMA score",
    description: "Trend / DMA component 0–100",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "dma_score",
    render: (row) => (
      <span className="tabular-nums">
        {row.dma_score != null ? formatNumber(row.dma_score, { maximumFractionDigits: 0 }) : "—"}
      </span>
    ),
  },
  {
    id: "volume_score",
    label: "Vol score",
    description: "Volume momentum component 0–100",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "volume_score",
    render: (row) => (
      <span className="tabular-nums">
        {row.volume_score != null
          ? formatNumber(row.volume_score, { maximumFractionDigits: 0 })
          : "—"}
      </span>
    ),
  },
  {
    id: "result_score",
    label: "Result score",
    description: "Fundamental / results component 0–100",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "result_score",
    render: (row) => (
      <span className="tabular-nums">
        {row.result_score != null
          ? formatNumber(row.result_score, { maximumFractionDigits: 0 })
          : "—"}
      </span>
    ),
  },
  {
    id: "trend_score",
    label: "Trend 0–5",
    description: "Trade trend score 0–5",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "trend_score",
    render: (row) => (
      <span className="font-[family-name:var(--font-display)] tabular-nums text-[var(--accent)]">
        {row.trend_score != null ? row.trend_score : "—"}
      </span>
    ),
  },
  {
    id: "sma_3",
    label: "3D MA",
    description: "3-day moving average from StockFilter",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "sma_3",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">{formatPrice(row.sma_3)}</span>
    ),
  },
  {
    id: "sma_7",
    label: "7D MA",
    description: "7-day moving average from StockFilter",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "sma_7",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">{formatPrice(row.sma_7)}</span>
    ),
  },
  {
    id: "sma_21",
    label: "21 DMA",
    shortLabel: "21 DMA",
    description: "21-day moving average",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "sma_21",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">{formatPrice(row.sma_21)}</span>
    ),
  },
  {
    id: "sma_50",
    label: "50 DMA",
    description: "50-day moving average",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "sma_50",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">{formatPrice(row.sma_50)}</span>
    ),
  },
  {
    id: "sma_200",
    label: "200 DMA",
    description: "200-day moving average",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "sma_200",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">{formatPrice(row.sma_200)}</span>
    ),
  },
  {
    id: "crossover_3_7",
    label: "3D > 7D",
    shortLabel: "3>7",
    description: "3-day MA above 7-day MA",
    defaultVisible: true,
    align: "center",
    render: (row) => <BoolCell value={row.crossover_3_7} />,
  },
  {
    id: "above_ma_21",
    label: "LTP > 21D",
    shortLabel: ">21",
    description: "Price above 21-day MA",
    defaultVisible: true,
    align: "center",
    render: (row) => <BoolCell value={row.above_ma_21} />,
  },
  {
    id: "above_ma_200",
    label: "LTP > 200D",
    shortLabel: ">200",
    description: "Price above 200-day MA",
    defaultVisible: false,
    align: "center",
    render: (row) => <BoolCell value={row.above_ma_200} />,
  },
  {
    id: "price_stack",
    label: "Price > 50 > 200",
    shortLabel: "P>50>200",
    description: "Stock price above 50 DMA and 50 DMA above 200 DMA",
    defaultVisible: true,
    align: "center",
    render: (row) => <BoolCell value={row.price_above_50_above_200} />,
  },
  {
    id: "dma_cross",
    label: "50 > 200 DMA",
    shortLabel: "50>200",
    description: "50 DMA above 200 DMA",
    defaultVisible: true,
    align: "center",
    render: (row) => <BoolCell value={row.sma_50_above_200} />,
  },
  {
    id: "volume_mover",
    label: "Volume Mover",
    description: "Latest volume vs 3M average (≥1.5x)",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "volume_ratio",
    render: (row) => (
      <div className="text-right">
        <div
          className={cn(
            "tabular-nums",
            row.volume_mover ? "text-[var(--accent)]" : "text-[var(--ink-soft)]",
          )}
        >
          {row.volume_ratio != null ? `${row.volume_ratio.toFixed(2)}x` : "—"}
        </div>
        <div className="text-xs text-[var(--ink-muted)]">
          {row.volume != null ? formatCompact(row.volume) : "—"}
        </div>
      </div>
    ),
  },
  {
    id: "return_1m",
    label: "1M Return",
    description: "1-month price return",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "return_1m_pct",
    render: (row) => <PctCell value={row.return_1m_pct} />,
  },
  {
    id: "return_3m",
    label: "3M Return",
    description: "3-month price return",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "return_3m_pct",
    render: (row) => <PctCell value={row.return_3m_pct} />,
  },
  {
    id: "return_6m",
    label: "6M Return",
    description: "6-month price return",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "return_6m_pct",
    render: (row) => <PctCell value={row.return_6m_pct} />,
  },
  {
    id: "distance_52w",
    label: "52W dist",
    description: "Distance from 52-week high (%)",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "distance_from_52w_high",
    render: (row) => <PctCell value={row.distance_from_52w_high} />,
  },
  {
    id: "pe",
    label: "PE",
    description: "PE from StockFilter",
    defaultVisible: true,
    align: "right",
    sortable: true,
    sortKey: "pe",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">
        {formatNumber(row.pe, { maximumFractionDigits: 2 })}
      </span>
    ),
  },
  {
    id: "eps",
    label: "EPS",
    description: "EPS from StockFilter",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "eps",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">
        {formatNumber(row.eps, { maximumFractionDigits: 2 })}
      </span>
    ),
  },
  {
    id: "market_cap",
    label: "MCap (Cr)",
    shortLabel: "MCap",
    description: "Market cap from StockFilter",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "market_cap",
    render: (row) => (
      <span className="tabular-nums text-[var(--ink-soft)]">
        {formatNumber(row.market_cap, { maximumFractionDigits: 2 })}
      </span>
    ),
  },
  {
    id: "trend",
    label: "Trend",
    description: "Trade trend label and 0–5 score",
    defaultVisible: false,
    align: "left",
    sortable: true,
    sortKey: "trend_score",
    render: (row) => (
      <div>
        <div className="text-[var(--ink)]">{row.trend ?? "—"}</div>
        <div className="text-xs text-[var(--ink-muted)]">
          {row.trend_score != null ? `trend ${row.trend_score}/5` : "—"}
        </div>
      </div>
    ),
  },
  {
    id: "company_strength",
    label: "Company Strength",
    shortLabel: "Strength",
    description: "Mapped from Trade trend score (0–5 → 0–100)",
    defaultVisible: false,
    align: "right",
    sortable: true,
    sortKey: "company_strength",
    render: (row) => (
      <div className="text-right">
        <div className="font-[family-name:var(--font-display)] tabular-nums text-[var(--ink)]">
          {row.company_strength != null
            ? formatNumber(row.company_strength, { maximumFractionDigits: 1 })
            : "—"}
        </div>
        <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--ink-muted)]">
          {row.company_strength_source === "trade_trend_score"
            ? "Trend"
            : row.company_strength_source === "engine"
              ? "Engine"
              : row.company_strength_source === "price_derived"
                ? "Provisional"
                : "—"}
        </div>
      </div>
    ),
  },
];

export const COLUMN_STORAGE_KEY = "screener.visibleColumns.v6";

export function defaultVisibleColumns(): ColumnId[] {
  return SCREENER_COLUMNS.filter((c) => c.defaultVisible).map((c) => c.id);
}

export function loadVisibleColumns(): ColumnId[] {
  if (typeof window === "undefined") return defaultVisibleColumns();
  try {
    const raw = window.localStorage.getItem(COLUMN_STORAGE_KEY);
    if (!raw) return defaultVisibleColumns();
    const parsed = JSON.parse(raw) as string[];
    const valid = new Set(SCREENER_COLUMNS.map((c) => c.id));
    const ids = parsed.filter((id): id is ColumnId => valid.has(id as ColumnId));
    // Stock column is always kept for context
    if (!ids.includes("stock")) ids.unshift("stock");
    // Momentum Score (0–100) must stay visible as the primary score
    if (!ids.includes("momentum_score")) {
      const ltpIdx = ids.indexOf("ltp");
      ids.splice(ltpIdx >= 0 ? ltpIdx + 1 : 1, 0, "momentum_score");
    }
    // Drop legacy 0–5 score column from saved prefs
    const cleaned = ids.filter((id) => id !== "trend_score");
    return cleaned.length ? cleaned : defaultVisibleColumns();
  } catch {
    return defaultVisibleColumns();
  }
}

export function saveVisibleColumns(ids: ColumnId[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(COLUMN_STORAGE_KEY, JSON.stringify(ids));
}
