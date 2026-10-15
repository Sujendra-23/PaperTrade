# PaperTrade engineering guide

Go price-time matching engine over gRPC; FastAPI/PostgreSQL risk, reservations,
double-entry journals and durable command recovery; Redis pub/sub and WebSockets;
React/TypeScript dashboard. Docker Compose runs the stack.

Never invent metrics; every number comes from a test or benchmark output.
Keep money as integer cents and positions as whole shares. Never use floating-point
money in the engine or ledger. Never bypass risk or accounting for simulator orders.
Run `go test -race ./...` in engine, `uv run pytest` in api, and `npm run check`
in web. Database tests need PostgreSQL and the Go engine (see README).
One API writer per database; a PostgreSQL advisory lock enforces this constraint.
The command journal is authoritative; recover/replay the in-memory engine before
accepting commands after a restart. No real broker or real-money connectivity.

Development assisted by OpenAI Codex. Do not claim a different tool was used.
