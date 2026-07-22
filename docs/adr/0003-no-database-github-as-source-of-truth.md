# 0003 — No database; GitHub is the source of truth

**Status:** Accepted

## Context

The reviewer needs to know whether it has already reviewed a given commit, and to avoid posting
duplicate reviews. The obvious solution is a database. But a database adds cost, operational surface,
and a stateful dependency to what is otherwise a stateless request/response service.

## Decision

Use **no database** (no Postgres/SQLite/Redis/Valkey). **GitHub is the source of truth.** Each review
Bicho publishes embeds a hidden HTML marker (head SHA, workflow version, run fingerprint, model id,
prompt version). Before publishing, Bicho lists existing reviews and skips if a marker already matches
the current head SHA and workflow version (unless `force=true` via the manual endpoint). A bounded
in-memory set of recently seen webhook delivery IDs deduplicates within a process run.

## Consequences

- Dramatically simpler and cheaper: one stateless container, nothing to migrate or back up.
- No transactional guarantees. The in-memory delivery-id dedup does not survive restarts; the
  GitHub-marker check is the durable protection. See
  [ADR-0004](0004-single-container-in-process-background-tasks.md) and
  [docs/limitations.md](../limitations.md).
- Idempotency is eventually correct via GitHub even if a task is retried or redelivered.
