from fastapi import HTTPException

from .generated import engine_pb2 as pb


def snapshot(trading, account_id="demo", symbol="AAPL"):
    with trading.lock:
        trading.ensure_ready()
        with trading.pool.connection() as db:
            account = db.execute("SELECT * FROM accounts WHERE id=%s", (account_id,)).fetchone()
            if not account or account["kind"] != "USER":
                raise HTTPException(404, "Practice account not found")
            symbols = db.execute("SELECT * FROM symbols ORDER BY symbol").fetchall()
            if symbol not in {s["symbol"] for s in symbols}:
                raise HTTPException(422, "Unsupported symbol")
            positions = db.execute(
                "SELECT p.*,s.last_price,s.name,p.quantity*s.last_price AS market_value,"
                "p.quantity*s.last_price-p.cost_basis AS unrealized FROM positions p "
                "JOIN symbols s USING(symbol) WHERE account_id=%s ORDER BY symbol",
                (account_id,),
            ).fetchall()
            equity = account["cash"] + sum(p["market_value"] for p in positions)
            orders = db.execute(
                "SELECT * FROM orders WHERE account_id=%s AND "
                "(status IN ('PENDING','OPEN','PARTIAL') OR id IN "
                "(SELECT id FROM orders WHERE account_id=%s ORDER BY created_at DESC LIMIT 100)) "
                "ORDER BY created_at DESC",
                (account_id, account_id),
            ).fetchall()
            trades = db.execute(
                "SELECT id,symbol,price,quantity,created_at FROM trades WHERE symbol=%s "
                "ORDER BY created_at DESC LIMIT 60",
                (symbol,),
            ).fetchall()
            history = db.execute(
                "SELECT created_at,equity FROM (SELECT * FROM equity_history WHERE account_id=%s "
                "ORDER BY id DESC LIMIT 120) h ORDER BY id",
                (account_id,),
            ).fetchall()
            prices = db.execute(
                "SELECT price,quantity,created_at FROM (SELECT * FROM trades WHERE symbol=%s "
                "ORDER BY created_at DESC LIMIT 180) t ORDER BY created_at",
                (symbol,),
            ).fetchall()
            seq = db.execute("SELECT COALESCE(max(seq),0) AS seq FROM events").fetchone()["seq"]
        book = trading.engine.GetBook(pb.Symbol(symbol=symbol), timeout=5)
        return {
            "sequence": seq,
            "symbol": symbol,
            "market": symbols,
            "account": {
                **account,
                "equity": equity,
                "buying_power": account["cash"] - account["reserved_cash"],
                "pnl": equity - account["initial_equity"],
            },
            "positions": positions,
            "orders": orders,
            "trades": trades,
            "book": {
                "bids": [
                    {"price": level.price, "quantity": level.quantity, "orders": level.orders}
                    for level in book.bids
                ],
                "asks": [
                    {"price": level.price, "quantity": level.quantity, "orders": level.orders}
                    for level in book.asks
                ],
            },
            "equity_history": history,
            "price_history": prices,
        }
