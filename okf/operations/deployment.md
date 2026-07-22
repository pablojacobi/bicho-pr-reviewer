---
type: Playbook
title: Deployment
description: Run locally with Docker Compose, or deploy the single container to Railway.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docker-compose.yml
tags: [operations, deployment, docker, railway]
timestamp: 2026-07-22T00:00:00Z
---

# The image

A multi-stage Docker build produces a slim, non-root image. Semgrep and pip-audit are installed as
isolated tools on `PATH` (kept out of the app virtualenv to avoid dependency conflicts), and the
curated `resources/` ruleset is copied in. The non-root user has a writable `HOME` so the scanners can
run.

# Local — Docker Compose

There is no database, cache, or broker, so Compose is a single service reading `.env`:

```bash
cp .env.example .env      # fill in real credentials
docker compose up --build # serves on :8000; GET /readyz, /version
```

`POST /reviews` works immediately. Webhooks need a public URL — expose `:8000` with a tunnel
(cloudflared/ngrok) or deploy to Railway.

# Railway

`railway.toml` builds the Dockerfile, runs one instance, and health-checks `/healthz`. Set the
`BICHO_*` and `LANGSMITH_*` variables (skip `PORT`/`BICHO_PORT` — Railway injects `$PORT`), paste the
private key as the single-line `\n` form, and set a real `BICHO_GITHUB__WEBHOOK_SECRET`. After deploy,
verify `/readyz` is 200, then point the GitHub App webhook at `https://<url>/webhooks/github`.

# Related

* [Configuration](configuration.md) — the variables to set.
* [Running a review](running-a-review.md) — verifying the deployment.
* [Single container decision](../decisions/single-container-background-tasks.md).

# Citations

[1] [docker-compose.yml](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docker-compose.yml)
[2] [railway.toml](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/railway.toml)
