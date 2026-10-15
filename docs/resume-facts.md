# Resume-ready facts

Repository: https://github.com/Sujendra-23/PaperTrade

Measured October 15, 2026; methodology and raw outputs: [benchmarks.md](benchmarks.md).

- Go: 12 top-level tests plus 7 matching subtests passed with `-race`.
- Python: 35 PostgreSQL/gRPC integration cases passed.
- In-process Go book: 1,000,000 seeded orders; 2,203,655 orders/sec; p50 0.292 µs; p99 1.541 µs.
- Reservation contention: 100 concurrent submissions; 55 accepted, 45 rejected; 0 overspend; ledger reconciled.
- Guest practice sessions and registered account sign-in, isolated portfolios, risk checks, Redis pub/sub, authenticated WebSockets, and a React dashboard.

Suggested bullets, preserving the measured boundary:

1. Built a Go price-time matching engine exposed over gRPC, benchmarking its in-process order book at **2.20M orders/sec** and **1.54 µs p99** across **1M seeded orders**.
2. Implemented a FastAPI/PostgreSQL double-entry ledger with durable idempotency, cash/share reservations, and restart replay; verified **100 concurrent order submissions with no overspend**.
3. Added pre-trade size, position, price-band, and buying-power checks, plus Redis/WebSocket market streaming and a React portfolio dashboard; validated with **12 Go tests, 7 matching subtests, and 35 Python integration cases**.

Development was assisted by OpenAI Codex. Explain the data structures, accounting convention, failure boundary, benchmark workload, and single-writer limitation in interviews. Do not describe the in-process benchmark as end-to-end gRPC or API throughput. Do not describe simulated prices as exchange data.
