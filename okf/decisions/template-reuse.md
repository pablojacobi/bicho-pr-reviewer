---
type: Decision Record
title: Start clean from the template
description: Borrow good structure from the audited template; copy no code; attribute in an ADR.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0002-start-clean-from-template.md
tags: [decision, template, attribution]
timestamp: 2026-07-22T00:00:00Z
---

# Context

An audited MIT FastAPI/LangGraph template exists, but it is a stateful Postgres + pgvector chatbot
with no tests — the inverse of a stateless, fully-tested reviewer.

# Decision

Start clean, borrowing only good structural practices (no clone, no code copy). Courtesy attribution
to the template lives in this decision and the README.

# Consequences

The repository reflects choices made for *this* system rather than inherited scaffolding, and there is
no licensing entanglement since no substantial portions are copied.

# Citations

[1] [ADR-0002](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0002-start-clean-from-template.md)
