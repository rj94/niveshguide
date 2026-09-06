import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type StockRow } from "../api";
import { StockTable } from "../components/StockTable";

const SCREENS = [
  { id: "", label: "All scored" },
  { id: "strong-momentum", label: "Strong momentum" },
  { id: "fresh-uptrend", label: "Fresh uptrend" },
  { id: "long-term-uptrend", label: "Long-term uptrend" },
  { id: "breakout-watchlist", label: "Breakout watchlist" },
  { id: "weak-avoid", label: "Weak / avoid" },
];

export default function Screener() {
  const [params, setParams] = useSearchParams();
  const trend = params.get("trend") || "";
  const [q, setQ] = useState(params.get("q") || "");
  const [minScore, setMinScore] = useState(params.get("min_score") || "");
  const [sort, setSort] = useState(params.get("sort") || "score");
  const [rows, setRows] = useState<StockRow[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .screener({ trend: trend || undefined, q: q || undefined, min_score: minScore || undefined, sort, limit: 250 })
      .then((payload) => {
        setRows(payload.items);
        setTotal(payload.total);
        setError(null);
      })
      .catch((err: Error) => setError(err.message));
  }, [trend, q, minScore, sort]);

  function setTrend(next: string) {
    const copy = new URLSearchParams(params);
    if (next) copy.set("trend", next);
    else copy.delete("trend");
    setParams(copy);
  }

  return (
    <div>
      <div className="page-title">
        <div>
          <h1>Screener</h1>
          <p>
            {total} matching names. Strong momentum requires all five trend conditions; breakout is within 5% of the 52-week high.
          </p>
        </div>
      </div>
      <div className="toolbar">
        {SCREENS.map((screen) => (
          <button key={screen.id} className={`chip ${trend === screen.id ? "on" : ""}`} onClick={() => setTrend(screen.id)}>
            {screen.label}
          </button>
        ))}
        <input placeholder="Search symbol" value={q} onChange={(event) => setQ(event.target.value.toUpperCase())} />
        <select value={minScore} onChange={(event) => setMinScore(event.target.value)}>
          <option value="">Min score</option>
          {[5, 4, 3, 2, 1, 0].map((score) => (
            <option key={score} value={score}>
              ≥ {score}
            </option>
          ))}
        </select>
        <select value={sort} onChange={(event) => setSort(event.target.value)}>
          <option value="score">Sort: score</option>
          <option value="return_3m">Sort: 3M return</option>
          <option value="return_6m">Sort: 6M return</option>
          <option value="distance">Sort: 52W distance</option>
          <option value="market_cap">Sort: market cap</option>
          <option value="ltp">Sort: LTP</option>
          <option value="symbol">Sort: symbol</option>
        </select>
      </div>
      {error ? <div className="error">{error}</div> : <StockTable rows={rows} />}
    </div>
  );
}
