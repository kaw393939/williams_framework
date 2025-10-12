# FastAPI Real-time Ingestion Architecture

**Version**: 1.0  
**Date**: October 12, 2025  
**Status**: Architecture Planning  

---

## 🎯 Executive Summary

This document outlines the architecture for decoupling the Streamlit UI from the ingestion backend by introducing a FastAPI REST API with Server-Sent Events (SSE) for real-time progress streaming. This follows our established TDD methodology with real services (no mocks) and maintains consistency with existing Sprint 4 patterns.

### Goals
1. **Decouple Frontend**: Remove direct CLI dependencies from Streamlit
2. **Real-time Progress**: Stream ingestion stages to UI via SSE
3. **API-First Design**: Enable future frontend replacements (React, Vue, etc.)
4. **TDD Compliance**: 90%+ coverage with real integration tests
5. **Production Ready**: Async, scalable, observable architecture

---

## 🏗️ Architecture Overview

### System Context

```
┌─────────────────┐
│  Streamlit UI   │
│   (Future: React)│
└────────┬────────┘
         │ HTTP/SSE
         ▼
┌─────────────────────────────────────┐
│     FastAPI Backend                 │
│  ┌─────────────────────────────┐   │
│  │  REST API Endpoints          │   │
│  │  - POST /api/v1/ingest       │   │
│  │  - GET /api/v1/ingest/{id}   │   │
│  │  - GET /api/v1/stream/{id}   │   │
│  │  - GET /api/v1/library       │   │
│  └─────────────┬───────────────┘   │
│                │                    │
│  ┌─────────────▼───────────────┐   │
│  │  Ingestion Service Layer    │   │
│  │  - IngestionOrchestrator    │   │
│  │  - ProgressTracker          │   │
│  │  - EventEmitter (SSE)       │   │
│  └─────────────┬───────────────┘   │
│                │                    │
│  ┌─────────────▼───────────────┐   │
│  │  Existing Pipeline Layer    │   │
│  │  - ContentPipeline          │   │
│  │  - Extractors/Transformers  │   │
│  │  - Loaders                  │   │
│  └─────────────┬───────────────┘   │
└────────────────┼───────────────────┘
                 │
         ┌───────▼────────┐
         │  Data Layer    │
         │  - PostgreSQL  │
         │  - Redis       │
         │  - Qdrant      │
         │  - MinIO       │
         └────────────────┘
```

### Component Layers

#### 1. API Layer (`app/api/`)
- **FastAPI Router**: HTTP endpoints for ingestion
- **SSE Handler**: Server-Sent Events for real-time streaming
- **Request/Response Models**: Pydantic validation
- **Error Handling**: HTTP status codes and error responses

#### 2. Service Layer (`app/services/ingestion_service.py`)
- **IngestionOrchestrator**: Coordinates pipeline execution
- **ProgressTracker**: Tracks and emits progress events
- **IngestionJobManager**: Manages concurrent ingestion jobs
- **EventEmitter**: Publishes SSE events to connected clients

#### 3. Pipeline Layer (Existing `app/pipeline/`)
- **ContentPipeline**: Unchanged, enhanced with progress callbacks
- **Extractors/Transformers/Loaders**: No modifications needed

#### 4. Data Layer (Existing `app/repositories/`)
- **PostgresRepository**: Store ingestion jobs and history
- **RedisRepository**: Cache job status and SSE events
- **QdrantRepository**: Vector embeddings (unchanged)
- **MinIORepository**: File storage (unchanged)

---

## 📡 API Design

### REST Endpoints

#### 1. POST /api/v1/ingest

**Purpose**: Submit a URL for ingestion and get a job ID

**Request Body**:
```json
{
  "url": "https://example.com/article",
  "priority": "normal",  // "high", "normal", "low"
  "options": {
    "force_refresh": false,  // Re-process even if cached
    "skip_screening": false  // Skip quality screening
  }
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "url": "https://example.com/article",
  "created_at": "2025-10-12T10:30:00Z",
  "stream_url": "/api/v1/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses**:
- 400: Invalid URL format
- 409: URL already being processed
- 429: Rate limit exceeded
- 503: Pipeline unavailable

---

#### 2. GET /api/v1/ingest/{job_id}

**Purpose**: Get current status of an ingestion job

**Response** (200 OK):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",  // queued, processing, completed, failed
  "url": "https://example.com/article",
  "created_at": "2025-10-12T10:30:00Z",
  "started_at": "2025-10-12T10:30:05Z",
  "completed_at": null,
  "progress": {
    "current_stage": "transform",
    "stages_completed": ["extract"],
    "percent_complete": 50,
    "error": null
  },
  "result": null  // Populated when status=completed
}
```

**Error Responses**:
- 404: Job not found

---

#### 3. GET /api/v1/stream/{job_id}

**Purpose**: Stream real-time progress via Server-Sent Events

**Response Headers**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**SSE Event Stream**:
```
event: job_started
data: {"job_id": "550e8400...", "timestamp": "2025-10-12T10:30:05Z"}

event: stage_started
data: {"stage": "extract", "message": "Fetching content from URL", "timestamp": "2025-10-12T10:30:06Z"}

event: stage_progress
data: {"stage": "extract", "percent": 25, "message": "Downloaded 1.2 MB", "timestamp": "2025-10-12T10:30:08Z"}

event: stage_completed
data: {"stage": "extract", "duration_ms": 3200, "timestamp": "2025-10-12T10:30:10Z"}

event: stage_started
data: {"stage": "transform", "message": "Processing content with AI", "timestamp": "2025-10-12T10:30:10Z"}

event: stage_completed
data: {"stage": "transform", "duration_ms": 5400, "timestamp": "2025-10-12T10:30:15Z"}

event: stage_started
data: {"stage": "load", "message": "Storing in library", "timestamp": "2025-10-12T10:30:15Z"}

event: stage_completed
data: {"stage": "load", "duration_ms": 1200, "timestamp": "2025-10-12T10:30:17Z"}

event: job_completed
data: {"job_id": "550e8400...", "duration_ms": 12000, "result": {"file_path": "data/library/tier-b/...", "title": "..."}, "timestamp": "2025-10-12T10:30:17Z"}

event: error
data: {"job_id": "550e8400...", "stage": "extract", "error": "Failed to fetch URL: Connection timeout", "timestamp": "2025-10-12T10:30:20Z"}
```

**Event Types**:
- `job_started`: Ingestion job began processing
- `stage_started`: Pipeline stage started (extract, transform, load)
- `stage_progress`: Incremental progress within a stage
- `stage_completed`: Pipeline stage finished successfully
- `job_completed`: Entire ingestion completed successfully
- `error`: Error occurred during processing
- `heartbeat`: Keep-alive ping (every 15 seconds)

---

#### 4. GET /api/v1/library

**Purpose**: List ingested library items with filtering

**Query Parameters**:
- `tier`: Filter by tier (tier-a, tier-b, tier-c, tier-d)
- `tag`: Filter by tag (repeatable)
- `limit`: Max results (default 100)
- `offset`: Pagination offset (default 0)
- `sort`: Sort field (created_at, quality_score, title)
- `order`: Sort order (asc, desc)

**Response** (200 OK):
```json
{
  "total": 47,
  "limit": 100,
  "offset": 0,
  "items": [
    {
      "title": "Understanding Transformers",
      "url": "https://example.com/transformers",
      "tier": "tier-a",
      "quality_score": 9.5,
      "tags": ["AI", "NLP", "Deep Learning"],
      "created_at": "2025-10-12T09:15:00Z",
      "file_path": "data/library/tier-a/understanding-transformers.md"
    }
  ]
}
```

---

## 🔧 Implementation Details

### Progress Tracking System

```python
# app/services/ingestion_service.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any
from uuid import UUID, uuid4
import asyncio


class IngestionStage(str, Enum):
    """Pipeline stages for progress tracking."""
    QUEUED = "queued"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """Single progress event in the ingestion pipeline."""
    job_id: UUID
    event_type: str  # job_started, stage_started, stage_progress, stage_completed, error
    stage: Optional[IngestionStage]
    message: str
    percent_complete: Optional[int]
    timestamp: datetime
    metadata: dict[str, Any]


class ProgressTracker:
    """Tracks progress and emits events for ingestion jobs."""
    
    def __init__(self, job_id: UUID):
        self.job_id = job_id
        self.events: list[ProgressEvent] = []
        self.callbacks: list[Callable[[ProgressEvent], None]] = []
        self.current_stage: Optional[IngestionStage] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    def on_progress(self, callback: Callable[[ProgressEvent], None]) -> None:
        """Register a callback to receive progress events."""
        self.callbacks.append(callback)
    
    def emit(
        self, 
        event_type: str,
        stage: Optional[IngestionStage] = None,
        message: str = "",
        percent: Optional[int] = None,
        **metadata
    ) -> None:
        """Emit a progress event to all registered callbacks."""
        event = ProgressEvent(
            job_id=self.job_id,
            event_type=event_type,
            stage=stage,
            message=message,
            percent_complete=percent,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.events.append(event)
        
        for callback in self.callbacks:
            callback(event)
    
    def job_started(self, url: str) -> None:
        """Emit job_started event."""
        self.started_at = datetime.now()
        self.emit("job_started", message=f"Starting ingestion for {url}", url=url)
    
    def stage_started(self, stage: IngestionStage) -> None:
        """Emit stage_started event."""
        self.current_stage = stage
        self.emit("stage_started", stage=stage, message=f"Stage {stage.value} started")
    
    def stage_progress(self, stage: IngestionStage, percent: int, message: str = "") -> None:
        """Emit stage_progress event."""
        self.emit("stage_progress", stage=stage, percent=percent, message=message)
    
    def stage_completed(self, stage: IngestionStage, duration_ms: int) -> None:
        """Emit stage_completed event."""
        self.emit(
            "stage_completed", 
            stage=stage, 
            message=f"Stage {stage.value} completed in {duration_ms}ms",
            duration_ms=duration_ms
        )
    
    def job_completed(self, result: dict[str, Any]) -> None:
        """Emit job_completed event."""
        self.completed_at = datetime.now()
        duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.emit(
            "job_completed", 
            stage=IngestionStage.COMPLETED,
            message="Ingestion completed successfully",
            result=result,
            duration_ms=duration_ms
        )
    
    def error(self, stage: IngestionStage, error_message: str) -> None:
        """Emit error event."""
        self.emit(
            "error",
            stage=stage,
            message=error_message,
            error=error_message
        )


class IngestionOrchestrator:
    """Orchestrates ingestion jobs with progress tracking."""
    
    def __init__(self, pipeline: ContentPipeline, redis_repo: RedisRepository):
        self.pipeline = pipeline
        self.redis = redis_repo
        self.active_jobs: dict[UUID, ProgressTracker] = {}
    
    async def submit_job(self, url: str, options: dict[str, Any]) -> UUID:
        """Submit a new ingestion job and return job ID."""
        job_id = uuid4()
        tracker = ProgressTracker(job_id)
        self.active_jobs[job_id] = tracker
        
        # Store job metadata in Redis
        await self.redis.set_json(
            f"ingestion:job:{job_id}",
            {
                "job_id": str(job_id),
                "url": url,
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "options": options
            },
            ttl=3600  # 1 hour TTL
        )
        
        # Start processing asynchronously
        asyncio.create_task(self._process_job(job_id, url, tracker))
        
        return job_id
    
    async def _process_job(self, job_id: UUID, url: str, tracker: ProgressTracker) -> None:
        """Process an ingestion job with progress tracking."""
        try:
            tracker.job_started(url)
            
            # Extract stage
            tracker.stage_started(IngestionStage.EXTRACT)
            start_time = datetime.now()
            
            raw_content = await self.pipeline.extractor.extract(url)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tracker.stage_completed(IngestionStage.EXTRACT, duration_ms)
            
            # Transform stage
            tracker.stage_started(IngestionStage.TRANSFORM)
            start_time = datetime.now()
            
            processed_content = await self.pipeline.transformer.transform(raw_content)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tracker.stage_completed(IngestionStage.TRANSFORM, duration_ms)
            
            # Load stage
            tracker.stage_started(IngestionStage.LOAD)
            start_time = datetime.now()
            
            library_file = await self.pipeline.loader.load(processed_content)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tracker.stage_completed(IngestionStage.LOAD, duration_ms)
            
            # Job completed
            result = {
                "file_path": str(library_file.file_path),
                "title": library_file.title,
                "tier": library_file.tier,
                "quality_score": library_file.quality_score
            }
            tracker.job_completed(result)
            
            # Update Redis status
            await self.redis.set_json(
                f"ingestion:job:{job_id}",
                {
                    "job_id": str(job_id),
                    "url": url,
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.now().isoformat()
                },
                ttl=3600
            )
            
        except Exception as e:
            tracker.error(tracker.current_stage or IngestionStage.FAILED, str(e))
            
            # Update Redis with error
            await self.redis.set_json(
                f"ingestion:job:{job_id}",
                {
                    "job_id": str(job_id),
                    "url": url,
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                },
                ttl=3600
            )
    
    def get_tracker(self, job_id: UUID) -> Optional[ProgressTracker]:
        """Get the progress tracker for a job."""
        return self.active_jobs.get(job_id)
    
    async def get_job_status(self, job_id: UUID) -> Optional[dict[str, Any]]:
        """Get job status from Redis."""
        return await self.redis.get_json(f"ingestion:job:{job_id}")
```

---

### FastAPI Router

```python
# app/api/routers/ingestion.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal
from uuid import UUID
import asyncio
import json

from app.services.ingestion_service import IngestionOrchestrator, ProgressEvent
from app.pipeline.cli import build_pipeline_for_url


router = APIRouter(prefix="/api/v1", tags=["ingestion"])


class IngestRequest(BaseModel):
    """Request model for POST /ingest."""
    url: HttpUrl
    priority: Literal["high", "normal", "low"] = "normal"
    options: dict[str, bool] = {}


class IngestResponse(BaseModel):
    """Response model for POST /ingest."""
    job_id: UUID
    status: str
    url: str
    created_at: str
    stream_url: str


class JobStatusResponse(BaseModel):
    """Response model for GET /ingest/{job_id}."""
    job_id: UUID
    status: str
    url: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: dict[str, Any]
    result: Optional[dict[str, Any]]


# Global orchestrator instance (will be injected via dependency in production)
_orchestrator: Optional[IngestionOrchestrator] = None


def get_orchestrator() -> IngestionOrchestrator:
    """Dependency injection for orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        from app.pipeline.cli import build_default_pipeline
        from app.repositories.redis_repository import RedisRepository
        from app.core.config import settings
        
        pipeline = build_default_pipeline()
        redis_repo = RedisRepository(
            host=settings.redis_host,
            port=settings.redis_port
        )
        _orchestrator = IngestionOrchestrator(pipeline, redis_repo)
    
    return _orchestrator


@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def submit_ingestion(request: IngestRequest) -> IngestResponse:
    """Submit a URL for ingestion and return job ID."""
    orchestrator = get_orchestrator()
    
    job_id = await orchestrator.submit_job(str(request.url), request.options)
    
    return IngestResponse(
        job_id=job_id,
        status="queued",
        url=str(request.url),
        created_at=datetime.now().isoformat(),
        stream_url=f"/api/v1/stream/{job_id}"
    )


@router.get("/ingest/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID) -> JobStatusResponse:
    """Get current status of an ingestion job."""
    orchestrator = get_orchestrator()
    
    job_data = await orchestrator.get_job_status(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    tracker = orchestrator.get_tracker(job_id)
    
    progress = {
        "current_stage": tracker.current_stage.value if tracker and tracker.current_stage else None,
        "stages_completed": [e.stage.value for e in tracker.events if e.event_type == "stage_completed"] if tracker else [],
        "percent_complete": 0,  # Calculate based on stages
        "error": None
    }
    
    return JobStatusResponse(
        job_id=job_id,
        status=job_data["status"],
        url=job_data["url"],
        created_at=job_data["created_at"],
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("completed_at"),
        progress=progress,
        result=job_data.get("result")
    )


@router.get("/stream/{job_id}")
async def stream_progress(job_id: UUID):
    """Stream real-time progress via Server-Sent Events."""
    orchestrator = get_orchestrator()
    
    # Verify job exists
    job_data = await orchestrator.get_job_status(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        """Generate SSE events from progress tracker."""
        tracker = orchestrator.get_tracker(job_id)
        if not tracker:
            # Job completed before stream connected
            yield f"event: job_completed\ndata: {json.dumps({'job_id': str(job_id)})}\n\n"
            return
        
        # Create a queue for this client
        queue = asyncio.Queue()
        
        def callback(event: ProgressEvent):
            """Callback to receive progress events."""
            queue.put_nowait(event)
        
        tracker.on_progress(callback)
        
        try:
            while True:
                # Wait for next event with timeout for heartbeat
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    
                    # Format as SSE
                    data = {
                        "job_id": str(event.job_id),
                        "stage": event.stage.value if event.stage else None,
                        "message": event.message,
                        "percent": event.percent_complete,
                        "timestamp": event.timestamp.isoformat(),
                        **event.metadata
                    }
                    
                    yield f"event: {event.event_type}\ndata: {json.dumps(data)}\n\n"
                    
                    # Stop streaming after job_completed or error
                    if event.event_type in ("job_completed", "error"):
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                    
        except asyncio.CancelledError:
            # Client disconnected
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/library")
async def list_library_items(
    tier: Optional[str] = None,
    tag: Optional[list[str]] = None,
    limit: int = 100,
    offset: int = 0,
    sort: str = "created_at",
    order: Literal["asc", "desc"] = "desc"
):
    """List ingested library items with filtering."""
    # This will be implemented using existing LibraryService
    # For now, placeholder
    return {
        "total": 0,
        "limit": limit,
        "offset": offset,
        "items": []
    }
```

---

### FastAPI Application Setup

```python
# app/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routers import ingestion
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    print("🚀 FastAPI server starting...")
    
    # Initialize services here if needed
    # await initialize_services()
    
    yield
    
    # Shutdown
    print("🛑 FastAPI server shutting down...")
    # await cleanup_services()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Williams Librarian API",
        description="AI-powered content ingestion and library management",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware for Streamlit
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501", "http://localhost:3000"],  # Streamlit and React
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    app.include_router(ingestion.router)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development only
        log_level="info"
    )
```

---

## 🧪 Testing Strategy

Following our established TDD methodology with **REAL services, NO MOCKS**.

### Test Pyramid Distribution

- **Unit Tests (50%)**: Business logic, utilities, models
- **Integration Tests (40%)**: API endpoints with real services
- **E2E Tests (10%)**: Full ingestion flow

### Test Structure

```
tests/
├── unit/
│   ├── api/
│   │   ├── test_ingest_request_model.py
│   │   ├── test_ingest_response_model.py
│   │   └── test_job_status_model.py
│   ├── services/
│   │   ├── test_progress_tracker.py
│   │   ├── test_ingestion_stage.py
│   │   └── test_progress_event.py
│
├── integration/
│   ├── api/
│   │   ├── test_ingest_endpoint_real.py        # POST /ingest with real pipeline
│   │   ├── test_job_status_endpoint_real.py    # GET /ingest/{id} with Redis
│   │   ├── test_sse_streaming_real.py          # SSE with real tracker
│   │   └── test_library_endpoint_real.py       # GET /library with real data
│   ├── services/
│   │   ├── test_orchestrator_real_pipeline.py  # Real pipeline execution
│   │   └── test_orchestrator_redis_integration.py
│
└── e2e/
    └── api/
        └── test_full_ingestion_flow.py         # Submit → Stream → Verify
```

---

## 📋 Sprint Planning

### Sprint 5: FastAPI Backend Foundation

**Duration**: 2 weeks  
**Goal**: Build API foundation with real integration tests  
**Stories**: 4

#### Story S5-501: Progress Tracking System ✅
**Priority**: P0 (Blocker)  
**Estimate**: 3 days

**Tasks**:
1. Create `IngestionStage` enum
2. Create `ProgressEvent` dataclass
3. Implement `ProgressTracker` class
4. Add callback mechanism
5. Write 10 unit tests (RED-GREEN-REFACTOR)
6. Achieve 100% coverage

**Tests**:
- `test_progress_tracker_initialization`
- `test_emit_event_calls_callbacks`
- `test_job_started_event`
- `test_stage_started_event`
- `test_stage_progress_event`
- `test_stage_completed_event`
- `test_job_completed_event`
- `test_error_event`
- `test_multiple_callbacks`
- `test_event_ordering`

**Acceptance Criteria**:
- ✅ All event types emit correctly
- ✅ Callbacks receive events in order
- ✅ Event history stored in tracker
- ✅ 100% test coverage

---

#### Story S5-502: Ingestion Orchestrator with Real Pipeline ✅
**Priority**: P0 (Blocker)  
**Estimate**: 5 days

**Tasks**:
1. Create `IngestionOrchestrator` class
2. Integrate with existing `ContentPipeline`
3. Add Redis job state management
4. Implement `submit_job()` method
5. Implement `_process_job()` with progress tracking
6. Write 8 integration tests with REAL services
7. Test with actual URL ingestion

**Tests** (ALL WITH REAL SERVICES):
- `test_submit_job_returns_job_id` (real Redis)
- `test_process_job_calls_pipeline` (real pipeline)
- `test_progress_events_emitted_during_processing` (real tracking)
- `test_job_stored_in_redis_on_submit` (real Redis read/write)
- `test_job_status_updated_to_completed` (real Redis)
- `test_error_handling_updates_redis` (real pipeline failure)
- `test_concurrent_jobs_independent` (real concurrent execution)
- `test_get_job_status_from_redis` (real Redis fetch)

**Acceptance Criteria**:
- ✅ Jobs execute with real ContentPipeline
- ✅ Progress tracked through all stages
- ✅ Redis stores job state (no mocks)
- ✅ Errors handled and logged
- ✅ 90%+ test coverage

---

#### Story S5-503: FastAPI Ingestion Endpoints ✅
**Priority**: P0 (Blocker)  
**Estimate**: 4 days

**Tasks**:
1. Create FastAPI app structure
2. Implement POST /api/v1/ingest
3. Implement GET /api/v1/ingest/{job_id}
4. Add request/response models
5. Add dependency injection for orchestrator
6. Write 12 integration tests with REAL API calls
7. Test error scenarios

**Tests** (ALL WITH REAL HTTP REQUESTS):
- `test_post_ingest_returns_202` (real HTTP)
- `test_post_ingest_invalid_url_returns_400` (real validation)
- `test_post_ingest_creates_job_in_redis` (real Redis check)
- `test_get_job_status_returns_200` (real HTTP)
- `test_get_job_status_not_found_returns_404` (real HTTP)
- `test_get_job_status_reflects_pipeline_progress` (real orchestrator)
- `test_post_ingest_starts_pipeline_execution` (real pipeline)
- `test_concurrent_ingestion_requests` (real concurrent HTTP)
- `test_job_status_updates_as_pipeline_progresses` (real polling)
- `test_completed_job_returns_result` (real pipeline completion)
- `test_failed_job_returns_error` (real pipeline failure)
- `test_cors_headers_present` (real CORS middleware)

**Acceptance Criteria**:
- ✅ Endpoints accept requests via HTTP
- ✅ Jobs created and tracked in Redis
- ✅ Status reflects real pipeline state
- ✅ CORS enabled for Streamlit
- ✅ 90%+ test coverage

---

#### Story S5-504: Server-Sent Events Streaming ✅
**Priority**: P1 (High)  
**Estimate**: 4 days

**Tasks**:
1. Implement GET /api/v1/stream/{job_id}
2. Create SSE event formatter
3. Add heartbeat mechanism (15s)
4. Handle client disconnections
5. Write 10 integration tests with REAL SSE connections
6. Test with multiple concurrent clients

**Tests** (ALL WITH REAL SSE CONNECTIONS):
- `test_sse_stream_connects_successfully` (real HTTP SSE)
- `test_sse_stream_receives_job_started_event` (real event)
- `test_sse_stream_receives_stage_events` (real pipeline progress)
- `test_sse_stream_receives_job_completed` (real completion)
- `test_sse_stream_receives_error_event` (real failure)
- `test_sse_stream_heartbeat_every_15_seconds` (real timing)
- `test_sse_stream_closes_after_completion` (real connection close)
- `test_sse_stream_not_found_for_invalid_job` (real 404)
- `test_multiple_clients_receive_same_events` (real concurrent SSE)
- `test_client_reconnect_after_disconnect` (real reconnection)

**Acceptance Criteria**:
- ✅ SSE streams real-time events
- ✅ Heartbeat keeps connection alive
- ✅ Multiple clients supported
- ✅ Graceful disconnection handling
- ✅ 90%+ test coverage

---

### Sprint 6: Streamlit Integration

**Duration**: 1 week  
**Goal**: Connect Streamlit UI to FastAPI backend  
**Stories**: 2

#### Story S6-601: Streamlit Ingest Page ✅
**Priority**: P0 (Blocker)  
**Estimate**: 3 days

**Tasks**:
1. Create `app/presentation/pages/ingest.py`
2. Add URL input form
3. Implement HTTP POST to /api/v1/ingest
4. Display job ID and stream URL
5. Add basic error handling
6. Write 5 UI tests

**Tests**:
- `test_ingest_page_renders`
- `test_url_input_validation`
- `test_submit_button_triggers_api_call`
- `test_api_error_displayed_to_user`
- `test_success_shows_job_id`

**Acceptance Criteria**:
- ✅ User can submit URLs
- ✅ API errors displayed clearly
- ✅ Job ID shown after submission
- ✅ 90%+ test coverage

---

#### Story S6-602: Real-time Progress Display ✅
**Priority**: P0 (Blocker)  
**Estimate**: 4 days

**Tasks**:
1. Create SSE client in Streamlit
2. Display progress bar for stages
3. Show stage messages in real-time
4. Handle completion and errors
5. Add retry mechanism
6. Write 7 integration tests

**Tests**:
- `test_sse_connection_established`
- `test_progress_bar_updates_with_events`
- `test_stage_messages_displayed`
- `test_completion_message_shown`
- `test_error_message_shown`
- `test_connection_lost_retry`
- `test_multiple_simultaneous_jobs`

**Acceptance Criteria**:
- ✅ Real-time progress visible
- ✅ All stages displayed
- ✅ Errors handled gracefully
- ✅ UI responsive during ingestion
- ✅ 90%+ test coverage

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
# Add FastAPI dependencies
poetry add fastapi uvicorn[standard] python-multipart sse-starlette

# Add test dependencies
poetry add --group dev httpx pytest-asyncio aiohttp
```

### 2. Run FastAPI Server

```bash
# Development mode with auto-reload
poetry run uvicorn app.api.main:app --reload --port 8000

# Production mode
poetry run uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Run Tests

```bash
# All tests
poetry run pytest

# Integration tests only (with real services)
poetry run pytest tests/integration/api/ -v

# Watch mode during development
poetry run pytest-watch

# Coverage report
poetry run pytest --cov=app --cov-report=html
```

### 4. Manual Testing

```bash
# Submit ingestion job
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Get job status
curl http://localhost:8000/api/v1/ingest/{job_id}

# Stream progress (SSE)
curl -N http://localhost:8000/api/v1/stream/{job_id}
```

---

## 📊 Success Metrics

### Coverage Goals
- **Overall**: 90%+ (enforced by CI)
- **API Layer**: 95%+
- **Service Layer**: 95%+
- **Integration Tests**: 100% real services

### Performance Goals
- **API Response Time**: < 100ms (excluding pipeline)
- **SSE Latency**: < 50ms per event
- **Concurrent Jobs**: 10+ simultaneous ingestions
- **Pipeline Throughput**: Same as current CLI

### Quality Goals
- **Zero Mocks**: 100% real service integration tests
- **TDD Compliance**: All code written test-first
- **Documentation**: 100% docstrings
- **Type Safety**: 100% type hints with mypy

---

## 🔄 Future Enhancements

### Phase 2 (Post-MVP)
- **WebSocket Support**: Replace SSE with WebSockets for bidirectional communication
- **Job Queue**: Add Celery/RQ for background processing
- **Rate Limiting**: Per-user API rate limits
- **Authentication**: JWT-based API authentication
- **Batch Ingestion**: Submit multiple URLs at once
- **Job Cancellation**: Cancel in-progress jobs
- **Job History**: Persistent job history in PostgreSQL

### Phase 3 (Scale)
- **Horizontal Scaling**: Multiple FastAPI workers
- **Load Balancing**: Nginx reverse proxy
- **Monitoring**: Prometheus metrics + Grafana dashboards
- **Observability**: OpenTelemetry tracing
- **Caching Layer**: Redis caching for library queries

---

## ✅ Next Steps

1. **Review & Approve** this architecture document
2. **Create Sprint 5 backlog** with detailed tasks
3. **Set up FastAPI project structure** (directories, main.py)
4. **Start Story S5-501** (Progress Tracking) with TDD
5. **Daily standups** to track progress and blockers

**Ready to begin implementation? Let's start with S5-501! 🚀**
