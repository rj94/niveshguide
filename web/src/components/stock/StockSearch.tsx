"use client";

import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  useTransition,
  type FormEvent,
} from "react";
import { Search } from "lucide-react";

import { formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listStocks } from "@/services/api";
import type { StockSummary } from "@/types/stock";

type Props = {
  initialQuery?: string;
  className?: string;
};

export function StockSearch({ initialQuery = "", className }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<StockSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const wrapRef = useRef<HTMLDivElement>(null);
  // Only fetch/open dropdown after the user edits the field (not on page mount).
  const userEditedRef = useRef(false);

  useEffect(() => {
    setQuery(initialQuery);
    userEditedRef.current = false;
    setOpen(false);
    setResults([]);
  }, [initialQuery]);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  useEffect(() => {
    if (!userEditedRef.current) return;

    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }

    const handle = window.setTimeout(() => {
      startTransition(async () => {
        try {
          const data = await listStocks({ q, limit: 8 });
          setResults(data.items);
          setError(null);
          setOpen(true);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Search failed");
          setResults([]);
          setOpen(true);
        }
      });
    }, 220);

    return () => window.clearTimeout(handle);
  }, [query]);

  function goTo(symbol: string, exchange: string) {
    setOpen(false);
    userEditedRef.current = false;
    router.push(`/stocks/${encodeURIComponent(symbol)}?exchange=${exchange}`);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const first = results[0];
    if (first) {
      goTo(first.symbol, first.exchange);
      return;
    }
    const q = query.trim().toUpperCase();
    if (q) {
      setOpen(false);
      userEditedRef.current = false;
      router.push(`/stocks/${encodeURIComponent(q)}`);
    }
  }

  return (
    <div ref={wrapRef} className={cn("relative z-50 w-full max-w-xl", className)}>
      <form onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="stock-search">
          Search stock
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--ink-muted)]" />
          <input
            id="stock-search"
            value={query}
            onChange={(e) => {
              userEditedRef.current = true;
              setQuery(e.target.value);
            }}
            onFocus={() => {
              if (userEditedRef.current && results.length > 0) setOpen(true);
            }}
            placeholder="Search stocks, sectors, indices..."
            autoComplete="off"
            className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] py-2.5 pl-10 pr-4 text-sm text-[var(--ink)] outline-none transition placeholder:text-[var(--ink-muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
          />
          {pending && (
            <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs text-[var(--ink-muted)]">
              Searching…
            </span>
          )}
        </div>
      </form>

      {open && (results.length > 0 || error) && (
        <div className="absolute left-0 right-0 top-full z-[60] mt-1.5 max-h-80 overflow-y-auto rounded-xl border border-[var(--line)] bg-[var(--surface-elevated)] shadow-[0_18px_40px_rgba(0,0,0,0.45)]">
          {error ? (
            <p className="px-4 py-3 text-sm text-[var(--down)]">{error}</p>
          ) : (
            <ul>
              {results.map((item) => (
                <li key={`${item.exchange}-${item.symbol}`}>
                  <button
                    type="button"
                    onClick={() => goTo(item.symbol, item.exchange)}
                    className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition hover:bg-white/[0.04]"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold tracking-wide text-[var(--ink)]">
                          {item.symbol}
                        </span>
                        <span className="text-[10px] uppercase tracking-[0.14em] text-[var(--ink-muted)]">
                          {item.exchange}
                        </span>
                      </div>
                      <p className="truncate text-xs text-[var(--ink-soft)]">
                        {item.company_name}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="tabular-nums text-sm text-[var(--ink)]">
                        {formatPrice(item.last_price)}
                      </p>
                      <p
                        className={cn(
                          "tabular-nums text-xs",
                          (item.change_pct ?? 0) >= 0
                            ? "text-[var(--up)]"
                            : "text-[var(--down)]",
                        )}
                      >
                        {formatPct(item.change_pct)}
                      </p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
