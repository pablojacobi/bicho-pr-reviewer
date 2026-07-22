---
type: Decision Record
title: Language-agnostic core with adapters
description: A LanguageAdapter contract keeps the core decoupled from any one language; Python is the first.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0006-language-agnostic-core-with-adapters.md
tags: [decision, language-adapter, extensibility]
timestamp: 2026-07-22T00:00:00Z
---

# Context

The first target is Python/FastAPI, but coupling the whole pipeline to Python would make the reviewer
a one-language tool.

# Decision

Put language-specific behavior behind a `LanguageAdapter` contract (scope, framework detection,
enclosing-symbol resolution, default analyzers, scanner rulesets, dependency manifests). A registry
picks the highest-scoring adapter with a generic fallback. A dummy adapter in tests drives the full
graph to prove the core is not coupled to Python.

# Consequences

Adding a language is a new adapter, not a core change. The generic fallback degrades cleanly on
unknown languages instead of failing.

# Citations

[1] [ADR-0006](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0006-language-agnostic-core-with-adapters.md)
