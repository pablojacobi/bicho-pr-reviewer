---
type: Overview
title: Bicho PR Reviewer
description: An automated GitHub PR review agent that publishes one verified review with inline comments.
resource: https://github.com/pablojacobi/bicho-pr-reviewer
tags: [overview, code-review, llm, github]
timestamp: 2026-07-22T00:00:00Z
---

# What it is

Bicho PR Reviewer analyzes a GitHub Pull Request and publishes **one** GitHub Review: an executive
summary plus multiple **inline comments** anchored to the exact file, line, and range, each carrying
a category, severity, explanation, impact, and recommendation. Findings that cannot be anchored to
the diff are surfaced in the summary instead.

It is a portfolio project, so architecture, security, tests, docs, and git history are treated as
first-class deliverables. The first version targets Python/FastAPI repositories, but the core stays
language-agnostic behind a [language-adapter contract](decisions/language-agnostic-core.md).

# What it does

- Triggers automatically on a GitHub App **webhook** (PR opened / reopened / synchronize /
  ready-for-review) and runs the analysis as an in-process background task — or on demand via a
  manual API endpoint (`POST /reviews`) with `dry_run` to preview a review without posting. See
  [running a review](operations/running-a-review.md).
- Routes the diff through a typed **LangGraph** workflow with fan-out/fan-in over deterministic
  scanners (Semgrep CE, pip-audit) and six specialized LLM analyzers, then a verifier that reduces
  false positives. See the [review pipeline](review-pipeline.md).
- Publishes exactly one review, guarded against duplicates and stale commits. See
  [one review, idempotency, and the stale-head guard](decisions/one-review-idempotency-stale-guard.md).

# Signal over volume

Only concrete, actionable, PR-introduced, evidence-backed, **verified** findings are published.
"No confirmed issues found" is a valid, good result. Style already covered by linters is out of scope.

# Stack

Python 3.14 · FastAPI · Pydantic v2 · LangChain / LangGraph v1 · MiniMax-M3 (or any OpenAI-compatible
provider) · LangSmith · Semgrep Community Edition · pip-audit · uv · pytest + Hypothesis + RESPX ·
Ruff · Pyright (strict) · Docker · Railway.

# Citations

[1] [Repository README](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/README.md)
