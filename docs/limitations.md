# Limitations

Bicho is a portfolio project that deliberately trades operational robustness for a **single, cheap
container**. These limitations are intentional, documented, and appropriate for the goal — not
oversights. A production system with high concurrency would make different choices (a durable queue and
independent workers); see the roadmap and ADRs.

## Non-durable background tasks

Webhook-triggered reviews run as **in-process background tasks** (asyncio) inside the same FastAPI
process — there is no broker, no separate worker, and no durable queue
([ADR-0004](adr/0004-single-container-in-process-background-tasks.md)).

Consequences:
- A task **does not survive a restart or redeploy**. A webhook accepted just before a restart can be
  lost while its analysis is in flight.
- There is **no exactly-once guarantee**.
- Recovery is manual: re-run the review via the manual API endpoint (or GitHub re-delivers the
  webhook). The idempotency guard makes re-runs safe and cheap.

## Single instance

The app is designed to run as **one instance**. In-memory state — the concurrency semaphore and the
recently-seen delivery-id set — is per-process and does **not** coordinate across replicas. Do not
scale horizontally without replacing these with shared infrastructure.

## No database — GitHub is the source of truth

There is no database ([ADR-0003](adr/0003-no-database-github-as-source-of-truth.md)). Idempotency is
achieved by embedding a hidden marker in each published review and checking existing reviews before
publishing again. The in-memory delivery-id deduplication is a best-effort, non-durable optimization on
top of that; it does not survive restarts.

## Privacy: code leaves the process

To analyze a PR, relevant code fragments and diffs are sent to the configured LLM provider (MiniMax)
and, when tracing is enabled, to LangSmith. Context is minimized, secrets are scrubbed from logs, and
tracing can be disabled — but be aware that snippets of the reviewed repository are transmitted to
those third parties. Do not point Bicho at a repository whose contents you may not share with them.

## Scope

The first release targets Python/FastAPI repositories. The core is language-agnostic (a dummy adapter
proves it in tests), but only the Python adapter is implemented; other languages degrade to generic
analysis.
