import logging
import json
from datetime import datetime, timezone


# ─────────────────────────────────────────────
# CONCEPT: Structured JSON Logging
#
# Standard Python logging outputs plain text:
#   ERROR:root:Something went wrong
#
# Structured logging outputs JSON:
#   {"timestamp": "...", "level": "ERROR", "message": "Something went wrong"}
#
# JSON logs can be:
# - Searched by field (find all ERROR logs)
# - Filtered by endpoint or user
# - Ingested by log management tools (Datadog, CloudWatch)
# - Parsed by machines, not just humans
# ─────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    Every log line is a valid JSON object — one per line.
    This format is called JSONL (JSON Lines).
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed to the logger
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName"
            }:
                log_data[key] = value

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with JSON formatting.
    Usage:
        logger = get_logger(__name__)
        logger.info("Invoice created", extra={"invoice_id": 1})
        logger.error("Something failed", extra={"endpoint": "/invoices"})
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger