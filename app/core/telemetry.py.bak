"""Central telemetry event logger for pipeline instrumentation."""
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("app.telemetry")


def log_event(event: dict[str, Any]) -> None:
    """Log a structured telemetry event as JSON."""
    event = dict(event)  # Defensive copy
    if "timestamp" not in event:
        event["timestamp"] = datetime.now(UTC).isoformat()
    logger.info("TELEMETRY_EVENT: %s", event)


class TelemetryService:
    """Service for tracking telemetry events with in-memory storage.

    This service provides:
    - Cache hit/miss tracking
    - Event storage for testing and analysis
    - Integration with presentation layer components
    """

    def __init__(self):
        """Initialize telemetry service."""
        self._events: list[dict[str, Any]] = []

    def track_cache_hit(self, cache_type: str, context: dict[str, Any]) -> None:
        """Track a cache hit event.

        Args:
            cache_type: Type of cache (e.g., "search_embedding")
            context: Additional context about the cache hit
        """
        event = {
            "event_type": "cache_hit",
            "cache_type": cache_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **context
        }
        self._events.append(event)
        log_event(event)

    def track_cache_miss(self, cache_type: str, context: dict[str, Any]) -> None:
        """Track a cache miss event.

        Args:
            cache_type: Type of cache (e.g., "search_embedding")
            context: Additional context about the cache miss
        """
        event = {
            "event_type": "cache_miss",
            "cache_type": cache_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **context
        }
        self._events.append(event)
        log_event(event)

    def get_events(self) -> list[dict[str, Any]]:
        """Get all tracked events.

        Returns:
            List of telemetry events
        """
        return self._events.copy()
