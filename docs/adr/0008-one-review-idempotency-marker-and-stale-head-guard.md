# 0008 — One review per run: idempotency marker and stale-head guard

**Status:** Accepted

## Context

Bicho publishes results to a GitHub PR. Webhooks are redelivered, the same head can be reviewed more
than once, and a PR can receive a new push *while* a review is being computed. With
[no database](0003-no-database-github-as-source-of-truth.md), the PR itself must carry enough state to
avoid duplicate or misleading reviews.

## Decision

Publish exactly **one** GitHub review per run: an executive summary plus inline comments, with
`commit_id` pinned to the analyzed head SHA. Confirmed findings that can be anchored to the diff become
inline comments; the rest go in the summary. Two graph guards gate publishing:

- **Idempotency guard** — before publishing (live runs only), list the PR's reviews and parse a hidden
  HTML **marker** (head SHA + workflow version + prompt version + model id) that Bicho embeds in every
  review it posts. If the current head + workflow was already reviewed, **skip** — unless `force`.
- **Stale-head guard** — re-fetch the head SHA immediately before publishing; if the PR moved, **abort**
  (`STALE`) rather than anchor a review to a commit that is no longer the head.

## Consequences

- No duplicate reviews across webhook redeliveries or re-runs, with no datastore — GitHub is the ledger.
- Bumping the prompt or workflow version legitimately allows a re-review of the same head.
- A stale run is dropped rather than published incorrectly; the next event (or the manual endpoint)
  produces a fresh review.
- Inline anchoring is pre-validated so an un-anchorable finding degrades to a summary bullet instead of
  failing the whole (atomic) review POST.
