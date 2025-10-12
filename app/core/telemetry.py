"""Central telemetry event logger for pipeline instrumentation."""
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("app.telemetry")


def log_event(event: Dict[str, Any]) -> None:
    """Log a structured telemetry event as JSON."""
    event = dict(event)  # Defensive copy
    if "timestamp" not in event:
        event["timestamp"] = datetime.utcnow().isoformat() + "Z"
    logger.info("TELEMETRY_EVENT: %s", event)
