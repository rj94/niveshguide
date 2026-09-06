"use client";

import { useId } from "react";

type Props = {
  data: number[];
  positive?: boolean;
  width?: number;
  height?: number;
  strokeWidth?: number;
  className?: string;
};

export function Sparkline({
  data,
  positive = true,
  width = 72,
  height = 28,
  strokeWidth = 1.5,
  className,
}: Props) {
  const uid = useId().replace(/:/g, "");
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * (width - pad * 2) + pad;
      const y = height - pad - ((v - min) / range) * (height - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  const color = positive ? "var(--up)" : "var(--down)";
  const fillId = `spark-${uid}`;

  const area = `${pad},${height - pad} ${points} ${width - pad},${height - pad}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${fillId})`} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
