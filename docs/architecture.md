# Architecture and design decisions

## Matching

The engine uses integer prices and quantities. Each price level holds a FIFO linked list; best prices are maintained by side-specific heaps. A map points order IDs at their resting nodes for cancellation. A mutex serializes book operations, including snapshots; the gRPC server also serializes command-cache and subscriber changes. This is deterministic and race-testable, with no claim of parallel matching inside one book.

Resting liquidity sets the execution price. A market order is immediate-or-cancel with a server-calculated 5% collar; the engine always requires a positive protection price. Encountering the same account's maker order cancels the taker remainder. One symbol's liquidity cannot match another symbol.

The gRPC server caches command results and rejects reuse with a different payload. Trade streams use bounded buffers and disconnect slow subscribers explicitly; clients must resynchronize. The API's authoritative recovery path uses the PostgreSQL command log rather than a gRPC trade subscription, so lost stream notifications cannot lose a settlement.

## Reservations and settlement

A BUY reserves `limit_or_protection_price × remaining_shares`. A SELL reserves shares. Risk counts existing reservations and pending buys. Each fill releases the corresponding part of the reservation and moves actual cash at the execution price. Price improvement therefore immediately returns buying power. Cancels and IOC remainders release everything left.

Cash and positions are nonnegative database-constrained balances; reserved amounts cannot exceed those balances. Commands and settlement use a coordinator lock and row locks. The process holds a dedicated PostgreSQL session advisory lock for its entire life, preventing a second writer for the same database. A broken writer connection fails closed.

## Double-entry convention

The journal is multi-unit. **Never add inventory quantities to dollar amounts.** Reconciliation groups both by journal and by unit.

For a trade of 3 AAPL shares at $190:

| Unit | Debit | Credit | Amount |
| --- | --- | --- | ---: |
| USD (integer cents) | Seller cash | Buyer cash | 57,000 |
| AAPL (whole shares) | Buyer inventory | Seller inventory | 3 |

Initial virtual funding debits account cash or inventory and credits its virtual equity counteraccount. Reconciliation checks journal balance per unit, cash against its journal, inventory against its journal, and cash/share reservations against open orders. Thus a balanced journal alone cannot hide a materialized cash or inventory mismatch.

Cost basis uses integer average-cost allocation; selling the last share removes all remaining basis. Unrealized P&L is marked inventory minus basis; realized P&L records proceeds minus allocated basis. Total P&L is current cash plus marked inventory minus initial funding. USD values remain integer cents through the engine and ledger; the frontend converts to dollars for display.

## Failure recovery

The durable `commands` table is ordered by sequence. An accepted order and its reservation commit before the engine call. Settlement, journals, fills, and command completion commit together afterward. A retry with the same account/key returns the current existing order, and a mismatched request fingerprint is rejected.

On startup or engine boot-ID change, reset the engine, replay all accepted commands in sequence, and settle only commands still pending in SQL. An uncertain RPC or failed settlement marks the coordinator dirty, forcing replay before the next command. Replay rebuilds the engine; it does not create a second journal for already completed commands. Trade IDs derive from order ID and fill index, making replay identities deterministic. Engine-generated timestamps during replay are not substituted for persisted historical timestamps.

The tests cover both a crash after placement and a crash after an actual fill but before SQL settlement, as well as an independent engine reset. There is no distributed two-phase transaction or claim of multi-writer support.

## Streaming

The simulator quotes a ladder around a random-walk center, then submits small crossing flow orders. Bot accounts obey the same reservation, fill, and journal code. Initial prices are synthetic seeds, not historical or live exchange quotes.

The publisher reads committed order/fill events from PostgreSQL, adds current synthetic ticks, and publishes them through Redis. It advances its cursor after publication succeeds. Redis is transient transport; PostgreSQL retains the history. Each WebSocket consumer receives a coherent authenticated snapshot and monotonically increasing database event sequence. Reconnects obtain the current state. Charts show actual trades and equity observations collected during this simulation, without fabricated backfilled history.

## Identity and local hosting

Guest sessions create independent virtual accounts. Registration associates an account with a unique normalized username and a salted scrypt password hash. Opaque random session tokens are hashed in PostgreSQL, expire after seven days, and are revoked on sign-out. Cookies are HttpOnly and SameSite=Strict. HTTP mutations check Origin when present; WebSockets validate Origin and recheck session validity during streaming. Account identifiers supplied by clients must match the authenticated session. Public trade tape responses omit participant and order IDs.

The Compose setup binds ports to localhost and defaults to non-Secure cookies for local HTTP. This is a local engineering demonstration supporting multiple accounts, not a hardened internet deployment. An internet deployment would need TLS with `SECURE_COOKIES=true`, an ingress rate limit, password recovery, managed secrets and migrations, and operational backup/monitoring policies. The internal engine RPCs, including Reset, belong on a private network.

## Deliberate boundaries

- One API writer and in-memory Go books prioritize correctness and inspectable recovery over horizontal write scaling.
- Replay is linear in the retained command log; neither snapshots nor log compaction are implemented. Long-running simulations grow the database and engine command cache.
- No real broker, market-data feed, dividends, splits, commissions, leverage, or short selling.
- Position and ledger reads are transactionally coherent with the coordinator; Redis delivery itself is not durable. A Redis outage interrupts live streaming until reconnect; HTTP trading and snapshots continue.
- The benchmark measures one in-process symbol with a seeded mixed flow. It does not measure RPC, SQL settlement, WebSocket fan-out, or the complete trading platform.
