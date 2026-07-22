---
type: Decision Record
title: Single container, in-process background tasks
description: One instance; webhooks schedule asyncio background tasks — no broker, no worker.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0004-single-container-in-process-background-tasks.md
tags: [decision, deployment, async, single-instance]
timestamp: 2026-07-22T00:00:00Z
---

# Context

A webhook must return quickly while the slow analysis runs asynchronously. The textbook answer is a
durable queue with worker processes — the right choice for high concurrency and overkill for a
single-tenant demo that should cost almost nothing.

# Decision

Run as a single Railway service, single container, single instance. Webhooks schedule the analysis as
an in-process asyncio background task in the same FastAPI process. No Celery/broker/worker. A
concurrency semaphore (default 1) bounds overlapping work; the manual endpoint runs the same use case
synchronously.

# Consequences

Cheapest possible footprint. Background tasks are non-durable (a restart drops in-flight work) with no
exactly-once guarantee — see [limitations](../limitations.md). A durable queue + workers is the
roadmap alternative.

# Citations

[1] [ADR-0004](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0004-single-container-in-process-background-tasks.md)
