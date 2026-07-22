# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-07-22

First working, deployed version: an automated GitHub PR reviewer running live on Railway.

### Added

- **Review pipeline** — a typed LangGraph workflow: fetch PR → normalize diff → detect language →
  gather file contents → fan out over analyzers/scanners → verify → dedup → anchor → compose →
  publish, with a resilient "degrade, never raise" invariant on every analyzer/scanner node.
- **Analyzers** — six LLM analyzers (correctness, security, performance, maintainability, tests,
  contracts) behind a shared `LLMAnalyzer` and a versioned prompt registry.
- **Deterministic scanners** — Semgrep CE (curated ruleset) and pip-audit, each implementing the
  analyzer contract and fanning out through the graph; sandboxed, optional, degrade-safe.
- **GitHub integration** — App JWT → cached installation token; a REST client (PR, files, reviews,
  file content, publish) with idempotency (hidden marker) and a stale-head guard.
- **Model provider** — an OpenAI-compatible provider behind a port, with structured output via
  function calling, multi-provider configuration (`ACTIVE` selector), and per-provider retry and
  concurrency limits for flaky endpoints.
- **API** — `POST /reviews` (dry-run by default), `POST /webhooks/github` (HMAC-verified, background
  execution), and `/healthz` / `/readyz` / `/version`.
- **Deployment** — multi-stage non-root Docker image with the scanner binaries baked in,
  `docker-compose.yml`, and Railway configuration.
- **Docs** — README, ARCHITECTURE, AGENTS, ADRs 0001–0009, limitations, and an OKF knowledge bundle.

[Unreleased]: https://github.com/pablojacobi/bicho-pr-reviewer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pablojacobi/bicho-pr-reviewer/releases/tag/v0.1.0
