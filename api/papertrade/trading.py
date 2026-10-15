"""Single-writer coordinator: durable intents, reservations, replay, and settlement."""

import hashlib
import json
import logging
import threading
import uuid
from pathlib import Path

import grpc
import psycopg
from fastapi import HTTPException
from google.protobuf.json_format import MessageToDict
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .config import Settings
from .generated import engine_pb2 as pb
from .generated.engine_pb2_grpc import MatchingEngineStub
from .models import OrderRequest

log = logging.getLogger(__name__)
SYMBOLS = [
    ("AAPL", "Apple Inc.", 18984),
    ("NVDA", "NVIDIA Corporation", 12762),
    ("MSFT", "Microsoft Corporation", 42876),
    ("TSLA", "Tesla, Inc.", 24850),
    ("AMZN", "Amazon.com, Inc.", 18643),
    ("GOOGL", "Alphabet Inc.", 17432),
]
OPEN = ("PENDING", "OPEN", "PARTIAL")
WRITER_LOCK = 74193201


def event(db, kind, payload):
    db.execute("INSERT INTO events(kind,payload) VALUES(%s,%s)", (kind, Jsonb(payload)))


def journal(db, journal_id, unit, debit_account, credit_account, amount):
    if amount <= 0:
        return
    db.execute(
        "INSERT INTO ledger(journal_id,unit,book_account,debit,credit) "
        "VALUES(%s,%s,%s,%s,0),(%s,%s,%s,0,%s)",
        (journal_id, unit, debit_account, amount, journal_id, unit, credit_account, amount),
    )


class Trading:
    def __init__(self, config: Settings):
        self.config = config
        self.lock = threading.RLock()
        self.pool = ConnectionPool(
            config.database_url,
            min_size=1,
            max_size=12,
            open=True,
            kwargs={"row_factory": dict_row},
        )
        self.pool.wait(timeout=30)
        # A session-scoped lock prevents a second API writer, including another process.
        self.writer = psycopg.connect(config.database_url, autocommit=True)
        if not self.writer.execute("SELECT pg_try_advisory_lock(%s)", (WRITER_LOCK,)).fetchone()[0]:
            self.writer.close()
            self.pool.close()
            raise RuntimeError(
                "One API writer per database is supported; another writer is running"
            )
        self.channel = grpc.insecure_channel(config.engine_address)
        grpc.channel_ready_future(self.channel).result(timeout=30)
        self.engine = MatchingEngineStub(self.channel)
        self.boot = ""
        self.dirty = True
        with self.pool.connection() as db:
            db.execute(Path(__file__).with_name("schema.sql").read_text())
            for symbol, name, price in SYMBOLS:
                db.execute(
                    "INSERT INTO symbols(symbol,name,last_price,open_price) VALUES(%s,%s,%s,%s) "
                    "ON CONFLICT DO NOTHING",
                    (symbol, name, price, price),
                )
        self.create_account("Practice account", account_id="demo")
        for bot in ("maker-bid", "maker-ask", "flow-buy", "flow-sell"):
            self.create_account(bot, account_id=bot, bot=True)
        self.recover()

    def close(self):
        self.channel.close()
        self.writer.close()
        self.pool.close()

    def create_account(self, name, account_id=None, bot=False):
        with self.lock, self.pool.connection() as db:
            account_id = account_id or str(uuid.uuid4())
            cash = 1_000_000_000_000 if bot else 10_000_000
            qty = 100_000 if bot else 0
            equity = cash + sum(p * qty for _, _, p in SYMBOLS)
            created = db.execute(
                "INSERT INTO accounts(id,name,kind,cash,initial_equity) VALUES(%s,%s,%s,%s,%s) "
                "ON CONFLICT DO NOTHING RETURNING id",
                (account_id, name, "BOT" if bot else "USER", cash, equity),
            ).fetchone()
            if created:
                journal(
                    db,
                    f"fund:{account_id}",
                    "USD",
                    f"{account_id}:cash",
                    f"{account_id}:equity",
                    cash,
                )
                for symbol, _, price in SYMBOLS:
                    db.execute(
                        "INSERT INTO positions(account_id,symbol,quantity,cost_basis) "
                        "VALUES(%s,%s,%s,%s)",
                        (account_id, symbol, qty, qty * price),
                    )
                    journal(
                        db,
                        f"fund:{account_id}:{symbol}",
                        symbol,
                        f"{account_id}:inventory",
                        f"{account_id}:equity",
                        qty,
                    )
                db.execute(
                    "INSERT INTO equity_history(account_id,equity) VALUES(%s,%s)",
                    (account_id, equity),
                )
                event(db, "account.created", {"account_id": account_id})
            return {"id": account_id, "name": name}

    def rpc(self, command):
        p = command["payload"]
        if command["kind"] == "PLACE":
            return self.engine.PlaceOrder(pb.Order(**p), timeout=10)
        return self.engine.CancelOrder(pb.Cancel(**p), timeout=10)

    def recover(self):
        """Replay committed commands; finish durable pending intents exactly once in SQL."""
        with self.lock:
            state = self.engine.Reset(pb.Empty(), timeout=10)
            self.boot = state.boot_id
            with self.pool.connection() as db:
                commands = db.execute("SELECT * FROM commands ORDER BY seq").fetchall()
            for command in commands:
                result = self.rpc(command)
                if command["state"] == "PENDING":
                    self.settle(command, result)
            self.dirty = False
            log.info("Recovered %d engine commands", len(commands))

    def ensure_ready(self):
        # A broken writer connection must fail closed, rather than lose exclusivity silently.
        self.writer.execute("SELECT 1")
        state = self.engine.Health(pb.Empty(), timeout=5)
        if self.dirty or state.boot_id != self.boot:
            self.recover()

    def _execute(self, command):
        try:
            result = self.rpc(command)
            self.settle(command, result)
        except Exception:
            self.dirty = True
            raise

    def place(self, request: OrderRequest, key: str):
        if not key or len(key) > 160:
            raise HTTPException(400, "Idempotency-Key must contain 1–160 characters")
        fingerprint = hashlib.sha256(
            json.dumps(request.model_dump(), sort_keys=True).encode()
        ).hexdigest()
        with self.lock:
            self.ensure_ready()
            with self.pool.connection() as db:
                previous = db.execute(
                    "SELECT * FROM orders WHERE account_id=%s AND idempotency_key=%s",
                    (request.account_id, key),
                ).fetchone()
                if previous:
                    if previous["fingerprint"] != fingerprint:
                        raise HTTPException(
                            409, "Idempotency-Key already used for a different order"
                        )
                    return self.serialize_order(previous)
                account = db.execute(
                    "SELECT * FROM accounts WHERE id=%s FOR UPDATE", (request.account_id,)
                ).fetchone()
                if not account:
                    raise HTTPException(404, "Account not found")
                symbol = db.execute(
                    "SELECT * FROM symbols WHERE symbol=%s", (request.symbol,)
                ).fetchone()
                if not symbol:
                    raise HTTPException(422, "Unsupported symbol")
                position = db.execute(
                    "SELECT * FROM positions WHERE account_id=%s AND symbol=%s FOR UPDATE",
                    (request.account_id, request.symbol),
                ).fetchone()
                price = self.risk(db, request, account, symbol, position)
                order_id = str(uuid.uuid4())
                db.execute(
                    "INSERT INTO orders(id,account_id,symbol,side,kind,price,quantity,remaining,"
                    "status,idempotency_key,fingerprint) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        order_id,
                        request.account_id,
                        request.symbol,
                        request.side,
                        request.kind,
                        price,
                        request.quantity,
                        request.quantity,
                        "PENDING",
                        key,
                        fingerprint,
                    ),
                )
                if request.side == "BUY":
                    db.execute(
                        "UPDATE accounts SET reserved_cash=reserved_cash+%s WHERE id=%s",
                        (price * request.quantity, request.account_id),
                    )
                else:
                    db.execute(
                        "UPDATE positions SET reserved=reserved+%s "
                        "WHERE account_id=%s AND symbol=%s",
                        (request.quantity, request.account_id, request.symbol),
                    )
                payload = {
                    "id": order_id,
                    "account_id": request.account_id,
                    "symbol": request.symbol,
                    "side": request.side,
                    "kind": request.kind,
                    "price": price,
                    "quantity": request.quantity,
                }
                command = {"id": order_id, "kind": "PLACE", "payload": payload}
                db.execute(
                    "INSERT INTO commands(id,kind,payload) VALUES(%s,%s,%s)",
                    (order_id, "PLACE", Jsonb(payload)),
                )
                event(db, "order.accepted", payload)
            self._execute(command)
            return self.order(order_id)

    def risk(self, db, r, account, symbol, position):
        max_size = 10_000 if account["kind"] == "BOT" else self.config.max_order_size
        max_pos = 1_000_000 if account["kind"] == "BOT" else self.config.max_position
        if r.quantity > max_size:
            raise HTTPException(422, f"Maximum order size is {max_size} shares")
        last = symbol["last_price"]
        if r.kind == "LIMIT" and r.price is None:
            raise HTTPException(422, "A limit price in cents is required")
        if r.kind == "MARKET" and r.price is not None:
            raise HTTPException(422, "Market orders use a server-set protection price; omit price")
        # Round inward: no fill can exceed the 5% collar.
        price = (
            r.price
            if r.kind == "LIMIT"
            else (last * 105 // 100 if r.side == "BUY" else (last * 95 + 99) // 100)
        )
        if abs(price - last) * 100 > last * 5:
            raise HTTPException(422, "Price must be within 5% of the last trade")
        if r.side == "BUY":
            pending = db.execute(
                "SELECT COALESCE(sum(remaining),0) AS qty FROM orders WHERE account_id=%s "
                "AND symbol=%s AND side='BUY' AND status IN ('PENDING','OPEN','PARTIAL')",
                (r.account_id, r.symbol),
            ).fetchone()["qty"]
            if position["quantity"] + pending + r.quantity > max_pos:
                raise HTTPException(
                    422, f"Maximum position is {max_pos} shares including open buys"
                )
            if price * r.quantity > account["cash"] - account["reserved_cash"]:
                raise HTTPException(422, "Insufficient buying power after open-order reservations")
        elif r.quantity > position["quantity"] - position["reserved"]:
            raise HTTPException(422, "Insufficient available shares; short selling is disabled")
        return price

    def release(self, db, order):
        qty = order["remaining"]
        if order["side"] == "BUY":
            db.execute(
                "UPDATE accounts SET reserved_cash=reserved_cash-%s WHERE id=%s",
                (order["price"] * qty, order["account_id"]),
            )
        else:
            db.execute(
                "UPDATE positions SET reserved=reserved-%s WHERE account_id=%s AND symbol=%s",
                (qty, order["account_id"], order["symbol"]),
            )

    def settle(self, command, result):
        with self.pool.connection() as db:
            saved = db.execute(
                "SELECT state FROM commands WHERE id=%s FOR UPDATE", (command["id"],)
            ).fetchone()
            if saved["state"] == "DONE":
                return
            for trade in result.trades:
                self.fill(db, trade)
            order = db.execute(
                "SELECT * FROM orders WHERE id=%s FOR UPDATE", (result.order_id,)
            ).fetchone()
            if result.status == "CANCELLED":
                self.release(db, order)
            db.execute("UPDATE orders SET status=%s WHERE id=%s", (result.status, result.order_id))
            result_json = MessageToDict(result, preserving_proto_field_name=True)
            db.execute(
                "UPDATE commands SET state='DONE',result=%s WHERE id=%s",
                (Jsonb(result_json), command["id"]),
            )
            event(db, "order." + result.status.lower(), {"id": result.order_id, **result_json})

    def fill(self, db, t):
        buy = db.execute(
            "SELECT * FROM orders WHERE id=%s FOR UPDATE", (t.buy_order_id,)
        ).fetchone()
        amount = t.price * t.quantity
        db.execute(
            "UPDATE accounts SET cash=cash-%s,reserved_cash=reserved_cash-%s WHERE id=%s",
            (amount, buy["price"] * t.quantity, t.buyer_id),
        )
        db.execute("UPDATE accounts SET cash=cash+%s WHERE id=%s", (amount, t.seller_id))
        seller_pos = db.execute(
            "SELECT * FROM positions WHERE account_id=%s AND symbol=%s FOR UPDATE",
            (t.seller_id, t.symbol),
        ).fetchone()
        removed_basis = seller_pos["cost_basis"] * t.quantity // seller_pos["quantity"]
        db.execute(
            "UPDATE positions SET quantity=quantity-%s,reserved=reserved-%s,"
            "cost_basis=cost_basis-%s,realized=realized+%s "
            "WHERE account_id=%s AND symbol=%s",
            (t.quantity, t.quantity, removed_basis, amount - removed_basis, t.seller_id, t.symbol),
        )
        db.execute(
            "UPDATE positions SET quantity=quantity+%s,cost_basis=cost_basis+%s "
            "WHERE account_id=%s AND symbol=%s",
            (t.quantity, amount, t.buyer_id, t.symbol),
        )
        for order_id in (t.buy_order_id, t.sell_order_id):
            db.execute(
                "UPDATE orders SET remaining=remaining-%s,filled=filled+%s,"
                "status=CASE WHEN remaining=%s THEN 'FILLED' ELSE 'PARTIAL' END WHERE id=%s",
                (t.quantity, t.quantity, t.quantity, order_id),
            )
        db.execute(
            "INSERT INTO trades(id,symbol,price,quantity,buy_order_id,sell_order_id,"
            "buyer_id,seller_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                t.id,
                t.symbol,
                t.price,
                t.quantity,
                t.buy_order_id,
                t.sell_order_id,
                t.buyer_id,
                t.seller_id,
            ),
        )
        journal(db, t.id, "USD", f"{t.seller_id}:cash", f"{t.buyer_id}:cash", amount)
        journal(
            db, t.id, t.symbol, f"{t.buyer_id}:inventory", f"{t.seller_id}:inventory", t.quantity
        )
        db.execute(
            "UPDATE symbols SET last_price=%s,updated_at=now() WHERE symbol=%s", (t.price, t.symbol)
        )
        event(db, "trade", MessageToDict(t, preserving_proto_field_name=True))

    def cancel(self, order_id, account_id):
        with self.lock:
            self.ensure_ready()
            with self.pool.connection() as db:
                order = db.execute(
                    "SELECT * FROM orders WHERE id=%s AND account_id=%s FOR UPDATE",
                    (order_id, account_id),
                ).fetchone()
                if not order:
                    raise HTTPException(404, "Order not found")
                if order["status"] not in OPEN:
                    return self.serialize_order(order)
                command_id = "cancel:" + order_id
                payload = {
                    "command_id": command_id,
                    "order_id": order_id,
                    "account_id": account_id,
                    "symbol": order["symbol"],
                }
                db.execute(
                    "INSERT INTO commands(id,kind,payload) VALUES(%s,%s,%s)",
                    (command_id, "CANCEL", Jsonb(payload)),
                )
                command = {"id": command_id, "kind": "CANCEL", "payload": payload}
                event(db, "order.cancel_requested", payload)
            self._execute(command)
            return self.order(order_id)

    @staticmethod
    def serialize_order(row):
        return {**row, "created_at": row["created_at"].isoformat()}

    def order(self, order_id):
        with self.pool.connection() as db:
            row = db.execute("SELECT * FROM orders WHERE id=%s", (order_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Order not found")
            return self.serialize_order(row)

    def reconcile(self):
        with self.pool.connection() as db:
            units = db.execute(
                "SELECT unit,sum(debit)::bigint AS debits,"
                "sum(credit)::bigint AS credits FROM ledger GROUP BY unit "
                "ORDER BY unit"
            ).fetchall()
            bad = db.execute(
                "SELECT journal_id,unit FROM ledger GROUP BY journal_id,unit "
                "HAVING sum(debit)<>sum(credit)"
            ).fetchall()
            cash_mismatch = db.execute(
                "SELECT a.id FROM accounts a LEFT JOIN ledger l ON l.book_account=a.id||':cash' "
                "AND l.unit='USD' GROUP BY a.id HAVING a.cash<>COALESCE(sum(l.debit-l.credit),0)"
            ).fetchall()
            position_mismatch = db.execute(
                "SELECT p.account_id,p.symbol FROM positions p LEFT JOIN ledger l "
                "ON l.book_account=p.account_id||':inventory' AND l.unit=p.symbol "
                "GROUP BY p.account_id,p.symbol,p.quantity "
                "HAVING p.quantity<>COALESCE(sum(l.debit-l.credit),0)"
            ).fetchall()
            reservation_mismatch = db.execute(
                "SELECT a.id FROM accounts a LEFT JOIN orders o ON o.account_id=a.id "
                "AND o.side='BUY' AND o.status IN ('PENDING','OPEN','PARTIAL') "
                "GROUP BY a.id HAVING a.reserved_cash<>COALESCE(sum(o.price*o.remaining),0)"
            ).fetchall()
            share_reservation_mismatch = db.execute(
                "SELECT p.account_id,p.symbol FROM positions p LEFT JOIN orders o "
                "ON o.account_id=p.account_id AND o.symbol=p.symbol AND o.side='SELL' "
                "AND o.status IN ('PENDING','OPEN','PARTIAL') "
                "GROUP BY p.account_id,p.symbol,p.reserved "
                "HAVING p.reserved<>COALESCE(sum(o.remaining),0)"
            ).fetchall()
            return {
                "balanced": not any(
                    (
                        bad,
                        cash_mismatch,
                        position_mismatch,
                        reservation_mismatch,
                        share_reservation_mismatch,
                    )
                ),
                "units": units,
                "unbalanced_journals": bad,
                "cash_mismatches": cash_mismatch,
                "position_mismatches": position_mismatch,
                "reservation_mismatches": reservation_mismatch,
                "share_reservation_mismatches": share_reservation_mismatch,
            }
