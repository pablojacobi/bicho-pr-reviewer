"""Tests for identifier generation."""

from bicho.domain.ports.system import IdGenerator
from bicho.infrastructure.ids import UuidGenerator


def test_uuid_generator_produces_unique_hex_ids() -> None:
    generator: IdGenerator = UuidGenerator()

    first = generator.new_id()
    second = generator.new_id()

    assert first != second
    assert len(first) == 32
    assert int(first, 16) >= 0  # valid hex string
