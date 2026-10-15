CREATE TABLE IF NOT EXISTS accounts (
 id text PRIMARY KEY, name text NOT NULL, kind text NOT NULL DEFAULT 'USER',
 cash bigint NOT NULL CHECK(cash >= 0), reserved_cash bigint NOT NULL DEFAULT 0,
 initial_equity bigint NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(reserved_cash >= 0 AND reserved_cash <= cash)
);
CREATE TABLE IF NOT EXISTS symbols (
 symbol text PRIMARY KEY, name text NOT NULL, last_price bigint NOT NULL CHECK(last_price>0),
 open_price bigint NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS positions (
 account_id text REFERENCES accounts(id), symbol text REFERENCES symbols(symbol),
 quantity bigint NOT NULL DEFAULT 0, reserved bigint NOT NULL DEFAULT 0,
 cost_basis bigint NOT NULL DEFAULT 0, realized bigint NOT NULL DEFAULT 0,
 PRIMARY KEY(account_id,symbol), CHECK(quantity>=0 AND reserved>=0 AND reserved<=quantity)
);
CREATE TABLE IF NOT EXISTS orders (
 id text PRIMARY KEY, account_id text NOT NULL REFERENCES accounts(id),
 symbol text NOT NULL REFERENCES symbols(symbol), side text NOT NULL, kind text NOT NULL,
 price bigint NOT NULL, quantity bigint NOT NULL, remaining bigint NOT NULL,
 filled bigint NOT NULL DEFAULT 0, status text NOT NULL,
 idempotency_key text NOT NULL, fingerprint text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(account_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS commands (
 seq bigserial PRIMARY KEY, id text UNIQUE NOT NULL, kind text NOT NULL,
 payload jsonb NOT NULL, state text NOT NULL DEFAULT 'PENDING', result jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS trades (
 id text PRIMARY KEY, symbol text NOT NULL, price bigint NOT NULL, quantity bigint NOT NULL,
 buy_order_id text NOT NULL REFERENCES orders(id), sell_order_id text NOT NULL REFERENCES orders(id),
 buyer_id text NOT NULL, seller_id text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ledger (
 id bigserial PRIMARY KEY, journal_id text NOT NULL, book_account text NOT NULL,
 unit text NOT NULL, debit bigint NOT NULL DEFAULT 0, credit bigint NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK((debit>0 AND credit=0) OR (credit>0 AND debit=0))
);
CREATE TABLE IF NOT EXISTS events (
 seq bigserial PRIMARY KEY, kind text NOT NULL, payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS equity_history (
 id bigserial PRIMARY KEY, account_id text NOT NULL REFERENCES accounts(id),
 equity bigint NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orders_account_time ON orders(account_id,created_at DESC);
CREATE INDEX IF NOT EXISTS trades_symbol_time ON trades(symbol,created_at DESC);
CREATE INDEX IF NOT EXISTS ledger_journal ON ledger(journal_id,unit);
CREATE INDEX IF NOT EXISTS equity_account_time ON equity_history(account_id,id DESC);
CREATE TABLE IF NOT EXISTS users (
 username text PRIMARY KEY, account_id text UNIQUE NOT NULL REFERENCES accounts(id),
 password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash text PRIMARY KEY, account_id text NOT NULL REFERENCES accounts(id),
 expires_at timestamptz NOT NULL DEFAULT now()+interval '7 days'
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
