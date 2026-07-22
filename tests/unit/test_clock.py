"""Tests for the system clock."""

from datetime import UTC, datetime

from bicho.domain.ports.system import Clock
from bicho.infrastructure.clock import SystemClock


def test_system_clock_returns_aware_utc_now() -> None:
    clock: Clock = SystemClock()

    before = datetime.now(UTC)
    value = clock.now()
    after = datetime.now(UTC)

    assert value.tzinfo == UTC
    assert before <= value <= after
