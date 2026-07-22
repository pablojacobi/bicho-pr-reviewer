"""Identifier generation."""

import uuid


class UuidGenerator:
    """An :class:`~bicho.domain.ports.system.IdGenerator` producing random UUID4 hex strings."""

    def new_id(self) -> str:
        """Return a fresh 32-character hex identifier."""
        return uuid.uuid4().hex
