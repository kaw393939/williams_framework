# Telemetry Schema for Pipeline Events

This document describes the structure of telemetry events emitted by the Williams Librarian pipeline, including error and storage failure events.

## Event Types

### 1. pipeline.error
Emitted when an unhandled exception or error occurs during pipeline processing.

```
{
  "event_type": "pipeline.error",
  "timestamp": "2025-10-12T12:34:56Z",
  "stage": "loader",  // e.g., extractor, transformer, loader
  "operation": "store",  // operation being performed
  "content_url": "https://...",
  "error_message": "Failed to store processed content: ...",
  "exception_type": "StorageError",
  "traceback": "...optional..."
}
```

### 2. storage.minio.failure
Emitted when a MinIO upload or retrieval fails.

```
{
  "event_type": "storage.minio.failure",
  "timestamp": "2025-10-12T12:34:56Z",
  "operation": "upload_to_tier",
  "bucket": "librarian-tier-a",
  "key": "...",
  "error_message": "...",
  "exception_type": "..."
}
```

## Emission
- Events should be logged to a central logger (e.g., `app.core.telemetry.log_event(event: dict)`) or pushed to a telemetry/monitoring backend if configured.
- All error paths in loaders and storage adapters should emit a structured event before raising or returning errors.

## Extension
- Add new event types as new pipeline stages or storage backends are introduced.
- Update this schema and provide example payloads for each new event type.
