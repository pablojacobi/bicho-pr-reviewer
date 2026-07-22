# 0002 — Start clean from the FastAPI/LangGraph template

**Status:** Accepted

## Context

We evaluated [`wassim249/fastapi-langgraph-agent-production-ready-template`](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
(MIT) as a scaffold. The audit found it is architected around a **stateful, multi-user, Postgres-backed
conversational chatbot**: pgvector + mem0 long-term memory, JWT auth/login, a Prometheus/Grafana stack,
Langfuse tracing, and — notably — **no test suite**. That is close to the inverse of a stateless,
single-container PR reviewer with no database and no users.

## Decision

**Start clean.** Build a minimal FastAPI + (later) LangGraph skeleton and borrow only good *structural
practices* from the template — not its code. Do not clone or fork it. Keep a courtesy attribution in
the README.

## Consequences

- A smaller, honest codebase that matches the actual product, rather than one we must gut.
- We implement configuration, logging, the LLM provider layer, and tests ourselves (they either don't
  fit or don't exist in the template).
- Because no substantial portion is copied, the MIT license imposes no attribution obligation; we keep
  the acknowledgement anyway as good practice.
