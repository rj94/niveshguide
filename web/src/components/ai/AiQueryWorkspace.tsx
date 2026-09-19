"use client";

import Link from "next/link";
import { Bot, LoaderCircle, Search } from "lucide-react";
import { useEffect, useState, useTransition, type FormEvent } from "react";

import { formatNumber, formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import { askAiQuery, getAiStatus } from "@/services/api";
import type { AiQueryFilter, AiQueryResponse, AiQueryRow } from "@/types/ai";

const SUGGESTED = [
  "Strong momentum stocks with volume expansion",
  "Stocks near 52 week high with trend score 5",
  "Compare TCS and INFY",
  "Banking stocks above 50 DMA and 200 DMA",
] as const;

function formatFilterValue(value: AiQueryFilter["value"]): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}

function PctCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-[var(--ink-muted)]">—</span>;
  }
  return (
    <span
      className={cn(
        "tabular-nums",
        value > 0 ? "text-[var(--up)]" : value < 0 ? "text-[var(--down)]" : "text-[var(--ink-muted)]",
      )}
    >
      {formatPct(value)}
    </span>
  );
}

function NumCell({
  value,
  digits = 1,
}: {
  value: number | null | undefined;
  digits?: number;
}) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-[var(--ink-muted)]">—</span>;
  }
  return (
    <span className="tabular-nums">
      {formatNumber(value, { maximumFractionDigits: digits })}
    </span>
  );
}

function isUnavailableError(message: string): boolean {
  return /ai_disabled|not enabled/i.test(message);
}

export function AiQueryWorkspace() {
  const [query, setQuery] = useState("");
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [result, setResult] = useState<AiQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;
    getAiStatus()
      .then((status) => {
        if (!cancelled) setEnabled(status.enabled);
      })
      .catch(() => {
        if (!cancelled) setEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function run(nextQuery: string) {
    const trimmed = nextQuery.trim();
    if (trimmed.length < 3) {
      setError("Enter at least 3 characters.");
      return;
    }
    setQuery(trimmed);
    startTransition(async () => {
      try {
        const data = await askAiQuery({
          query: trimmed,
          exchange: "NSE",
          limit: 25,
          include_explanation: true,
        });
        setResult(data);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Query failed";
        if (isUnavailableError(message)) {
          setEnabled(false);
          setError(null);
        } else {
          setError(message);
        }
        setResult(null);
      }
    });
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    run(query);
  }

  if (enabled === null) {
    return (
      <div className="space-y-5">
        <Header />
        <div className="flex items-center gap-2 rounded-2xl border border-[var(--line)] bg-[var(--surface)] px-4 py-8 text-sm text-[var(--ink-muted)]">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          Checking whether AI Search is available…
        </div>
      </div>
    );
  }

  if (enabled === false) {
    return (
      <div className="space-y-5">
        <Header />
        <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] px-5 py-10 text-center">
          <Bot className="mx-auto h-8 w-8 text-[var(--ink-muted)]" />
          <h2 className="mt-3 text-lg font-semibold text-[var(--ink)]">AI Search is not available yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-[var(--ink-muted)]">
            This workspace will let you ask natural-language questions about NSE stocks.
            It stays off until the server has AI Search enabled.
          </p>
          <Link
            href="/screener"
            className="mt-5 inline-flex rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
          >
            Open screener
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Header />

      <form onSubmit={onSubmit} className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
        <label htmlFor="ai-query" className="sr-only">
          Ask about NSE stocks
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--ink-muted)]" />
            <input
              id="ai-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask about momentum, sectors, or compare two stocks…"
              maxLength={500}
              className="h-11 w-full rounded-xl border border-[var(--line)] bg-[var(--surface-muted)] pl-10 pr-3 text-sm text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2"
            />
          </div>
          <button
            type="submit"
            disabled={pending || enabled !== true}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-4 text-sm font-medium text-white disabled:opacity-60"
          >
            {pending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
            Ask
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTED.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => run(chip)}
              className="rounded-full border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-1 text-left text-xs text-[var(--ink-soft)] hover:border-[var(--accent)] hover:text-[var(--ink)]"
            >
              {chip}
            </button>
          ))}
        </div>
      </form>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {pending && !result ? (
        <div className="flex items-center gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-8 text-sm text-[var(--ink-muted)]">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          Interpreting your question and fetching matching stocks…
        </div>
      ) : null}

      {result ? <ResultPanel data={result} pending={pending} /> : null}
    </div>
  );
}

function Header() {
  return (
    <header>
      <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-wide text-[var(--ink)] sm:text-4xl">
        AI Search
      </h1>
      <p className="mt-1 max-w-2xl text-sm text-[var(--ink-muted)]">
        Ask a market question in plain English. Answers are grounded in NiveshGuide data and are
        informational only — not financial advice.
      </p>
    </header>
  );
}

function ResultPanel({ data, pending }: { data: AiQueryResponse; pending: boolean }) {
  return (
    <div className={cn("space-y-4", pending && "opacity-70")}>
      <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-muted)]">Answer</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--ink)]">{data.answer}</p>
        <p className="mt-3 text-xs text-[var(--ink-muted)]">{data.interpreted_query}</p>
      </section>

      {data.filters.length > 0 ? (
        <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-muted)]">
            Applied filters
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.filters.map((filter) => (
              <span
                key={`${filter.field}-${filter.operator}-${formatFilterValue(filter.value)}`}
                className="rounded-full border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-1 text-xs text-[var(--ink-soft)]"
              >
                {filter.field} {filter.operator} {formatFilterValue(filter.value)}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {data.warnings.length > 0 ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {data.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--surface)]">
        <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-3">
          <h2 className="text-sm font-medium text-[var(--ink)]">Matching stocks</h2>
          <span className="text-xs text-[var(--ink-muted)]">{data.total} total</span>
        </div>
        {data.rows.length === 0 ? (
          <p className="px-4 py-8 text-sm text-[var(--ink-muted)]">
            No rows matched those filters. Try a broader sector or a lower score threshold.
          </p>
        ) : (
          <div className="dashboard-scroll overflow-x-auto">
            <table className="min-w-[720px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Symbol</th>
                  <th className="px-3 py-2.5 font-medium">Company</th>
                  <th className="px-3 py-2.5 font-medium">Sector</th>
                  <th className="px-3 py-2.5 font-medium">LTP</th>
                  <th className="px-3 py-2.5 font-medium">Trend</th>
                  <th className="px-3 py-2.5 font-medium">Momentum</th>
                  <th className="px-3 py-2.5 font-medium">1M</th>
                  <th className="px-3 py-2.5 font-medium">3M</th>
                  <th className="px-3 py-2.5 font-medium">Vol ratio</th>
                  <th className="px-3 py-2.5 font-medium">P/E</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <ResultRow key={row.symbol} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function ResultRow({ row }: { row: AiQueryRow }) {
  return (
    <tr className="border-t border-[var(--line)]">
      <td className="px-4 py-2.5">
        <Link href={`/stocks/${encodeURIComponent(row.symbol)}`} className="font-medium text-[var(--accent)] hover:underline">
          {row.symbol}
        </Link>
      </td>
      <td className="max-w-[180px] truncate px-3 py-2.5 text-[var(--ink-soft)]" title={row.company_name ?? undefined}>
        {row.company_name || "—"}
      </td>
      <td className="max-w-[140px] truncate px-3 py-2.5 text-[var(--ink-soft)]">{row.sector || "—"}</td>
      <td className="px-3 py-2.5 tabular-nums">{formatPrice(row.ltp)}</td>
      <td className="px-3 py-2.5 tabular-nums">{row.trend_score ?? "—"}</td>
      <td className="px-3 py-2.5">
        <NumCell value={row.momentum_score} />
      </td>
      <td className="px-3 py-2.5">
        <PctCell value={row.return_1m} />
      </td>
      <td className="px-3 py-2.5">
        <PctCell value={row.return_3m} />
      </td>
      <td className="px-3 py-2.5">
        <NumCell value={row.volume_ratio} digits={2} />
      </td>
      <td className="px-3 py-2.5">
        <NumCell value={row.pe} digits={1} />
      </td>
    </tr>
  );
}
