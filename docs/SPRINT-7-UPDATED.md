# Sprint 7: FastAPI Backend + Streaming + Visualization - UPDATED TDD Plan

**Duration:** 2 weeks (10 working days)  
**Focus:** REST API, real-time streaming, graph visualization, production deployment  
**Testing Philosophy:** RED-GREEN-REFACTOR with real services (NO MOCKS)  
**Target:** 35 new tests, maintain 85%+ coverage  
**Updated:** October 12, 2025 (Post-Sprint 5 & 6 Completion)

---

## 🎯 Sprint Goals (Updated from Sprint 5 & 6 Foundation)

**Building on Sprint 5 & 6 Achievements:**
- ✅ Multi-provider AI architecture (Sprint 5)
- ✅ Neo4j knowledge graph with provenance (Sprint 5)
- ✅ Entity extraction + enhanced chunking (Sprint 5)
- ✅ Existing Streamlit presentation layer (Sprint 5)
- ✅ Service layer (SearchService, LibraryService, etc.) (Sprint 5)
- ✅ Coreference, entity linking, relations, RAG citations (Sprint 6)

**Sprint 7 Enhancements:**
1. **FastAPI REST API**: Wrap existing services with REST endpoints
2. **Server-Sent Events**: Real-time progress streaming for ingestion
3. **Enhanced Streamlit UI**: Ingestion page with live progress
4. **Graph Visualization**: D3.js interactive knowledge graph
5. **Production Ready**: Docker deployment, monitoring, health checks

---

## 📦 Sprint 5 & 6 Foundation (What We Built)

### Existing Service Layer (Sprint 5)
```
app/services/
├── search_service.py          # Vector search + RAG (Sprint 5 + 6)
├── library_service.py         # Library management (Sprint 5)
├── content_service.py         # Content ingestion (Sprint 5)
├── entity_linking_service.py  # Entity linking (Sprint 6)
└── citation_service.py        # Citation resolution (Sprint 6)
```

### Existing Presentation Layer (Sprint 5)
```
app/presentation/
├── streamlit_app.py                # Main app (Sprint 5)
├── components/
│   ├── library_stats.py            # Statistics dashboard (Sprint 5)
│   ├── tag_filter.py               # Tag filtering (Sprint 5)
│   └── tier_filter.py              # Tier filtering (Sprint 5)
├── pages/
│   └── ingest.py                   # Basic ingestion page (Sprint 5)
└── navigation.py                   # Navigation builder (Sprint 5)
```

### Existing Pipeline (Sprint 5 + 6)
```
app/pipeline/
├── etl.py                          # Orchestration (Sprint 5)
├── transformers/
│   ├── enhanced_chunker.py         # Semantic chunking (Sprint 5)
│   ├── entity_extractor.py         # spaCy + LLM NER (Sprint 5)
│   ├── coref_resolver.py           # Coreference (Sprint 6)
│   └── relation_extractor.py       # Relations (Sprint 6)
└── loaders/
    └── library.py                  # Library storage (Sprint 5)
```

---

## 📋 Stories & Acceptance Criteria (Updated)

### Story S7-701: FastAPI REST API Wrapper (12 tests)
**Priority:** P0 (Core Feature)  
**Estimate:** 3 days

**Context:** Wrap existing services with REST API for programmatic access and Streamlit integration.

**Acceptance Criteria:**
- [ ] Create `app/api/` directory for FastAPI application
- [ ] REST endpoints wrapping existing services:
  - `POST /api/ingest` → calls `ContentService.process_url()`
  - `GET /api/search` → calls `SearchService.answer_with_citations()`
  - `POST /api/graph/query` → calls `NeoRepository` graph queries
  - `GET /api/library` → calls `LibraryService.list_files()`
  - `GET /api/health` → service health checks
- [ ] Request/response models using Pydantic (reuse existing models)
- [ ] Error handling with proper HTTP status codes
- [ ] CORS configuration for Streamlit frontend
- [ ] OpenAPI documentation auto-generated at `/docs`
- [ ] Authentication middleware (optional: API key validation)
- [ ] Rate limiting for production (optional)
- [ ] Logging and telemetry integration
- [ ] Use existing Settings from `app/core/config.py`

**Test Scenarios:**
1. POST `/api/ingest` with URL returns 202 Accepted
2. GET `/api/search` returns RAG answer with citations
3. POST `/api/graph/query` returns entity relationships
4. GET `/api/library?tier=tier-a` returns filtered files
5. GET `/api/health` returns service status
6. Invalid URL returns 400 Bad Request
7. Missing fields returns 422 Unprocessable Entity
8. Server errors return 500 Internal Server Error
9. CORS headers present in responses
10. OpenAPI docs accessible at `/docs`
11. Rate limiting enforced (optional)
12. API key authentication (optional)

**Implementation Notes:**
- Add `app/api/main.py` for FastAPI app
- Add `app/api/routes/` for endpoint organization
- Add `app/api/models/` for request/response Pydantic models (reuse existing)
- Reuse existing service layer (no duplication)

---

### Story S7-702: Server-Sent Events for Progress Streaming (8 tests)
**Priority:** P0 (Real-time UX)  
**Estimate:** 2 days

**Context:** Stream real-time progress updates during ingestion using SSE.

**Acceptance Criteria:**
- [ ] SSE endpoint: `GET /api/ingest/{task_id}/progress`
- [ ] Progress events emitted during ingestion:
  ```json
  {
    "stage": "extracting",
    "percentage": 25,
    "message": "Extracting content from URL...",
    "entities_found": 0,
    "relations_found": 0,
    "timestamp": "2025-10-12T10:30:00Z"
  }
  ```
- [ ] Stages: `extracting`, `chunking`, `entity_extraction`, `entity_linking`, `relation_extraction`, `storing`, `complete`
- [ ] Background task queue for async ingestion (use FastAPI BackgroundTasks)
- [ ] Task ID generation for tracking
- [ ] Task status storage (Redis or in-memory)
- [ ] Completion event includes final stats
- [ ] Error events include error details
- [ ] Client reconnection handling
- [ ] Integration with existing ETL pipeline

**Test Scenarios:**
1. Start ingestion returns task_id
2. SSE stream emits progress events
3. Progress events include all required fields
4. Stages progress in correct order
5. Completion event includes final stats
6. Error event on ingestion failure
7. Multiple concurrent tasks handled
8. Client reconnection works correctly

**Implementation Notes:**
- Add `app/api/routes/streaming.py` for SSE endpoints
- Add `app/api/tasks.py` for background task management
- Use Redis for task status (or in-memory for MVP)
- Emit events from ETL pipeline stages

---

### Story S7-703: Enhanced Streamlit Ingestion UI (5 tests)
**Priority:** P0 (User-Facing)  
**Estimate:** 1 day

**Context:** Enhance existing Streamlit ingestion page with real-time progress.

**Acceptance Criteria:**
- [ ] Update `app/presentation/pages/ingest.py` with SSE integration
- [ ] URL input with validation
- [ ] "Ingest" button triggers FastAPI `/api/ingest`
- [ ] Real-time progress bar using SSE stream
- [ ] Live updates: "Extracting entities... (15 found)", "Linking entities...", etc.
- [ ] Display entities and relations as discovered (live table)
- [ ] Success message with link to library
- [ ] Error message on failure with details
- [ ] Cancel button (optional)
- [ ] Recent ingestions history
- [ ] Use existing Streamlit components and styling

**Test Scenarios:**
1. URL input validation works
2. "Ingest" button disabled during processing
3. Progress bar updates in real-time
4. Live entity count updates
5. Success message shown with library link

**Implementation Notes:**
- Update existing `app/presentation/pages/ingest.py`
- Use `streamlit-extras` for SSE client (or custom JavaScript)
- Reuse existing navigation and layout

---

### Story S7-704: Knowledge Graph Visualization Page (6 tests)
**Priority:** P1 (High Value)  
**Estimate:** 3 days

**Context:** Create interactive graph visualization of entities and relations.

**Acceptance Criteria:**
- [ ] New Streamlit page: `app/presentation/pages/graph.py`
- [ ] D3.js force-directed graph embedded via Streamlit component
- [ ] Data fetched from FastAPI `/api/graph/export`
- [ ] Nodes:
  - Colored by entity type (PERSON=blue, ORG=green, GPE=red, etc.)
  - Sized by mention count
  - Label shows canonical name
- [ ] Edges:
  - Labeled with relation type
  - Width proportional to confidence
  - Arrow direction for directional relations
- [ ] Interactions:
  - Click node → show entity details sidebar
  - Click edge → show relation details + evidence
  - Hover → highlight connected nodes
  - Search bar → find and center on entity
- [ ] Filters:
  - Entity types (checkboxes)
  - Relation types (checkboxes)
  - Confidence threshold (slider)
- [ ] Controls:
  - Zoom/pan
  - Reset view
  - Export as PNG/SVG
  - Full-screen mode
- [ ] Layout options: force-directed, hierarchical, circular
- [ ] Integration with RAG: highlight reasoning path for answer

**Test Scenarios:**
1. Graph renders with correct number of nodes/edges
2. Nodes colored by entity type
3. Edge labels show relation types
4. Node click displays entity details
5. Filter by entity type updates graph
6. Search finds and centers on entity

**Implementation Notes:**
- Add `app/presentation/pages/graph.py`
- Use `streamlit-agraph` or custom D3.js component
- Fetch data from FastAPI `/api/graph/export`
- Reuse existing page layout and navigation

---

### Story S7-705: Graph Export and Query APIs (4 tests)
**Priority:** P1 (API completeness)  
**Estimate:** 1 day

**Context:** Provide APIs for graph export and advanced queries.

**Acceptance Criteria:**
- [ ] `GET /api/graph/export` → full graph JSON/GraphML
- [ ] `GET /api/graph/entity/{entity_id}` → entity with relationships
- [ ] `GET /api/graph/subgraph?center={entity_id}&depth=2` → subgraph
- [ ] `POST /api/graph/path` → shortest path between entities
- [ ] Query parameters:
  - `entity_types`: filter by types
  - `relation_types`: filter by relations
  - `min_confidence`: confidence threshold
  - `format`: json|graphml|cytoscape
- [ ] Pagination for large result sets
- [ ] Caching for frequently accessed subgraphs
- [ ] Use existing `NeoRepository` methods from Sprint 6

**Test Scenarios:**
1. Export full graph returns valid JSON
2. Get entity by ID returns relationships
3. Get subgraph with depth limit
4. Find shortest path between entities

**Implementation Notes:**
- Add `app/api/routes/graph.py`
- Reuse `NeoRepository` from Sprint 6
- Add caching with Redis (optional)

---

## 🧪 Testing Strategy (Updated from Sprint 5 & 6)

### Test Organization
```
tests/
├── integration/
│   ├── api/
│   │   ├── test_rest_endpoints.py          # 12 tests (REST API)
│   │   ├── test_sse_streaming.py           # 8 tests (SSE)
│   │   └── test_graph_apis.py              # 4 tests (graph export)
│   └── presentation/
│       ├── test_streamlit_ingestion.py     # 5 tests (UI)
│       └── test_graph_visualization.py     # 6 tests (viz)
└── unit/
    └── (minimal - focus on integration)
```

### Coverage Targets (Aligned with Sprint 5 & 6)
- Overall: 85%+ (maintained from Sprint 5)
- API layer: 90%+
- Integration tests: 85%+
- Presentation layer: 70%+ (UI testing limitations)

### NO MOCKS Policy (From Sprint 5)
- All API tests call REAL services
- All graph tests use REAL Neo4j
- All ingestion tests use REAL pipeline
- Only UI component tests may use simplified mocks

---

## 📂 File Structure (Building on Sprint 5 & 6)

### New Files
```
app/api/
├── __init__.py
├── main.py                              # FastAPI application
├── routes/
│   ├── __init__.py
│   ├── ingestion.py                     # POST /api/ingest
│   ├── search.py                        # GET /api/search
│   ├── graph.py                         # Graph endpoints
│   ├── library.py                       # GET /api/library
│   └── streaming.py                     # SSE endpoints
├── models/
│   ├── __init__.py
│   ├── requests.py                      # Request models
│   └── responses.py                     # Response models
└── tasks.py                             # Background task management

app/presentation/pages/
└── graph.py                             # NEW: Graph visualization page

tests/integration/api/
└── (new test files)
```

### Modified Files
```
app/presentation/pages/ingest.py         # ENHANCED: Add SSE progress
app/presentation/streamlit_app.py        # ENHANCED: Add graph page
app/presentation/navigation.py           # ENHANCED: Add graph nav item
```

---

## 🚀 Sprint Execution Plan

### Week 1: API Layer (Days 1-5)
- **Days 1-3**: Story S7-701 (FastAPI REST API)
- **Days 4-5**: Story S7-702 (SSE Streaming)

### Week 2: Visualization (Days 6-10)
- **Days 6**: Story S7-703 (Enhanced Ingestion UI)
- **Days 7-9**: Story S7-704 (Graph Visualization)
- **Day 10**: Story S7-705 (Graph Export APIs)

---

## 🔗 Integration with Sprint 5 & 6

### Reuse from Sprint 5 & 6
1. **Service Layer**: Wrap existing services with REST API (no duplication)
2. **Presentation Layer**: Enhance existing Streamlit pages
3. **Configuration**: Use existing Settings and ai_services.yml
4. **Testing**: Follow Sprint 5 patterns (NO MOCKS)
5. **Graph Queries**: Use Sprint 6 Neo4j enhancements
6. **Citations**: Leverage Sprint 6 RAG improvements

### Sprint 5 & 6 → Sprint 7 Architecture
```
Sprint 5 & 6:                   Sprint 7 Additions:
Services (Python)               → FastAPI REST API (wraps services)
Streamlit UI (basic)            → Enhanced UI + Graph Viz
Neo4j (direct access)           → REST API + caching layer
No real-time updates            → SSE streaming
```

---

## 🐳 Deployment (Production Ready)

### Docker Compose
```yaml
version: '3.8'
services:
  fastapi:
    build: ./app/api
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_HOST=redis
    depends_on:
      - neo4j
      - redis
  
  streamlit:
    build: ./app/presentation
    ports:
      - "8501:8501"
    environment:
      - FASTAPI_URL=http://fastapi:8000
  
  neo4j:
    image: neo4j:5.28.0
    # (existing config from Sprint 5)
  
  redis:
    image: redis:7-alpine
    # (for task queue and caching)
```

### Monitoring
- [ ] Health check endpoints
- [ ] Prometheus metrics export
- [ ] Structured logging
- [ ] Error tracking (Sentry integration optional)

---

## 📊 Success Metrics

### Test Metrics
- [ ] 35 new tests added (12 + 8 + 5 + 6 + 4)
- [ ] All tests passing (excluding unavailable service errors)
- [ ] 85%+ overall coverage maintained
- [ ] 90%+ coverage on new API code

### Performance Metrics
- [ ] API response time: <500ms for most endpoints
- [ ] SSE latency: <100ms per event
- [ ] Graph export: <2s for graphs with <1000 nodes
- [ ] Ingestion throughput: 1 URL per minute
- [ ] Concurrent requests: handle 10 simultaneous users

### Feature Completeness
- [ ] REST API functional with OpenAPI docs
- [ ] SSE streaming working
- [ ] Ingestion UI enhanced
- [ ] Graph visualization working
- [ ] Production deployment ready

---

## 🎯 Definition of Done

- [ ] All 35 tests passing
- [ ] 85%+ test coverage maintained
- [ ] NO MOCKS in integration tests
- [ ] All performance benchmarks met
- [ ] OpenAPI documentation complete
- [ ] Docker deployment working
- [ ] Code reviewed and committed
- [ ] Technical debt audit clean
- [ ] Production deployment guide updated
- [ ] User documentation updated

---

**Updated:** October 12, 2025  
**Status:** Ready to start after Sprint 6  
**Prerequisites:** 
- Sprint 5 complete ✅ (77/77 tests passing, 85.22% coverage)
- Sprint 6 complete (entity linking, relations, RAG citations)
