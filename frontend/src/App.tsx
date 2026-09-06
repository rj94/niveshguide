import type { ReactNode } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Screener from "./pages/Screener";
import Signals from "./pages/Signals";
import StockDetail from "./pages/StockDetail";

function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">NSE TREND DESK</div>
        <div className="brand-sub">Sheets → DB → Screener</div>
        <nav className="nav">
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/screener">Screener</NavLink>
          <NavLink to="/screener?trend=strong-momentum">Strong momentum</NavLink>
          <NavLink to="/screener?trend=fresh-uptrend">Fresh uptrend</NavLink>
          <NavLink to="/screener?trend=long-term-uptrend">Long-term</NavLink>
          <NavLink to="/screener?trend=breakout-watchlist">Breakout</NavLink>
          <NavLink to="/screener?trend=weak-avoid">Weak / avoid</NavLink>
          <NavLink to="/signals">Signals</NavLink>
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/screener" element={<Screener />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/stocks/:symbol" element={<StockDetail />} />
      </Routes>
    </Layout>
  );
}
