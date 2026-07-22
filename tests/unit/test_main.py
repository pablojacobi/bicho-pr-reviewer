"""Tests for the local development entrypoint."""

from unittest.mock import patch

import bicho.main


def test_run_invokes_uvicorn() -> None:
    with patch("bicho.main.uvicorn.run") as mock_run:
        bicho.main.run()

    mock_run.assert_called_once_with(
        "bicho.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
    )
