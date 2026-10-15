# Measured results

Measured October 15, 2026 on the development Mac. These are actual local outputs, not target figures.

## Engine benchmark

```sh
./bench/run.sh
# Equivalent: cd engine && go run ./cmd/bench -n 1000000
```

| Environment | Observed value |
| --- | --- |
| CPU | Apple M4 |
| Logical CPUs / GOMAXPROCS | 10 / 10 |
| Memory | 25,769,803,776 bytes (24 GiB) |
| OS | macOS 27.0, build 26A428, darwin/arm64 |
| Go | go1.27.0 |
| Random seed | 2026 |
| Measurement timestamp | 2026-10-15T16:13:30Z (09:13:30 PDT) |

| Metric | Actual output |
| --- | ---: |
| Orders | 1,000,000 |
| Trades produced | 747,360 |
| Wall time | 0.453791625 seconds |
| Orders / second | 2,203,654.595873161 |
| p50 | 0.292 microseconds |
| p99 | 1.541 microseconds |

Raw machine-readable output: [benchmark-result.json](benchmark-result.json).

The runner pre-generates one million seeded random limit orders in one symbol, roughly balanced BUY/SELL, 101 price points around 10,000 cents, and quantities from 1 through 20. Buyer and seller identities differ so self-trade prevention does not suppress the workload. It runs garbage collection, then submits orders sequentially to the real `book.Engine.Place` implementation. Per-order timing covers the method call, including mutex acquisition, matching and allocations. Throughput includes the per-order timing overhead and trade-count collection. The quantiles use sorted nearest-lower ranks at `(N-1)*p/100`.

**Excluded:** input generation, gRPC, database, risk/ledger transactions, Redis, UI, race instrumentation, and concurrent HTTP ingestion. This is one local run, not a sustained service-load claim or a hardware-independent SLA. No end-to-end throughput number has been measured.

## Correctness and concurrency

- `go vet ./...` and `go test -race -count=1 -json ./...` passed: **12 top-level tests**, including **7 matching subtests**. [Raw JSONL](go-tests.jsonl).
- PostgreSQL and a separate real Go gRPC engine: **35 pytest cases passed**. [JUnit XML](python-tests.xml), [console output](python-test-output.txt).
- One account started with **10,000,000 cents**. A barrier synchronized a 100-worker pool before it submitted **100 BUY orders**, each for **10 shares at 18,040 cents**. **55 were accepted and 45 rejected**. Final cash was **10,000,000 cents**, reservations **9,922,000 cents**, and available cash **78,000 cents**. **No overspend**; ledger and reservations reconciled. This tests reservation contention, not HTTP throughput.
- Crash-injection tests passed after engine execution and after an actual fill before settlement; restart replay preserved the book and balanced accounting.
- Browser smoke checks passed against Docker Compose: [browser-smoke.json](browser-smoke.json).

Reproduce API tests with `./scripts/test-api.sh -v -s`. The suite uses a dedicated test database and engine. Performance runs never use `-race`.
