import concurrent.futures
import threading
import uuid

import httpx
import pytest

from papertrade.generated import engine_pb2 as pb
from papertrade.main import app
from papertrade.models import OrderRequest


def place(client, account, key=None, **overrides):
    data = {
        "account_id": account,
        "symbol": "AAPL",
        "side": "BUY",
        "kind": "LIMIT",
        "quantity": 1,
        "price": 18984,
    }
    data.update(overrides)
    if account.startswith("maker-"):
        result = app.state.trading.place(OrderRequest(**data), key or str(uuid.uuid4()))
        return httpx.Response(201, json=result)
    return client.post(
        "/api/orders", json=data, headers={"Idempotency-Key": key or str(uuid.uuid4())}
    )


def test_account_funded(client, account):
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    assert state["account"]["cash"] == 10_000_000
    assert state["account"]["pnl"] == 0


def test_limit_requires_price(client, account):
    assert place(client, account, price=None).status_code == 422


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"quantity": 1001}, "Maximum order size"),
        ({"price": 30000}, "within 5%"),
        ({"side": "SELL"}, "Insufficient available shares"),
        ({"quantity": 1000}, "buying power"),
        ({"symbol": "FAKE"}, "Unsupported symbol"),
        ({"kind": "MARKET", "price": 18984}, "omit price"),
    ],
)
def test_risk(client, account, overrides, reason):
    response = place(client, account, **overrides)
    assert response.status_code == 422
    assert reason in response.json()["detail"]


def test_position_limit_includes_open_buys(client, account):
    with app.state.trading.pool.connection() as db:
        db.execute(
            "UPDATE positions SET quantity=1999 WHERE account_id=%s AND symbol='AAPL'", (account,)
        )
    try:
        assert place(client, account, price=18040).status_code == 201
        response = place(client, account, price=18040)
        assert response.status_code == 422
        assert "Maximum position" in response.json()["detail"]
    finally:
        for order in client.get("/api/snapshot", params={"account_id": account}).json()["orders"]:
            client.delete("/api/orders/" + order["id"], params={"account_id": account})
        with app.state.trading.pool.connection() as db:
            db.execute(
                "UPDATE positions SET quantity=0 WHERE account_id=%s AND symbol='AAPL'", (account,)
            )


def test_idempotent(client, account):
    key = str(uuid.uuid4())
    first = place(client, account, key=key)
    second = place(client, account, key=key)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert place(client, account, key=key, quantity=2).status_code == 409


def test_header_required(client, account):
    assert (
        client.post(
            "/api/orders", json={"symbol": "AAPL", "side": "BUY", "quantity": 1, "price": 18984}
        ).status_code
        == 422
    )


def test_cancel_releases_cash(client, account):
    order = place(client, account, price=18040, quantity=10).json()
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    assert state["account"]["reserved_cash"] == 180400
    response = client.delete("/api/orders/" + order["id"], params={"account_id": account})
    assert response.status_code == 200
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    assert state["account"]["reserved_cash"] == 0
    assert (
        client.delete("/api/orders/" + order["id"], params={"account_id": account}).json()["status"]
        == "CANCELLED"
    )


def test_fill_and_balanced_ledger(client, account):
    maker = place(client, "maker-ask", side="SELL", quantity=5, price=18984).json()
    bought = place(client, account, quantity=3).json()
    assert bought["status"] == "FILLED"
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    aapl = next(p for p in state["positions"] if p["symbol"] == "AAPL")
    assert aapl["quantity"] == 3
    assert state["account"]["cash"] == 10_000_000 - 3 * 18984
    assert client.get("/api/reconciliation").json()["balanced"]
    app.state.trading.cancel(maker["id"], "maker-ask")


def test_market_ioc_releases_remainder(client, account):
    # MSFT has no liquidity in the isolated test engine.
    response = place(client, account, symbol="MSFT", kind="MARKET", price=None, quantity=2)
    assert response.json()["status"] == "CANCELLED"
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    assert state["account"]["reserved_cash"] == 0


def test_100_concurrent_never_overspend(client, account):
    start = threading.Barrier(100)

    def submit(_):
        start.wait(timeout=20)
        return place(client, account, quantity=10, price=18040)

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as pool:
        results = list(pool.map(submit, range(100)))
    accepted = [r for r in results if r.status_code == 201]
    rejected = [r for r in results if r.status_code == 422]
    assert len(accepted) == 55
    assert len(rejected) == 45
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    assert state["account"]["cash"] == 10_000_000
    assert state["account"]["reserved_cash"] == 9_922_000
    assert state["account"]["buying_power"] == 78_000
    assert client.get("/api/reconciliation").json()["balanced"]
    print(
        "\nCONCURRENCY: submitted=100 accepted=55 rejected=45 "
        "reserved_cents=9922000 available_cents=78000 overspend=0"
    )


def test_engine_restart_replays_open_orders(client, account):
    order = place(client, account, symbol="NVDA", price=12762, quantity=7).json()
    app.state.trading.engine.Reset(pb.Empty(), timeout=5)
    state = client.get("/api/snapshot", params={"account_id": account, "symbol": "NVDA"}).json()
    assert any(row["price"] == 12762 and row["quantity"] >= 7 for row in state["book"]["bids"])
    client.delete("/api/orders/" + order["id"], params={"account_id": account})
    assert client.get("/api/reconciliation").json()["balanced"]


def test_crash_after_engine_before_settlement(client, account, monkeypatch):
    trading = app.state.trading
    original = trading.settle

    def crash(*args):
        raise RuntimeError("injected crash after RPC")

    key = str(uuid.uuid4())
    with monkeypatch.context() as m:
        m.setattr(trading, "settle", crash)
        with pytest.raises(RuntimeError, match="injected crash"):
            place(client, account, key=key, symbol="TSLA", price=24850, quantity=2)
    assert trading.dirty
    retried = place(client, account, key=key, symbol="TSLA", price=24850, quantity=2)
    assert retried.status_code == 201
    assert retried.json()["remaining"] == 2
    assert trading.settle == original
    assert client.get("/api/reconciliation").json()["balanced"]


def test_crash_after_fill_before_settlement(client, account, monkeypatch):
    maker = place(client, "maker-ask", symbol="GOOGL", side="SELL", price=17432, quantity=3).json()
    trading = app.state.trading
    key = str(uuid.uuid4())
    with monkeypatch.context() as m:

        def crash(*args):
            raise RuntimeError("injected fill crash")

        m.setattr(trading, "settle", crash)
        with pytest.raises(RuntimeError, match="injected fill crash"):
            place(client, account, key=key, symbol="GOOGL", price=17432, quantity=2)
    retried = place(client, account, key=key, symbol="GOOGL", price=17432, quantity=2)
    assert retried.json()["filled"] == 2
    state = client.get("/api/snapshot", params={"account_id": account}).json()
    assert state["account"]["cash"] == 10_000_000 - 34864
    assert client.get("/api/reconciliation").json()["balanced"]
    app.state.trading.cancel(maker["id"], "maker-ask")


def test_event_cursor(client, account):
    place(client, account)
    place(client, account)
    page = client.get("/api/events?limit=2").json()
    assert len(page["events"]) == 2
    next_page = client.get(f"/api/events?after={page['next_cursor']}&limit=2").json()
    assert next_page["events"][0]["seq"] > page["next_cursor"]


def test_websocket_snapshot(client, account):
    with client.websocket_connect(f"/api/ws?account_id={account}&symbol=AAPL") as ws:
        data = ws.receive_json()
        assert data["account"]["id"] == account
        assert data["symbol"] == "AAPL"
        assert "sequence" in data


def test_no_cross_account_cancel(client, account):
    order = place(client, account, price=18040).json()
    assert (
        client.delete("/api/orders/" + order["id"], params={"account_id": "demo"}).status_code
        == 403
    )


def test_reconciliation(client):
    assert client.get("/api/reconciliation").json()["balanced"] is True


def test_partial_fill_cancel_releases_exact_reservation(client, account):
    # Use AMZN so no resting AAPL orders from this test can interfere.
    maker = place(client, "maker-ask", symbol="AMZN", side="SELL", price=18643, quantity=2).json()
    bought = place(client, account, symbol="AMZN", price=18645, quantity=5).json()
    assert bought["filled"] == 2
    assert bought["remaining"] == 3
    state = client.get("/api/snapshot").json()
    assert state["account"]["cash"] == 10_000_000 - 2 * 18643
    assert state["account"]["reserved_cash"] == 3 * 18645
    client.delete("/api/orders/" + bought["id"])
    assert client.get("/api/snapshot").json()["account"]["reserved_cash"] == 0
    assert app.state.trading.order(maker["id"])["status"] == "FILLED"
    assert client.get("/api/reconciliation").json()["balanced"]


def test_sell_reservation_prevents_oversell_and_releases(client, account):
    place(client, "maker-ask", symbol="AMZN", side="SELL", price=18643, quantity=5)
    place(client, account, symbol="AMZN", price=18643, quantity=5)
    sell = place(client, account, symbol="AMZN", side="SELL", price=19000, quantity=4).json()
    rejected = place(client, account, symbol="AMZN", side="SELL", price=19000, quantity=2)
    assert rejected.status_code == 422
    assert "available shares" in rejected.json()["detail"]
    client.delete("/api/orders/" + sell["id"])
    assert (
        place(client, account, symbol="AMZN", side="SELL", price=19000, quantity=5).status_code
        == 201
    )
    assert client.get("/api/reconciliation").json()["balanced"]


def test_concurrent_same_key_executes_once(client, account):
    key = uuid.uuid4().hex
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: place(client, account, key=key, price=18040), range(20)))
    assert all(r.status_code == 201 for r in results)
    assert len({r.json()["id"] for r in results}) == 1
    assert client.get("/api/snapshot").json()["account"]["reserved_cash"] == 18040


def test_market_partial_cancels_unfilled_reservation(client, account):
    place(client, "maker-ask", symbol="MSFT", side="SELL", price=42876, quantity=2)
    order = place(client, account, symbol="MSFT", kind="MARKET", price=None, quantity=5).json()
    assert order["status"] == "CANCELLED"
    assert order["filled"] == 2 and order["remaining"] == 3
    state = client.get("/api/snapshot").json()
    assert state["account"]["cash"] == 10_000_000 - 2 * 42876
    assert state["account"]["reserved_cash"] == 0
    assert client.get("/api/reconciliation").json()["balanced"]


def test_sell_fill_realizes_pnl(client, account):
    place(client, "maker-ask", symbol="MSFT", side="SELL", price=42876, quantity=2)
    place(client, account, symbol="MSFT", price=42876, quantity=2)
    place(client, "maker-bid", symbol="MSFT", side="BUY", price=42880, quantity=2)
    sold = place(client, account, symbol="MSFT", side="SELL", price=42880, quantity=2).json()
    assert sold["status"] == "FILLED"
    state = client.get("/api/snapshot").json()
    position = next(p for p in state["positions"] if p["symbol"] == "MSFT")
    assert position["quantity"] == position["cost_basis"] == 0
    assert position["realized"] == 8
    assert state["account"]["pnl"] == 8
    # Restore the synthetic reference for independently repeatable tests.
    with app.state.trading.pool.connection() as db:
        db.execute("UPDATE symbols SET last_price=42876 WHERE symbol='MSFT'")
    assert client.get("/api/reconciliation").json()["balanced"]
