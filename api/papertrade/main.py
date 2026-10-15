import asyncio
import contextlib
import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Annotated

import grpc
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from .auth import (
    COOKIE,
    Credentials,
    check_account,
    current_account,
    new_session,
    password_hash,
    verify_password,
)
from .config import settings
from .models import OrderRequest
from .simulator import Simulator
from .trading import Trading
from .views import snapshot

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
CHANNEL = "papertrade:updates"


async def publish_updates(app):
    # PostgreSQL is the durable outbox. Publish only committed events and advance
    # the local cursor only after Redis acknowledges the publication.
    with app.state.trading.pool.connection() as db:
        cursor = db.execute("SELECT COALESCE(max(seq),0) AS seq FROM events").fetchone()["seq"]
    while True:
        try:
            with app.state.trading.pool.connection() as db:
                events = db.execute(
                    "SELECT * FROM events WHERE seq>%s ORDER BY seq LIMIT 1000", (cursor,)
                ).fetchall()
                ticks = db.execute(
                    "SELECT symbol,last_price,updated_at FROM symbols ORDER BY symbol"
                ).fetchall()
            next_cursor = events[-1]["seq"] if events else cursor
            payload = {"sequence": next_cursor, "events": events, "ticks": ticks}
            await app.state.redis.publish(CHANNEL, json.dumps(jsonable_encoder(payload)))
            cursor = next_cursor
            app.state.redis_ok = True
        except Exception:
            app.state.redis_ok = False
            log.warning("Redis publication unavailable; retrying")
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app):
    app.state.trading = await asyncio.to_thread(Trading, settings)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis_ok = False
    tasks = [asyncio.create_task(publish_updates(app))]
    if settings.simulator_enabled:
        tasks.append(asyncio.create_task(Simulator(app.state.trading).run()))
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # to_thread work may outlive cancellation; drain under the coordinator lock.
        def close_trading():
            with app.state.trading.lock:
                app.state.trading.close()

        await asyncio.to_thread(close_trading)
        await app.state.redis.aclose()


app = FastAPI(
    title="PaperTrade",
    version="0.1.0",
    lifespan=lifespan,
    description="Local paper-trading sandbox. All prices and funds are simulated.",
)


@app.exception_handler(grpc.RpcError)
async def engine_error(request: Request, exc: grpc.RpcError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Matching engine unavailable. Please retry; reuse the same order key."},
    )


@app.get("/api/health")
def health():
    trading = app.state.trading
    with trading.lock:
        trading.ensure_ready()
    return {
        "status": "ok",
        "engine": "ready",
        "redis": "ready" if app.state.redis_ok else "unavailable",
        "simulation": True,
    }


@app.get("/api/auth/session")
def session(account=Depends(current_account)):
    return account


@app.post("/api/auth/guest", status_code=201)
def guest(response: Response):
    account = app.state.trading.create_account("Practice account")
    new_session(app.state.trading, account["id"], response)
    return {**account, "username": None}


@app.post("/api/auth/signup", status_code=201)
def signup(credentials: Credentials, response: Response):
    trading = app.state.trading
    username = credentials.username.lower()
    with trading.lock:
        with trading.pool.connection() as db:
            if db.execute("SELECT 1 FROM users WHERE username=%s", (username,)).fetchone():
                raise HTTPException(409, "Username is already taken")
        encoded = password_hash(credentials.password)
        account = trading.create_account(credentials.username)
        with trading.pool.connection() as db:
            db.execute(
                "INSERT INTO users(username,account_id,password_hash) VALUES(%s,%s,%s)",
                (username, account["id"], encoded),
            )
        new_session(trading, account["id"], response)
    return {**account, "username": username}


@app.post("/api/auth/login")
def login(credentials: Credentials, response: Response):
    trading = app.state.trading
    with trading.pool.connection() as db:
        user = db.execute(
            "SELECT * FROM users WHERE username=%s", (credentials.username.lower(),)
        ).fetchone()
    # Match the expensive hash path for unknown users too.
    encoded = user["password_hash"] if user else password_hash(secrets.token_hex(16))
    valid = verify_password(credentials.password, encoded)
    if not user or not valid:
        raise HTTPException(401, "Incorrect username or password")
    new_session(trading, user["account_id"], response)
    return {"id": user["account_id"], "username": user["username"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, account=Depends(current_account)):
    token = request.cookies.get(COOKIE, "")
    with app.state.trading.pool.connection() as db:
        db.execute(
            "DELETE FROM sessions WHERE token_hash=%s",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
    response.delete_cookie(COOKIE)
    return {"signed_out": True}


@app.get("/api/snapshot")
def get_snapshot(
    account_id: str | None = None, symbol: str = "AAPL", account=Depends(current_account)
):
    return snapshot(app.state.trading, check_account(account, account_id), symbol)


@app.post("/api/orders", status_code=201)
def place_order(
    request: OrderRequest,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=160)],
    account=Depends(current_account),
):
    try:
        account_id = check_account(account, request.account_id)
        return app.state.trading.place(
            request.model_copy(update={"account_id": account_id}), idempotency_key
        )
    except grpc.RpcError as exc:
        raise HTTPException(
            503, "Matching engine unavailable; retry with the same Idempotency-Key"
        ) from exc


@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, account_id: str | None = None, account=Depends(current_account)):
    return app.state.trading.cancel(order_id, check_account(account, account_id))


@app.get("/api/reconciliation")
def reconciliation(account=Depends(current_account)):
    with app.state.trading.lock:
        return app.state.trading.reconcile()


@app.get("/api/events")
def events(
    after: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    account=Depends(current_account),
):
    with app.state.trading.pool.connection() as db:
        rows = db.execute(
            "SELECT * FROM events WHERE seq>%s AND (payload->>'account_id'=%s "
            "OR payload->>'buyer_id'=%s OR payload->>'seller_id'=%s "
            "OR payload->>'id' IN (SELECT id FROM orders WHERE account_id=%s) "
            "OR payload->>'order_id' IN (SELECT id FROM orders WHERE account_id=%s)) "
            "ORDER BY seq LIMIT %s",
            (
                after,
                account["id"],
                account["id"],
                account["id"],
                account["id"],
                account["id"],
                limit,
            ),
        ).fetchall()
    return {"events": rows, "next_cursor": rows[-1]["seq"] if rows else after}


@app.websocket("/api/ws")
async def websocket(ws: WebSocket, account_id: str | None = None, symbol: str = "AAPL"):
    # WebSockets bypass HTTP dependencies, so authenticate before accepting.
    origin = ws.headers.get("origin")
    from urllib.parse import urlsplit

    if origin and urlsplit(origin).netloc != ws.headers.get("host"):
        await ws.close(code=1008)
        return
    token = ws.cookies.get(COOKIE, "")
    with app.state.trading.pool.connection() as db:
        session_row = db.execute(
            "SELECT account_id FROM sessions WHERE token_hash=%s AND expires_at>now()",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
    if not session_row or (account_id and account_id != session_row["account_id"]):
        await ws.close(code=1008)
        return
    account_id = session_row["account_id"]
    await ws.accept()
    try:
        async with app.state.redis.pubsub() as pubsub:
            await pubsub.subscribe(CHANNEL)
            while True:
                with app.state.trading.pool.connection() as db:
                    active = db.execute(
                        "SELECT 1 FROM sessions WHERE token_hash=%s AND expires_at>now()",
                        (hashlib.sha256(token.encode()).hexdigest(),),
                    ).fetchone()
                if not active:
                    await ws.close(code=1008, reason="Session expired; sign in again")
                    return
                data = await asyncio.to_thread(snapshot, app.state.trading, account_id, symbol)
                await ws.send_json(jsonable_encoder(data))
                # Every publication triggers a current, coherent snapshot. A timeout also
                # refreshes the client; sequence numbers let it detect missed notifications.
                await pubsub.get_message(ignore_subscribe_messages=True, timeout=2)
                await asyncio.sleep(0.15)
    except (WebSocketDisconnect, RuntimeError):
        return
    except HTTPException as exc:
        await ws.close(code=1008, reason=str(exc.detail))
    except Exception:
        log.exception("WebSocket disconnected; client should reconnect")
        with contextlib.suppress(RuntimeError):
            await ws.close(code=1013, reason="Stream unavailable; reconnecting")
