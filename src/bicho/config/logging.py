"""Structured logging configuration (structlog).

Human-readable console output for local/test and JSON for production. Every event passes through a
processor that redacts known-sensitive keys, so tokens, signatures, and private keys never reach
the logs.
"""

import logging

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

from bicho.config.settings import Settings

_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "token",
        "access_token",
        "installation_token",
        "api_key",
        "private_key",
        "secret",
        "webhook_secret",
        "password",
        "x-hub-signature-256",
    }
)
_REDACTED = "***redacted***"


def scrub_sensitive(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Redact values for known-sensitive keys before the event is rendered."""
    for key in event_dict:
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure structlog processors and level from settings.

    Idempotent: safe to call again (e.g. after settings change). Callers own *when* to configure;
    this module never reads the environment itself.
    """
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if settings.render_json_logs
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            scrub_sensitive,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level]
        ),
        cache_logger_on_first_use=True,
    )
