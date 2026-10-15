# PaperTrade

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Go matching engine and gRPC; Python FastAPI and PostgreSQL; Redis pub/sub;
React with TypeScript; Docker Compose; Go race tests, pytest and GitHub Actions.
These technologies are specified in the supplied build brief.

## Users
The author building an engineering portfolio and reviewers evaluating it.
Confirmed: both guest practice sessions and registered users with sign-in.
Each session has an isolated account, portfolio, orders and activity.

## Product Purpose
Place and cancel simulated orders, inspect price-time matching, monitor positions,
and demonstrate correct accounting and measurable engine performance.

## Operating Context
Local Docker Compose environment. Each practice account starts with simulated funds.
A random-walk bot market creates synthetic liquidity through the same trading API.

## Capabilities and Constraints
Limit orders, price-protected IOC market orders, cancellation, partial fills,
one book per symbol, reservations, cash and share journals, reconciliation,
pre-trade risk checks, a durable command/event log, live market data, P&L.
No real money, live exchange prices, broker connection, short selling or leverage.
One API writer per database; local demo, not a hosted financial service.

## Evidence on Hand
The supplied PaperTrade build workflow. Test and benchmark results must come from
actual runs. This repository was developed with OpenAI Codex assistance.

## Product Principles
- Accounting correctness precedes throughput claims.
- Every displayed price is clearly simulated.
- Every order has a clear outcome and every reservation can be released.
- Measurements state the system boundary they measure.
