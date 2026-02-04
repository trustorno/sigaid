"""Structured logging configuration for Authority Service."""

import logging
import sys
import json
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        for key in ["agent_id", "session_id", "endpoint", "method", "status_code", "duration_ms"]:
            value = getattr(record, key, None)
            if value is not None:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        base = f"{timestamp} {color}{record.levelname:8}{reset} {record.name}: {record.getMessage()}"

        # Add context
        context = []
        for key in ["agent_id", "endpoint", "status_code", "duration_ms"]:
            value = getattr(record, key, None)
            if value is not None:
                context.append(f"{key}={value}")

        if context:
            base += f" [{', '.join(context)}]"

        return base


def setup_logging(debug: bool = False, json_format: bool = False) -> None:
    """Configure logging for Authority Service.

    Args:
        debug: Enable debug logging
        json_format: Use JSON format (for production)
    """
    level = logging.DEBUG if debug else logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = ConsoleFormatter()
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    # Reduce noise from other libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class RequestLogger:
    """Context manager for logging requests."""

    def __init__(self, logger: logging.Logger, method: str, endpoint: str, agent_id: str | None = None):
        """Initialize request logger.

        Args:
            logger: Logger instance
            method: HTTP method
            endpoint: Request endpoint
            agent_id: Optional agent ID
        """
        self.logger = logger
        self.method = method
        self.endpoint = endpoint
        self.agent_id = agent_id
        self.start_time: float = 0

    def __enter__(self) -> "RequestLogger":
        """Start timing request."""
        import time
        self.start_time = time.time()
        self.logger.info(
            f"{self.method} {self.endpoint}",
            extra={
                "method": self.method,
                "endpoint": self.endpoint,
                "agent_id": self.agent_id,
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Log request completion."""
        import time
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            self.logger.error(
                f"{self.method} {self.endpoint} failed: {exc_val}",
                extra={
                    "method": self.method,
                    "endpoint": self.endpoint,
                    "agent_id": self.agent_id,
                    "duration_ms": round(duration_ms, 2),
                },
                exc_info=True,
            )
        else:
            self.logger.info(
                f"{self.method} {self.endpoint} completed",
                extra={
                    "method": self.method,
                    "endpoint": self.endpoint,
                    "agent_id": self.agent_id,
                    "duration_ms": round(duration_ms, 2),
                }
            )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for an Authority component.

    Args:
        name: Component name

    Returns:
        Logger instance
    """
    return logging.getLogger(f"authority.{name}")
