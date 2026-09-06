"use client";

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Maximize2 } from "lucide-react";

import type { ChartPoint, ChartStats } from "@/lib/dashboard-data";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

const RANGES = ["1D", "5D", "1M", "6M", "1Y", "5Y", "Max"] as const;

const RANGE_BARS: Record<(typeof RANGES)[number], number | null> = {
  "1D": 2,
  "5D": 5,
  "1M": 22,
  "6M": 126,
  "1Y": 252,
  "5Y": 1260,
  Max: null,
};

type Props = {
  title: string;
  price: number;
  change: number;
  changePct: number;
  points: ChartPoint[];
  stats: ChartStats;
};

export function MainChartCard({
  title,
  price,
  change,
  changePct,
  points,
  stats,
}: Props) {
  const [range, setRange] = useState<(typeof RANGES)[number]>("1M");
  const up = changePct >= 0;
  const stroke = up ? "#10b981" : "#ef4444";
  const prevClose = stats.prevClose;

  const visible = useMemo(() => {
    const n = RANGE_BARS[range];
    if (n === null) return points;
    return points.slice(-n);
  }, [points, range]);

  const domain = useMemo(() => {
    if (visible.length === 0) return [0, 1] as [number, number];
    const values = visible.map((p) => p.value);
    const min = Math.min(...values, prevClose);
    const max = Math.max(...values, prevClose);
    const pad = (max - min) * 0.08 || 20;
    return [Math.floor(min - pad), Math.ceil(max + pad)] as [number, number];
  }, [visible, prevClose]);

  return (
    <article className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-[var(--ink-soft)]">{title}</h2>
          <div className="mt-1 flex flex-wrap items-baseline gap-2">
            <p className="text-2xl font-semibold tabular-nums tracking-tight text-[var(--ink)]">
              {formatNumber(price, { maximumFractionDigits: 2 })}
            </p>
            <p
              className={cn(
                "text-sm tabular-nums",
                up ? "text-[var(--up)]" : "text-[var(--down)]",
              )}
            >
              {up ? "+" : ""}
              {formatNumber(change, { maximumFractionDigits: 2 })} ({formatPct(changePct)})
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <div className="flex items-center rounded-lg bg-[var(--surface-muted)] p-0.5">
            {RANGES.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setRange(item)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium transition",
                  range === item
                    ? "bg-[var(--accent)] text-white"
                    : "text-[var(--ink-muted)] hover:text-[var(--ink)]",
                )}
              >
                {item}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="ml-1 rounded-lg p-2 text-[var(--ink-muted)] transition hover:bg-white/5 hover:text-[var(--ink)]"
            aria-label="Expand chart"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="mt-4 h-[260px] w-full sm:h-[300px]">
        {visible.length < 2 ? (
          <div className="flex h-full items-center justify-center text-sm text-[var(--ink-muted)]">
            No price history available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={visible} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="mainArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="time"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                minTickGap={28}
              />
              <YAxis
                domain={domain}
                tickLine={false}
                axisLine={false}
                width={56}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickFormatter={(v) => formatNumber(v, { maximumFractionDigits: 0 })}
              />
              <Tooltip
                contentStyle={{
                  background: "#151921",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 10,
                  color: "#f3f4f6",
                  fontSize: 12,
                }}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as ChartPoint | undefined;
                  return row?.date ?? "";
                }}
                formatter={(value) => [
                  formatNumber(Number(value), { maximumFractionDigits: 2 }),
                  title,
                ]}
              />
              <ReferenceLine
                y={prevClose}
                stroke="rgba(255,255,255,0.25)"
                strokeDasharray="4 4"
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={stroke}
                strokeWidth={2}
                fill="url(#mainArea)"
                activeDot={{ r: 4, fill: stroke, stroke: "#0b0e14", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-[var(--line)] pt-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          ["Open", stats.open],
          ["High", stats.high],
          ["Low", stats.low],
          ["Prev Close", stats.prevClose],
          ["52W High", stats.high52w],
          ["52W Low", stats.low52w],
        ].map(([label, value]) => (
          <div key={label as string}>
            <dt className="text-[11px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">
              {label}
            </dt>
            <dd className="mt-1 text-sm font-medium tabular-nums text-[var(--ink)]">
              {formatNumber(value as number, { maximumFractionDigits: 2 })}
            </dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
