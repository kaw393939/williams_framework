# YouTube Architecture Updates - Production Features Added

**Date:** October 12, 2025
**Status:** Enhanced with Job Queue, Status Tracking, Retries, and CRUD

---

## 🎯 Updates Summary

Based on your feedback, I've enhanced the YouTube Processing Architecture with **critical production features**:

1. ✅ **Job Queue System** (Celery + Redis)
2. ✅ **Persistent Status Tracking** (PostgreSQL + Redis)
3. ✅ **Automatic & Manual Retry** (Configurable limits)
4. ✅ **Complete CRUD Operations** (With cascading deletes)
5. ✅ **RESTful API** (FastAPI with WebSocket support)

---

## 🚀 New Components Added

### Component 0: Job Queue & Status Tracking System

**Purpose:** Decouple API requests from long-running processing

**Key Features:**
```python
# Async job creation
job = await job_manager.create_job(url, priority=5)
# Returns immediately with job_id

# Real-time status tracking
status = await job_manager.get_job(job_id)
# Shows: pending → queued → downloading → transcribing → completed

# WebSocket streaming
ws://api/videos/status/{job_id}/stream
# Real-time progress updates
```

**Job States:**
- `PENDING` - Job created, waiting to queue
- `QUEUED` - In Celery queue
- `DOWNLOADING` - Downloading video
- `EXTRACTING_AUDIO` - Extracting audio
- `TRANSCRIBING` - Running transcription
- `EXTRACTING_METADATA` - Getting metadata
- `EXTRACTING_COMMENTS` - Getting comments
- `COMPLETED` - Successfully finished
- `FAILED` - Error occurred
- `RETRYING` - Automatic retry in progress
- `CANCELLED` - User cancelled

**Database Schema:**
```sql
CREATE TABLE processing_jobs (
    job_id VARCHAR(32) PRIMARY KEY,
    video_id VARCHAR(20),
    url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    progress_percent FLOAT DEFAULT 0.0,
    current_stage TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    video_path TEXT,
    audio_path TEXT,
    transcript_id UUID,
    
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    
    priority INT DEFAULT 5,
    user_id VARCHAR(50)
);
```

---

### Component 1: CRUD Operations & Data Lifecycle

**Purpose:** Complete video lifecycle management with cascading operations

**Create:**
```python
# Start processing
job_id = await video_manager.create_video(url, priority=5)
```

**Read:**
```python
# Get complete video data
video_data = await video_manager.get_video(video_id)
# Includes: metadata, transcript, comments, chapters, relationships
# Cached in Redis for 1 hour
```

**Update:**
```python
# Update metadata
await video_manager.update_video(
    video_id,
    {"title": "New Title", "tags": ["updated"]}
)
# Invalidates cache, updates PostgreSQL & Neo4j
```

**Delete:**
```python
# Soft delete (mark as deleted, keep data)
await video_manager.delete_video(video_id, hard_delete=False)

# Hard delete (permanent removal)
await video_manager.delete_video(video_id, hard_delete=True)
```

**Cascading Delete Order:**
```
1. Redis (cache)
   └─ Invalidate video:{video_id}

2. Neo4j (graph relationships)
   └─ DELETE all relationships and nodes

3. PostgreSQL (relational data)
   ├─ comments (FK: video_id)
   ├─ chapters (FK: video_id)
   ├─ transcriptions (FK: video_id)
   ├─ processing_jobs (FK: video_id)
   └─ video_metadata (PK: video_id)

4. MinIO (object storage)
   ├─ youtube-videos/{video_id}/
   ├─ youtube-audio/{video_id}/
   └─ youtube-thumbnails/{video_id}/
```

**Reprocessing:**
```python
# Reprocess with better algorithms (uses stored files)
job_id = await video_manager.reprocess_video(
    video_id,
    force_whisper=True,
    model_size="large-v3"
)
# No re-download needed!
```

---

### Retry Functionality

**Automatic Retry:**
```python
# Built into Celery task
@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, job_id, url):
    try:
        # Process video
        pass
    except Exception as e:
        # Automatic retry with exponential backoff
        await job_manager.retry_job(job_id, manual=False)
        raise

# Retry delays: 4s, 16s, 64s (exponential backoff)
```

**Manual Retry:**
```python
# API endpoint for manual retry
POST /api/jobs/{job_id}/retry

# Higher priority, more retries allowed
success = await job_manager.retry_job(job_id, manual=True)

# Manual: 10 retries max
# Automatic: 3 retries max
```

**Retry Logic:**
```python
async def retry_job(self, job_id: str, manual: bool = False) -> bool:
    job = await self.get_job(job_id)
    
    # Check retry limit
    max_retries = 10 if manual else 3
    if job.retry_count >= max_retries:
        return False  # Max retries exceeded
    
    # Increment count
    await self.postgres.increment_retry_count(job_id)
    
    # Reset and requeue
    await self.update_job_status(job_id, JobStatus.RETRYING, ...)
    
    # Higher priority for manual retries
    priority = 1 if manual else job.priority
    process_video_task.apply_async(args=[job_id, url], priority=priority)
    
    return True
```

---

## 🌐 API Endpoints

### Video Processing

**Start Processing:**
```bash
POST /api/videos/process
{
  "url": "https://youtube.com/watch?v=...",
  "priority": 5,
  "force_whisper": false
}

Response:
{
  "job_id": "abc123...",
  "status": "queued",
  "message": "Video processing started"
}
```

**Get Status:**
```bash
GET /api/videos/status/{job_id}

Response:
{
  "job_id": "abc123...",
  "status": "transcribing",
  "progress": 65.5,
  "stage": "Transcribing audio with faster-whisper",
  "video_id": "dQw4w9WgXcQ",
  "created_at": "2025-10-12T10:00:00Z",
  "error": null
}
```

**Real-time Updates (WebSocket):**
```javascript
const ws = new WebSocket('ws://api/videos/status/abc123.../stream');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(update.progress);  // 65.5
  // Update UI progress bar
};
```

---

### CRUD Operations

**Get Video:**
```bash
GET /api/videos/{video_id}?include_comments=false

Response:
{
  "video_id": "dQw4w9WgXcQ",
  "metadata": {...},
  "transcript": {...},
  "chapters": [...]
}
```

**List Videos:**
```bash
GET /api/videos?status=completed&limit=100&offset=0

Response:
{
  "videos": [...],
  "total": 1234,
  "limit": 100,
  "offset": 0
}
```

**Update Video:**
```bash
PATCH /api/videos/{video_id}
{
  "title": "New Title",
  "tags": ["updated", "tags"]
}

Response:
{
  "success": true,
  "video_id": "dQw4w9WgXcQ"
}
```

**Delete Video:**
```bash
DELETE /api/videos/{video_id}?hard_delete=true

Response:
{
  "success": true,
  "deleted": true,
  "hard_delete": true,
  "video_id": "dQw4w9WgXcQ"
}
```

---

### Job Management

**Retry Job:**
```bash
POST /api/jobs/{job_id}/retry?manual=true

Response:
{
  "success": true,
  "job_id": "abc123...",
  "retry_count": 2,
  "status": "retrying"
}
```

**Cancel Job:**
```bash
POST /api/jobs/{job_id}/cancel

Response:
{
  "success": true,
  "job_id": "abc123...",
  "status": "cancelled"
}
```

**Job Statistics:**
```bash
GET /api/jobs/stats

Response:
{
  "total": 1234,
  "completed": 1100,
  "failed": 50,
  "pending": 20,
  "processing": 64,
  "success_rate": 0.956,
  "avg_processing_time": 180.5
}
```

---

### Reprocessing

**Reprocess with Better Algorithm:**
```bash
POST /api/videos/{video_id}/reprocess
{
  "force_whisper": true,
  "model_size": "large-v3"
}

Response:
{
  "job_id": "xyz789...",
  "video_id": "dQw4w9WgXcQ",
  "status": "queued",
  "message": "Reprocessing started"
}
```

---

### File Downloads

**Download Video:**
```bash
GET /api/videos/{video_id}/download/video

Response: Streaming video file (MP4)
```

**Download Audio:**
```bash
GET /api/videos/{video_id}/download/audio

Response: Streaming audio file (MP3)
```

---

## 🔧 Technology Stack

### Added Technologies

**Job Queue:**
- **Celery** (5.3+) - Distributed task queue
- **Redis** (7.0+) - Message broker + cache + pub/sub

**Dependencies:**
```toml
[tool.poetry.dependencies]
celery = "^5.3.0"
redis = "^5.0.0"
fastapi = "^0.104.0"  # Already have
websockets = "^12.0"
```

---

## 📊 System Flow

### Complete Processing Flow

```
1. User Request
   ↓
   POST /api/videos/process
   ↓
2. Create Job (PostgreSQL)
   └─ job_id, status=PENDING
   ↓
3. Queue in Redis
   └─ Celery queue
   ↓
4. Return Immediately
   └─ {"job_id": "...", "status": "queued"}
   ↓
5. Worker Picks Up (Celery)
   ├─ Update: status=DOWNLOADING, progress=10%
   ├─ Download video → MinIO
   ├─ Update: status=EXTRACTING_AUDIO, progress=30%
   ├─ Extract audio → MinIO
   ├─ Update: status=TRANSCRIBING, progress=50%
   ├─ Transcribe → PostgreSQL
   ├─ Update: status=EXTRACTING_METADATA, progress=70%
   ├─ Metadata → PostgreSQL + Neo4j
   └─ Update: status=COMPLETED, progress=100%
   ↓
6. User Polls or WebSocket
   └─ GET /api/videos/status/{job_id}
   └─ WS: Real-time updates

7. On Error
   ├─ Update: status=FAILED, error="..."
   ├─ Automatic retry (3 times)
   └─ If still fails: status=FAILED (final)

8. User Can Manually Retry
   └─ POST /api/jobs/{job_id}/retry
```

---

## 🧪 Testing Updates

### New Test Categories

**Job Queue Tests:**
```python
# tests/unit/test_job_manager.py
async def test_create_job():
    job = await job_manager.create_job(url, priority=5)
    assert job.status == JobStatus.PENDING

async def test_retry_job_automatic():
    success = await job_manager.retry_job(job_id, manual=False)
    assert success
    assert job.retry_count == 1

async def test_retry_job_max_exceeded():
    # After 3 retries
    success = await job_manager.retry_job(job_id, manual=False)
    assert not success
```

**CRUD Tests:**
```python
# tests/integration/test_video_manager.py
async def test_create_and_get_video():
    job_id = await video_manager.create_video(url)
    # Wait for completion
    video = await video_manager.get_video(video_id)
    assert video is not None

async def test_delete_video_cascading():
    await video_manager.delete_video(video_id, hard_delete=True)
    
    # Verify all deleted
    assert not await postgres.video_exists(video_id)
    assert not await neo4j.video_exists(video_id)
    assert not await minio.file_exists(f"youtube-videos/{video_id}/")

async def test_reprocess_video():
    job_id = await video_manager.reprocess_video(video_id)
    # Should use cached files, not re-download
```

**API Tests:**
```python
# tests/e2e/test_api.py
def test_process_video_endpoint():
    response = client.post("/api/videos/process", json={"url": url})
    assert response.status_code == 200
    job_id = response.json()["job_id"]

def test_websocket_status_stream():
    with client.websocket_connect(f"/api/videos/status/{job_id}/stream") as ws:
        update = ws.receive_json()
        assert "progress" in update
```

---

## 📈 Monitoring Enhancements

### New Metrics to Track

```python
# Job Queue Metrics
celery_queue_length = Gauge('celery_queue_length')
celery_active_workers = Gauge('celery_active_workers')
jobs_processing_rate = Counter('jobs_processing_rate')

# Status Metrics
jobs_by_status = Gauge('jobs_by_status', ['status'])
jobs_retry_count = Histogram('jobs_retry_count')
jobs_processing_duration = Histogram('jobs_processing_duration')

# CRUD Metrics
videos_created_total = Counter('videos_created_total')
videos_deleted_total = Counter('videos_deleted_total', ['hard_delete'])
videos_reprocessed_total = Counter('videos_reprocessed_total')
```

---

## ✅ Implementation Checklist

### Phase 1: Job Queue & Status (Week 1)
- [ ] Install Celery + Redis
- [ ] Create ProcessingJob model
- [ ] Implement JobManager
- [ ] Create Celery tasks
- [ ] Add PostgreSQL job table
- [ ] Add Redis pub/sub
- [ ] Write tests

### Phase 2: CRUD Operations (Week 1)
- [ ] Implement VideoManager
- [ ] Add cascading delete logic
- [ ] Add reprocessing capability
- [ ] Write tests

### Phase 3: API Endpoints (Week 2)
- [ ] Create FastAPI endpoints
- [ ] Add WebSocket support
- [ ] Add file download endpoints
- [ ] Write API tests

### Phase 4: Integration (Week 2)
- [ ] Connect all components
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Deploy to staging

---

## 🎯 Benefits

### For Users:
- ✅ Non-blocking API (immediate response)
- ✅ Real-time progress tracking
- ✅ Retry failed jobs without re-uploading
- ✅ Complete control over video data
- ✅ Reprocess with better algorithms

### For System:
- ✅ Horizontal scaling (add more Celery workers)
- ✅ Fault tolerance (automatic retry)
- ✅ Resource efficiency (job queuing)
- ✅ Clean data management (cascading deletes)
- ✅ Storage optimization (reprocessing uses cached files)

### For Developers:
- ✅ Clear separation of concerns
- ✅ Easy to test (mocked dependencies)
- ✅ Observable system (metrics & logs)
- ✅ Maintainable code (modular design)

---

## 📝 Next Steps

1. **Review Updates** - Check YOUTUBE-PRODUCTION-ARCHITECTURE.md
2. **Install Dependencies** - `poetry add celery redis websockets`
3. **Create Database Tables** - Run migration for processing_jobs
4. **Implement JobManager** - Start with TDD
5. **Implement VideoManager** - CRUD operations
6. **Add API Endpoints** - FastAPI integration
7. **Test End-to-End** - Complete workflow

**Updated documentation is ready for implementation!** 🚀

---

**Files Updated:**
- `docs/YOUTUBE-PRODUCTION-ARCHITECTURE.md` - Added Components 0-1, API section

**New Components:**
- Job Queue & Status Tracking System (Component 0)
- CRUD Operations & Data Lifecycle (Component 1)
- Complete RESTful API with WebSocket support

**Key Features:**
- ✅ Async job queue
- ✅ Persistent status tracking
- ✅ Automatic & manual retry
- ✅ Cascading deletes
- ✅ Reprocessing capability
- ✅ Real-time updates
