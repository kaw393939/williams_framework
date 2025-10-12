# FastAPI Real-time Ingestion - Visual Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│                                                                          │
│  ┌────────────────┐                    ┌─────────────────┐             │
│  │  Streamlit UI  │                    │   Future: React │             │
│  │  (Port 8501)   │                    │   (Port 3000)   │             │
│  └────────┬───────┘                    └────────┬────────┘             │
│           │                                     │                       │
└───────────┼─────────────────────────────────────┼───────────────────────┘
            │                                     │
            │ HTTP POST /api/v1/ingest            │
            │ HTTP GET  /api/v1/ingest/{id}       │
            │ SSE GET   /api/v1/stream/{id}       │
            └─────────────────┬───────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────┐
│                         FASTAPI BACKEND                                │
│                         (Port 8000)                                    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    API ROUTER LAYER                          │    │
│  │                                                              │    │
│  │  POST /api/v1/ingest          │  Submit URL, get job_id    │    │
│  │  GET  /api/v1/ingest/{id}     │  Poll job status           │    │
│  │  GET  /api/v1/stream/{id}     │  SSE real-time stream      │    │
│  │  GET  /api/v1/library         │  List library items        │    │
│  │                                                              │    │
│  └─────────────────────────┬────────────────────────────────────┘    │
│                            │                                          │
│  ┌─────────────────────────▼────────────────────────────────────┐    │
│  │              INGESTION SERVICE LAYER                         │    │
│  │                                                              │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │  IngestionOrchestrator                              │   │    │
│  │  │  • submit_job(url) → job_id                         │   │    │
│  │  │  • get_job_status(job_id) → status_dict            │   │    │
│  │  │  • _process_job(job_id, url, tracker)              │   │    │
│  │  │  • active_jobs: Dict[UUID, ProgressTracker]        │   │    │
│  │  └──────────────────┬──────────────────────────────────┘   │    │
│  │                     │                                       │    │
│  │  ┌──────────────────▼──────────────────────────────────┐   │    │
│  │  │  ProgressTracker                                     │   │    │
│  │  │  • emit(event_type, stage, message, percent)        │   │    │
│  │  │  • job_started(url)                                 │   │    │
│  │  │  • stage_started(stage)                             │   │    │
│  │  │  • stage_progress(stage, percent, message)          │   │    │
│  │  │  • stage_completed(stage, duration_ms)              │   │    │
│  │  │  • job_completed(result)                            │   │    │
│  │  │  • error(stage, error_message)                      │   │    │
│  │  │  • callbacks: List[Callable]                        │   │    │
│  │  │  • events: List[ProgressEvent]                      │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                              │    │
│  └──────────────────────────┬───────────────────────────────────┘    │
│                             │                                         │
└─────────────────────────────┼─────────────────────────────────────────┘
                              │
                              │ Calls pipeline.run()
                              │
┌─────────────────────────────▼─────────────────────────────────────────┐
│                    EXISTING PIPELINE LAYER                             │
│                    (No changes needed)                                 │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  ContentPipeline                                             │    │
│  │                                                              │    │
│  │  async def run(url):                                         │    │
│  │    1. raw = await extractor.extract(url)    ← EXTRACT       │    │
│  │    2. processed = await transformer.transform(raw) ← TRANSFORM│   │
│  │    3. file = await loader.load(processed)   ← LOAD           │    │
│  │    return PipelineResult(raw, processed, file)               │    │
│  │                                                              │    │
│  └──────────────────────┬───────────────────────────────────────┘    │
│                         │                                             │
└─────────────────────────┼─────────────────────────────────────────────┘
                          │
                          │ Reads/Writes
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       DATA LAYER (Docker Compose)                       │
│                                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────┐│
│  │  PostgreSQL   │  │     Redis     │  │    Qdrant     │  │  MinIO   ││
│  │  (Port 5432)  │  │  (Port 6379)  │  │  (Port 6333)  │  │ (Port    ││
│  │               │  │               │  │               │  │  9000)   ││
│  │  • Metadata   │  │  • Job state  │  │  • Vectors    │  │ • Files  ││
│  │  • History    │  │  • Cache      │  │  • Embeddings │  │ • Tiers  ││
│  │  • Stats      │  │  • Sessions   │  │  • Search     │  │ • Backup ││
│  └───────────────┘  └───────────────┘  └───────────────┘  └──────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## SSE Event Flow Diagram

```
┌──────────────┐                ┌──────────────┐                ┌──────────────┐
│   Browser    │                │    FastAPI   │                │  Orchestrator│
│  (Streamlit) │                │   /stream    │                │   Pipeline   │
└──────┬───────┘                └──────┬───────┘                └──────┬───────┘
       │                               │                               │
       │ GET /api/v1/stream/{job_id}   │                               │
       ├──────────────────────────────>│                               │
       │                               │                               │
       │      Connection Established   │                               │
       │<──────────────────────────────┤                               │
       │                               │                               │
       │                               │   Register event callback     │
       │                               ├──────────────────────────────>│
       │                               │                               │
       │                               │                               │ Extract stage
       │                               │   event: job_started          │ begins
       │<──────────────────────────────┤<──────────────────────────────┤
       │ data: {"job_id": "...", ...}  │                               │
       │                               │                               │
       │                               │   event: stage_started        │
       │<──────────────────────────────┤<──────────────────────────────┤
       │ data: {"stage": "extract"}    │                               │
       │                               │                               │
       │                               │   event: stage_progress       │ Downloading
       │<──────────────────────────────┤<──────────────────────────────┤ content
       │ data: {"percent": 25, ...}    │                               │
       │                               │                               │
       │                               │   event: stage_completed      │ Extract done
       │<──────────────────────────────┤<──────────────────────────────┤
       │ data: {"duration_ms": 3200}   │                               │
       │                               │                               │
       │                               │   event: stage_started        │ Transform
       │<──────────────────────────────┤<──────────────────────────────┤ begins
       │ data: {"stage": "transform"}  │                               │
       │                               │                               │
       │         (15 seconds pass)     │                               │
       │                               │                               │
       │   event: heartbeat            │                               │ Keep-alive
       │<──────────────────────────────┤                               │
       │ data: {"timestamp": ...}      │                               │
       │                               │                               │
       │                               │   event: stage_completed      │ Transform
       │<──────────────────────────────┤<──────────────────────────────┤ done
       │ data: {"duration_ms": 5400}   │                               │
       │                               │                               │
       │                               │   event: stage_started        │ Load begins
       │<──────────────────────────────┤<──────────────────────────────┤
       │ data: {"stage": "load"}       │                               │
       │                               │                               │
       │                               │   event: stage_completed      │ Load done
       │<──────────────────────────────┤<──────────────────────────────┤
       │ data: {"duration_ms": 1200}   │                               │
       │                               │                               │
       │                               │   event: job_completed        │ All done!
       │<──────────────────────────────┤<──────────────────────────────┤
       │ data: {"result": {...}}       │                               │
       │                               │                               │
       │      Connection Closed        │                               │
       │<──────────────────────────────┤                               │
       │                               │                               │
```

---

## TDD Workflow Diagram

```
                    RED-GREEN-REFACTOR CYCLE
                            
┌─────────────────────────────────────────────────────────────┐
│                    🔴 RED PHASE                             │
│                                                             │
│  1. Write Test First (test_feature.py)                     │
│     ┌─────────────────────────────────────────────┐        │
│     │ def test_feature():                         │        │
│     │     result = feature()                      │        │
│     │     assert result == expected               │        │
│     └─────────────────────────────────────────────┘        │
│                                                             │
│  2. Run Test                                               │
│     $ pytest tests/test_feature.py                         │
│                                                             │
│  3. Verify FAILS ❌                                        │
│     ImportError: No module 'feature'                       │
│                                                             │
│  4. Commit                                                 │
│     $ git commit -m "RED: Test feature implementation"     │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    🟢 GREEN PHASE                           │
│                                                             │
│  1. Write MINIMAL Code (feature.py)                        │
│     ┌─────────────────────────────────────────────┐        │
│     │ def feature():                              │        │
│     │     return expected  # Simplest possible    │        │
│     └─────────────────────────────────────────────┘        │
│                                                             │
│  2. Run Test                                               │
│     $ pytest tests/test_feature.py                         │
│                                                             │
│  3. Verify PASSES ✅                                       │
│     test_feature.py::test_feature PASSED                   │
│                                                             │
│  4. Commit                                                 │
│     $ git commit -m "GREEN: Implement feature"             │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   🔄 REFACTOR PHASE                         │
│                                                             │
│  1. Improve Code Quality                                   │
│     ┌─────────────────────────────────────────────┐        │
│     │ def feature():                              │        │
│     │     # Better implementation                 │        │
│     │     result = calculate_properly()           │        │
│     │     return validate(result)                 │        │
│     └─────────────────────────────────────────────┘        │
│                                                             │
│  2. Run ALL Tests                                          │
│     $ pytest                                               │
│                                                             │
│  3. Verify Still PASSES ✅                                 │
│     465 tests passed                                       │
│                                                             │
│  4. Commit                                                 │
│     $ git commit -m "REFACTOR: Improve feature clarity"    │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Next Feature │
                    │  (RED phase)  │
                    └───────────────┘
```

---

## Real Services Integration Test Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                  INTEGRATION TEST EXECUTION                         │
│                  (NO MOCKS - Real Services)                         │
└─────────────────────────────────────────────────────────────────────┘

Test: test_post_ingest_creates_job_in_real_redis

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Test Client │      │   FastAPI    │      │ Real Redis   │
│   (httpx)    │      │   Server     │      │  (Docker)    │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       │ POST /api/v1/ingest │                     │
       ├────────────────────>│                     │
       │                     │                     │
       │                     │ REAL: set_json()    │
       │                     ├────────────────────>│
       │                     │                     │
       │                     │   REAL: Success     │
       │                     │<────────────────────┤
       │                     │                     │
       │   202 Accepted      │                     │
       │<────────────────────┤                     │
       │ {"job_id": "..."}   │                     │
       │                     │                     │
       │                     │                     │
       │  TEST: Verify in Redis                    │
       ├───────────────────────────────────────────>│
       │                     │                     │
       │  REAL: get_json(job_id)                   │
       │<───────────────────────────────────────────┤
       │  {"status": "queued", ...}                │
       │                     │                     │
       ✅ ASSERT job_data["status"] == "queued"    │
       │                     │                     │

Result: Test PASSES ✅ because it verified REAL Redis storage
```

---

## Progress Tracking State Machine

```
                         INGESTION JOB LIFECYCLE
                                
  ┌─────────┐
  │ QUEUED  │  Job created, waiting to start
  └────┬────┘
       │ _process_job() called
       ▼
  ┌─────────┐
  │ EXTRACT │  Stage: Fetching content from URL
  │         │  Events: stage_started, stage_progress, stage_completed
  └────┬────┘
       │ extractor.extract() completes
       ▼
  ┌─────────────┐
  │ TRANSFORM   │  Stage: Processing with AI (summarize, extract metadata)
  │             │  Events: stage_started, stage_progress, stage_completed
  └──────┬──────┘
         │ transformer.transform() completes
         ▼
  ┌─────────┐
  │  LOAD   │  Stage: Store in library (MinIO, Qdrant, PostgreSQL)
  │         │  Events: stage_started, stage_completed
  └────┬────┘
       │ loader.load() completes
       ▼
  ┌───────────┐
  │ COMPLETED │  Success! Result contains file_path, title, tier, quality_score
  └───────────┘
  
  
  ERROR PATH:
  Any stage ──[Exception]──> ┌────────┐
                              │ FAILED │  Error captured in Redis with stage and message
                              └────────┘
```

---

## File Structure Tree

```
williams-librarian/
├── app/
│   ├── api/                          # NEW: FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── ingestion.py          # Ingestion endpoints
│   │
│   ├── services/                     # NEW: Service layer
│   │   ├── __init__.py
│   │   └── ingestion_service.py      # IngestionOrchestrator, ProgressTracker
│   │
│   ├── pipeline/                     # EXISTING: No changes
│   │   ├── cli.py
│   │   ├── etl.py
│   │   ├── extractors/
│   │   ├── transformers/
│   │   └── loaders/
│   │
│   ├── repositories/                 # EXISTING: Used by orchestrator
│   │   ├── redis_repository.py
│   │   ├── postgres_repository.py
│   │   ├── qdrant_repository.py
│   │   └── minio_repository.py
│   │
│   ├── core/                         # EXISTING: Shared models
│   │   ├── models.py
│   │   └── config.py
│   │
│   └── presentation/                 # EXISTING: Streamlit UI
│       └── streamlit_app.py
│
├── tests/
│   ├── unit/
│   │   ├── api/                      # NEW: API model tests
│   │   │   ├── test_ingest_request.py
│   │   │   └── test_ingest_response.py
│   │   └── services/                 # NEW: Service logic tests
│   │       ├── test_progress_tracker.py
│   │       └── test_ingestion_stage.py
│   │
│   ├── integration/
│   │   ├── api/                      # NEW: Real HTTP tests
│   │   │   ├── test_ingest_endpoint_real.py
│   │   │   ├── test_job_status_endpoint_real.py
│   │   │   └── test_sse_streaming_real.py
│   │   └── services/                 # NEW: Real pipeline tests
│   │       ├── test_orchestrator_real_pipeline.py
│   │       └── test_orchestrator_redis_integration.py
│   │
│   └── e2e/
│       └── api/                      # NEW: Full flow tests
│           └── test_full_ingestion_flow.py
│
├── docs/
│   ├── FASTAPI-INGESTION-ARCHITECTURE.md       # Complete architecture
│   ├── SPRINT-5-TDD-PLAN.md                    # Day-by-day plan
│   ├── FASTAPI-IMPLEMENTATION-SUMMARY.md       # Quick reference
│   └── FASTAPI-VISUAL-ARCHITECTURE.md          # This file
│
├── pyproject.toml                    # Dependencies (add fastapi, uvicorn)
├── docker-compose.yml                # EXISTING: Services already running
└── README.md
```

---

## Component Interaction Matrix

| From ↓ To →     | ProgressTracker | Orchestrator | FastAPI Router | ContentPipeline | Redis | Qdrant | MinIO |
|-----------------|-----------------|--------------|----------------|-----------------|-------|--------|-------|
| **FastAPI Router** | Read (get_tracker) | Call (submit_job, get_job_status) | - | - | - | - | - |
| **Orchestrator** | Create, Write | - | - | Call (run) | Write (job state) | - | - |
| **ProgressTracker** | - | Callback | - | - | - | - | - |
| **ContentPipeline** | - | - | - | - | - | Write (vectors) | Write (files) |
| **SSE Handler** | Read (events) | Call (get_tracker) | - | - | - | - | - |

---

## Test Coverage Heatmap

```
Layer                    Unit Tests   Integration Tests   E2E Tests   Total
──────────────────────────────────────────────────────────────────────────
ProgressTracker          10 tests     -                   -           10
IngestionStage           3 tests      -                   -           3
ProgressEvent            5 tests      -                   -           5
──────────────────────────────────────────────────────────────────────────
IngestionOrchestrator    -            8 tests             -           8
Pipeline Integration     -            5 tests             2 tests     7
──────────────────────────────────────────────────────────────────────────
POST /ingest             2 tests      6 tests             1 test      9
GET /ingest/{id}         2 tests      4 tests             1 test      7
GET /stream/{id}         -            10 tests            1 test      11
GET /library             3 tests      3 tests             -           6
──────────────────────────────────────────────────────────────────────────
TOTAL                    25 tests     36 tests            5 tests     66 tests

Coverage:                100%         90%+                80%+        95%+
```

---

## Deployment Architecture

```
                    PRODUCTION DEPLOYMENT
                                
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
│                    (Nginx / AWS ALB)                    │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼────────┐     ┌────────▼────────┐
│  FastAPI Worker │     │  FastAPI Worker │
│  (uvicorn)      │     │  (uvicorn)      │
│  Port 8000      │     │  Port 8001      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │                       │
┌────────▼────────┐     ┌────────▼────────┐
│  Streamlit UI   │     │  React/Vue UI   │
│  Port 8501      │     │  Port 3000      │
└─────────────────┘     └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
    ┌────────────────┴────────────────┐
    │                                 │
┌───▼────────┐  ┌──────────┐  ┌──────▼───┐  ┌────────┐
│ PostgreSQL │  │  Redis   │  │  Qdrant  │  │ MinIO  │
│  (RDS)     │  │ (Elastica│  │ (Cloud)  │  │ (S3)   │
│            │  │  che)    │  │          │  │        │
└────────────┘  └──────────┘  └──────────┘  └────────┘

Metrics & Monitoring:
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Prometheus  │→ │  Grafana    │  │    Logs     │
│ (Metrics)   │  │ (Dashboard) │  │ (CloudWatch)│
└─────────────┘  └─────────────┘  └─────────────┘
```

---

This visual documentation complements the detailed architecture and implementation plan documents! 🎨
