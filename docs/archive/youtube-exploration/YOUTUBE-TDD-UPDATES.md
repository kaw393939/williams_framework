# TDD Plan Updated - Production Features Included ✅

**Date:** October 12, 2025
**Status:** Complete TDD plan with Job Queue, CRUD, and API tests

---

## 🎯 What's Been Added to TDD Plan

The TDD plan has been enhanced with comprehensive tests for all the new production features:

### Phase 0: Job Queue & Infrastructure (NEW - Days 1-2)

**Day 1: Job Manager & Status Tracking**
- ✅ 10 unit tests for `JobManager`
- ✅ Tests for job creation, status updates, retries
- ✅ Tests for automatic vs manual retries
- ✅ Tests for job cancellation
- ✅ Tests for job listing and statistics

**Day 2: CRUD Operations & Video Manager**
- ✅ 9 unit tests for `VideoManager`
- ✅ Tests for complete CRUD operations
- ✅ Tests for caching (Redis)
- ✅ Tests for soft delete vs hard delete
- ✅ Tests for cascading deletes
- ✅ Tests for reprocessing capability

---

## 📚 Updated Test Structure

### New Test Files

```
tests/
├── unit/
│   ├── queue/                          ← NEW
│   │   ├── test_job_manager.py         (10 tests)
│   │   └── test_celery_tasks.py        (5-10 tests)
│   ├── crud/                           ← NEW
│   │   └── test_video_manager.py       (9 tests)
│   ├── api/                            ← NEW
│   │   ├── test_video_endpoints.py     (10-15 tests)
│   │   ├── test_job_endpoints.py       (5-10 tests)
│   │   └── test_websocket.py           (3-5 tests)
│   └── pipeline/                       (Existing)
│       └── extractors/
│           ├── test_video_downloader.py
│           ├── test_transcription_engine.py
│           └── ...
│
├── integration/                        
│   ├── test_job_queue_integration.py   ← NEW (5-10 tests)
│   ├── test_crud_operations.py         ← NEW (5-10 tests)
│   ├── test_retry_functionality.py     ← NEW (5-10 tests)
│   └── ... (existing tests)
│
└── e2e/
    ├── test_youtube_api_workflow.py    ← NEW (5-10 tests)
    └── ... (existing tests)
```

---

## 🧪 Test Examples Included

### 1. Job Manager Tests

**Test Coverage:**
```python
✅ test_create_job_success              # Create new job
✅ test_get_job_success                 # Retrieve job by ID
✅ test_update_job_status               # Update status & progress
✅ test_retry_job_automatic             # Automatic retry (3 max)
✅ test_retry_job_max_exceeded          # Retry limit enforcement
✅ test_retry_job_manual                # Manual retry (10 max)
✅ test_cancel_job                      # Cancel running job
✅ test_cannot_cancel_completed_job     # Cannot cancel completed
✅ test_list_jobs                       # List with filtering
✅ test_get_job_stats                   # Aggregate statistics
```

**Key Test Example:**
```python
@pytest.mark.asyncio
async def test_retry_job_automatic(self, job_manager, mock_postgres):
    """Test automatic retry with exponential backoff."""
    job_id = "abc123"
    
    # Mock failed job with 0 retries
    job = ProcessingJob(
        job_id=job_id,
        url="https://youtube.com/...",
        status=JobStatus.FAILED,
        retry_count=0,
        max_retries=3
    )
    mock_postgres.get_job.return_value = job
    
    # Act - Retry
    success = await job_manager.retry_job(job_id, manual=False)
    
    # Assert - Should succeed and requeue
    assert success is True
    mock_postgres.increment_retry_count.assert_called_once()
    job_manager.celery.apply_async.assert_called_once()
```

---

### 2. Video Manager (CRUD) Tests

**Test Coverage:**
```python
✅ test_create_video                    # Start processing
✅ test_get_video_from_cache            # Cache hit (Redis)
✅ test_get_video_from_database         # Cache miss (PostgreSQL)
✅ test_update_video                    # Update metadata
✅ test_soft_delete_video               # Mark as deleted
✅ test_hard_delete_video               # Permanent removal (cascading)
✅ test_reprocess_video                 # Reprocess with stored files
✅ test_reprocess_video_not_found       # Error handling
✅ test_list_videos                     # List with filters
```

**Key Test Example:**
```python
@pytest.mark.asyncio
async def test_hard_delete_video(self, video_manager, mock_postgres, 
                                  mock_redis, mock_neo4j, mock_minio):
    """Test cascading delete removes all related data."""
    video_id = "dQw4w9WgXcQ"
    
    # Act - Hard delete
    await video_manager.delete_video(video_id, hard_delete=True)
    
    # Assert - All systems cleared
    mock_redis.delete.assert_called_once()              # Cache
    mock_neo4j.execute.assert_called_once()             # Relationships
    assert mock_postgres.execute.call_count >= 5        # 5 tables
    assert mock_minio.delete_folder.call_count == 3     # 3 folders
```

---

### 3. API Endpoint Tests (To Be Added)

**Test File:** `tests/unit/api/test_video_endpoints.py`

```python
from fastapi.testclient import TestClient

class TestVideoEndpoints:
    """Unit tests for video API endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_process_video_endpoint(self, client):
        """Test POST /api/videos/process"""
        response = client.post(
            "/api/videos/process",
            json={"url": "https://youtube.com/watch?v=...", "priority": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    def test_get_job_status_endpoint(self, client):
        """Test GET /api/videos/status/{job_id}"""
        job_id = "test_job_123"
        
        response = client.get(f"/api/videos/status/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "progress" in data
        assert "status" in data
    
    def test_get_video_endpoint(self, client):
        """Test GET /api/videos/{video_id}"""
        video_id = "dQw4w9WgXcQ"
        
        response = client.get(f"/api/videos/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert "metadata" in data
        assert "transcript" in data
    
    def test_delete_video_endpoint(self, client):
        """Test DELETE /api/videos/{video_id}"""
        video_id = "dQw4w9WgXcQ"
        
        response = client.delete(
            f"/api/videos/{video_id}?hard_delete=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
    
    def test_retry_job_endpoint(self, client):
        """Test POST /api/jobs/{job_id}/retry"""
        job_id = "test_job_123"
        
        response = client.post(
            f"/api/jobs/{job_id}/retry?manual=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

---

### 4. WebSocket Tests

**Test File:** `tests/unit/api/test_websocket.py`

```python
from fastapi.testclient import TestClient

class TestWebSocketStatusStream:
    """Test WebSocket real-time status updates."""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection establishes."""
        job_id = "test_job_123"
        
        with client.websocket_connect(
            f"/api/videos/status/{job_id}/stream"
        ) as websocket:
            # Should receive initial status
            data = websocket.receive_json()
            assert "status" in data
            assert "progress" in data
    
    def test_websocket_receives_updates(self, client, mock_redis):
        """Test WebSocket receives real-time updates."""
        job_id = "test_job_123"
        
        # Mock Redis pub/sub
        mock_redis.pubsub.return_value.listen.return_value = [
            {
                "type": "message",
                "data": '{"status": "transcribing", "progress": 50.0}'
            },
            {
                "type": "message",
                "data": '{"status": "completed", "progress": 100.0}'
            }
        ]
        
        with client.websocket_connect(
            f"/api/videos/status/{job_id}/stream"
        ) as websocket:
            # Receive updates
            update1 = websocket.receive_json()
            assert update1["status"] == "transcribing"
            
            update2 = websocket.receive_json()
            assert update2["status"] == "completed"
```

---

### 5. Integration Tests (To Be Added)

**Test File:** `tests/integration/test_job_queue_integration.py`

```python
@pytest.mark.integration
class TestJobQueueIntegration:
    """Integration tests for complete job queue workflow."""
    
    @pytest.mark.asyncio
    async def test_job_creation_to_completion(self):
        """Test job from creation to completion with real services."""
        # Create job
        job_manager = JobManager(postgres_repo, redis_client, celery_app)
        job = await job_manager.create_job(
            "https://youtube.com/watch?v=jNQXAC9IVRw",
            priority=5
        )
        
        # Wait for processing
        await asyncio.sleep(30)
        
        # Check status
        final_job = await job_manager.get_job(job.job_id)
        assert final_job.status == JobStatus.COMPLETED
        assert final_job.progress_percent == 100.0
    
    @pytest.mark.asyncio
    async def test_automatic_retry_on_failure(self):
        """Test automatic retry when job fails."""
        # Create job that will fail
        job = await job_manager.create_job(
            "https://youtube.com/watch?v=invalid",
            priority=5
        )
        
        # Wait for failure and retry
        await asyncio.sleep(60)
        
        # Check retry happened
        final_job = await job_manager.get_job(job.job_id)
        assert final_job.retry_count > 0
```

**Test File:** `tests/integration/test_crud_operations.py`

```python
@pytest.mark.integration
class TestCRUDIntegration:
    """Integration tests for CRUD operations with real databases."""
    
    @pytest.mark.asyncio
    async def test_create_get_delete_workflow(self):
        """Test complete CRUD workflow."""
        video_manager = VideoManager(
            minio_repo, postgres_repo, neo4j_repo, redis_client
        )
        
        # Create (start processing)
        job_id = await video_manager.create_video(
            "https://youtube.com/watch?v=jNQXAC9IVRw",
            priority=5
        )
        
        # Wait for completion
        await asyncio.sleep(30)
        
        # Get (should be cached after first retrieval)
        video = await video_manager.get_video("jNQXAC9IVRw")
        assert video is not None
        assert video.metadata["title"] is not None
        
        # Update
        success = await video_manager.update_video(
            "jNQXAC9IVRw",
            {"title": "Updated Title"}
        )
        assert success is True
        
        # Delete (cascading)
        await video_manager.delete_video("jNQXAC9IVRw", hard_delete=True)
        
        # Verify deleted from all systems
        assert not await postgres_repo.video_exists("jNQXAC9IVRw")
        assert not await neo4j_repo.video_exists("jNQXAC9IVRw")
        assert not await minio_repo.file_exists(
            "youtube-videos/jNQXAC9IVRw/original.mp4"
        )
```

---

## 📊 Updated Test Coverage Goals

### Phase 0: Job Queue & Infrastructure
```
Component              Tests    Coverage
────────────────────────────────────────
JobManager            10       95%+
VideoManager          9        95%+
Celery Tasks          5-10     90%+
API Endpoints         20-30    95%+
WebSocket             3-5      90%+
────────────────────────────────────────
Total Phase 0         47-64    95%+
```

### Complete Project
```
Phase                  Tests    Coverage
────────────────────────────────────────
Phase 0 (NEW)         47-64    95%+
Phase 1 (Existing)    200-300  95%+
Integration (NEW)     70-120   90%+
E2E (NEW)             10-20    85%+
────────────────────────────────────────
Total Project         327-504  95%+
```

---

## 🗓️ Updated Implementation Timeline

### Week 1: Infrastructure & Core Pipeline

**Days 1-2: Job Queue & CRUD (NEW)**
- Day 1: JobManager + tests (10 tests, TDD)
- Day 2: VideoManager + tests (9 tests, TDD)

**Days 3-4: Video Downloader**
- VideoDownloader + tests (15 tests, TDD)

**Days 5-6: Transcription Engine**
- TranscriptionEngine + tests (15 tests, TDD)

**Day 7: Integration**
- Connect all components
- Run integration tests
- Fix issues

### Week 2: Advanced Features & API

**Days 1-2: API Endpoints**
- FastAPI endpoints + tests (20-30 tests, TDD)
- WebSocket support + tests (3-5 tests, TDD)

**Days 3-4: Audio & Metadata**
- AudioExtractor + tests
- MetadataExtractor + tests

**Days 5-7: Integration & E2E**
- Full integration testing
- E2E workflows
- Performance testing

---

## ✅ What You Have Now

### Complete TDD Plan for:
1. ✅ **Job Queue System**
   - JobManager with 10 unit tests
   - Celery task tests
   - Automatic & manual retry tests
   
2. ✅ **CRUD Operations**
   - VideoManager with 9 unit tests
   - Caching tests (Redis)
   - Cascading delete tests
   
3. ✅ **API Endpoints**
   - Test templates for all endpoints
   - WebSocket testing approach
   - Integration test examples
   
4. ✅ **Existing Pipeline**
   - VideoDownloader tests
   - TranscriptionEngine tests
   - All other component tests

---

## 🚀 How to Use This TDD Plan

### Step 1: Start with Phase 0 (Days 1-2)

```bash
# Day 1: Job Manager
cd tests/unit/queue
touch test_job_manager.py

# Copy tests from TDD plan
# Run: pytest test_job_manager.py -v
# All should FAIL (RED)

# Implement app/queue/job_manager.py
# Run tests again - should PASS (GREEN)

# Refactor code
# Tests still PASS
```

### Step 2: Continue with Phase 1 (Days 3-7)

```bash
# Day 3: Video Downloader
cd tests/unit/pipeline/extractors
# Follow TDD plan for VideoDownloader tests
```

### Step 3: Integration Testing

```bash
# After all units tested
cd tests/integration
# Run integration tests with real services
docker-compose up -d
pytest tests/integration -v
```

---

## 📝 Files to Reference

**Main TDD Plan:**
- `docs/YOUTUBE-TDD-PLAN.md` - Complete plan with all tests

**Architecture:**
- `docs/YOUTUBE-PRODUCTION-ARCHITECTURE.md` - System design
- `docs/YOUTUBE-PRODUCTION-UPDATES.md` - What's been added

**Quick Start:**
- `docs/YOUTUBE-QUICKSTART.md` - 5-minute setup
- `docs/YOUTUBE-EXECUTIVE-SUMMARY.md` - 10-minute overview

---

## 🎯 Next Steps

1. **Review Complete TDD Plan** - Check `YOUTUBE-TDD-PLAN.md`
2. **Set Up Environment** - Install dependencies
3. **Day 1: JobManager** - Start with 10 unit tests (RED → GREEN → REFACTOR)
4. **Day 2: VideoManager** - Continue with 9 CRUD tests
5. **Week 1 Complete** - All infrastructure + core pipeline tested

**You now have a complete TDD implementation plan covering all production features!** 🎉

---

**Summary:**
- ✅ 47-64 new tests for job queue & CRUD
- ✅ Complete test examples with assertions
- ✅ Integration test templates
- ✅ API endpoint test templates
- ✅ WebSocket test templates
- ✅ Updated timeline with Phase 0
- ✅ >95% coverage for all new components

**Ready to start TDD implementation!** 🚀
