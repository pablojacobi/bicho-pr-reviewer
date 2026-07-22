# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub's **[Report a
vulnerability](https://github.com/pablojacobi/bicho-pr-reviewer/security/advisories/new)** flow
(Security → Advisories) rather than opening a public issue. You'll get an acknowledgement, and a fix
or mitigation will be coordinated before any public disclosure.

Since this is a single-maintainer portfolio project, response is best-effort — but security reports
are taken seriously.

## Security model

Bicho reviews pull requests, so it processes untrusted input by design. The safeguards:

- **All repository content is untrusted.** Code, diffs, PR titles, filenames, commit messages, and
  scanner output may carry prompt-injection; analyzer prompts treat them strictly as data to analyze,
  never as instructions.
- **Webhooks are verified.** Each webhook is checked with HMAC-SHA256 over the raw body
  (constant-time compare) before parsing; bad or missing signatures are rejected.
- **No untrusted code execution.** Scanners never clone the repo, install dependencies, or run its
  code. Files are materialized into an isolated workspace at sanitized paths (absolute / `..` / NUL
  rejected; binary/generated/vendored/oversized skipped); only static analysis runs, via a no-shell
  subprocess with a hard timeout.
- **Secrets via environment only.** The GitHub App private key and model API keys are `SecretStr`,
  scrubbed from logs, and never committed. The container runs as a non-root user.

See [docs/adr/](docs/adr/) and the [OKF security concept](okf/security-model.md) for detail.

## Supported versions

The `main` branch is the only supported version; fixes land there.
