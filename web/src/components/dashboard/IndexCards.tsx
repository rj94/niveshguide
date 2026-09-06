import { Building2, Flame, Globe2, IndianRupee, LineChart } from "lucide-react";

import { Sparkline } from "@/components/dashboard/Sparkline";
import type { IndexCard } from "@/lib/dashboard-data";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

const ICONS = {
  chart: LineChart,
  bank: Building2,
  flame: Flame,
  currency: IndianRupee,
  globe: Globe2,
} as const;

const KIND_LABEL: Record<string, string> = {
  index: "Index",
  commodity: "Commodity",
  fx: "FX",
  sector: "Sector",
};

type Props = {
  indices: IndexCard[];
};

export function IndexCards({ indices }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {indices.map((card, i) => {
        const up = card.changePct >= 0;
        const Icon = ICONS[card.icon];
        const isSector = card.kind === "sector";
        return (
          <article
            key={card.id}
            className="animate-[fade-up_0.45s_ease_both] rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3.5"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--ink-muted)]">
                  {KIND_LABEL[card.kind] ?? card.kind}
                </p>
                <p className="mt-0.5 truncate text-xs font-medium text-[var(--ink)]">
                  {card.name}
                </p>
              </div>
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                  up ? "bg-[var(--up-soft)] text-[var(--up)]" : "bg-[var(--down-soft)] text-[var(--down)]",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
              </span>
            </div>
            <div className="mt-2 flex items-end justify-between gap-2">
              <div>
                <p className="text-xl font-semibold tabular-nums tracking-tight text-[var(--ink)]">
                  {isSector
                    ? formatNumber(card.value, { maximumFractionDigits: 0 })
                    : formatNumber(card.value, { maximumFractionDigits: 2 })}
                </p>
                <p
                  className={cn(
                    "mt-1 text-xs tabular-nums",
                    up ? "text-[var(--up)]" : "text-[var(--down)]",
                  )}
                >
                  {isSector ? (
                    <>
                      {up ? "+" : ""}
                      {formatNumber(card.change, { maximumFractionDigits: 1 })} score 1W
                      {card.changePct !== 0 ? (
                        <span className="text-[var(--ink-muted)]">
                          {" "}
                          · {formatPct(card.changePct)} ret
                        </span>
                      ) : null}
                    </>
                  ) : (
                    <>
                      {up ? "+" : ""}
                      {formatNumber(card.change, { maximumFractionDigits: 2 })}{" "}
                      ({formatPct(card.changePct)})
                    </>
                  )}
                </p>
              </div>
              {card.sparkline.length > 1 ? (
                <Sparkline data={card.sparkline} positive={up} width={68} height={30} />
              ) : null}
            </div>
          </article>
        );
      })}
    </div>
  );
}
