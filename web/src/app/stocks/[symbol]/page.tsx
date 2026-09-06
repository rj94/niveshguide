import Link from "next/link";

import { StockDetailView } from "@/components/stock/StockDetailView";
import { StockSearch } from "@/components/stock/StockSearch";
import { getStock } from "@/services/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ symbol: string }>;
  searchParams: Promise<{ exchange?: string }>;
};

export async function generateMetadata({ params }: PageProps) {
  const { symbol } = await params;
  return {
    title: `${symbol.toUpperCase()} · Stock Intelligence`,
  };
}

export default async function StockPage({ params, searchParams }: PageProps) {
  const { symbol } = await params;
  const { exchange } = await searchParams;

  try {
    const stock = await getStock(symbol, { exchange, price_limit: 250 });
    return <StockDetailView stock={stock} />;
  } catch {
    return (
      <div className="page-shell py-12">
        <p className="font-[family-name:var(--font-display)] text-sm uppercase tracking-[0.28em] text-[var(--accent)]">
          Stock Intelligence
        </p>
        <h1 className="mt-4 font-[family-name:var(--font-display)] text-4xl text-[var(--ink)]">
          {symbol.toUpperCase()} not found
        </h1>
        <p className="mt-3 max-w-lg text-[var(--ink-soft)]">
          That symbol is not in the database, or the API is unreachable. Try
          another search.
        </p>
        <div className="mt-8">
          <StockSearch />
        </div>
        <Link
          href="/"
          className="mt-8 inline-block text-sm text-[var(--accent)] underline-offset-4 hover:underline"
        >
          Back to home
        </Link>
      </div>
    );
  }
}
