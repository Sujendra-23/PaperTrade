export interface Instrument {
  symbol: string;
  name: string;
  last_price: number;
  open_price: number;
  updated_at: string;
}
export interface Order {
  id: string;
  account_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  kind: "LIMIT" | "MARKET";
  price: number;
  quantity: number;
  remaining: number;
  filled: number;
  status: string;
  created_at: string;
}
export interface Position {
  symbol: string;
  name: string;
  quantity: number;
  reserved: number;
  cost_basis: number;
  realized: number;
  last_price: number;
  market_value: number;
  unrealized: number;
}
export interface Trade {
  id: string;
  symbol: string;
  price: number;
  quantity: number;
  created_at: string;
  buy_order_id: string;
  sell_order_id: string;
}
export interface Level {
  price: number;
  quantity: number;
  orders: number;
}
export interface Snapshot {
  sequence: number;
  symbol: string;
  market: Instrument[];
  account: {
    id: string;
    name: string;
    cash: number;
    reserved_cash: number;
    initial_equity: number;
    equity: number;
    buying_power: number;
    pnl: number;
  };
  positions: Position[];
  orders: Order[];
  trades: Trade[];
  book: { bids: Level[]; asks: Level[] };
  equity_history: { created_at: string; equity: number }[];
  price_history: { price: number; quantity: number; created_at: string }[];
}
