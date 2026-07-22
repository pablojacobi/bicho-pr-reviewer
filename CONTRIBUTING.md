# Contributing

Thanks for your interest in Bicho PR Reviewer. This is a portfolio project, so the bar for
architecture, tests, and git history is deliberately high — contributions are welcome as long as they
hold that bar.

## Ground rules

- **[AGENTS.md](AGENTS.md) is the source of truth.** Read it (and the relevant [ADRs](docs/adr/))
  before making changes.
- **TDD is mandatory.** Write the failing test first, for the right reason, then make it pass.
- **100% line *and* branch coverage** on `src/bicho` is CI-blocking. `# pragma: no cover` is allowed
  only with a documented justification.
- **One small PR per logical change**, on a `feat/…` / `fix/…` / `docs/…` branch. `main` is protected
  and requires green CI.
- All artifacts (code comments, docs, ADRs, PR bodies) are written in **English**.

## Local workflow

Everything runs through [uv](https://docs.astral.sh/uv/); the coverage/lint/type gates live in
`pyproject.toml`.

```bash
uv sync                     # install (Python 3.14)
uv run ruff format .        # format
uv run ruff check .         # lint
uv run pyright              # type-check (strict)
uv run pytest               # tests @ 100% line + branch
```

A change is ready to open as a PR when all four pass locally.

## Design constraints (don't "fix" these)

They are intentional and documented in the [ADRs](docs/adr/):

- No database, broker, queue, or separate worker — the single-container / no-DB design is deliberate.
- All repository content (diffs, filenames, prompts in fixtures) is **untrusted data**; it must never
  influence Bicho's behavior. Never execute untrusted repository code.
- The domain imports nothing framework-specific; keep the `api → application → domain ← infrastructure`
  dependency rule intact.

## Reporting bugs and ideas

Open an issue with a minimal reproduction (a diff or a failing test is ideal). Security issues follow
[SECURITY.md](SECURITY.md) instead.
