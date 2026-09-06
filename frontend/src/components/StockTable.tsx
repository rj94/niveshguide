import { Link } from "react-router-dom";
import type { StockRow } from "../api";

export function fmt(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function fmtPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}%`;
}

export function fmtVol(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (Math.abs(value) >= 10_000_000) return `${(value / 10_000_000).toLocaleString("en-IN", { maximumFractionDigits: 2 })} Cr`;
  if (Math.abs(value) >= 100_000) return `${(value / 100_000).toLocaleString("en-IN", { maximumFractionDigits: 2 })} L`;
  return value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function TrendBadge({ trend }: { trend: string | null }) {
  const cls = (trend || "neutral").toLowerCase().replace(/\s+/g, "-");
  return <span className={`badge ${cls}`}>{trend || "—"}</span>;
}

export function Flag({ value }: { value: boolean | null | undefined }) {
  if (value === null || value === undefined) return <span className="flag">—</span>;
  return <span className={`flag ${value ? "yes" : "no"}`}>{value ? "Yes" : "No"}</span>;
}

export function StockTable({ rows }: { rows: StockRow[] }) {
  if (!rows.length) return <div className="empty">No stocks match this screen yet. Sync the Google Sheet and calculate indicators.</div>;
  return (
    <div className="card" style={{ overflowX: "auto" }}>
      <table className="data">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>LTP</th>
            <th>Score</th>
            <th>Trend</th>
            <th>3D MA</th>
            <th>7D MA</th>
            <th>21D MA</th>
            <th>50D MA</th>
            <th>200D MA</th>
            <th>3&gt;7</th>
            <th>&gt;21</th>
            <th>&gt;200</th>
            <th>50&gt;200</th>
            <th>3M ret</th>
            <th>6M ret</th>
            <th>Volume</th>
            <th>3M avg vol</th>
            <th>52W dist</th>
            <th>PE</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.symbol}>
              <td>
                <Link className="sym" to={`/stocks/${row.symbol}`}>
                  {row.symbol}
                </Link>
              </td>
              <td>{fmt(row.ltp)}</td>
              <td className="gold">{row.trend_score ?? "—"}</td>
              <td>
                <TrendBadge trend={row.trend} />
              </td>
              <td>{fmt(row.ma_3, 1)}</td>
              <td>{fmt(row.ma_7, 1)}</td>
              <td>{fmt(row.ma_21, 1)}</td>
              <td>{fmt(row.ma_50, 1)}</td>
              <td>{fmt(row.ma_200, 1)}</td>
              <td>
                <Flag value={row.crossover_3_7} />
              </td>
              <td>
                <Flag value={row.above_ma_21} />
              </td>
              <td>
                <Flag value={row.above_ma_200} />
              </td>
              <td>
                <Flag value={row.golden_cross} />
              </td>
              <td className={row.return_3m == null ? "" : row.return_3m >= 0 ? "up" : "down"}>{fmtPct(row.return_3m)}</td>
              <td className={row.return_6m == null ? "" : row.return_6m >= 0 ? "up" : "down"}>{fmtPct(row.return_6m)}</td>
              <td>{fmtVol(row.volume)}</td>
              <td>{fmtVol(row.avg_volume_3m)}</td>
              <td className={(row.distance_from_52w_high ?? -99) > -5 ? "up" : "down"}>
                {row.distance_from_52w_high == null ? "—" : `${fmt(row.distance_from_52w_high)}%`}
              </td>
              <td>{fmt(row.pe)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
