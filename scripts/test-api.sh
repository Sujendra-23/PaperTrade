#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
docker compose --profile test up -d --build --wait postgres redis test-engine
exists=$(docker compose exec -T postgres psql -U papertrade -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='papertrade_test'")
if [ "$exists" != "1" ]; then
  docker compose exec -T postgres createdb -U papertrade papertrade_test
fi
cd api
DATABASE_URL=postgresql://papertrade:papertrade@localhost:55432/papertrade_test ENGINE_ADDRESS=localhost:50052 uv run pytest "$@"
