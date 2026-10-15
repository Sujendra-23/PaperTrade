import { useState } from "react";
import {
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  ChevronDown,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Instrument, Snapshot } from "./types";
const money = (cents: number) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
const clock = (time: string) =>
  new Date(time).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
export default function PriceChart({
  data,
  instrument,
  equity,
}: {
  data: Snapshot;
  instrument?: Instrument;
  equity: boolean;
}) {
  const [range, setRange] = useState("Recent");
  const rows = equity
    ? data.equity_history.map((p) => ({
        time: new Date(p.created_at).getTime(),
        value: p.equity / 100,
      }))
    : data.price_history.map((p) => ({
        time: new Date(p.created_at).getTime(),
        value: p.price / 100,
      }));
  const minutes = range === "1m" ? 1 : range === "5m" ? 5 : Infinity;
  const end = rows.at(-1)?.time ?? 0;
  const filtered = rows.filter((p) => p.time >= end - minutes * 60000);
  const change = instrument
    ? ((instrument.last_price - instrument.open_price) /
        instrument.open_price) *
      100
    : 0;
  const positive = equity ? data.account.pnl >= 0 : change >= 0;
  const color = positive ? "#93d7b0" : "#ef9990";
  return (
    <>
      <div className="chart-title">
        <div className="chart-instrument">
          <span className={`ticker-logo large logo-${data.symbol}`}>
            {equity ? <BarChart3 size={20} /> : data.symbol.slice(0, 1)}
          </span>
          <div>
            <h2>
              {equity ? "Account equity" : data.symbol}
              <span>{equity ? "USD" : "SIM"}</span>
            </h2>
            <p>
              {equity ? "Your portfolio over this session" : instrument?.name}
            </p>
          </div>
          <ChevronDown size={14} />
        </div>
        <span className="chart-source">
          <i />
          Simulated market
        </span>
      </div>
      <div className="chart-price">
        <strong>
          {money(equity ? data.account.equity : (instrument?.last_price ?? 0))}
        </strong>
        <span className={positive ? "positive" : "negative"}>
          {positive ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}{" "}
          {equity
            ? money(data.account.pnl)
            : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`}
          <small>{equity ? "since funding" : "from session open"}</small>
        </span>
      </div>
      <div className="chart-toolbar">
        <div className="chart-view-label">
          <Activity size={14} />
          {equity ? "Portfolio value" : "Trade price"}
          <span>USD</span>
        </div>
        <div className="range-tabs" aria-label="Chart range">
          {["1m", "5m", "Recent"].map((r) => (
            <button
              key={r}
              aria-pressed={range === r}
              className={range === r ? "selected" : ""}
              onClick={() => setRange(r)}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div className="price-chart">
        {filtered.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={filtered}
              margin={{ top: 12, right: 5, left: 3, bottom: 0 }}
            >
              <defs>
                <linearGradient id="price-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.16} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                stroke="#262c33"
                strokeDasharray="3 5"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                type="number"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(v) =>
                  new Date(v).toLocaleTimeString("en-US", {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                }
                tick={{ fill: "#939da9", fontSize: 10 }}
                minTickGap={65}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                orientation="right"
                domain={["auto", "auto"]}
                tickFormatter={(v) =>
                  Number(v).toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })
                }
                tick={{ fill: "#939da9", fontSize: 10 }}
                width={equity ? 76 : 63}
                axisLine={false}
                tickLine={false}
                tickCount={5}
              />
              <Tooltip
                contentStyle={{
                  background: "#1d242c",
                  border: "1px solid #3b4651",
                  borderRadius: 5,
                  color: "#e7edf0",
                }}
                labelFormatter={(v) => clock(new Date(Number(v)).toISOString())}
                formatter={(v) => [
                  money(Number(v) * 100),
                  equity ? "Equity" : "Trade price",
                ]}
              />
              <Area
                type="linear"
                dataKey="value"
                stroke={color}
                fill="url(#price-fill)"
                strokeWidth={1.6}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-empty">
            <Activity size={22} />
            <p>
              {equity
                ? "Your equity history starts here."
                : "Waiting for the first trades."}
            </p>
            <small>Live data will appear as the session progresses.</small>
          </div>
        )}
      </div>
      <div className="chart-caption">
        <span>
          {filtered.length} {equity ? "account snapshots" : "executed trades"}
          <span className="caption-dot">·</span>Session data only
        </span>
        <span>Price-time priority</span>
      </div>
    </>
  );
}
