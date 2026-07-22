---
type: Decision Record
title: Deterministic scanners — Semgrep CE and pip-audit
description: Two deterministic scanners implement the analyzer contract and fan out with the LLM analyzers.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0009-deterministic-scanners-semgrep-and-pip-audit.md
tags: [decision, scanners, semgrep, pip-audit, security]
timestamp: 2026-07-22T00:00:00Z
---

# Context

LLM analyzers are good at judgement but non-deterministic. Known-vulnerable dependencies and well-known
insecure patterns are better found by deterministic tools — without giving up determinism, safety, or
the offline test suite, and without executing untrusted code.

# Decision

Add two scanners that implement the same `Analyzer` protocol as the LLM analyzers, so they fan out
through the existing graph: **Semgrep CE** (a curated ruleset over the changed files) and **pip-audit**
(auditing changed `requirements*.txt` for known-vulnerable pins). Both materialize files into an
isolated workspace at sanitized paths and run via a no-shell subprocess runner with a hard timeout;
every failure degrades to a diagnostic. Each is optional via a settings flag.

# Consequences

High-signal deterministic findings flow through the same verify/dedup/anchor/publish path as LLM
findings. The suite stays offline and 100%-coverable (the subprocess runner is faked). Where a binary
is absent, Bicho degrades to LLM-only review.

# Citations

[1] [ADR-0009](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0009-deterministic-scanners-semgrep-and-pip-audit.md)
