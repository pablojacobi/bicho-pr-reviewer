"""Pydantic models for the subset of pip-audit JSON output Bicho consumes.

Validating the output as data means a malformed payload becomes a degraded outcome, never an
exception. Unknown keys are ignored so pip-audit version drift does not break parsing.
"""

from pydantic import BaseModel, ConfigDict


class PipAuditVuln(BaseModel):
    """One known vulnerability affecting a pinned dependency."""

    model_config = ConfigDict(extra="ignore")

    id: str
    description: str = ""
    fix_versions: list[str] = []


class PipAuditDependency(BaseModel):
    """A pinned dependency and its vulnerabilities (empty when clean)."""

    model_config = ConfigDict(extra="ignore")

    name: str
    version: str = ""
    vulns: list[PipAuditVuln] = []


class PipAuditOutput(BaseModel):
    """The top-level pip-audit JSON document."""

    model_config = ConfigDict(extra="ignore")

    dependencies: list[PipAuditDependency] = []
