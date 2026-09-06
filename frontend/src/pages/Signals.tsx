import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type SignalRow } from "../api";

export default function Signals() {
  const [items, setItems] = useState<SignalRow[]>([]);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .signalsToday()
      .then((payload) => {
        setItems(payload.items);
        setAsOf(payload.as_of);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div>
      <div className="page-title">
        <div>
          <h1>Signals</h1>
          <p>Fresh crossovers, golden/death crosses, 52-week highs, and regime changes{asOf ? ` for ${asOf}` : ""}.</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="card" style={{ overflowX: "auto" }}>
        <table className="data">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Signal</th>
              <th>Direction</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4}>No signals stored yet.</td>
              </tr>
            ) : (
              items.map((item, index) => (
                <tr key={`${item.symbol}-${item.signal_type}-${index}`}>
                  <td>
                    <Link className="sym" to={`/stocks/${item.symbol}`}>
                      {item.symbol}
                    </Link>
                  </td>
                  <td>{item.signal_type}</td>
                  <td className={item.direction === "BULLISH" ? "up" : "down"}>{item.direction}</td>
                  <td>{item.signal_date}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
