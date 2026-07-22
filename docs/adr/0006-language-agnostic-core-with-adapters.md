# 0006 — Language-agnostic core with adapters

**Status:** Accepted

## Context

The first release targets Python/FastAPI, but a PR reviewer that is hard-wired to one language is a
dead end. We want to add TypeScript, Go, Ruby, etc. later without rewriting the orchestration.

## Decision

Keep the core **language-agnostic** behind a **Language Adapter** contract (detect scope, extract the
enclosing symbol, choose analyzers, provide Semgrep rulesets and dependency manifests, …). Implement a
**Python/FastAPI** adapter first (stdlib `ast`, no Tree-sitter in the MVP). Include a **dummy adapter**
used only in tests that runs the full graph, proving the core is not coupled to Python.

## Consequences

- Adding a language is implementing one adapter, not touching the workflow.
- A small amount of upfront abstraction and a test-only adapter to maintain.
- Unknown languages degrade cleanly to generic analysis rather than failing.
