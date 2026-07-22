"""System clock implementation."""

from datetime import UTC, datetime


class SystemClock:
    """A :class:`~bicho.domain.ports.system.Clock` backed by the real wall clock, in UTC."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""
        return datetime.now(UTC)
