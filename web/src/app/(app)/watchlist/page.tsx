"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";

import { changeHeatColor } from "@/lib/dashboard-data";
import { getClientKey } from "@/lib/client-key";
import { formatNumber, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  addToMyWatchlist,
  getMyWatchlist,
  listStocks,
  removeFromMyWatchlist,
  replaceMyWatchlist,
} from "@/services/api";
import type { WatchlistItem, WatchlistResponse } from "@/types/watchlist";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

export default function WatchlistPage() {
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const key = getClientKey();
    const res = await getMyWatchlist(key);
    setData(res);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await refresh();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load watchlist");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = query.trim().toUpperCase();
    if (!symbol) return;
    setBusy(true);
    setError(null);
    try {
      const key = getClientKey();
      // Resolve via search so typos fail gracefully.
      const found = await listStocks({ q: symbol, exchange: "NSE", limit: 8 });
      const hit =
        found.items.find((s) => s.symbol === symbol && s.has_prices) ??
        found.items.find((s) => s.symbol.startsWith(symbol) && s.has_prices);
      if (!hit) {
        setError(`No priced NSE symbol matching "${symbol}"`);
        return;
      }
      const res = await addToMyWatchlist(key, hit.symbol, hit.exchange);
      setData(res);
      setQuery("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add symbol");
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(symbol: string) {
    setBusy(true);
    setError(null);
    try {
      const key = getClientKey();
      const res = await removeFromMyWatchlist(key, symbol);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove symbol");
    } finally {
      setBusy(false);
    }
  }

  async function onReorder(next: WatchlistItem[]) {
    setBusy(true);
    setError(null);
    try {
      const key = getClientKey();
      const res = await replaceMyWatchlist(
        key,
        next.map((i) => i.symbol),
      );
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reorder");
    } finally {
      setBusy(false);
    }
  }

  function move(symbol: string, dir: -1 | 1) {
    if (!data) return;
    const items = [...data.items].sort((a, b) => a.position - b.position);
    const idx = items.findIndex((i) => i.symbol === symbol);
    const swap = idx + dir;
    if (idx < 0 || swap < 0 || swap >= items.length) return;
    const copy = [...items];
    const tmp = copy[idx]!;
    copy[idx] = copy[swap]!;
    copy[swap] = tmp;
    void onReorder(copy);
  }

  const items = [...(data?.items ?? [])].sort((a, b) => a.position - b.position);

  return (
    <div className="page-shell mx-auto max-w-[1200px] space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            Watchlist
          </h1>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Saved to this browser via anonymous client key. Homepage heatmap mirrors this selection.
          </p>
        </div>
        <Link
          href="/"
          className="text-sm font-medium text-[var(--accent-hover)] hover:text-white"
        >
          ← Back to Dashboard
        </Link>
      </div>

      <form
        onSubmit={onAdd}
        className="flex flex-col gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Add NSE symbol (e.g. RELIANCE)"
          className="w-full flex-1 rounded-lg border border-[var(--line)] bg-transparent px-3 py-2 text-sm text-[var(--ink)] outline-none focus:border-[var(--accent)]"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          Add
        </button>
      </form>

      {error ? (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-[var(--ink-muted)]">Loading watchlist…</p>
      ) : items.length === 0 ? (
        <p className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-10 text-center text-sm text-[var(--ink-muted)]">
          No symbols yet. Add your first stock above.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {items.map((item) => {
              const changePct = item.change_pct;
              const price = num(item.price);
              if (changePct === null || price === null) {
                return (
                  <div
                    key={item.symbol}
                    className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3 text-sm text-[var(--ink-muted)]"
                  >
                    {item.symbol}
                  </div>
                );
              }
              return (
                <Link
                  key={item.symbol}
                  href={`/stocks/${encodeURIComponent(item.symbol)}`}
                  className="flex min-h-[100px] flex-col justify-between rounded-lg p-3 transition hover:brightness-110"
                  style={{ background: changeHeatColor(changePct) }}
                >
                  <span className="text-xs font-semibold text-white">{item.symbol}</span>
                  <span>
                    <span className="block text-base font-semibold tabular-nums text-white">
                      {formatNumber(price, { maximumFractionDigits: 2 })}
                    </span>
                    <span className="text-xs tabular-nums text-white/95">
                      {formatPct(changePct)}
                    </span>
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Symbol</th>
                  <th className="px-4 py-3 font-medium">Price</th>
                  <th className="px-4 py-3 font-medium">Change</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {items.map((item) => {
                  const changePct = item.change_pct;
                  const price = num(item.price);
                  const up = (changePct ?? 0) >= 0;
                  return (
                    <tr key={item.symbol}>
                      <td className="px-4 py-3">
                        <Link
                          href={`/stocks/${encodeURIComponent(item.symbol)}`}
                          className="font-medium text-[var(--ink)] hover:text-white"
                        >
                          {item.symbol}
                        </Link>
                        <p className="text-xs text-[var(--ink-muted)]">{item.name}</p>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-[var(--ink)]">
                        {price === null
                          ? "—"
                          : formatNumber(price, { maximumFractionDigits: 2 })}
                      </td>
                      <td
                        className={cn(
                          "px-4 py-3 tabular-nums",
                          up ? "text-[var(--up)]" : "text-[var(--down)]",
                        )}
                      >
                        {changePct === null ? "—" : formatPct(changePct)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => move(item.symbol, -1)}
                            className="rounded-md border border-[var(--line)] px-2 py-1 text-xs text-[var(--ink-soft)] hover:bg-white/5"
                          >
                            ↑
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => move(item.symbol, 1)}
                            className="rounded-md border border-[var(--line)] px-2 py-1 text-xs text-[var(--ink-soft)] hover:bg-white/5"
                          >
                            ↓
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void onRemove(item.symbol)}
                            className="rounded-md border border-[var(--line)] p-1.5 text-[var(--down)] hover:bg-white/5"
                            aria-label={`Remove ${item.symbol}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
