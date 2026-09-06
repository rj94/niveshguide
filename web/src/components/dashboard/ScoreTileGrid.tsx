import type { ReactNode } from "react";
import Link from "next/link";

import { sectorColor } from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

export type ScoreTile = {
  id: string;
  name: string;
  href: string;
  score: number;
  secondary: string | null;
  tertiary?: string | null;
};

type Props = {
  tiles: ScoreTile[];
  emptyText: string;
};

/** Shared colored score tiles for Sector Strength + Sector Rotation. */
export function ScoreTileGrid({ tiles, emptyText }: Props) {
  if (tiles.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-[var(--ink-muted)]">{emptyText}</p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {tiles.map((tile) => (
        <Link
          key={tile.id}
          href={tile.href}
          className="flex min-h-[88px] flex-col justify-between rounded-lg p-2.5 transition hover:brightness-110"
          style={{ background: sectorColor(tile.score) }}
        >
          <span className="line-clamp-2 text-[11px] font-medium leading-tight text-white/95">
            {tile.name}
          </span>
          <span>
            <span className="block text-lg font-semibold tabular-nums text-white">
              {Math.round(tile.score)}
            </span>
            {tile.secondary ? (
              <span className="block text-[10px] capitalize tabular-nums text-white/90">
                {tile.secondary}
              </span>
            ) : null}
            {tile.tertiary ? (
              <span className="block text-[9px] tabular-nums text-white/65">
                {tile.tertiary}
              </span>
            ) : null}
          </span>
        </Link>
      ))}
    </div>
  );
}

export function ScoreCardShell({
  title,
  chip,
  children,
  footer,
}: {
  title: string;
  chip: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <article className="flex h-full flex-col rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">{title}</h2>
        <span
          className={cn(
            "rounded-md border border-[var(--line)] px-2 py-0.5 text-[10px] text-[var(--ink-muted)]",
          )}
        >
          {chip}
        </span>
      </div>
      <div className="min-h-0 flex-1">{children}</div>
      {footer}
    </article>
  );
}
