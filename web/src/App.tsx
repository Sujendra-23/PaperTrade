import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Minus,
  Plus,
  Search,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react";
import { request } from "./api";
import type { Instrument, Snapshot } from "./types";

const PriceChart = lazy(() => import("./PriceChart"));

const money = (cents: number) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
const num = (n: number) => n.toLocaleString("en-US");
const clock = (time: string) =>
  new Date(time).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
type User = { id: string; name?: string; username: string | null };
type Mode = "trade" | "portfolio" | "activity";

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [symbol, setSymbol] = useState("AAPL");
  const [mode, setMode] = useState<Mode>("trade");
  const [data, setData] = useState<Snapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedPrice, setSelectedPrice] = useState<{
    price: number;
    nonce: number;
  } | null>(null);
  const [guide, setGuide] = useState(false);
  useEffect(() => {
    const shortcut = (e: KeyboardEvent) => {
      if (e.key === "/" && !(e.target instanceof HTMLInputElement)) {
        e.preventDefault();
        document.querySelector<HTMLInputElement>(".search input")?.focus();
      }
    };
    document.addEventListener("keydown", shortcut);
    return () => document.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => {
    if (!guide) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setGuide(false);
      if (e.key === "Tab") {
        const elements = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".guide-drawer button,.guide-drawer a",
          ),
        );
        const first = elements[0],
          last = elements.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      document
        .querySelector<HTMLElement>('[aria-label="Trading guide"]')
        ?.focus();
    };
  }, [guide]);
  useEffect(() => {
    request<User>("/auth/session")
      .then(setUser)
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);
  const refresh = useCallback(async () => {
    try {
      const state = await request<Snapshot>(`/snapshot?symbol=${symbol}`);
      setData(state);
      setConnectionError("");
    } catch (e) {
      setConnectionError((e as Error).message);
    }
  }, [symbol]);
  useEffect(() => {
    if (!user) return;
    let closed = false,
      socket: WebSocket | undefined,
      timer: ReturnType<typeof setTimeout>;
    function connect() {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/ws?symbol=${symbol}`,
      );
      socket.onmessage = (event) => {
        if (closed) return;
        setData(JSON.parse(event.data));
        setConnected(true);
        setConnectionError("");
      };
      socket.onclose = () => {
        if (closed) return;
        setConnected(false);
        setConnectionError("Live feed interrupted. Reconnecting…");
        timer = setTimeout(connect, 2000);
      };
      socket.onerror = () => socket?.close();
    }
    void refresh();
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      socket?.close();
      setConnected(false);
    };
  }, [user, symbol, refresh]);
  const instrument = data?.market.find((i) => i.symbol === symbol);
  async function signOut() {
    await request("/auth/logout", { method: "POST" });
    setUser(null);
    setData(null);
  }
  const pickSymbol = (s: string) => {
    setSymbol(s);
    setSelectedPrice(null);
  };
  if (checking)
    return (
      <div className="boot">
        <LoaderCircle className="spin" />
        <span>Opening PaperTrade…</span>
      </div>
    );
  if (!user) return <Auth onUser={setUser} />;
  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          href="#"
          className="brand"
          aria-label="PaperTrade home"
          onClick={(e) => {
            e.preventDefault();
            setMode("trade");
          }}
        >
          <span className="brand-mark">
            <TrendingUp size={21} />
          </span>
          Paper<span>Trade</span>
          <span className="beta">SANDBOX</span>
        </a>
        <nav aria-label="Workspace">
          <button
            className={mode === "trade" ? "active" : ""}
            onClick={() => setMode("trade")}
          >
            <LayoutDashboard size={15} />
            Trade
          </button>
          <button
            className={mode === "portfolio" ? "active" : ""}
            onClick={() => setMode("portfolio")}
          >
            <BarChart3 size={15} />
            Portfolio
          </button>
          <button
            className={mode === "activity" ? "active" : ""}
            onClick={() => setMode("activity")}
          >
            <Activity size={15} />
            Activity
          </button>
        </nav>
        <div className="header-end">
          <span className={`connection ${connected ? "online" : ""}`}>
            <i />
            {connected ? "Market live" : "Connecting"}
          </span>
          <button
            className="icon-button"
            aria-label="Trading guide"
            onClick={() => setGuide(true)}
          >
            <CircleHelp size={18} />
          </button>
          <span className="avatar">
            {(user.username ?? "P").slice(0, 1).toUpperCase()}
          </span>
          <button
            className="icon-button"
            aria-label="Sign out"
            onClick={() => void signOut()}
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>
      <aside className="watchlist">
        <div className="watch-title">
          <h2>Watchlist</h2>
          <span>{data?.market.length ?? 6}</span>
        </div>
        <label className="search">
          <Search size={15} />
          <input
            aria-label="Find a symbol"
            placeholder="Find a symbol"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <kbd>/</kbd>
        </label>
        <div className="watch-labels">
          <span>Instrument</span>
          <span>Last / change</span>
        </div>
        <div className="instruments">
          {data?.market
            .filter((i) =>
              `${i.symbol} ${i.name}`
                .toLowerCase()
                .includes(search.toLowerCase()),
            )
            .map((i) => (
              <Watch
                key={i.symbol}
                instrument={i}
                active={i.symbol === symbol}
                onClick={() => pickSymbol(i.symbol)}
              />
            ))}
        </div>
        {search &&
          data?.market.every(
            (i) =>
              !`${i.symbol} ${i.name}`
                .toLowerCase()
                .includes(search.toLowerCase()),
          ) && <p className="empty-search">No matching instruments.</p>}
        <div className="watch-bottom">
          <div>
            <ShieldCheck size={16} />
            <strong>Practice with perspective.</strong>
          </div>
          <p>
            Simulated prices. Virtual funds.
            <br />A real place to learn.
          </p>
          <button onClick={() => setGuide(true)}>
            How trading works <ArrowUpRight size={14} />
          </button>
        </div>
        <a
          className="source-link"
          href="https://github.com/Sujendra-23/PaperTrade"
          target="_blank"
          rel="noreferrer"
        >
          <BookOpen size={14} />
          Project & documentation
          <ExternalLink size={12} />
        </a>
      </aside>
      <main>
        <div className="workspace-heading">
          <div>
            <h1>
              {mode === "trade"
                ? "Trading workspace"
                : mode === "portfolio"
                  ? "Your portfolio"
                  : "Account activity"}
            </h1>
            <p>
              {mode === "trade"
                ? "Read the market. Make your move."
                : mode === "portfolio"
                  ? "Every position, with the full picture."
                  : "An auditable record of your trading session."}
            </p>
          </div>
          <div className="account-label">
            <span className="account-dot" />
            {user.username ?? "Practice account"}
            <span>USD</span>
          </div>
        </div>
        {connectionError && (
          <div className="connection-alert" role="status">
            <Activity size={15} />
            {connectionError}
            <button onClick={() => void refresh()}>Retry</button>
          </div>
        )}
        {data ? (
          <>
            <section className="account-strip" aria-label="Account overview">
              <Metric
                label="Account equity"
                value={money(data.account.equity)}
                hint="Cash + market value"
              />
              <Metric
                label="Buying power"
                value={money(data.account.buying_power)}
                hint="Available to trade"
              />
              <Metric
                label="Invested value"
                value={money(
                  data.positions.reduce((s, p) => s + p.market_value, 0),
                )}
                hint={`${data.positions.filter((p) => p.quantity > 0).length} open positions`}
              />
              <Metric
                label="Total P&L"
                value={`${data.account.pnl >= 0 ? "+" : ""}${money(data.account.pnl)}`}
                hint={`${((data.account.pnl / data.account.initial_equity) * 100).toFixed(2)}% since funding`}
                tone={data.account.pnl >= 0 ? "positive" : "negative"}
              />
            </section>
            {mode === "activity" ? (
              <ActivityLog sequence={data.sequence} />
            ) : (
              <div className="trading-grid">
                <section className="market-panel">
                  <Suspense
                    fallback={
                      <div className="chart-empty">
                        <LoaderCircle className="spin" />
                        Loading chart…
                      </div>
                    }
                  >
                    <PriceChart
                      data={data}
                      instrument={instrument}
                      equity={mode === "portfolio"}
                    />
                  </Suspense>
                </section>
                <section className="book-panel">
                  <Depth
                    data={data}
                    onPrice={(price) =>
                      setSelectedPrice({ price, nonce: Date.now() })
                    }
                  />
                </section>
                <aside className="ticket-panel">
                  <Ticket
                    symbol={symbol}
                    instrument={instrument}
                    data={data}
                    selected={selectedPrice}
                    refresh={refresh}
                  />
                </aside>
                <section className="blotter-panel">
                  <Blotter
                    data={data}
                    portfolio={mode === "portfolio"}
                    refresh={refresh}
                    onSymbol={pickSymbol}
                  />
                </section>
                <section className="tape-panel">
                  <Tape data={data} />
                </section>
              </div>
            )}
          </>
        ) : (
          <div className="loading-workspace">
            <LoaderCircle className="spin" />
            <h2>Connecting to your workspace</h2>
            <p>The simulated market is getting ready.</p>
            <button onClick={() => void refresh()}>Try again</button>
          </div>
        )}
        <footer className="footer">
          <span>
            <ShieldCheck size={12} />
            Paper trading only · No real money at risk
          </span>
          <span>
            All market data is simulated{" "}
            <span className="footer-separator">/</span>{" "}
            {data ? `Event ${num(data.sequence)}` : "Waiting for data"}
          </span>
        </footer>
      </main>
      {guide && (
        <div className="drawer-backdrop" onClick={() => setGuide(false)}>
          <section
            className="guide-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Trading guide"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close-button"
              autoFocus
              aria-label="Close guide"
              onClick={() => setGuide(false)}
            >
              <X size={20} />
            </button>
            <ShieldCheck size={30} className="positive" />
            <h2>A market you can learn in.</h2>
            <p>
              Every order trades against simulated liquidity. Your account
              starts with $100,000 in virtual cash.
            </p>
            <h3>Place an order</h3>
            <p>
              A limit order sets your price and waits for a match. A market
              order fills immediately within a 5% price collar; any remainder is
              canceled. Click an order-book price to use it in your ticket.
            </p>
            <h3>Know your limits</h3>
            <p>
              Up to 1,000 shares per order and 2,000 shares per instrument,
              including open buys. Limit prices must be within 5% of the last
              trade. Cash and shares are reserved for open orders. Short selling
              is disabled.
            </p>
            <h3>Follow the accounting</h3>
            <p>
              Positions and cash update together when a trade settles. Your P&L
              is current equity minus initial funding. Activity records your
              orders and fills.
            </p>
            <a
              href="https://github.com/Sujendra-23/PaperTrade"
              target="_blank"
              rel="noreferrer"
            >
              Explore the architecture <ArrowUpRight size={15} />
            </a>
            <button className="primary" onClick={() => setGuide(false)}>
              Back to the workspace <ArrowRight size={16} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
function Metric({
  label,
  value,
  hint,
  tone = "",
}: {
  label: string;
  value: string;
  hint: string;
  tone?: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}
function Watch({
  instrument: i,
  active,
  onClick,
}: {
  instrument: Instrument;
  active: boolean;
  onClick: () => void;
}) {
  const change = ((i.last_price - i.open_price) / i.open_price) * 100;
  return (
    <button
      className={`instrument ${active ? "selected" : ""}`}
      onClick={onClick}
      aria-pressed={active}
    >
      <span className={`ticker-logo logo-${i.symbol}`}>
        {i.symbol.slice(0, 1)}
      </span>
      <span className="instrument-name">
        <strong>{i.symbol}</strong>
        <small>{i.name.split(" Corporation")[0].split(" Inc.")[0]}</small>
      </span>
      <span className="instrument-price">
        <strong>{money(i.last_price).slice(1)}</strong>
        <small className={change >= 0 ? "positive" : "negative"}>
          {change >= 0 ? "+" : ""}
          {change.toFixed(2)}%
        </small>
      </span>
      {active && <span className="selected-marker" />}
    </button>
  );
}

function Depth({
  data,
  onPrice,
}: {
  data: Snapshot;
  onPrice: (p: number) => void;
}) {
  const asks = data.book.asks.slice(0, 7).reverse(),
    bids = data.book.bids.slice(0, 7),
    max = Math.max(1, ...[...asks, ...bids].map((l) => l.quantity));
  const spread =
    data.book.asks[0] && data.book.bids[0]
      ? data.book.asks[0].price - data.book.bids[0].price
      : null;
  return (
    <>
      <div className="panel-heading">
        <h2>Order book</h2>
        <span className="subtle">{data.symbol}</span>
      </div>
      <div className="book-head">
        <span>Price (USD)</span>
        <span>Size</span>
        <span>Total (USD)</span>
      </div>
      <div className="book-mobile-head">
        <span>Buy · Price / Size / Total</span>
        <span>Sell · Price / Size / Total</span>
      </div>
      <div className="depth-levels asks">
        {asks.length ? (
          asks.map((l) => (
            <button
              key={l.price}
              className="depth-row ask"
              style={
                {
                  "--depth": `${(l.quantity / max) * 100}%`,
                } as React.CSSProperties
              }
              onClick={() => onPrice(l.price)}
              aria-label={`Use ask price ${money(l.price)}`}
            >
              <span>{money(l.price).slice(1)}</span>
              <span>{num(l.quantity)}</span>
              <span>{num(Math.round((l.price * l.quantity) / 100))}</span>
            </button>
          ))
        ) : (
          <p className="empty-book">No sell orders</p>
        )}
      </div>
      <div className="spread">
        <strong className="positive">
          {money(
            data.market.find((i) => i.symbol === data.symbol)?.last_price ?? 0,
          )}
          <ArrowUpRight size={13} />
        </strong>
        <span>Spread {spread === null ? "—" : money(spread)}</span>
      </div>
      <div className="depth-levels bids">
        {bids.length ? (
          bids.map((l) => (
            <button
              key={l.price}
              className="depth-row bid"
              style={
                {
                  "--depth": `${(l.quantity / max) * 100}%`,
                } as React.CSSProperties
              }
              onClick={() => onPrice(l.price)}
              aria-label={`Use bid price ${money(l.price)}`}
            >
              <span>{money(l.price).slice(1)}</span>
              <span>{num(l.quantity)}</span>
              <span>{num(Math.round((l.price * l.quantity) / 100))}</span>
            </button>
          ))
        ) : (
          <p className="empty-book">No buy orders</p>
        )}
      </div>
      <div className="book-legend">
        <span>
          <i />
          Buy liquidity
        </span>
        <span>
          <i />
          Sell liquidity
        </span>
      </div>
    </>
  );
}
function Ticket({
  symbol,
  instrument,
  data,
  selected,
  refresh,
}: {
  symbol: string;
  instrument?: Instrument;
  data: Snapshot;
  selected: { price: number; nonce: number } | null;
  refresh: () => Promise<void>;
}) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY"),
    [kind, setKind] = useState<"LIMIT" | "MARKET">("LIMIT"),
    [qty, setQty] = useState("10"),
    [price, setPrice] = useState(""),
    [busy, setBusy] = useState(false),
    [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(
      null,
    );
  const [picked, setPicked] = useState(false);
  const retry = useRef<{ signature: string; key: string } | null>(null);
  useEffect(() => {
    setPrice("");
    setFeedback(null);
    retry.current = null;
  }, [symbol]);
  useEffect(() => {
    if (selected) {
      setPrice((selected.price / 100).toFixed(2));
      setKind("LIMIT");
      setPicked(true);
      const timer = setTimeout(() => setPicked(false), 900);
      return () => clearTimeout(timer);
    }
  }, [selected]);
  const cents =
    price === ""
      ? (instrument?.last_price ?? 0)
      : Math.round(Number(price) * 100);
  const protection =
    side === "BUY"
      ? Math.floor(((instrument?.last_price ?? 0) * 105) / 100)
      : Math.ceil(((instrument?.last_price ?? 0) * 95) / 100);
  const estimate = (kind === "LIMIT" ? cents : protection) * Number(qty);
  const position = data.positions.find((p) => p.symbol === symbol);
  const available =
    side === "BUY"
      ? data.account.buying_power
      : (position?.quantity ?? 0) - (position?.reserved ?? 0);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setFeedback(null);
    const payload = {
      symbol,
      side,
      kind,
      quantity: Number(qty),
      ...(kind === "LIMIT" ? { price: cents } : {}),
    };
    const signature = JSON.stringify(payload);
    if (retry.current?.signature !== signature)
      retry.current = { signature, key: crypto.randomUUID() };
    try {
      const result = await request<{
        status: string;
        filled: number;
        remaining: number;
      }>("/orders", {
        method: "POST",
        headers: { "Idempotency-Key": retry.current.key },
        body: signature,
      });
      retry.current = null;
      const text =
        result.status === "FILLED"
          ? `${num(result.filled)} ${symbol} shares filled.`
          : result.status === "CANCELLED"
            ? `${num(result.filled)} shares filled. Remaining ${num(result.remaining)} canceled.`
            : `${side === "BUY" ? "Buy" : "Sell"} order placed. ${num(result.remaining)} shares ${result.filled ? "remaining" : "open"}.`;
      setFeedback({ ok: true, text });
      await refresh();
    } catch (e) {
      setFeedback({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }
  const max =
    side === "BUY"
      ? Math.max(
          0,
          Math.min(
            1000,
            2000 -
              (position?.quantity ?? 0) -
              data.orders
                .filter(
                  (o) =>
                    o.symbol === symbol &&
                    o.side === "BUY" &&
                    ["OPEN", "PARTIAL", "PENDING"].includes(o.status),
                )
                .reduce((s, o) => s + o.remaining, 0),
            Math.floor(available / (kind === "LIMIT" ? cents : protection)),
          ),
        )
      : Math.min(1000, available);
  return (
    <>
      <div className="panel-heading">
        <h2>Place order</h2>
        <span className="ticket-symbol">{symbol}</span>
      </div>
      <form onSubmit={(e) => void submit(e)} className="ticket-form">
        <div className="side-toggle">
          {(["BUY", "SELL"] as const).map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={side === s}
              className={side === s ? `selected ${s.toLowerCase()}` : ""}
              onClick={() => {
                setSide(s);
                setFeedback(null);
              }}
            >
              {s === "BUY" ? "Buy" : "Sell"}
            </button>
          ))}
        </div>
        <div className="kind-tabs">
          {(["LIMIT", "MARKET"] as const).map((k) => (
            <button
              type="button"
              key={k}
              aria-pressed={kind === k}
              className={kind === k ? "selected" : ""}
              onClick={() => setKind(k)}
            >
              {k === "LIMIT" ? "Limit order" : "Market order"}
            </button>
          ))}
        </div>
        <label className="field-label" htmlFor="quantity">
          Quantity{" "}
          <button type="button" onClick={() => setQty(String(max))}>
            Max {num(max)}
          </button>
        </label>
        <div className="quantity-field">
          <button
            type="button"
            aria-label="Decrease quantity"
            onClick={() => setQty(String(Math.max(1, Number(qty) - 1)))}
          >
            <Minus size={14} />
          </button>
          <input
            id="quantity"
            inputMode="numeric"
            type="number"
            min="1"
            max="1000"
            step="1"
            required
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
          <span>shares</span>
          <button
            type="button"
            aria-label="Increase quantity"
            onClick={() => setQty(String(Math.min(1000, Number(qty) + 1)))}
          >
            <Plus size={14} />
          </button>
        </div>
        {kind === "LIMIT" ? (
          <>
            <label className="field-label" htmlFor="price">
              Limit price <span>USD</span>
            </label>
            <div className={`price-input ${picked ? "picked" : ""}`}>
              <span>$</span>
              <input
                id="price"
                type="number"
                min="0.01"
                step="0.01"
                required
                value={
                  price === ""
                    ? instrument
                      ? String((instrument.last_price / 100).toFixed(2))
                      : ""
                    : price
                }
                onChange={(e) => setPrice(e.target.value)}
              />
              <span>USD</span>
            </div>
            <p className="field-hint">Executes at your price or better.</p>
          </>
        ) : (
          <div className="market-note">
            <ShieldCheck size={15} />
            <p>
              Immediate execution within a 5% price collar. Unfilled shares are
              canceled.
            </p>
          </div>
        )}
        <dl className="order-summary">
          <div>
            <dt>{side === "BUY" ? "Buying power" : "Available shares"}</dt>
            <dd>{side === "BUY" ? money(available) : num(available)}</dd>
          </div>
          <div>
            <dt>{kind === "MARKET" ? "Maximum notional" : "Order value"}</dt>
            <dd>{money(Number.isFinite(estimate) ? estimate : 0)}</dd>
          </div>
          <div>
            <dt>Trading fees</dt>
            <dd>$0.00</dd>
          </div>
        </dl>
        <div className="estimated">
          <span>
            {side === "BUY" ? "Estimated cost" : "Estimated proceeds"}
          </span>
          <strong>{money(Number.isFinite(estimate) ? estimate : 0)}</strong>
        </div>
        <button
          className={`submit-order ${side.toLowerCase()}`}
          disabled={busy || !Number(qty) || !cents}
          type="submit"
        >
          {busy ? (
            <LoaderCircle size={16} className="spin" />
          ) : side === "BUY" ? (
            <Plus size={16} />
          ) : (
            <Minus size={16} />
          )}{" "}
          {busy
            ? "Submitting…"
            : `${side === "BUY" ? "Buy" : "Sell"} ${symbol}`}{" "}
          {!busy && <ArrowRight size={16} />}
        </button>
        <p className="ticket-disclaimer">
          <ShieldCheck size={12} />
          Virtual funds. Real practice.
        </p>
        {feedback && (
          <div
            role={feedback.ok ? "status" : "alert"}
            className={`order-feedback ${feedback.ok ? "success" : "error"}`}
          >
            {feedback.ok ? <Check size={16} /> : <CircleHelp size={16} />}
            <span>{feedback.text}</span>
          </div>
        )}
      </form>
    </>
  );
}
function Blotter({
  data,
  portfolio,
  refresh,
  onSymbol,
}: {
  data: Snapshot;
  portfolio: boolean;
  refresh: () => Promise<void>;
  onSymbol: (s: string) => void;
}) {
  const [tab, setTab] = useState<"orders" | "positions" | "history">(
      portfolio ? "positions" : "orders",
    ),
    [error, setError] = useState(""),
    [canceling, setCanceling] = useState("");
  useEffect(() => setTab(portfolio ? "positions" : "orders"), [portfolio]);
  const open = data.orders.filter((o) =>
    ["OPEN", "PARTIAL", "PENDING"].includes(o.status),
  );
  const positions = data.positions.filter((p) => p.quantity > 0);
  async function cancel(id: string) {
    setCanceling(id);
    setError("");
    try {
      await request(`/orders/${id}`, { method: "DELETE" });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCanceling("");
    }
  }
  return (
    <>
      <div className="blotter-tabs" aria-label="Account tables">
        <button
          className={tab === "orders" ? "selected" : ""}
          onClick={() => setTab("orders")}
        >
          Open orders <span>{open.length}</span>
        </button>
        <button
          className={tab === "positions" ? "selected" : ""}
          onClick={() => setTab("positions")}
        >
          Positions <span>{positions.length}</span>
        </button>
        <button
          className={tab === "history" ? "selected" : ""}
          onClick={() => setTab("history")}
        >
          Order history
        </button>
        <span className="blotter-account">{data.account.name}</span>
      </div>
      {error && (
        <p role="alert" className="table-error">
          {error}
        </p>
      )}
      <div className="table-wrap">
        {tab === "positions" ? (
          <table>
            <thead>
              <tr>
                <th>Instrument</th>
                <th>Shares</th>
                <th>Avg. cost</th>
                <th>Market value</th>
                <th>Unrealized P&L</th>
                <th>Realized P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.symbol}>
                  <td>
                    <button
                      className="symbol-link"
                      onClick={() => onSymbol(p.symbol)}
                    >
                      {p.symbol}
                      <ArrowUpRight size={12} />
                    </button>
                  </td>
                  <td>{num(p.quantity)}</td>
                  <td>{money(p.cost_basis / p.quantity)}</td>
                  <td>{money(p.market_value)}</td>
                  <td className={p.unrealized >= 0 ? "positive" : "negative"}>
                    {money(p.unrealized)}
                  </td>
                  <td className={p.realized >= 0 ? "positive" : "negative"}>
                    {money(p.realized)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Instrument</th>
                <th>Side / type</th>
                <th>Quantity</th>
                <th>Limit price</th>
                <th>Status</th>
                <th>{tab === "orders" ? "Action" : "Placed"}</th>
              </tr>
            </thead>
            <tbody>
              {(tab === "orders" ? open : data.orders).map((o) => (
                <tr key={o.id}>
                  <td>
                    <button
                      className="symbol-link"
                      onClick={() => onSymbol(o.symbol)}
                    >
                      {o.symbol}
                    </button>
                  </td>
                  <td>
                    <span
                      className={o.side === "BUY" ? "positive" : "negative"}
                    >
                      {o.side === "BUY" ? "Buy" : "Sell"}
                    </span>
                    <span className="type-divider">/</span>
                    {o.kind === "LIMIT" ? "Limit" : "Market"}
                  </td>
                  <td>
                    {o.filled}
                    <span className="subtle"> / {o.quantity}</span>
                  </td>
                  <td>{o.kind === "LIMIT" ? money(o.price) : "Market"}</td>
                  <td>
                    <span className={`status status-${o.status.toLowerCase()}`}>
                      {o.status === "PARTIAL"
                        ? "Partial fill"
                        : o.status.charAt(0) + o.status.slice(1).toLowerCase()}
                    </span>
                  </td>
                  <td>
                    {tab === "orders" ? (
                      <button
                        className="cancel-button"
                        disabled={canceling === o.id}
                        onClick={() => void cancel(o.id)}
                      >
                        {canceling === o.id ? "Canceling…" : "Cancel"}
                        <X size={12} />
                      </button>
                    ) : (
                      clock(o.created_at)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {(tab === "positions"
        ? positions.length === 0
        : tab === "orders"
          ? open.length === 0
          : data.orders.length === 0) && (
        <div className="table-empty">
          {tab === "positions" ? (
            <BarChart3 size={23} />
          ) : (
            <BookOpen size={23} />
          )}
          <div>
            <strong>
              {tab === "positions"
                ? "Your portfolio starts with a trade."
                : tab === "orders"
                  ? "A clear order book. Your next move?"
                  : "Your trading story starts here."}
            </strong>
            <p>
              {tab === "positions"
                ? "Buy shares to track your positions and P&L here."
                : tab === "orders"
                  ? "Open limit orders will appear here until filled or canceled."
                  : "Every order and its outcome will appear here."}
            </p>
          </div>
        </div>
      )}
      <div className="blotter-note">
        <ShieldCheck size={12} />
        Cash and shares are reserved for open orders.
      </div>
    </>
  );
}
function Tape({ data }: { data: Snapshot }) {
  return (
    <>
      <div className="panel-heading">
        <h2>Recent trades</h2>
        <span className="subtle">{data.symbol}</span>
      </div>
      <div className="tape-head">
        <span>Price (USD)</span>
        <span>Size</span>
        <span>Time</span>
      </div>
      <div className="tape-rows">
        {data.trades.slice(0, 5).map((t, i) => (
          <div key={t.id}>
            <span
              className={
                t.price >= (data.trades[i + 1]?.price ?? t.price)
                  ? "positive"
                  : "negative"
              }
            >
              {money(t.price).slice(1)}
            </span>
            <span>{num(t.quantity)}</span>
            <span>{clock(t.created_at)}</span>
          </div>
        ))}
      </div>
      {!data.trades.length && (
        <p className="empty-book">Waiting for executed trades.</p>
      )}
      <div className="tape-note">
        <span className="live-dot" />
        Executed in the matching engine
      </div>
    </>
  );
}
function ActivityLog({ sequence }: { sequence: number }) {
  const [events, setEvents] = useState<
      {
        seq: number;
        kind: string;
        created_at: string;
        payload: Record<string, unknown>;
      }[]
    >([]),
    [error, setError] = useState(""),
    [balanced, setBalanced] = useState<boolean | null>(null);
  useEffect(() => {
    let canceled = false;
    request<{ events: typeof events }>("/events?limit=1000")
      .then((r) => {
        if (!canceled) setEvents(r.events.reverse());
      })
      .catch((e) => {
        if (!canceled) setError(e.message);
      });
    return () => {
      canceled = true;
    };
  }, [sequence]);
  return (
    <section className="activity-panel">
      <div className="panel-heading">
        <h2>Order & settlement log</h2>
        <button
          className="reconcile-button"
          onClick={() =>
            void request<{ balanced: boolean }>("/reconciliation")
              .then((r) => setBalanced(r.balanced))
              .catch((e) => setError(e.message))
          }
        >
          <ShieldCheck size={14} />
          {balanced === null
            ? "Check ledger"
            : balanced
              ? "Ledger balanced"
              : "Reconciliation failed"}
        </button>
      </div>
      {error && <p className="table-error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Type</th>
              <th>Instrument</th>
              <th>Order / trade ID</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.seq}>
                <td>#{e.seq}</td>
                <td>{e.kind}</td>
                <td>{String(e.payload.symbol ?? "—")}</td>
                <td className="event-id">
                  {String(
                    e.payload.id ??
                      e.payload.order_id ??
                      e.payload.account_id ??
                      "—",
                  )}
                </td>
                <td>{clock(e.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!events.length && (
        <div className="table-empty">
          <Activity size={22} />
          <p>Your account events will appear here.</p>
        </div>
      )}
    </section>
  );
}
function Auth({ onUser }: { onUser: (u: User) => void }) {
  const [signup, setSignup] = useState(false),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function start(guest = false) {
    setBusy(true);
    setError("");
    try {
      const u = await request<User>(
        guest ? "/auth/guest" : signup ? "/auth/signup" : "/auth/login",
        {
          method: "POST",
          body: guest ? undefined : JSON.stringify({ username, password }),
        },
      );
      onUser(u);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <a className="brand" href="#">
        <span className="brand-mark">
          <TrendingUp size={21} />
        </span>
        Paper<span>Trade</span>
      </a>
      <div className="auth-layout">
        <div className="auth-intro">
          <h1>
            Build conviction.
            <br />
            Before capital.
          </h1>
          <p>
            A trading workspace to practice your decisions, understand the order
            book, and follow every dollar.
          </p>
          <div className="auth-features">
            <span>
              <ShieldCheck size={17} />
              $100,000 in virtual funds
            </span>
            <span>
              <Activity size={17} />
              Live simulated order books
            </span>
            <span>
              <BarChart3 size={17} />
              Your portfolio, accounted for
            </span>
          </div>
          <a
            href="https://github.com/Sujendra-23/PaperTrade"
            target="_blank"
            rel="noreferrer"
          >
            Open source, from engine to ledger <ArrowUpRight size={15} />
          </a>
        </div>
        <section className="auth-form-panel">
          <h2>
            {signup ? "Create your account" : "Your next move starts here."}
          </h2>
          <p>
            {signup
              ? "Keep your portfolio and return to your progress."
              : "Sign in to your workspace or explore as a guest."}
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void start();
            }}
          >
            <label htmlFor="username">Username</label>
            <input
              id="username"
              autoComplete="username"
              required
              minLength={3}
              maxLength={40}
              pattern="[a-zA-Z0-9_.\-]+"
              placeholder="Your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete={signup ? "new-password" : "current-password"}
              required
              minLength={10}
              maxLength={128}
              placeholder="At least 10 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button className="primary" disabled={busy}>
              {busy ? (
                <LoaderCircle size={16} className="spin" />
              ) : signup ? (
                "Create account"
              ) : (
                "Sign in"
              )}
              {!busy && <ArrowRight size={16} />}
            </button>
          </form>
          {error && (
            <p role="alert" className="auth-error">
              {error}
            </p>
          )}
          <p className="switch-auth">
            {signup ? "Already have an account?" : "New to PaperTrade?"}{" "}
            <button
              onClick={() => {
                setSignup(!signup);
                setError("");
              }}
            >
              {signup ? "Sign in" : "Create an account"}
            </button>
          </p>
          <div className="auth-divider">
            <span />
            or explore first
            <span />
          </div>
          <button
            className="guest-button"
            disabled={busy}
            onClick={() => void start(true)}
          >
            Start a practice session <ChevronRight size={16} />
          </button>
          <small className="auth-footnote">
            Guest sessions stay in this browser for 7 days.
            <br />
            All prices and funds are simulated.
          </small>
        </section>
      </div>
      <div className="auth-bottom">
        <span>Paper trading. Thoughtfully engineered.</span>
        <span>Go · FastAPI · PostgreSQL · React</span>
      </div>
    </div>
  );
}
export default App;
