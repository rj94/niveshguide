/** Filters junk / illiquid / rights issues from marketing & dashboard movers. */

export type MoverLike = {
  symbol: string;
  price: number;
  changePct: number;
};

const RIGHTS_RE = /-RE$/i;

/** True when the row should be excluded from Top Gainers / Top Losers. */
export function isJunkMover(
  row: MoverLike,
  opts?: { volumeMover?: boolean },
): boolean {
  const symbol = (row.symbol || "").trim();
  if (!symbol) return true;
  if (RIGHTS_RE.test(symbol)) return true;
  // Soft rights / odd-lot patterns: FOO-RE, FOORE (rare), *.
  if (/\bRE$/i.test(symbol) && symbol.includes("-")) return true;

  const volumeMover = Boolean(opts?.volumeMover);
  if (!volumeMover && row.price < 10) return true;
  // Circuit / illiquid spike without volume confirmation
  if (!volumeMover && Math.abs(row.changePct) > 20) return true;
  return false;
}

/** Soft filter for gainers: prefer liquid names (ltp >= 20) after junk cut. */
export function isWeakGainer(row: MoverLike): boolean {
  if (isJunkMover(row)) return true;
  if (row.price < 20) return true;
  return false;
}

export function filterMovers<T extends MoverLike>(
  rows: T[],
  opts?: { volumeMover?: boolean; softGainers?: boolean; limit?: number },
): T[] {
  const limit = opts?.limit ?? 5;
  const out: T[] = [];
  for (const row of rows) {
    if (opts?.softGainers) {
      if (isWeakGainer(row)) continue;
    } else if (isJunkMover(row, { volumeMover: opts?.volumeMover })) {
      continue;
    }
    out.push(row);
    if (out.length >= limit) break;
  }
  return out;
}
