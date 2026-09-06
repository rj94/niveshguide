import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Dashboard } from "../api";

export default function Dashboard() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <div className="error">API error: {error}. Start the backend: python -m cli serve --port 8010</div>;
  if (!data) return <div className="empty">Loading market overview…</div>;

  const cards = [
    ["Universe scored", data.total_active, data.as_of ? `as of ${data.as_of}` : "no snapshot yet"],
    ["Strong uptrend", data.strong_uptrend, "score = 5"],
    ["Uptrend", data.uptrend, "score 3–4"],
    ["Neutral", data.neutral, "score = 2"],
    ["Downtrend", data.downtrend, "score = 1"],
    ["Strong downtrend", data.strong_downtrend, "score = 0"],
    ["Fresh bullish 3/7", data.fresh_bullish_crossovers, "today"],
    ["New 52W highs", data.new_52_week_highs, "today"],
  ] as const;

  return (
    <div>
      <div className="page-title">
        <div>
          <h1>Market overview</h1>
          <p>Live quotes from the StockFilter Google Sheet. Trend scores use 3/7/21/50/200-day averages.</p>
        </div>
        <a className="chip" href={data.source_workbook} target="_blank" rel="noreferrer">
          Open Google Sheet
        </a>
      </div>
      <div className="grid">
        {cards.map(([label, value, hint]) => (
          <div className="card" key={label}>
            <div className="label">{label}</div>
            <div className="value">{value}</div>
            <div className="hint">{hint}</div>
          </div>
        ))}
      </div>
      <div className="card">
        <div className="label">Data source batches</div>
        <table className="data">
          <thead>
            <tr>
              <th>Batch</th>
              <th>Sheet</th>
              <th>Status</th>
              <th>Last success</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {data.batches.length === 0 ? (
              <tr>
                <td colSpan={5}>No batches registered. Run `python -m cli sync`.</td>
              </tr>
            ) : (
              data.batches.map((batch) => (
                <tr key={batch.batch_name}>
                  <td className="sym">{batch.batch_name}</td>
                  <td>
                    <a href={batch.url} target="_blank" rel="noreferrer">
                      gid {batch.gid ?? "—"} / {batch.sheet_name}
                    </a>
                  </td>
                  <td className={batch.status === "ACTIVE" ? "up" : "down"}>{batch.status}</td>
                  <td>{batch.last_successful_sync ?? "—"}</td>
                  <td>{batch.error_message ?? "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p style={{ color: "var(--muted)", marginTop: 16 }}>
        Jump to <Link to="/screener?trend=strong-momentum">strong momentum</Link> or{" "}
        <Link to="/signals">today’s signals</Link>.
      </p>
    </div>
  );
}
