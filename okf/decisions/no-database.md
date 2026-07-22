---
type: Decision Record
title: No database — GitHub as source of truth
description: Persist nothing; GitHub reviews and a hidden marker carry all the state Bicho needs.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0003-no-database-github-as-source-of-truth.md
tags: [decision, no-database, idempotency, statelessness]
timestamp: 2026-07-22T00:00:00Z
---

# Context

A reviewer needs to know what it has already reviewed, but a database (Postgres/Redis) is cost and
operational overhead for a single-tenant portfolio demo.

# Decision

Persist nothing. GitHub is the store: Bicho embeds a hidden HTML **marker** (head SHA + workflow
version + prompt version + model id) in every review it posts, and reads it back to decide whether a
head was already reviewed. See [one review + idempotency](one-review-idempotency-stale-guard.md).

# Consequences

Zero persistence to operate; the PR itself is the ledger. The trade-off is non-durable in-process
work (see [limitations](../limitations.md)), mitigated by the marker, cheap re-runs, and the manual
endpoint.

# Citations

[1] [ADR-0003](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0003-no-database-github-as-source-of-truth.md)
