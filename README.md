# Bicho PR Reviewer

> Automated GitHub Pull Request review agent — it gathers PR context, runs deterministic scanners
> (Semgrep CE, pip-audit) plus LLM-based specialized analyzers, **verifies** findings to cut false
> positives, and publishes a **single** GitHub Review: an executive summary plus multiple **inline
> comments** anchored to the exact file/line/range.

🚧 **Under active construction.** This repository is being built in the open, phase by phase, with
strict TDD and 100% line + branch coverage. It is not yet functional.

## What it will do

- Trigger automatically on a GitHub App **webhook** (PR opened / reopened / synchronize / ready for
  review) and run the analysis as an in-process background task — or on demand via a **manual API
  endpoint** with `dry_run`.
- Route the diff through a typed **LangGraph** workflow with fan-out/fan-in over deterministic
  scanners and specialized analyzers (correctness, security, performance, maintainability, tests,
  contracts), then an **evidence verifier** that reduces false positives.
- Publish one GitHub Review with inline comments — each with category, severity, explanation, impact
  and a recommendation. Findings that can't be anchored to the diff go into the summary.

## Design highlights

- **Single container, no database.** GitHub is the source of truth; idempotency via a hidden review
  marker keyed on the head SHA. Deliberately cheap, single-instance, honestly documented limitations.
- **Language-agnostic core** behind a Language Adapter contract (first adapter: Python/FastAPI).
- **MiniMax-M3** via LangChain's OpenAI-compatible client, behind a provider registry — swap models
  without touching the domain. **LangSmith** for tracing and evals.
- **Deterministic, offline test suite** — no credentials, no network, no real services.

## Tech

Python 3.14 · FastAPI · Pydantic v2 · LangChain / LangGraph v1 · MiniMax-M3 · LangSmith ·
Semgrep Community Edition · pip-audit · uv · pytest + Hypothesis + RESPX · Ruff · Pyright · Docker ·
Railway.

## Status

Phase 1 — foundation (bootstrapping). Documentation, architecture diagrams, and a live demo will land
as the build progresses.

## Acknowledgements

Project structure takes inspiration (no code copied) from the MIT-licensed
[`fastapi-langgraph-agent-production-ready-template`](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template).

## License

[MIT](LICENSE) © 2026 Pablo Jacobi
