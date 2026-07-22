---
type: Decision Record
title: 100% coverage and TDD
description: Test-first, 100% line and branch coverage, CI-blocking, achievable because I/O is injected.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0005-one-hundred-percent-coverage-and-tdd.md
tags: [decision, testing, tdd, coverage, determinism]
timestamp: 2026-07-22T00:00:00Z
---

# Context

For a portfolio piece, test quality is part of the deliverable, and a reviewer that publishes to
GitHub must be trustworthy.

# Decision

Practice TDD (failing test first) and enforce **100% line AND branch** coverage as a CI-blocking gate.
The whole suite runs with no credentials and no network — GitHub, the model, scanners, clock, and
filesystem are all injected and faked. `# pragma: no cover` is used only with documented justification.

# Consequences

Reachable 100% coverage offline is a direct consequence of the [ports-and-adapters
architecture](../architecture.md). Regressions are caught before merge; behavior is deterministic and
reproducible.

# Citations

[1] [ADR-0005](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0005-one-hundred-percent-coverage-and-tdd.md)
