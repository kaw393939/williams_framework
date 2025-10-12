# Sprint 5 TDD Implementation Plan

**Sprint**: Sprint 5 - FastAPI Backend Foundation  
**Duration**: 2 weeks (10 working days)  
**Date**: October 12 - October 26, 2025  
**Coverage Target**: 90%+ with REAL services (NO MOCKS)

---

## 🎯 Sprint Goal

Build a production-ready FastAPI backend with real-time ingestion progress streaming, following strict TDD methodology with real integration tests using actual Docker services (PostgreSQL, Redis, Qdrant, MinIO).

---

## 📋 Sprint Backlog

| Story | Priority | Estimate | Status |
|-------|----------|----------|--------|
| S5-501: Progress Tracking System | P0 | 3 days | TODO |
| S5-502: Ingestion Orchestrator | P0 | 5 days | TODO |
| S5-503: FastAPI Endpoints | P0 | 4 days | TODO |
| S5-504: SSE Streaming | P1 | 4 days | TODO |

**Total**: 16 days (slightly over-estimated for 10-day sprint, will prioritize)

---

## 📖 TDD Methodology Reminder

### RED-GREEN-REFACTOR Cycle

```
🔴 RED Phase:
   1. Write a failing test FIRST
   2. Run test → verify it FAILS
   3. Commit message: "RED: [test description]"

🟢 GREEN Phase:
   1. Write MINIMAL code to pass the test
   2. Run test → verify it PASSES
   3. Commit message: "GREEN: [test description]"

🔄 REFACTOR Phase:
   1. Improve code quality
   2. Run ALL tests → verify still passing
   3. Commit message: "REFACTOR: [improvement description]"
```

### Real Services Rule

**❌ NO MOCKS FOR INTEGRATION TESTS**

- Use real Redis running in Docker
- Use real PostgreSQL running in Docker
- Use real Qdrant running in Docker
- Use real MinIO running in Docker
- Use real HTTP requests with `httpx.AsyncClient`
- Use real SSE connections

**✅ OK to use test doubles for:**
- Time manipulation (freezegun)
- UUID generation (for deterministic tests)
- External API calls that cost money (OpenAI)

---

## 📅 Day-by-Day Plan

### Day 1-2: Setup & S5-501 Foundation

#### Day 1 Morning: Project Setup
**Tasks**:
1. Create directory structure
2. Add FastAPI dependencies to pyproject.toml
3. Set up basic FastAPI app skeleton
4. Verify Docker services running

**Commands**:
```bash
# Add dependencies
poetry add fastapi uvicorn[standard] python-multipart sse-starlette
poetry add --group dev httpx pytest-asyncio aiohttp

# Create directories
mkdir -p app/api/routers
mkdir -p app/services
mkdir -p tests/unit/api
mkdir -p tests/unit/services
mkdir -p tests/integration/api
mkdir -p tests/integration/services
mkdir -p tests/e2e/api

# Verify Docker
sudo docker-compose ps
```

**Deliverables**:
- ✅ Directory structure created
- ✅ Dependencies installed
- ✅ Docker services verified

#### Day 1 Afternoon: Progress Tracking Models (RED)
**Story**: S5-501  
**Phase**: 🔴 RED

**Test File**: `tests/unit/services/test_progress_tracker.py`

**Test 1: IngestionStage Enum**
```python
def test_ingestion_stage_enum_values():
    """🔴 RED: Should define all pipeline stages"""
    from app.services.ingestion_service import IngestionStage
    
    assert IngestionStage.QUEUED == "queued"
    assert IngestionStage.EXTRACT == "extract"
    assert IngestionStage.TRANSFORM == "transform"
    assert IngestionStage.LOAD == "load"
    assert IngestionStage.COMPLETED == "completed"
    assert IngestionStage.FAILED == "failed"
```

**Steps**:
1. Write test above
2. Run `pytest tests/unit/services/test_progress_tracker.py::test_ingestion_stage_enum_values`
3. **Verify FAILS** (ImportError: No module named 'app.services.ingestion_service')
4. Commit: `git commit -m "RED: S5-501 - Test IngestionStage enum values"`

**Test 2: ProgressEvent Dataclass**
```python
def test_progress_event_creation():
    """🔴 RED: Should create ProgressEvent with required fields"""
    from app.services.ingestion_service import ProgressEvent, IngestionStage
    from uuid import uuid4
    from datetime import datetime
    
    job_id = uuid4()
    event = ProgressEvent(
        job_id=job_id,
        event_type="job_started",
        stage=IngestionStage.QUEUED,
        message="Starting job",
        percent_complete=0,
        timestamp=datetime.now(),
        metadata={"url": "https://example.com"}
    )
    
    assert event.job_id == job_id
    assert event.event_type == "job_started"
    assert event.stage == IngestionStage.QUEUED
    assert event.message == "Starting job"
    assert event.percent_complete == 0
    assert isinstance(event.timestamp, datetime)
    assert event.metadata["url"] == "https://example.com"
```

**Steps**:
1. Write test above
2. Run test
3. **Verify FAILS** (ProgressEvent not defined)
4. Commit: `git commit -m "RED: S5-501 - Test ProgressEvent dataclass creation"`

**Test 3: ProgressTracker Initialization**
```python
def test_progress_tracker_initialization():
    """🔴 RED: Should initialize ProgressTracker with job_id"""
    from app.services.ingestion_service import ProgressTracker
    from uuid import uuid4
    
    job_id = uuid4()
    tracker = ProgressTracker(job_id)
    
    assert tracker.job_id == job_id
    assert tracker.events == []
    assert tracker.callbacks == []
    assert tracker.current_stage is None
    assert tracker.started_at is None
    assert tracker.completed_at is None
```

**Steps**:
1. Write test
2. Run test
3. **Verify FAILS** (ProgressTracker not defined)
4. Commit: `git commit -m "RED: S5-501 - Test ProgressTracker initialization"`

**End of Day 1**: 3 failing tests ✅

---

#### Day 2 Morning: Progress Tracking Implementation (GREEN)
**Story**: S5-501  
**Phase**: 🟢 GREEN

**Implementation File**: `app/services/ingestion_service.py`

**Step 1: Create IngestionStage Enum**
```python
from enum import Enum

class IngestionStage(str, Enum):
    """Pipeline stages for progress tracking."""
    QUEUED = "queued"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Steps**:
1. Create file and add code above
2. Run `pytest tests/unit/services/test_progress_tracker.py::test_ingestion_stage_enum_values`
3. **Verify PASSES** ✅
4. Commit: `git commit -m "GREEN: S5-501 - Implement IngestionStage enum"`

**Step 2: Create ProgressEvent Dataclass**
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

@dataclass
class ProgressEvent:
    """Single progress event in the ingestion pipeline."""
    job_id: UUID
    event_type: str
    stage: Optional[IngestionStage]
    message: str
    percent_complete: Optional[int]
    timestamp: datetime
    metadata: dict[str, Any]
```

**Steps**:
1. Add code above to file
2. Run `pytest tests/unit/services/test_progress_tracker.py::test_progress_event_creation`
3. **Verify PASSES** ✅
4. Commit: `git commit -m "GREEN: S5-501 - Implement ProgressEvent dataclass"`

**Step 3: Create ProgressTracker Class**
```python
from typing import Callable

class ProgressTracker:
    """Tracks progress and emits events for ingestion jobs."""
    
    def __init__(self, job_id: UUID):
        self.job_id = job_id
        self.events: list[ProgressEvent] = []
        self.callbacks: list[Callable[[ProgressEvent], None]] = []
        self.current_stage: Optional[IngestionStage] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
```

**Steps**:
1. Add code above
2. Run `pytest tests/unit/services/test_progress_tracker.py::test_progress_tracker_initialization`
3. **Verify PASSES** ✅
4. Commit: `git commit -m "GREEN: S5-501 - Implement ProgressTracker initialization"`

**Checkpoint**: Run all 3 tests together
```bash
pytest tests/unit/services/test_progress_tracker.py -v
```
All should pass ✅

---

#### Day 2 Afternoon: Progress Tracker Methods (RED-GREEN)

**Test 4: Emit Event with Callback** 🔴
```python
def test_emit_event_calls_callbacks():
    """🔴 RED: Should call all registered callbacks when emitting event"""
    from app.services.ingestion_service import ProgressTracker, IngestionStage
    from uuid import uuid4
    
    job_id = uuid4()
    tracker = ProgressTracker(job_id)
    
    events_received = []
    
    def callback(event):
        events_received.append(event)
    
    tracker.on_progress(callback)
    tracker.emit(
        event_type="test_event",
        stage=IngestionStage.EXTRACT,
        message="Test message",
        percent=50
    )
    
    assert len(events_received) == 1
    assert events_received[0].event_type == "test_event"
    assert events_received[0].message == "Test message"
    assert events_received[0].percent_complete == 50
```

**Steps**:
1. Write test
2. Run test → **FAILS** (AttributeError: 'ProgressTracker' has no attribute 'on_progress')
3. Commit: `git commit -m "RED: S5-501 - Test emit event with callback"`

**Implementation** 🟢
```python
class ProgressTracker:
    # ... existing code ...
    
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
```

**Steps**:
1. Add code above
2. Run test → **PASSES** ✅
3. Commit: `git commit -m "GREEN: S5-501 - Implement emit and on_progress methods"`

**Test 5-10: Helper Methods** (Similar RED-GREEN cycle)
```python
def test_job_started_emits_correct_event():
    """🔴 RED: Should emit job_started event"""
    # Test implementation...

def test_stage_started_emits_correct_event():
    """🔴 RED: Should emit stage_started event"""
    # Test implementation...

def test_stage_progress_emits_correct_event():
    """🔴 RED: Should emit stage_progress event"""
    # Test implementation...

def test_stage_completed_emits_correct_event():
    """🔴 RED: Should emit stage_completed event"""
    # Test implementation...

def test_job_completed_emits_correct_event():
    """🔴 RED: Should emit job_completed event"""
    # Test implementation...

def test_error_emits_correct_event():
    """🔴 RED: Should emit error event"""
    # Test implementation...
```

**End of Day 2**: S5-501 Foundation complete with 10 tests passing ✅

---

### Day 3-5: S5-502 Ingestion Orchestrator

#### Day 3 Morning: Orchestrator Setup (RED)

**Test File**: `tests/integration/services/test_orchestrator_real_pipeline.py`

**Test 1: Orchestrator Initialization with Real Pipeline** 🔴
```python
import pytest
from app.services.ingestion_service import IngestionOrchestrator
from app.pipeline.cli import build_default_pipeline
from app.repositories.redis_repository import RedisRepository
from app.core.config import settings


@pytest.fixture
async def redis_repo():
    """Create real Redis repository connected to Docker."""
    repo = RedisRepository(
        host=settings.redis_host,
        port=settings.redis_port
    )
    await repo.connect()
    yield repo
    await repo.close()


@pytest.fixture
def real_pipeline():
    """Create real ContentPipeline with all extractors/transformers/loaders."""
    return build_default_pipeline()


@pytest.mark.asyncio
async def test_orchestrator_initialization_with_real_services(redis_repo, real_pipeline):
    """🔴 RED: Should initialize orchestrator with real pipeline and Redis"""
    orchestrator = IngestionOrchestrator(real_pipeline, redis_repo)
    
    assert orchestrator.pipeline is not None
    assert orchestrator.redis is not None
    assert orchestrator.active_jobs == {}
```

**Steps**:
1. Write test
2. Run test → **FAILS** (IngestionOrchestrator not defined)
3. Commit: `git commit -m "RED: S5-502 - Test orchestrator initialization with real services"`

#### Day 3 Afternoon: Orchestrator Implementation (GREEN)

**Implementation**: Add to `app/services/ingestion_service.py`
```python
class IngestionOrchestrator:
    """Orchestrates ingestion jobs with progress tracking."""
    
    def __init__(self, pipeline: ContentPipeline, redis_repo: RedisRepository):
        self.pipeline = pipeline
        self.redis = redis_repo
        self.active_jobs: dict[UUID, ProgressTracker] = {}
```

**Steps**:
1. Add code
2. Run test → **PASSES** ✅
3. Commit: `git commit -m "GREEN: S5-502 - Implement orchestrator initialization"`

#### Day 4: Submit Job with Real Redis (RED-GREEN)

**Test 2: Submit Job Stores in Redis** 🔴
```python
@pytest.mark.asyncio
async def test_submit_job_stores_in_real_redis(redis_repo, real_pipeline):
    """🔴 RED: Should store job metadata in real Redis"""
    orchestrator = IngestionOrchestrator(real_pipeline, redis_repo)
    
    url = "https://example.com/test-article"
    job_id = await orchestrator.submit_job(url, options={})
    
    # Verify job stored in REAL Redis
    job_data = await redis_repo.get_json(f"ingestion:job:{job_id}")
    
    assert job_data is not None
    assert job_data["url"] == url
    assert job_data["status"] == "queued"
    assert "created_at" in job_data
```

**Steps**:
1. Write test
2. Run test → **FAILS** (AttributeError: 'IngestionOrchestrator' has no attribute 'submit_job')
3. Commit: `git commit -m "RED: S5-502 - Test submit job stores in real Redis"`

**Implementation** 🟢
```python
from uuid import uuid4
import asyncio

class IngestionOrchestrator:
    # ... existing code ...
    
    async def submit_job(self, url: str, options: dict[str, Any]) -> UUID:
        """Submit a new ingestion job and return job ID."""
        job_id = uuid4()
        tracker = ProgressTracker(job_id)
        self.active_jobs[job_id] = tracker
        
        # Store job metadata in REAL Redis
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
```

**Steps**:
1. Add code
2. Run test → **PASSES** ✅
3. Commit: `git commit -m "GREEN: S5-502 - Implement submit_job with Redis storage"`

#### Day 5: Process Job with Real Pipeline (RED-GREEN)

**Test 3: Process Job Executes Real Pipeline** 🔴
```python
@pytest.mark.asyncio
async def test_process_job_executes_real_pipeline(redis_repo, real_pipeline):
    """🔴 RED: Should execute real ContentPipeline and emit progress events"""
    orchestrator = IngestionOrchestrator(real_pipeline, redis_repo)
    
    events_received = []
    
    url = "https://example.com/test-article"
    job_id = await orchestrator.submit_job(url, options={})
    
    # Get tracker and register callback
    tracker = orchestrator.get_tracker(job_id)
    tracker.on_progress(lambda event: events_received.append(event))
    
    # Wait for job to complete (real pipeline execution)
    await asyncio.sleep(10)  # Give pipeline time to run
    
    # Verify events emitted from REAL pipeline execution
    event_types = [e.event_type for e in events_received]
    assert "job_started" in event_types
    assert "stage_started" in event_types
    assert "stage_completed" in event_types
    assert "job_completed" in event_types or "error" in event_types
    
    # Verify Redis updated by REAL pipeline
    job_data = await redis_repo.get_json(f"ingestion:job:{job_id}")
    assert job_data["status"] in ("completed", "failed")
```

**Steps**:
1. Write test
2. Run test → **FAILS** (AttributeError: '_process_job' not defined)
3. Commit: `git commit -m "RED: S5-502 - Test process job with real pipeline"`

**Implementation** 🟢
```python
class IngestionOrchestrator:
    # ... existing code ...
    
    async def _process_job(self, job_id: UUID, url: str, tracker: ProgressTracker) -> None:
        """Process an ingestion job with progress tracking using REAL pipeline."""
        try:
            tracker.job_started(url)
            
            # EXTRACT stage with REAL extractor
            tracker.stage_started(IngestionStage.EXTRACT)
            start_time = datetime.now()
            
            raw_content = await self.pipeline.extractor.extract(url)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tracker.stage_completed(IngestionStage.EXTRACT, duration_ms)
            
            # TRANSFORM stage with REAL transformer
            tracker.stage_started(IngestionStage.TRANSFORM)
            start_time = datetime.now()
            
            processed_content = await self.pipeline.transformer.transform(raw_content)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tracker.stage_completed(IngestionStage.TRANSFORM, duration_ms)
            
            # LOAD stage with REAL loader
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
            
            # Update REAL Redis status
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
            
            # Update REAL Redis with error
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
        """Get job status from REAL Redis."""
        return await self.redis.get_json(f"ingestion:job:{job_id}")
```

**Steps**:
1. Add code
2. Run test → **PASSES** ✅ (takes ~10 seconds due to real pipeline)
3. Commit: `git commit -m "GREEN: S5-502 - Implement process_job with real pipeline execution"`

**End of Day 5**: S5-502 core implementation complete with real pipeline integration ✅

---

### Day 6-8: S5-503 FastAPI Endpoints

#### Day 6: FastAPI Setup and POST /ingest (RED-GREEN)

**Test File**: `tests/integration/api/test_ingest_endpoint_real.py`

**Test 1: POST /ingest Returns 202 with Real Job** 🔴
```python
import pytest
from httpx import AsyncClient
from app.api.main import create_app


@pytest.fixture
async def client():
    """Create real HTTP client for FastAPI app."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_post_ingest_returns_202_with_real_job(client):
    """🔴 RED: Should return 202 and create real job in Redis"""
    response = await client.post(
        "/api/v1/ingest",
        json={"url": "https://example.com/article"}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["url"] == "https://example.com/article"
    assert "stream_url" in data
```

**Steps**:
1. Write test
2. Run test → **FAILS** (404 Not Found - endpoint doesn't exist)
3. Commit: `git commit -m "RED: S5-503 - Test POST /ingest returns 202"`

**Implementation**: Create FastAPI app and router

1. **Create `app/api/__init__.py`** (empty file)

2. **Create `app/api/main.py`**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    print("🚀 FastAPI server starting...")
    yield
    print("🛑 FastAPI server shutting down...")


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
        allow_origins=["http://localhost:8501", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import and register routers
    from app.api.routers import ingestion
    app.include_router(ingestion.router)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}
    
    return app


app = create_app()
```

3. **Create `app/api/routers/__init__.py`** (empty file)

4. **Create `app/api/routers/ingestion.py`**:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

from app.services.ingestion_service import IngestionOrchestrator
from app.pipeline.cli import build_default_pipeline
from app.repositories.redis_repository import RedisRepository
from app.core.config import settings


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


# Global orchestrator (will be dependency injection in production)
_orchestrator: Optional[IngestionOrchestrator] = None


def get_orchestrator() -> IngestionOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
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
    
    job_id = await orchestrator.submit_job(str(request.url), dict(request.options))
    
    return IngestResponse(
        job_id=job_id,
        status="queued",
        url=str(request.url),
        created_at=datetime.now().isoformat(),
        stream_url=f"/api/v1/stream/{job_id}"
    )
```

**Steps**:
1. Create files above
2. Run test → **PASSES** ✅
3. Commit: `git commit -m "GREEN: S5-503 - Implement POST /ingest endpoint"`

#### Day 7: GET /ingest/{job_id} (RED-GREEN)

*Similar pattern: Write tests first, implement endpoints*

#### Day 8: Additional API Tests

*Write comprehensive error handling and edge case tests*

---

### Day 9-10: S5-504 SSE Streaming

#### Day 9-10: Implement SSE with Real Connections

**Test File**: `tests/integration/api/test_sse_streaming_real.py`

**Test: Real SSE Connection Receives Events** 🔴
```python
import pytest
from httpx import AsyncClient
import asyncio


@pytest.mark.asyncio
async def test_sse_stream_receives_real_pipeline_events(client):
    """🔴 RED: Should receive SSE events from real pipeline execution"""
    # Submit job
    response = await client.post(
        "/api/v1/ingest",
        json={"url": "https://example.com/article"}
    )
    job_id = response.json()["job_id"]
    
    # Connect to SSE stream (REAL connection)
    events_received = []
    
    async with client.stream("GET", f"/api/v1/stream/{job_id}") as response:
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                data = line[5:].strip()
                events_received.append(data)
                
                # Stop after completion
                if "job_completed" in data or "error" in data:
                    break
    
    # Verify we received real events from actual pipeline
    assert len(events_received) > 0
    assert any("job_started" in e for e in events_received)
    assert any("stage_completed" in e for e in events_received)
```

*Implementation follows similar RED-GREEN pattern*

---

## 📊 Success Criteria

### Coverage Requirements
- **Unit Tests**: 100% coverage for models and utilities
- **Integration Tests**: 90%+ coverage with REAL services
- **End-to-End**: Full ingestion flow tested

### Test Execution Time
- **Unit Tests**: < 5 seconds
- **Integration Tests**: < 60 seconds (includes real pipeline)
- **Full Suite**: < 90 seconds

### Quality Gates
- ✅ All tests pass
- ✅ No mocks in integration tests
- ✅ MyPy type checking passes
- ✅ Ruff linting passes
- ✅ 90%+ overall coverage

---

## 🚀 Daily Checklist

Each day:
- [ ] Morning standup (5 min)
- [ ] Review previous day's commits
- [ ] Write tests FIRST (RED phase)
- [ ] Implement MINIMAL code (GREEN phase)
- [ ] Refactor if needed (REFACTOR phase)
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Commit with clear messages
- [ ] Push to main branch

---

## 📝 Commit Message Format

```bash
# RED phase
git commit -m "RED: S5-XXX - [Test description]"

# GREEN phase
git commit -m "GREEN: S5-XXX - [Implementation description]"

# REFACTOR phase
git commit -m "REFACTOR: S5-XXX - [Improvement description]"

# Final story commit
git commit -m "✅ COMPLETE: S5-XXX - [Story title] - [X tests, Y% coverage]"
```

---

## 🎓 Learning Objectives

By end of Sprint 5, team will have:
1. **Mastered TDD** with real services
2. **Built production API** with FastAPI
3. **Implemented SSE** for real-time streaming
4. **Integrated services** without mocks
5. **Achieved 90%+ coverage** with meaningful tests

---

**Ready to start? Let's begin with Day 1 setup! 🚀**

**First command**: 
```bash
poetry add fastapi uvicorn[standard] python-multipart sse-starlette
```
