"""Runtime environment definition."""

from enum import StrEnum


class Environment(StrEnum):
    """The environment Bicho is running in.

    Only three environments exist by design — local development, the automated test suite, and the
    single production instance on Railway. There is intentionally no staging environment.
    """

    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        """Whether this is the production environment."""
        return self is Environment.PRODUCTION
