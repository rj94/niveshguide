export type WatchlistItem = {
  symbol: string;
  name: string;
  exchange: string;
  position: number;
  price: string | number | null;
  change: string | number | null;
  change_pct: number | null;
  sparkline: number[];
  as_of: string | null;
};

export type WatchlistResponse = {
  id: number;
  name: string;
  client_key: string;
  items: WatchlistItem[];
  as_of: string | null;
};
