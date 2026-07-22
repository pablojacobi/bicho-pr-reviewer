---
type: Process
title: The review pipeline
description: A LangGraph spine into one parallel fan-out superstep, then a gated publish tail.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/application/graph/builder.py
tags: [langgraph, pipeline, fan-out, resilience]
timestamp: 2026-07-22T00:00:00Z
---

# Topology

The workflow is a linear spine into a single parallel fan-out superstep, fanned back in via
`operator.add` reducers, then a gated linear finish:

```
fetch_pull_request → fetch_changed_files → normalize_diff → detect_language
  → gather_file_contents → select_analyzers
  ─fan-out→ { correctness · security · performance · maintainability · tests · contracts
              · semgrep · pip-audit }  → collect_findings   ←fan-in
  → verify_findings → compose_review
  → idempotency_guard ─cond→ stale_head_guard ─cond→ publish_github_review → END
```

# Load-bearing invariant: degrade, never raise

In LangGraph, if any branch of a parallel superstep raises, the **whole superstep rolls back** and the
run errors. Therefore every scanner/analyzer node is wrapped so it catches everything (budget,
timeout, invalid model output, subprocess errors) and returns a degraded `AnalyzerOutcome` with
diagnostics instead of raising. `compose_review` surfaces the degradation in the summary — **degrade
and report, never hide**. This invariant was observed working in production: when a MiniMax analyzer
timed out or returned no structured output, the review still completed with the other analyzers.

# Fan-out

`select_analyzers` returns the subset of analyzers/scanners to run (from the language adapter plus
`focus`/`categories`), and a conditional edge routes to exactly that subset. Each node reads the full
shared state; only the `outcomes` reducer key is written by the parallel nodes, which keeps the
superstep valid.

# Verify, dedup, anchor, publish

Findings are verified (only confident findings survive), deduplicated by a line-independent
fingerprint, anchored to commentable diff lines, and composed into one review draft. Publishing is
gated by the [idempotency and stale-head guards](decisions/one-review-idempotency-stale-guard.md).

# Related

* [Deterministic scanners](decisions/deterministic-scanners.md) — Semgrep and pip-audit as analyzers.
* [Model-provider abstraction](decisions/model-provider-function-calling.md) — how the LLM is called.

# Citations

[1] [graph builder](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/application/graph/builder.py)
