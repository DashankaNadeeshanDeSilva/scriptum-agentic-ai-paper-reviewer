"""Structured logging with Loguru for SCRIPTUM backend.

Provides JSON-formatted structured logging with request correlation IDs,
log rotation, and configurable log levels. Logs are stored in ~/.scriptum/logs/.
"""

import sys
import uuid
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

# Context variable for request correlation
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Default log directory
LOG_DIR = Path.home() / ".scriptum" / "logs"


def _serialize_record(record: dict) -> str:  # type: ignore[type-arg]
    """Format a log record as a JSON string for structured logging."""
    import json
    from datetime import timezone

    subset = {
        "timestamp": record["time"].astimezone(timezone.utc).isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # Include request_id if present
    req_id = request_id_ctx.get("")
    if req_id:
        subset["request_id"] = req_id

    # Include any extra data bound to the logger
    if record.get("extra"):
        for key, value in record["extra"].items():
            if key not in ("request_id",):
                subset[key] = value

    # Include exception info if present
    if record["exception"] is not None:
        subset["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
        }

    return json.dumps(subset, default=str)


def _json_sink(message: object) -> None:
    """Sink that outputs serialized JSON to stderr."""
    record = message.record  # type: ignore[union-attr]
    serialized = _serialize_record(record)
    sys.stderr.write(serialized + "\n")
    sys.stderr.flush()


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_to_file: bool = True,
) -> None:
    """Configure the Loguru logger for the SCRIPTUM application.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        json_format: If True, output structured JSON logs to console.
        log_to_file: If True, also write logs to ~/.scriptum/logs/.
    """
    # Remove default loguru handler
    logger.remove()

    # Console handler
    if json_format:
        logger.add(
            _json_sink,
            level=level,
            format="{message}",
            colorize=False,
        )
    else:
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "{message}"
            ),
            colorize=True,
        )

    # File handler with rotation
    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(LOG_DIR / "scriptum_{time:YYYY-MM-DD}.log"),
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}:{function}:{line} | {message}",
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            enqueue=True,
        )

        # Separate error log
        logger.add(
            str(LOG_DIR / "scriptum_errors_{time:YYYY-MM-DD}.log"),
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}:{function}:{line} | {message}",
            rotation="10 MB",
            retention="60 days",
            compression="gz",
            enqueue=True,
        )

    logger.info("Logging initialized", level=level, log_dir=str(LOG_DIR))


def generate_request_id() -> str:
    """Generate a unique request ID for correlation."""
    return uuid.uuid4().hex[:12]


def get_logger() -> "logger":  # type: ignore[type-arg]
    """Return the configured Loguru logger instance."""
    return logger
