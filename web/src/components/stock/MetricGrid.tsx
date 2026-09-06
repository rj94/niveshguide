import { cn } from "@/lib/utils";

export type Metric = {
  label: string;
  value: string;
  tone?: "default" | "up" | "down" | "muted";
};

type Props = {
  title: string;
  subtitle?: string;
  metrics: Metric[];
  emptyMessage?: string;
};

export function MetricGrid({ title, subtitle, metrics, emptyMessage }: Props) {
  const hasValues = metrics.some((m) => m.value !== "—");

  return (
    <section className="border-t border-[var(--line)] pt-8">
      <div className="mb-5">
        <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-[var(--ink)]">
          {title}
        </h2>
        {subtitle ? (
          <p className="mt-1 text-sm text-[var(--ink-muted)]">{subtitle}</p>
        ) : null}
      </div>

      {!hasValues ? (
        <p className="text-sm text-[var(--ink-muted)]">
          {emptyMessage ?? "Data not available yet"}
        </p>
      ) : (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-5">
          {metrics.map((metric) => (
            <div key={metric.label}>
              <dt className="text-xs uppercase tracking-[0.16em] text-[var(--ink-muted)]">
                {metric.label}
              </dt>
              <dd
                className={cn(
                  "mt-1 font-[family-name:var(--font-display)] text-xl tabular-nums text-[var(--ink)]",
                  metric.tone === "up" && "text-[var(--up)]",
                  metric.tone === "down" && "text-[var(--down)]",
                  metric.tone === "muted" && "text-[var(--ink-muted)]",
                )}
              >
                {metric.value}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
