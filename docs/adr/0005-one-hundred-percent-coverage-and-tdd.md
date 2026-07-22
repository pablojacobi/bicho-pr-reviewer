# 0005 — 100% coverage and TDD

**Status:** Accepted

## Context

The portfolio bar is high: the codebase should demonstrate discipline and be safe to refactor as the
LangGraph workflow grows. Partial coverage tends to hide exactly the branches (error paths, degraded
outcomes) that matter most for a reviewer that must fail gracefully.

## Decision

Practice **TDD** (red → green → refactor) and enforce **100% line and branch coverage** on `src/bicho`
in CI (`--cov-branch --cov-fail-under=100`). `# pragma: no cover` is allowed only with a written
justification. Standard, non-cheating exclusions (`if __name__ == "__main__"`, `if TYPE_CHECKING`,
Protocol `...` bodies) live in `pyproject.toml`. Every side effect sits behind an injectable port so
full coverage is reachable offline with fakes.

## Consequences

- High confidence and refactor safety; error/degradation paths are actually exercised.
- A real discipline cost, and pressure to keep architecture testable (which we want anyway).
- The 100% gate is a hard merge blocker, so tests are written with the code, not after.
