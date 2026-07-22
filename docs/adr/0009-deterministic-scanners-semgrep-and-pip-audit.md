# 0009 — Deterministic scanners: Semgrep CE and pip-audit

**Status:** Accepted

## Context

LLM analyzers are good at judgement but are non-deterministic and can hallucinate. Some classes of
issue — known-vulnerable dependencies, well-known insecure patterns — are better found by
deterministic tools. We want that signal without giving up determinism, safety, or the offline test
suite, and without executing untrusted repository code.

## Decision

Add two scanners that implement the **same `Analyzer` protocol** as the LLM analyzers, so they fan out
and fan in through the existing graph with no special wiring:

- **Semgrep Community Edition** — runs a shipped, curated ruleset over the changed files.
- **pip-audit** — audits changed `requirements*.txt` manifests for known-vulnerable pinned deps.

Both materialize the in-scope changed files into an **isolated temp workspace at sanitized paths** and
run via the injected `SubprocessRunner` (no shell, hard timeout, no `--config=auto`, no metrics). The
repository is **never cloned and its code is never executed** — only static analysis / manifest audit
runs. Every failure mode (timeout, non-zero exit, unparseable output) becomes a **degraded outcome**,
never an exception. Each scanner is **optional** (a settings flag) so the app runs where the binary is
absent or the environment is offline.

## Consequences

- High-signal, deterministic findings complement the LLM analyzers; both flow through the same
  verify / dedup / anchor / publish path.
- The whole suite stays offline and 100%-coverable: the `SubprocessRunner` is faked, so no real binary
  or network is needed in tests.
- pip-audit needs outbound network (a vulnerability DB) in production; it is timeout-bounded and
  toggleable, and degrades cleanly when unavailable.
- **Trade-off:** shipping/installing the `semgrep` binary and ruleset is a deployment concern; when it
  is absent, Bicho degrades to LLM-only review rather than failing.
