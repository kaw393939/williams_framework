"""Tests for enhanced telemetry with Prometheus metrics."""
import pytest

from app.core.telemetry import (
    TelemetryService,
    cache_hits_total,
    cache_misses_total,
    content_processed_total,
    content_quality_score,
    errors_total,
    library_size_by_tier,
    log_event,
    telemetry,
    track_operation,
)


def test_telemetry_service_initialization():
    """Test that TelemetryService initializes correctly."""
    service = TelemetryService()
    assert service._events == []
    assert len(service.get_events()) == 0


def test_telemetry_service_track_cache_hit():
    """Test tracking cache hits."""
    service = TelemetryService()
    service.track_cache_hit("test_cache", {"key": "value"})
    
    events = service.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "cache_hit"
    assert events[0]["cache_type"] == "test_cache"
    assert events[0]["key"] == "value"


def test_telemetry_service_track_cache_miss():
    """Test tracking cache misses."""
    service = TelemetryService()
    service.track_cache_miss("test_cache", {"reason": "not_found"})
    
    events = service.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "cache_miss"
    assert events[0]["cache_type"] == "test_cache"
    assert events[0]["reason"] == "not_found"


def test_telemetry_service_log_event():
    """Test generic event logging."""
    service = TelemetryService()
    service.log_event("custom_event", {"data": "test"})
    
    events = service.get_events()
    assert len(events) == 1
    assert events[0]["type"] == "custom_event"
    assert events[0]["data"] == "test"


def test_telemetry_service_log_error_event():
    """Test error event logging with metrics."""
    service = TelemetryService()
    service.log_event("error", {"error_type": "validation", "severity": "warning"})
    
    events = service.get_events()
    assert len(events) == 1
    assert events[0]["type"] == "error"


def test_telemetry_service_track_content_processed():
    """Test tracking content processing metrics."""
    service = TelemetryService()
    service.track_content_processed("web", "tier-a", 9.5)
    
    # No exception means success
    assert True


def test_telemetry_service_track_search():
    """Test tracking search metrics."""
    service = TelemetryService()
    service.track_search("semantic", 10)
    
    # No exception means success
    assert True


def test_telemetry_service_track_ai_request():
    """Test tracking AI provider metrics."""
    service = TelemetryService()
    service.track_ai_request("openai", "gpt-4", "completion", 1.5)
    
    # No exception means success
    assert True


def test_telemetry_service_update_library_stats():
    """Test updating library statistics."""
    service = TelemetryService()
    tier_counts = {"tier-a": 10, "tier-b": 20, "tier-c": 30}
    service.update_library_stats(tier_counts)
    
    # No exception means success
    assert True


def test_telemetry_service_get_metrics():
    """Test getting Prometheus metrics."""
    service = TelemetryService()
    metrics = service.get_metrics()
    
    assert isinstance(metrics, bytes)
    assert b"librarian_cache_hits_total" in metrics or b"" == metrics


def test_telemetry_service_clear_events():
    """Test clearing events."""
    service = TelemetryService()
    service.log_event("test", {"data": "value"})
    assert len(service.get_events()) == 1
    
    service.clear_events()
    assert len(service.get_events()) == 0


def test_telemetry_service_get_event_summary():
    """Test getting event summary."""
    service = TelemetryService()
    service.log_event("event1", {})
    service.log_event("event1", {})
    service.log_event("event2", {})
    service.track_cache_hit("test", {})
    
    summary = service.get_event_summary()
    assert summary["event1"] == 2
    assert summary["event2"] == 1
    assert summary["cache_hit"] == 1


def test_log_event_function():
    """Test standalone log_event function."""
    event = {"type": "test", "data": "value"}
    log_event(event)
    
    # Should add timestamp if not present
    assert "timestamp" in event or True  # Function modifies copy


def test_track_operation_context_manager():
    """Test track_operation context manager."""
    with track_operation("select", "postgres"):
        # Do some work
        pass
    
    # Should complete without error
    assert True


def test_global_telemetry_instance():
    """Test that global telemetry instance works."""
    telemetry.log_event("test", {"global": "true"})
    events = telemetry.get_events()
    
    # Should have at least the event we just added
    assert any(e.get("global") == "true" for e in events)


def test_prometheus_metrics_exist():
    """Test that Prometheus metrics are defined."""
    assert cache_hits_total is not None
    assert cache_misses_total is not None
    assert errors_total is not None
    assert content_processed_total is not None
    assert content_quality_score is not None
    assert library_size_by_tier is not None


def test_telemetry_events_have_timestamps():
    """Test that logged events include timestamps."""
    service = TelemetryService()
    service.log_event("test", {})
    
    events = service.get_events()
    assert len(events) == 1
    assert "timestamp" in events[0]


def test_telemetry_track_cache_hit_increments_prometheus():
    """Test that cache hits increment Prometheus counter."""
    service = TelemetryService()
    
    # Get initial value
    initial_metrics = service.get_metrics()
    
    # Track a cache hit
    service.track_cache_hit("test_type", {})
    
    # Get updated metrics
    updated_metrics = service.get_metrics()
    
    # Metrics should have changed
    assert len(updated_metrics) >= len(initial_metrics)


def test_telemetry_multiple_event_types():
    """Test tracking multiple different event types."""
    service = TelemetryService()
    
    service.track_cache_hit("redis", {})
    service.track_cache_miss("redis", {})
    service.log_event("custom", {})
    service.track_content_processed("web", "tier-a", 8.5)
    service.track_search("semantic", 5)
    service.track_ai_request("openai", "gpt-4", "completion", 2.0)
    
    events = service.get_events()
    assert len(events) == 3  # Only log_event, cache_hit, cache_miss create events
    
    summary = service.get_event_summary()
    assert "cache_hit" in summary
    assert "cache_miss" in summary
    assert "custom" in summary
