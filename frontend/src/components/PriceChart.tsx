import { useMemo, useState } from "react";
import { fmt } from "./StockTable";

export type PricePoint = { date: string; close: number | null };

const RANGES = [
  { id: "3M", days: 63 },
  { id: "6M", days: 126 },
  { id: "1Y", days: 252 },
  { id: "ALL", days: 0 },
] as const;

type RangeId = (typeof RANGES)[number]["id"];

function sliceRange(points: PricePoint[], days: number) {
  const valid = points.filter((point) => point.close != null && Number.isFinite(point.close));
  if (!days || valid.length <= days) return valid;
  return valid.slice(-days);
}

export function PriceChart({ prices }: { prices: PricePoint[] }) {
  const [range, setRange] = useState<RangeId>("1Y");
  const [hover, setHover] = useState<number | null>(null);

  const series = useMemo(() => {
    const days = RANGES.find((item) => item.id === range)?.days ?? 252;
    return sliceRange(prices, days);
  }, [prices, range]);

  const layout = useMemo(() => {
    const width = 720;
    const height = 228;
    const pad = { top: 14, right: 12, bottom: 28, left: 54 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const closes = series.map((point) => point.close as number);
    if (!closes.length) return null;
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const padY = (max - min || max || 1) * 0.08;
    const lo = min - padY;
    const hi = max + padY;
    const span = hi - lo || 1;
    const xAt = (index: number) =>
      pad.left + (series.length === 1 ? innerW / 2 : (index / (series.length - 1)) * innerW);
    const yAt = (close: number) => pad.top + ((hi - close) / span) * innerH;
    const coords = series.map((point, index) => ({
      x: xAt(index),
      y: yAt(point.close as number),
      date: point.date,
      close: point.close as number,
    }));
    const line = coords.map((pt, index) => `${index === 0 ? "M" : "L"}${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`).join(" ");
    const area = `${line} L${coords[coords.length - 1].x.toFixed(2)} ${(pad.top + innerH).toFixed(2)} L${coords[0].x.toFixed(2)} ${(pad.top + innerH).toFixed(2)} Z`;
    const ticks = [hi, (hi + lo) / 2, lo];
    const first = coords[0];
    const last = coords[coords.length - 1];
    const change = first.close ? (last.close - first.close) / first.close : 0;
    return { width, height, pad, innerW, innerH, coords, line, area, ticks, first, last, change, min, max };
  }, [series]);

  if (!layout) return <div className="empty">No price history for this range.</div>;

  const active =
    hover == null || hover >= layout.coords.length
      ? layout.coords[layout.coords.length - 1]
      : layout.coords[hover];
  const up = layout.change >= 0;

  return (
    <div className="price-chart">
      <div className="price-chart-bar">
        <div>
          <div className="price-chart-ltp">
            {fmt(active.close)} <span className={up ? "up" : "down"}>{up ? "+" : ""}{fmt(layout.change * 100)}%</span>
          </div>
          <div className="hint">{active.date} · {series.length} sessions · {fmt(layout.min)} – {fmt(layout.max)}</div>
        </div>
        <div className="price-chart-ranges">
          {RANGES.map((item) => (
            <button key={item.id} className={`chip ${range === item.id ? "on" : ""}`} onClick={() => setRange(item.id)}>
              {item.id}
            </button>
          ))}
        </div>
      </div>
      <svg
        className="price-chart-svg"
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        preserveAspectRatio="xMidYMid meet"
        onMouseLeave={() => setHover(null)}
        onMouseMove={(event) => {
          const box = event.currentTarget.getBoundingClientRect();
          const x = ((event.clientX - box.left) / box.width) * layout.width;
          let nearest = 0;
          let best = Infinity;
          layout.coords.forEach((pt, index) => {
            const dist = Math.abs(pt.x - x);
            if (dist < best) {
              best = dist;
              nearest = index;
            }
          });
          setHover(nearest);
        }}
      >
        {layout.ticks.map((tick) => {
          const y = layout.coords.length
            ? layout.pad.top + ((layout.ticks[0] - tick) / (layout.ticks[0] - layout.ticks[2] || 1)) * layout.innerH
            : 0;
          return (
            <g key={tick}>
              <line x1={layout.pad.left} x2={layout.width - layout.pad.right} y1={y} y2={y} className="chart-grid" />
              <text x={layout.pad.left - 8} y={y + 4} className="chart-axis" textAnchor="end">
                {fmt(tick, 0)}
              </text>
            </g>
          );
        })}
        <text x={layout.pad.left} y={layout.height - 8} className="chart-axis">
          {layout.first.date}
        </text>
        <text x={layout.width - layout.pad.right} y={layout.height - 8} className="chart-axis" textAnchor="end">
          {layout.last.date}
        </text>
        <path d={layout.area} className={up ? "chart-area up" : "chart-area down"} />
        <path d={layout.line} className={up ? "chart-line up" : "chart-line down"} />
        <line x1={active.x} x2={active.x} y1={layout.pad.top} y2={layout.pad.top + layout.innerH} className="chart-cross" />
        <circle cx={active.x} cy={active.y} r="4" className={up ? "chart-dot up" : "chart-dot down"} />
      </svg>
    </div>
  );
}
