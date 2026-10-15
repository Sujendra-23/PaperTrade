"""Synthetic liquidity enters through exactly the same coordinator as user orders."""

import asyncio
import logging
import random
import uuid

from fastapi import HTTPException

from .models import OrderRequest
from .trading import SYMBOLS

log = logging.getLogger(__name__)


class Simulator:
    def __init__(self, trading):
        self.trading = trading
        self.rng = random.Random(2026)
        self.quotes = {}

    def step(self, symbol):
        t = self.trading
        for order_id, account_id in self.quotes.get(symbol, []):
            t.cancel(order_id, account_id)
        self.quotes[symbol] = []
        with t.pool.connection() as db:
            last = db.execute(
                "SELECT last_price FROM symbols WHERE symbol=%s", (symbol,)
            ).fetchone()["last_price"]
        shift = self.rng.choice([-5, -3, -1, 1, 3, 5])
        center = last + shift
        spread = max(2, last // 4000)
        for level in range(1, 9):
            for side, account in [("BUY", "maker-bid"), ("SELL", "maker-ask")]:
                price = center + (-1 if side == "BUY" else 1) * spread * level
                qty = self.rng.randint(30, 180) * level
                r = t.place(
                    OrderRequest(
                        account_id=account, symbol=symbol, side=side, price=price, quantity=qty
                    ),
                    str(uuid.uuid4()),
                )
                self.quotes[symbol].append((r["id"], account))
        side = "BUY" if shift > 0 else "SELL"
        t.place(
            OrderRequest(
                account_id="flow-buy" if side == "BUY" else "flow-sell",
                symbol=symbol,
                side=side,
                kind="MARKET",
                quantity=self.rng.randint(2, 25),
            ),
            str(uuid.uuid4()),
        )

    def record_equity(self):
        with self.trading.lock, self.trading.pool.connection() as db:
            db.execute(
                "INSERT INTO equity_history(account_id,equity) "
                "SELECT a.id,a.cash+COALESCE(sum(p.quantity*s.last_price),0) FROM accounts a "
                "LEFT JOIN positions p ON p.account_id=a.id LEFT JOIN symbols s "
                "ON s.symbol=p.symbol WHERE a.kind='USER' GROUP BY a.id"
            )

    def clean_stale_quotes(self):
        with self.trading.pool.connection() as db:
            orders = db.execute(
                "SELECT id,account_id FROM orders WHERE account_id "
                "IN ('maker-bid','maker-ask') AND status IN ('OPEN','PARTIAL')"
            ).fetchall()
        for o in orders:
            self.trading.cancel(o["id"], o["account_id"])

    async def run(self):
        await asyncio.to_thread(self.clean_stale_quotes)
        while True:
            for symbol, _, _ in SYMBOLS:
                try:
                    await asyncio.to_thread(self.step, symbol)
                except HTTPException as exc:
                    log.warning("Simulator risk rejection: %s", exc.detail)
                except Exception:
                    log.exception("Simulator step failed; coordinator will recover on next command")
                await asyncio.sleep(0.25)
            await asyncio.to_thread(self.record_equity)
            await asyncio.sleep(1)
