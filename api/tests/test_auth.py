import uuid

from papertrade.auth import COOKIE


def credentials():
    return {"username": "test-" + uuid.uuid4().hex[:16], "password": "a-long-test-password!"}


def test_signup_logout_login_persists_account(client):
    body = credentials()
    signup = client.post("/api/auth/signup", json=body)
    assert signup.status_code == 201
    account = signup.json()["id"]
    assert "HttpOnly" in signup.headers["set-cookie"]
    assert "SameSite=strict" in signup.headers["set-cookie"]
    assert client.get("/api/auth/session").json()["id"] == account
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/snapshot").status_code == 401
    assert client.post("/api/auth/login", json=body).json()["id"] == account


def test_wrong_password_and_duplicate_username(client):
    body = credentials()
    assert client.post("/api/auth/signup", json=body).status_code == 201
    assert client.post("/api/auth/signup", json=body).status_code == 409
    body["password"] = "incorrect-but-long"
    assert client.post("/api/auth/login", json=body).status_code == 401


def test_guest_isolation(client):
    first = client.post("/api/auth/guest").json()["id"]
    client.post("/api/auth/guest")
    assert client.get("/api/snapshot", params={"account_id": first}).status_code == 403
    response = client.post(
        "/api/orders",
        headers={"Idempotency-Key": "unauthorized"},
        json={"account_id": first, "symbol": "AAPL", "side": "BUY", "quantity": 1, "price": 18984},
    )
    assert response.status_code == 403


def test_signout_revokes_cookie(client):
    client.post("/api/auth/guest")
    saved = client.cookies.get(COOKIE)
    client.post("/api/auth/logout")
    client.cookies.set(COOKIE, saved)
    assert client.get("/api/auth/session").status_code == 401
    client.cookies.clear()


def test_mutation_rejects_foreign_origin(client):
    client.post("/api/auth/guest")
    response = client.post(
        "/api/orders",
        headers={"Origin": "https://unrelated.example", "Idempotency-Key": "csrf"},
        json={"symbol": "AAPL", "side": "BUY", "quantity": 1, "price": 18984},
    )
    assert response.status_code == 403


def test_events_are_private(client):
    client.post("/api/auth/guest")
    response = client.post(
        "/api/orders",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json={"symbol": "AAPL", "side": "BUY", "quantity": 1, "price": 18040},
    )
    order_id = response.json()["id"]
    client.post("/api/auth/guest")
    events = client.get("/api/events?limit=1000").json()["events"]
    assert all(e["payload"].get("id") != order_id for e in events)


def test_expired_session_rejected(client):
    import hashlib

    from papertrade.main import app

    client.post("/api/auth/guest")
    token = client.cookies.get(COOKIE)
    with app.state.trading.pool.connection() as db:
        db.execute(
            "UPDATE sessions SET expires_at=now()-interval '1 second' WHERE token_hash=%s",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
    assert client.get("/api/snapshot").status_code == 401


def test_logged_out_websocket_rejected(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    client.cookies.clear()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws"):
            pass
