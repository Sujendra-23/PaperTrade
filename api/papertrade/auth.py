"""Password hashing and opaque, revocable, server-side sessions for the local demo."""

import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, Field

COOKIE = "papertrade_session"


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return salt + ":" + key.hex()


def verify_password(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split(":")[0]), encoded)


def new_session(trading, account_id, response: Response):
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with trading.pool.connection() as db:
        db.execute("DELETE FROM sessions WHERE expires_at<now()")
        db.execute(
            "INSERT INTO sessions(token_hash,account_id) VALUES(%s,%s)", (digest, account_id)
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        max_age=604800,
        secure=trading.config.secure_cookies,
    )


def current_account(request: Request):
    # SameSite cookies plus an explicit Origin check protect browser mutations.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        from urllib.parse import urlsplit

        if urlsplit(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin requests are not allowed")
    token = request.cookies.get(COOKIE, "")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with request.app.state.trading.pool.connection() as db:
        account = db.execute(
            "SELECT a.id,a.name,u.username FROM sessions s JOIN accounts a ON a.id=s.account_id "
            "LEFT JOIN users u ON u.account_id=a.id WHERE s.token_hash=%s AND s.expires_at>now()",
            (digest,),
        ).fetchone()
    if not account:
        raise HTTPException(401, "Sign in or start a practice session")
    return account


def check_account(account, requested):
    if requested and requested != account["id"]:
        raise HTTPException(403, "This account belongs to another session")
    return account["id"]
