import os

os.environ["SIMULATOR_ENABLED"] = "false"
# Tests use an isolated database and engine; never truncate a running demo database.
os.environ.setdefault(
    "DATABASE_URL", "postgresql://papertrade:papertrade@localhost:55432/papertrade_test"
)
os.environ.setdefault("ENGINE_ADDRESS", "localhost:50052")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from papertrade.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def account(client):
    return client.post("/api/auth/guest").json()["id"]


@pytest.fixture(autouse=True)
def clean_open_orders(client):
    # Mutate only the dedicated test database; make reruns independent of old test data.
    from papertrade.main import app

    trading = app.state.trading
    assert trading.config.database_url.rsplit("/", 1)[-1].startswith("papertrade_test")

    def clean():
        with trading.pool.connection() as db:
            orders = db.execute(
                "SELECT id,account_id FROM orders WHERE status IN ('OPEN','PARTIAL')"
            ).fetchall()
        for order in orders:
            trading.cancel(order["id"], order["account_id"])

    clean()
    yield
    clean()
