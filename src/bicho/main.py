"""Local development entrypoint.

In production, uvicorn is invoked directly against ``bicho.api.app:create_app`` (see the
Dockerfile), binding the container port. This module is only a convenience for running the app
locally with ``python -m bicho.main`` and intentionally binds to loopback.
"""

import uvicorn


def run() -> None:
    """Run the application with uvicorn for local development (loopback only)."""
    uvicorn.run("bicho.api.app:create_app", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
