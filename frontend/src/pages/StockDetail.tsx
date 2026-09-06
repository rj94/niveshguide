import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type SignalRow, type StockRow } from "../api";
import { PriceChart } from "../components/PriceChart";
import { Flag, TrendBadge, fmt, fmtPct, fmtVol } from "../components/StockTable";

type Detail = StockRow & {
  prices: Array<{ date: string; close: number | null }>;
  signals: SignalRow[];
  trend_history: Array<{ date: string; trend: string | null; trend_score: number | null }>;
};

export default function StockDetail() {
  const { symbol } = useParams();
  const [data, setData] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    setData(null);
    setError(null);
    api.stock(symbol).then(setData).catch((err: Error) => setError(err.message));
  }, [symbol]);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="empty">Loading {symbol}…</div>;

  const metrics = [
    ["LTP", fmt(data.ltp)],
    ["Day high", fmt(data.day_high)],
    ["Prev close", fmt(data.prev_close)],
    ["Market cap", fmt(data.market_cap, 0)],
    ["52W high", fmt(data.high_52_week)],
    ["52W low", fmt(data.low_52_week)],
    ["Return 3M", fmtPct(data.return_3m)],
    ["Return 6M", fmtPct(data.return_6m)],
    ["Volume", fmtVol(data.volume)],
    ["3M avg vol", fmtVol(data.avg_volume_3m)],
    ["6M avg vol", fmtVol(data.avg_volume_6m)],
    ["1Y avg vol", fmtVol(data.avg_volume_1y)],
    ["Dist. 52W high", data.distance_from_52w_high == null ? "—" : `${fmt(data.distance_from_52w_high)}%`],
    ["PE", fmt(data.pe)],
    ["EPS", fmt(data.eps)],
    ["3D MA", fmt(data.ma_3)],
    ["7D MA", fmt(data.ma_7)],
    ["21D MA", fmt(data.ma_21)],
    ["50D MA", fmt(data.ma_50)],
    ["200D MA", fmt(data.ma_200)],
  ];

  return (
    <div>
      <div className="page-title">
        <div>
          <h1>{data.symbol}</h1>
          <p>
            {data.company_name || "NSE"} · score {data.trend_score ?? "—"} · <TrendBadge trend={data.trend} />
          </p>
        </div>
      </div>
      <div className="detail-grid">
        <div className="card">
          <div className="label">Price history</div>
          <PriceChart prices={data.prices} />
          <div className="kv" style={{ marginTop: 16 }}>
            {metrics.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <b>{value}</b>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="label">Conditions</div>
          <div className="kv">
            <div>
              <span>3D &gt; 7D</span>
              <Flag value={data.crossover_3_7} />
            </div>
            <div>
              <span>LTP &gt; 21D</span>
              <Flag value={data.above_ma_21} />
            </div>
            <div>
              <span>21D &gt; 50D</span>
              <Flag value={data.ma21_gt_ma50} />
            </div>
            <div>
              <span>LTP &gt; 200D</span>
              <Flag value={data.above_ma_200} />
            </div>
            <div>
              <span>50D &gt; 200D</span>
              <Flag value={data.golden_cross} />
            </div>
          </div>
          <div className="label" style={{ marginTop: 18 }}>
            Signal history
          </div>
          <table className="data">
            <tbody>
              {data.signals.length === 0 ? (
                <tr>
                  <td>No stored signals.</td>
                </tr>
              ) : (
                data.signals.map((item, index) => (
                  <tr key={`${item.signal_type}-${index}`}>
                    <td>{item.signal_date}</td>
                    <td>{item.signal_type}</td>
                    <td className={item.direction === "BULLISH" ? "up" : "down"}>{item.direction}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
