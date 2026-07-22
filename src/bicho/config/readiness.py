"""Configuration readiness checks.

Readiness is about *configuration*, not liveness: the process can be up (``/healthz``) yet unable to
do real work because required credentials are absent. ``/readyz`` reports the missing pieces so a
misconfigured deploy fails visibly instead of silently erroring on the first webhook.
"""

from bicho.config.settings import Settings


def missing_requirements(settings: Settings) -> list[str]:
    """Return the human-readable list of required settings that are absent (empty means ready)."""
    problems: list[str] = []
    github = settings.github
    if not github.app_id:
        problems.append("github.app_id is not set")
    if not github.private_key.get_secret_value():
        problems.append("github.private_key is not set")
    if github.installation_id == 0:
        problems.append("github.installation_id is not set")
    if not settings.llm.api_key.get_secret_value():
        problems.append("llm.api_key is not set")
    return problems
