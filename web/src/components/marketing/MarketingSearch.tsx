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
  size?: "nav" | "hero";
  variant?: "light" | "dark";
  className?: string;
  placeholder?: string;
};

export function MarketingSearch({
  size = "hero",
  variant = "light",
  className,
  placeholder = "Search stocks (e.g. TCS, HDFCBANK)",
}: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const wrapRef = useRef<HTMLDivElement>(null);
  const userEditedRef = useRef(false);

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

  function goTo(symbol: string) {
    setOpen(false);
    router.push(`/stocks/${encodeURIComponent(symbol)}`);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    if (results[0]) {
      goTo(results[0].symbol);
      return;
    }
    goTo(q.toUpperCase());
  }

  const isHero = size === "hero";
  const isDark = variant === "dark";

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <form
        onSubmit={onSubmit}
        className={cn(
          "flex w-full items-stretch overflow-hidden rounded-xl border shadow-sm",
          isDark
            ? "border-white/8 bg-[#0d1219]"
            : "border-slate-200 bg-white",
        )}
      >
        <div className="relative flex min-w-0 flex-1 items-center">
          <Search
            className={cn(
              "pointer-events-none absolute left-3",
              isDark ? "text-slate-500" : "text-slate-400",
              isHero ? "h-5 w-5" : "h-4 w-4",
            )}
          />
          <input
            type="search"
            value={query}
            onChange={(e) => {
              userEditedRef.current = true;
              setQuery(e.target.value);
            }}
            onFocus={() => {
              if (results.length > 0 || error) setOpen(true);
            }}
            placeholder={placeholder}
            className={cn(
              "w-full bg-transparent outline-none",
              isDark
                ? "text-slate-100 placeholder:text-slate-600"
                : "text-slate-900 placeholder:text-slate-400",
              isHero ? "py-3.5 pl-11 pr-3 text-base" : "py-2 pl-9 pr-2 text-sm",
            )}
            aria-label="Search stocks"
          />
        </div>
        <button
          type="submit"
          className={cn(
            "shrink-0 bg-emerald-500 font-semibold text-[#06110d] transition hover:bg-emerald-400",
            isHero ? "px-6 text-sm" : "px-4 text-xs",
          )}
        >
          {pending ? "…" : "Search"}
        </button>
      </form>

      {open ? (
        <div
          className={cn(
            "absolute z-30 mt-2 w-full overflow-hidden rounded-xl border shadow-lg",
            isDark
              ? "border-white/8 bg-[#0d1219]"
              : "border-slate-200 bg-white",
          )}
        >
          {error ? (
            <p className="px-4 py-3 text-sm text-red-600">{error}</p>
          ) : results.length === 0 ? (
            <p className="px-4 py-3 text-sm text-slate-500">No matches</p>
          ) : (
            <ul>
              {results.map((row) => (
                <li key={`${row.exchange}-${row.symbol}`}>
                  <button
                    type="button"
                    onClick={() => goTo(row.symbol)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left",
                      isDark ? "hover:bg-white/5" : "hover:bg-slate-50",
                    )}
                  >
                    <span className="min-w-0">
                      <span
                        className={cn(
                          "block truncate text-sm font-semibold",
                          isDark ? "text-slate-100" : "text-slate-900",
                        )}
                      >
                        {row.symbol}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {row.company_name || row.exchange}
                      </span>
                    </span>
                    <span className="shrink-0 text-right">
                      <span
                        className={cn(
                          "block text-sm tabular-nums",
                          isDark ? "text-slate-200" : "text-slate-800",
                        )}
                      >
                        {formatPrice(row.last_price)}
                      </span>
                      <span
                        className={cn(
                          "block text-xs tabular-nums",
                          (row.change_pct ?? 0) >= 0
                            ? "text-emerald-600"
                            : "text-red-500",
                        )}
                      >
                        {formatPct(row.change_pct)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
