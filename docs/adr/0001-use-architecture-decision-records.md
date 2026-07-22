# 0001 — Use Architecture Decision Records

**Status:** Accepted

## Context

This is a portfolio project where the *reasoning* behind design choices matters as much as the code. A
reviewer should be able to see why the architecture is shaped the way it is, and several deliberate
constraints (no database, in-process tasks) look like omissions unless their rationale is written down.

## Decision

Record significant, hard-to-reverse decisions as numbered ADRs under `docs/adr/`, each with Context /
Decision / Consequences. ADRs are immutable once Accepted; a new ADR supersedes an old one rather than
editing it. Decisions may be recorded before their implementation lands.

## Consequences

- Rationale is discoverable and stable; reviewers and future contributors get the "why".
- Small ongoing overhead to write an ADR when a real decision is made (not for routine changes).
