"""Versioned analyzer prompt templates.

Prompts are versioned so a review's marker records which prompt produced it. Bumping a prompt
changes ``PROMPT_VERSION``, which legitimately lets a PR be re-reviewed (see the idempotency guard).
"""

PROMPT_VERSION = "v1"

_CORRECTNESS = (
    "You are a meticulous senior engineer reviewing a pull request diff for correctness and "
    "reliability bugs: logic errors, edge cases, mishandled None values, swallowed exceptions, "
    "unclosed resources, race conditions, non-idempotent effects, and broken invariants. Report "
    "only concrete, high-signal issues introduced or affected by this diff, each anchored to a "
    "file and line range. If there are none, return an empty list of findings."
)

_TEMPLATES: dict[str, str] = {"correctness": _CORRECTNESS}


def get_prompt(role: str) -> str:
    """Return the prompt template for an analyzer role."""
    return _TEMPLATES[role]
