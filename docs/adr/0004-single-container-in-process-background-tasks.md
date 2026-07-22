# 0004 — Single container, in-process background tasks

**Status:** Accepted

## Context

A webhook must return quickly while the (slow) analysis runs asynchronously. The textbook solution is a
durable queue (Redis/RabbitMQ) with independent worker processes. That is the right choice for high
concurrency — and overkill for a single-tenant portfolio demo that should cost almost nothing to run.

## Decision

Run as a **single Railway service, single container, single instance**. Webhooks schedule the analysis
as an **in-process asyncio background task** in the same FastAPI process. No Celery/Taskiq/RQ/Dramatiq,
no broker, no separate worker. A configurable concurrency semaphore (default 1) bounds overlapping
work. The manual API endpoint runs the *same* use case synchronously.

## Consequences

- Cheapest possible footprint; nothing to operate beyond one container.
- Background tasks are **non-durable**: a restart/redeploy drops in-flight work, and there is **no
  exactly-once guarantee**. Mitigations: the GitHub-marker idempotency guard
  ([ADR-0003](0003-no-database-github-as-source-of-truth.md)), safe/cheap re-runs, and recovery via the
  manual endpoint. Documented in [docs/limitations.md](../limitations.md).
- In-memory coordination (semaphore, delivery-id set) assumes a single instance; horizontal scaling
  would require shared infrastructure.
- **Alternative (roadmap):** a durable queue + independent workers for real high-concurrency use.
