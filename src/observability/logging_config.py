"""Structured Logging Configuration with PII Scrubbing for NutriConcierge."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from src.config import settings
from src.observability.pii_scrubber import PIIScrubber


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter with automated PII scrubbing for structured observability logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": PIIScrubber.scrub_text(record.getMessage()),
        }

        # Attach custom extra context if present
        for attr in ["session_id", "agent_name", "tool_name", "duration_ms", "trace_id", "action_intended", "status"]:
            if hasattr(record, attr):
                val = getattr(record, attr)
                log_entry[attr] = PIIScrubber.scrub_data(val)

        if record.exc_info:
            log_entry["exception"] = PIIScrubber.scrub_text(self.formatException(record.exc_info))

        return json.dumps(log_entry)


def setup_logger(name: str = "nutri_concierge") -> logging.Logger:
    """Initialize and configure a structured logger."""
    logger = logging.getLogger(name)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
