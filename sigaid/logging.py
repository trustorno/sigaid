"""Logging configuration for SigAid SDK."""

import logging
import sys
from typing import Any


class SigAidLogFormatter(logging.Formatter):
    """Structured log formatter for SigAid."""

    def __init__(self, include_timestamp: bool = True):
        """Initialize formatter.

        Args:
            include_timestamp: Whether to include timestamps
        """
        if include_timestamp:
            fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        else:
            fmt = "[%(levelname)s] %(name)s: %(message)s"
        super().__init__(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with extra context."""
        # Add context fields if present
        extra_fields = []
        for key in ["agent_id", "session_id", "sequence", "action"]:
            value = getattr(record, key, None)
            if value is not None:
                extra_fields.append(f"{key}={value}")

        message = super().format(record)
        if extra_fields:
            message += f" [{', '.join(extra_fields)}]"
        return message


class SigAidLogger(logging.LoggerAdapter):
    """Logger adapter that adds agent context to logs."""

    def __init__(self, logger: logging.Logger, agent_id: str | None = None):
        """Initialize logger adapter.

        Args:
            logger: Base logger
            agent_id: Agent ID for context
        """
        super().__init__(logger, {"agent_id": agent_id})

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict]:
        """Process log message with context."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

    def with_context(self, **context) -> "SigAidLogger":
        """Create new logger with additional context.

        Args:
            **context: Additional context fields

        Returns:
            New logger adapter with merged context
        """
        merged = {**self.extra, **context}
        new_logger = SigAidLogger(self.logger, agent_id=merged.get("agent_id"))
        new_logger.extra = merged
        return new_logger


def setup_logging(
    level: int | str = logging.INFO,
    format_timestamps: bool = True,
    handler: logging.Handler | None = None,
) -> None:
    """Configure logging for SigAid SDK.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_timestamps: Whether to include timestamps
        handler: Custom log handler (uses stderr if None)
    """
    # Get root sigaid logger
    logger = logging.getLogger("sigaid")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    if handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)

    # Set formatter
    formatter = SigAidLogFormatter(include_timestamp=format_timestamps)
    handler.setFormatter(formatter)

    logger.addHandler(handler)


def get_logger(name: str, agent_id: str | None = None) -> SigAidLogger:
    """Get a logger for a SigAid component.

    Args:
        name: Component name (e.g., "sigaid.client")
        agent_id: Optional agent ID for context

    Returns:
        Configured logger adapter
    """
    logger = logging.getLogger(name)
    return SigAidLogger(logger, agent_id=agent_id)


# Module-level logger for SDK
logger = get_logger("sigaid")
