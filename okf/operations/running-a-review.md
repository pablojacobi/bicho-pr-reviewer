---
type: Playbook
title: Running a review
description: Trigger a review manually via POST /reviews (dry-run) or automatically via a webhook.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/api/routes/reviews.py
tags: [operations, api, webhook, dry-run]
timestamp: 2026-07-22T00:00:00Z
---

# Manual endpoint (dry-run by default)

`POST /reviews` runs the same pipeline as the webhook and returns the composed result. `dry_run`
(the default from the API) returns the would-be draft — summary plus the inline comments that would be
posted — **without touching GitHub**.

```bash
curl -X POST http://localhost:8000/reviews \
  -H 'content-type: application/json' \
  -d '{"repository": "octo/hello-world", "pr_number": 42, "dry_run": true}'
```

`force` bypasses the idempotency guard; `focus` / `categories` filter which analyzers run.

# Webhook (automatic, publishes)

`POST /webhooks/github` verifies the HMAC signature over the raw body, filters to reviewable
`pull_request` actions (skipping drafts), de-duplicates redeliveries, and returns 202 — then runs the
review off-request as a background task and **publishes** one review. Point the GitHub App's webhook at
`https://<host>/webhooks/github` with the shared secret and the `pull_request` event.

# What you get

Confirmed findings that anchor to the diff become inline comments (category, severity, explanation,
impact, recommendation); the rest go in the summary. The event is `COMMENT` or `REQUEST_CHANGES` per
severity. A hidden marker makes re-runs idempotent. See the [review pipeline](../review-pipeline.md).

# Citations

[1] [reviews route](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/api/routes/reviews.py)
[2] [webhooks route](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/api/routes/webhooks.py)
