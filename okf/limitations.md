---
type: Reference
title: Limitations
description: Deliberate constraints of the single-container, no-database design, stated honestly.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/limitations.md
tags: [limitations, trade-offs, durability]
timestamp: 2026-07-22T00:00:00Z
---

# Deliberate constraints

These are intentional cost/portfolio choices, documented rather than hidden. See the individual
[decisions](decisions/index.md) for the rationale.

- **Non-durable background tasks.** Webhook-triggered reviews run in-process; a restart or redeploy
  drops an accepted-but-unfinished review. There is **no exactly-once guarantee**. Mitigations: the
  [GitHub-marker idempotency guard](decisions/one-review-idempotency-stale-guard.md), safe/cheap
  re-runs, and recovery via the manual endpoint.
- **Single instance.** In-memory coordination (the concurrency semaphore and the recent-delivery-id
  set) assumes one instance; horizontal scaling would require shared infrastructure.
- **No database / broker / worker.** GitHub is the store; there is no queue and no separate worker
  process. A durable queue with independent workers is the roadmap alternative for high concurrency.
- **Optional scanners.** Semgrep and pip-audit require their binaries (and, for pip-audit, outbound
  network). When absent, Bicho degrades to LLM-only review rather than failing.
- **Model reliability.** LLM analyzers can occasionally time out or return no structured output; the
  pipeline degrades that single analyzer to a diagnostic note rather than failing the review.

# Citations

[1] [docs/limitations.md](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/limitations.md)
