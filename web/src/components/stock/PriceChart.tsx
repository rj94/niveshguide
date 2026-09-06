"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";

import type { PriceBar } from "@/types/stock";

type Props = {
  prices: PriceBar[];
};

export function PriceChart({ prices }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#5a6b76",
        fontFamily: "var(--font-body), sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(20, 36, 48, 0.06)" },
        horzLines: { color: "rgba(20, 36, 48, 0.06)" },
      },
      rightPriceScale: {
        borderColor: "rgba(20, 36, 48, 0.12)",
      },
      timeScale: {
        borderColor: "rgba(20, 36, 48, 0.12)",
      },
      crosshair: {
        vertLine: { color: "rgba(11, 110, 79, 0.35)" },
        horzLine: { color: "rgba(11, 110, 79, 0.35)" },
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#0B6E4F",
      downColor: "#B42318",
      borderUpColor: "#0B6E4F",
      borderDownColor: "#B42318",
      wickUpColor: "#0B6E4F",
      wickDownColor: "#B42318",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    const data: CandlestickData<Time>[] = prices.map((bar) => ({
      time: bar.date as Time,
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
    }));
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [prices]);

  if (prices.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center border border-dashed border-[var(--line)] text-sm text-[var(--ink-muted)]">
        No price history available yet
      </div>
    );
  }

  return <div ref={containerRef} className="h-72 w-full md:h-96" />;
}
