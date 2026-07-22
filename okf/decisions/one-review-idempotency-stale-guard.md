---
type: Decision Record
title: One review per run — idempotency marker and stale-head guard
description: Publish exactly one review, never a duplicate, never anchored to a commit that moved.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0008-one-review-idempotency-marker-and-stale-head-guard.md
tags: [decision, idempotency, publishing, github]
timestamp: 2026-07-22T00:00:00Z
---

# Context

Webhooks are redelivered, the same head can be reviewed more than once, and a PR can receive a new
push while a review is being computed. With [no database](no-database.md), the PR must carry the state.

# Decision

Publish exactly **one** GitHub review per run (`commit_id` pinned to the analyzed head). Two graph
guards gate publishing:

- **Idempotency guard** — lists the PR's reviews and parses Bicho's hidden marker; if the current head
  + workflow was already reviewed, it **skips** (unless `force`).
- **Stale-head guard** — re-fetches the head SHA just before publishing and **aborts** if the PR moved.

# Consequences

No duplicate reviews across redeliveries or re-runs, with no datastore. A stale run is dropped rather
than published incorrectly. Un-anchorable findings degrade to summary bullets so the atomic review
POST never fails.

# Citations

[1] [ADR-0008](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0008-one-review-idempotency-marker-and-stale-head-guard.md)
