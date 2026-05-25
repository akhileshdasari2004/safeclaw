"""Structured JSON logging configuration."""

import logging
import sys

import structlog


def configure_logging(app_env: str = "development") -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if app_env == "production":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_deployment_context(
    deployment_id: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Bind deployment/correlation IDs for structured logs in workers."""
    import structlog

    ctx: dict[str, str] = {}
    if deployment_id:
        ctx["deployment_id"] = deployment_id
    if correlation_id:
        ctx["correlation_id"] = correlation_id
    if ctx:
        structlog.contextvars.bind_contextvars(**ctx)
