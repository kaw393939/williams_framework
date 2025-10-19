"""Enhanced telemetry with Prometheus metrics support."""
import asyncio
import logging
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import wraps
from typing import Any, Callable

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger("app.telemetry")

# Create registry
registry = CollectorRegistry()

# Cache metrics
cache_hits_total = Counter(
    "librarian_cache_hits_total", "Total cache hits", ["cache_type"], registry=registry
)

cache_misses_total = Counter(
    "librarian_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=registry,
)

# Error metrics
errors_total = Counter(
    "librarian_errors_total", "Total errors", ["error_type", "severity"], registry=registry
)

# Content metrics
content_processed_total = Counter(
    "librarian_content_processed_total",
    "Total content items processed",
    ["source_type", "tier"],
    registry=registry,
)

content_quality_score = Histogram(
    "librarian_content_quality_score",
    "Content quality scores",
    ["tier"],
    buckets=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    registry=registry,
)

library_size_by_tier = Gauge(
    "librarian_library_size_by_tier",
    "Number of items in library by tier",
    ["tier"],
    registry=registry,
)

# AI Provider metrics
ai_provider_requests_total = Counter(
    "librarian_ai_provider_requests_total",
    "Total AI provider requests",
    ["provider", "model", "operation"],
    registry=registry,
)

ai_provider_latency_seconds = Histogram(
    "librarian_ai_provider_latency_seconds",
    "AI provider request latency",
    ["provider", "model"],
    registry=registry,
)

# Search metrics
search_queries_total = Counter(
    "librarian_search_queries_total",
    "Total search queries",
    ["search_type"],
    registry=registry,
)

search_results_count = Histogram(
    "librarian_search_results_count",
    "Number of search results returned",
    buckets=(0, 1, 5, 10, 25, 50, 100),
    registry=registry,
)


@contextmanager
def track_operation(operation: str, repository: str):
    """Context manager for tracking database operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start


def log_event(event: dict[str, Any]) -> None:
    """Log a structured telemetry event as JSON."""
    event = dict(event)
    if "timestamp" not in event:
        event["timestamp"] = datetime.now(UTC).isoformat()
    logger.info("TELEMETRY_EVENT: %s", event)


class TelemetryService:
    """Enhanced telemetry service with Prometheus metrics."""

    def __init__(self):
        """Initialize telemetry service."""
        self._events: list[dict[str, Any]] = []
        logger.info("TelemetryService initialized with Prometheus metrics")

    def track_cache_hit(self, cache_type: str, context: dict[str, Any]) -> None:
        """Track a cache hit event."""
        event = {
            "event_type": "cache_hit",
            "cache_type": cache_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **context,
        }
        self._events.append(event)
        log_event(event)
        cache_hits_total.labels(cache_type=cache_type).inc()

    def track_cache_miss(self, cache_type: str, context: dict[str, Any]) -> None:
        """Track a cache miss event."""
        event = {
            "event_type": "cache_miss",
            "cache_type": cache_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **context,
        }
        self._events.append(event)
        log_event(event)
        cache_misses_total.labels(cache_type=cache_type).inc()

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log a telemetry event."""
        event = {"type": event_type, "timestamp": time.time(), **data}
        logger.info("TELEMETRY_EVENT: %s", event)
        self._events.append(event)

        if event_type == "error":
            errors_total.labels(
                error_type=data.get("error_type", "unknown"),
                severity=data.get("severity", "error"),
            ).inc()

    def track_content_processed(
        self, source_type: str, tier: str, quality_score: float
    ) -> None:
        """Track content processing metrics."""
        content_processed_total.labels(source_type=source_type, tier=tier).inc()
        content_quality_score.labels(tier=tier).observe(quality_score)

    def track_search(self, search_type: str, result_count: int) -> None:
        """Track search metrics."""
        search_queries_total.labels(search_type=search_type).inc()
        search_results_count.observe(result_count)

    def track_ai_request(
        self,
        provider: str,
        model: str,
        operation: str,
        latency: float,
    ) -> None:
        """Track AI provider metrics."""
        ai_provider_requests_total.labels(
            provider=provider, model=model, operation=operation
        ).inc()
        ai_provider_latency_seconds.labels(provider=provider, model=model).observe(latency)

    def update_library_stats(self, tier_counts: dict[str, int]) -> None:
        """Update library size metrics by tier."""
        for tier, count in tier_counts.items():
            library_size_by_tier.labels(tier=tier).set(count)

    def get_metrics(self) -> bytes:
        """Get Prometheus metrics in text format."""
        return generate_latest(registry)

    def get_events(self) -> list[dict[str, Any]]:
        """Get all tracked events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear all logged events."""
        self._events.clear()

    def get_event_summary(self) -> dict[str, int]:
        """Get summary of events by type."""
        summary = {}
        for event in self._events:
            event_type = event.get("type") or event.get("event_type", "unknown")
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary


telemetry = TelemetryService()
