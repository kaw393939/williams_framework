# YouTube Processing TDD Implementation Plan

**Version:** 2.0 (Production-Ready with Job Queue & CRUD)
**Date:** October 12, 2025
**Updated:** Added Job Queue, Status Tracking, Retry, and CRUD tests
**Approach:** Test-Driven Development (Red → Green → Refactor)

---

## TDD Principles

### Red-Green-Refactor Cycle

```
1. RED: Write a failing test
   ↓
2. GREEN: Write minimal code to pass
   ↓
3. REFACTOR: Improve code quality
   ↓
4. REPEAT
```

### Test Pyramid

```
    ╱───────╲
   ╱  E2E    ╲      ← Few (5-10 tests)
  ╱─────────────╲
 ╱ Integration   ╲  ← Some (50-100 tests)
╱─────────────────╲
| Unit Tests       | ← Many (200-300 tests)
└─────────────────┘
```

**Our Strategy:**
- **Unit Tests:** Each component in isolation (mock dependencies)
- **Integration Tests:** Components working together (real services)
- **E2E Tests:** Complete user workflows (real YouTube videos)

---

## Test Structure

### Directory Layout

```
tests/
├── unit/
│   ├── queue/                          ← NEW: Job queue tests
│   │   ├── test_job_manager.py
│   │   └── test_celery_tasks.py
│   ├── crud/                           ← NEW: CRUD tests
│   │   └── test_video_manager.py
│   ├── api/                            ← NEW: API tests
│   │   ├── test_video_endpoints.py
│   │   ├── test_job_endpoints.py
│   │   └── test_websocket.py
│   ├── pipeline/
│   │   ├── extractors/
│   │   │   ├── test_video_downloader.py
│   │   │   ├── test_subtitle_extractor.py
│   │   │   ├── test_audio_extractor.py
│   │   │   ├── test_transcription_engine.py
│   │   │   ├── test_metadata_extractor.py
│   │   │   ├── test_comment_extractor.py
│   │   │   └── test_chapter_detector.py
│   │   └── processors/
│   │       ├── test_long_video_processor.py
│   │       └── test_youtube_pipeline.py
│   └── conftest.py
├── integration/
│   ├── test_job_queue_integration.py   ← NEW
│   ├── test_crud_operations.py         ← NEW
│   ├── test_retry_functionality.py     ← NEW
│   ├── test_youtube_storage.py
│   ├── test_youtube_transcription.py
│   ├── test_youtube_full_pipeline.py
│   └── conftest.py
├── e2e/
│   ├── test_youtube_api_workflow.py    ← NEW
│   ├── test_youtube_end_to_end.py
│   ├── test_youtube_long_videos.py
│   └── conftest.py
├── fixtures/
│   ├── sample_video_metadata.json
│   ├── sample_transcript.txt
│   ├── sample_subtitles.srt
│   ├── sample_audio.mp3 (short test file)
│   └── sample_jobs.json                ← NEW
└── helpers/
    ├── youtube_test_config.py
    ├── mock_youtube_api.py
    ├── mock_celery.py                  ← NEW
    └── test_video_generator.py
```

---

## Phase 0: Job Queue & Infrastructure (Days 1-2)

### Day 1: Job Manager & Status Tracking

#### Test File: `tests/unit/queue/test_job_manager.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.queue.job_manager import JobManager, JobStatus, ProcessingJob


class TestJobManager:
    """Unit tests for JobManager."""
    
    @pytest.fixture
    def mock_postgres(self):
        """Mock PostgreSQL repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_celery(self):
        """Mock Celery app."""
        return Mock()
    
    @pytest.fixture
    def job_manager(self, mock_postgres, mock_redis, mock_celery):
        """Create JobManager with mocked dependencies."""
        return JobManager(mock_postgres, mock_redis, mock_celery)
    
    # Test 1: Create job successfully
    @pytest.mark.asyncio
    async def test_create_job_success(self, job_manager, mock_postgres, mock_redis):
        """RED: Test creating a new job."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Mock task creation
        job_manager.celery.apply_async = Mock(return_value=Mock(id="task123"))
        
        # Act
        job = await job_manager.create_job(url, priority=5)
        
        # Assert
        assert isinstance(job, ProcessingJob)
        assert job.url == url
        assert job.status == JobStatus.PENDING
        assert job.priority == 5
        assert job.job_id is not None
        
        # Verify saved to PostgreSQL
        mock_postgres.save_job.assert_called_once()
        
        # Verify queued in Redis
        mock_redis.hset.assert_called()
    
    # Test 2: Get job by ID
    @pytest.mark.asyncio
    async def test_get_job_success(self, job_manager, mock_postgres):
        """RED: Test retrieving job by ID."""
        job_id = "abc123"
        expected_job = ProcessingJob(
            job_id=job_id,
            url="https://youtube.com/...",
            status=JobStatus.COMPLETED,
            progress_percent=100.0,
            current_stage="Completed",
            created_at=datetime.utcnow()
        )
        
        mock_postgres.get_job.return_value = expected_job
        
        # Act
        job = await job_manager.get_job(job_id)
        
        # Assert
        assert job.job_id == job_id
        assert job.status == JobStatus.COMPLETED
        mock_postgres.get_job.assert_called_once_with(job_id)
    
    # Test 3: Update job status
    @pytest.mark.asyncio
    async def test_update_job_status(self, job_manager, mock_postgres, mock_redis):
        """RED: Test updating job status and progress."""
        job_id = "abc123"
        
        # Act
        await job_manager.update_job_status(
            job_id,
            JobStatus.TRANSCRIBING,
            progress=65.5,
            stage="Transcribing audio with faster-whisper"
        )
        
        # Assert - PostgreSQL updated
        mock_postgres.update_job.assert_called_once_with(
            job_id=job_id,
            status="transcribing",
            progress_percent=65.5,
            current_stage="Transcribing audio with faster-whisper",
            error_message=None
        )
        
        # Assert - Redis updated
        mock_redis.hset.assert_called_once()
        
        # Assert - Published to pub/sub
        mock_redis.publish.assert_called_once()
    
    # Test 4: Automatic retry
    @pytest.mark.asyncio
    async def test_retry_job_automatic(self, job_manager, mock_postgres):
        """RED: Test automatic retry with limit."""
        job_id = "abc123"
        
        # Mock job with 0 retries
        job = ProcessingJob(
            job_id=job_id,
            url="https://youtube.com/...",
            status=JobStatus.FAILED,
            progress_percent=30.0,
            current_stage="Failed at download",
            created_at=datetime.utcnow(),
            retry_count=0,
            max_retries=3
        )
        mock_postgres.get_job.return_value = job
        job_manager.celery.apply_async = Mock()
        
        # Act
        success = await job_manager.retry_job(job_id, manual=False)
        
        # Assert
        assert success is True
        mock_postgres.increment_retry_count.assert_called_once_with(job_id)
        job_manager.celery.apply_async.assert_called_once()
    
    # Test 5: Retry max exceeded
    @pytest.mark.asyncio
    async def test_retry_job_max_exceeded(self, job_manager, mock_postgres):
        """RED: Test retry fails when max attempts exceeded."""
        job_id = "abc123"
        
        # Mock job with max retries
        job = ProcessingJob(
            job_id=job_id,
            url="https://youtube.com/...",
            status=JobStatus.FAILED,
            progress_percent=30.0,
            current_stage="Failed",
            created_at=datetime.utcnow(),
            retry_count=3,
            max_retries=3
        )
        mock_postgres.get_job.return_value = job
        
        # Act
        success = await job_manager.retry_job(job_id, manual=False)
        
        # Assert
        assert success is False
        mock_postgres.increment_retry_count.assert_not_called()
    
    # Test 6: Manual retry with higher limit
    @pytest.mark.asyncio
    async def test_retry_job_manual(self, job_manager, mock_postgres):
        """RED: Test manual retry allows more attempts."""
        job_id = "abc123"
        
        # Mock job with 5 retries (exceeds automatic limit)
        job = ProcessingJob(
            job_id=job_id,
            url="https://youtube.com/...",
            status=JobStatus.FAILED,
            progress_percent=30.0,
            current_stage="Failed",
            created_at=datetime.utcnow(),
            retry_count=5,
            max_retries=3
        )
        mock_postgres.get_job.return_value = job
        job_manager.celery.apply_async = Mock()
        
        # Act - Manual retry allows up to 10
        success = await job_manager.retry_job(job_id, manual=True)
        
        # Assert
        assert success is True
        mock_postgres.increment_retry_count.assert_called_once()
        
        # Verify priority is higher for manual retries
        call_kwargs = job_manager.celery.apply_async.call_args[1]
        assert call_kwargs["priority"] == 1  # Highest priority
    
    # Test 7: Cancel job
    @pytest.mark.asyncio
    async def test_cancel_job(self, job_manager, mock_postgres):
        """RED: Test cancelling a running job."""
        job_id = "abc123"
        
        # Mock running job
        job = ProcessingJob(
            job_id=job_id,
            url="https://youtube.com/...",
            status=JobStatus.TRANSCRIBING,
            progress_percent=50.0,
            current_stage="Transcribing",
            created_at=datetime.utcnow()
        )
        mock_postgres.get_job.return_value = job
        job_manager.celery.control.revoke = Mock()
        
        # Act
        success = await job_manager.cancel_job(job_id)
        
        # Assert
        assert success is True
        job_manager.celery.control.revoke.assert_called_once_with(
            job_id,
            terminate=True
        )
    
    # Test 8: Cannot cancel completed job
    @pytest.mark.asyncio
    async def test_cannot_cancel_completed_job(self, job_manager, mock_postgres):
        """RED: Test cannot cancel already completed job."""
        job_id = "abc123"
        
        # Mock completed job
        job = ProcessingJob(
            job_id=job_id,
            url="https://youtube.com/...",
            status=JobStatus.COMPLETED,
            progress_percent=100.0,
            current_stage="Completed",
            created_at=datetime.utcnow()
        )
        mock_postgres.get_job.return_value = job
        
        # Act
        success = await job_manager.cancel_job(job_id)
        
        # Assert
        assert success is False
    
    # Test 9: List jobs with filtering
    @pytest.mark.asyncio
    async def test_list_jobs(self, job_manager, mock_postgres):
        """RED: Test listing jobs with status filter."""
        # Mock job list
        jobs = [
            ProcessingJob(
                job_id=f"job{i}",
                url=f"https://youtube.com/watch?v={i}",
                status=JobStatus.COMPLETED,
                progress_percent=100.0,
                current_stage="Completed",
                created_at=datetime.utcnow()
            )
            for i in range(10)
        ]
        mock_postgres.list_jobs.return_value = jobs
        
        # Act
        result = await job_manager.list_jobs(
            status=JobStatus.COMPLETED,
            limit=10,
            offset=0
        )
        
        # Assert
        assert len(result) == 10
        mock_postgres.list_jobs.assert_called_once_with(
            status="completed",
            limit=10,
            offset=0
        )
    
    # Test 10: Get job statistics
    @pytest.mark.asyncio
    async def test_get_job_stats(self, job_manager, mock_postgres):
        """RED: Test retrieving aggregate statistics."""
        expected_stats = {
            "total": 1234,
            "completed": 1100,
            "failed": 50,
            "pending": 20,
            "processing": 64,
            "success_rate": 0.956
        }
        mock_postgres.get_job_stats.return_value = expected_stats
        
        # Act
        stats = await job_manager.get_job_stats()
        
        # Assert
        assert stats["total"] == 1234
        assert stats["success_rate"] > 0.95
        mock_postgres.get_job_stats.assert_called_once()


class TestProcessingJob:
    """Unit tests for ProcessingJob dataclass."""
    
    def test_job_creation(self):
        """RED: Test creating ProcessingJob."""
        job = ProcessingJob(
            job_id="test123",
            url="https://youtube.com/...",
            status=JobStatus.PENDING,
            progress_percent=0.0,
            current_stage="Created",
            created_at=datetime.utcnow()
        )
        
        assert job.job_id == "test123"
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
    
    def test_job_status_enum(self):
        """RED: Test JobStatus enum values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.RETRYING.value == "retrying"
```

#### Implementation File: `app/queue/job_manager.py`

```python
"""Job queue management for YouTube video processing."""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional
from uuid import uuid4
import json


class JobStatus(Enum):
    """Job status states."""
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    EXTRACTING_METADATA = "extracting_metadata"
    EXTRACTING_COMMENTS = "extracting_comments"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class ProcessingJob:
    """Represents a video processing job."""
    job_id: str
    url: str
    status: JobStatus
    progress_percent: float
    current_stage: str
    created_at: datetime
    
    video_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_id: Optional[str] = None
    
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 5


class JobManager:
    """Manages video processing jobs."""
    
    def __init__(self, postgres_repo, redis_client, celery_app):
        self.postgres = postgres_repo
        self.redis = redis_client
        self.celery = celery_app
    
    async def create_job(
        self,
        url: str,
        priority: int = 5,
        user_id: Optional[str] = None
    ) -> ProcessingJob:
        """Create new processing job."""
        job = ProcessingJob(
            job_id=uuid4().hex,
            url=url,
            status=JobStatus.PENDING,
            progress_percent=0.0,
            current_stage="Created",
            created_at=datetime.utcnow(),
            priority=priority,
        )
        
        # Save to PostgreSQL
        await self.postgres.save_job(job)
        
        # Queue in Celery
        from app.queue.celery_tasks import process_video_task
        task = process_video_task.apply_async(
            args=[job.job_id, url],
            priority=priority,
            task_id=job.job_id
        )
        
        # Update status
        await self.update_job_status(
            job.job_id,
            JobStatus.QUEUED,
            progress=5.0,
            stage="Queued for processing"
        )
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job by ID."""
        return await self.postgres.get_job(job_id)
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float,
        stage: str,
        error: Optional[str] = None
    ):
        """Update job status and progress."""
        await self.postgres.update_job(
            job_id=job_id,
            status=status.value,
            progress_percent=progress,
            current_stage=stage,
            error_message=error
        )
        
        # Update Redis for real-time tracking
        await self.redis.hset(
            f"job:{job_id}",
            mapping={
                "status": status.value,
                "progress": progress,
                "stage": stage,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        # Publish to pub/sub
        await self.redis.publish(
            f"job_updates:{job_id}",
            json.dumps({
                "job_id": job_id,
                "status": status.value,
                "progress": progress,
                "stage": stage
            })
        )
    
    async def retry_job(self, job_id: str, manual: bool = False) -> bool:
        """Retry failed job."""
        job = await self.get_job(job_id)
        if not job:
            return False
        
        # Check retry limit
        max_retries = 10 if manual else job.max_retries
        if job.retry_count >= max_retries:
            await self.update_job_status(
                job_id,
                JobStatus.FAILED,
                job.progress_percent,
                f"Max retries ({max_retries}) exceeded",
                error="Retry limit reached"
            )
            return False
        
        # Increment retry count
        await self.postgres.increment_retry_count(job_id)
        
        # Requeue
        priority = 1 if manual else job.priority
        from app.queue.celery_tasks import process_video_task
        process_video_task.apply_async(
            args=[job_id, job.url],
            priority=priority,
            task_id=f"{job_id}_retry_{job.retry_count + 1}"
        )
        
        return True
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel pending or running job."""
        job = await self.get_job(job_id)
        if not job:
            return False
        
        # Cannot cancel if completed or failed
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return False
        
        # Revoke Celery task
        self.celery.control.revoke(job_id, terminate=True)
        
        # Update status
        await self.update_job_status(
            job_id,
            JobStatus.CANCELLED,
            job.progress_percent,
            "Cancelled by user"
        )
        
        return True
    
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ProcessingJob]:
        """List jobs with optional filtering."""
        return await self.postgres.list_jobs(
            status=status.value if status else None,
            limit=limit,
            offset=offset
        )
    
    async def get_job_stats(self) -> dict:
        """Get aggregate job statistics."""
        return await self.postgres.get_job_stats()
```

---

### Day 2: CRUD Operations & Video Manager

#### Test File: `tests/unit/crud/test_video_manager.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.crud.video_manager import VideoManager, VideoData


class TestVideoManager:
    """Unit tests for VideoManager."""
    
    @pytest.fixture
    def mock_minio(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_postgres(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_neo4j(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()
    
    @pytest.fixture
    def video_manager(self, mock_minio, mock_postgres, mock_neo4j, mock_redis):
        return VideoManager(mock_minio, mock_postgres, mock_neo4j, mock_redis)
    
    # Test 1: Create video (start processing)
    @pytest.mark.asyncio
    async def test_create_video(self, video_manager):
        """RED: Test creating video processing job."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Act
        job_id = await video_manager.create_video(url, priority=5)
        
        # Assert
        assert job_id is not None
        assert isinstance(job_id, str)
    
    # Test 2: Get video with caching
    @pytest.mark.asyncio
    async def test_get_video_from_cache(self, video_manager, mock_redis):
        """RED: Test getting video from Redis cache."""
        video_id = "dQw4w9WgXcQ"
        
        # Mock cached data
        cached_data = '{"video_id": "dQw4w9WgXcQ", "title": "Test"}'
        mock_redis.get.return_value = cached_data
        
        # Act
        video_data = await video_manager.get_video(video_id)
        
        # Assert
        assert video_data is not None
        mock_redis.get.assert_called_once_with(f"video:{video_id}")
        # Should not hit database
        video_manager.postgres.get_video_metadata.assert_not_called()
    
    # Test 3: Get video from database (cache miss)
    @pytest.mark.asyncio
    async def test_get_video_from_database(self, video_manager, mock_redis, mock_postgres):
        """RED: Test getting video from database when not cached."""
        video_id = "dQw4w9WgXcQ"
        
        # Mock cache miss
        mock_redis.get.return_value = None
        
        # Mock database data
        mock_postgres.get_video_metadata.return_value = {
            "video_id": video_id,
            "title": "Test Video"
        }
        mock_postgres.get_transcript.return_value = {"text": "Transcript"}
        mock_postgres.get_comments.return_value = []
        mock_postgres.get_chapters.return_value = []
        
        # Act
        video_data = await video_manager.get_video(video_id)
        
        # Assert
        assert video_data is not None
        mock_postgres.get_video_metadata.assert_called_once_with(video_id)
        
        # Should cache the result
        mock_redis.setex.assert_called_once()
    
    # Test 4: Update video metadata
    @pytest.mark.asyncio
    async def test_update_video(self, video_manager, mock_postgres, mock_redis):
        """RED: Test updating video metadata."""
        video_id = "dQw4w9WgXcQ"
        updates = {"title": "New Title", "tags": ["updated"]}
        
        mock_postgres.update_video_metadata.return_value = True
        
        # Act
        success = await video_manager.update_video(video_id, updates)
        
        # Assert
        assert success is True
        mock_postgres.update_video_metadata.assert_called_once_with(video_id, updates)
        
        # Should invalidate cache
        mock_redis.delete.assert_called_once_with(f"video:{video_id}")
    
    # Test 5: Soft delete video
    @pytest.mark.asyncio
    async def test_soft_delete_video(self, video_manager, mock_postgres, mock_redis):
        """RED: Test soft delete (mark as deleted)."""
        video_id = "dQw4w9WgXcQ"
        
        # Act
        await video_manager.delete_video(video_id, hard_delete=False)
        
        # Assert - Should mark as deleted in PostgreSQL
        mock_postgres.execute.assert_called_once()
        call_args = mock_postgres.execute.call_args[0]
        assert "deleted_at" in call_args[0]
        
        # Should invalidate cache
        mock_redis.delete.assert_called_once()
        
        # Should NOT delete from MinIO
        video_manager.minio.delete_folder.assert_not_called()
    
    # Test 6: Hard delete video (cascading)
    @pytest.mark.asyncio
    async def test_hard_delete_video(self, video_manager, mock_postgres, mock_redis, mock_neo4j, mock_minio):
        """RED: Test hard delete with cascading."""
        video_id = "dQw4w9WgXcQ"
        
        # Act
        await video_manager.delete_video(video_id, hard_delete=True)
        
        # Assert - Redis cache cleared
        mock_redis.delete.assert_called_once_with(f"video:{video_id}")
        
        # Assert - Neo4j relationships deleted
        mock_neo4j.execute.assert_called_once()
        
        # Assert - PostgreSQL data deleted (multiple tables)
        assert mock_postgres.execute.call_count >= 5  # comments, chapters, transcripts, jobs, metadata
        
        # Assert - MinIO files deleted
        assert mock_minio.delete_folder.call_count == 3  # videos, audio, thumbnails
    
    # Test 7: Reprocess video
    @pytest.mark.asyncio
    async def test_reprocess_video(self, video_manager, mock_minio):
        """RED: Test reprocessing video with stored files."""
        video_id = "dQw4w9WgXcQ"
        
        # Mock video exists in MinIO
        mock_minio.get_file_path.return_value = f"youtube-videos/{video_id}/original.mp4"
        
        # Act
        job_id = await video_manager.reprocess_video(
            video_id,
            force_whisper=True,
            model_size="large-v3"
        )
        
        # Assert
        assert job_id is not None
        mock_minio.get_file_path.assert_called_once()
    
    # Test 8: Reprocess fails if video not in storage
    @pytest.mark.asyncio
    async def test_reprocess_video_not_found(self, video_manager, mock_minio):
        """RED: Test reprocess fails if video not stored."""
        video_id = "nonexistent"
        
        # Mock video not in MinIO
        mock_minio.get_file_path.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="not found in storage"):
            await video_manager.reprocess_video(video_id)
    
    # Test 9: List videos with filtering
    @pytest.mark.asyncio
    async def test_list_videos(self, video_manager, mock_postgres):
        """RED: Test listing videos with filters."""
        mock_postgres.list_videos.return_value = [
            {"video_id": "1", "title": "Video 1"},
            {"video_id": "2", "title": "Video 2"},
        ]
        
        # Act
        videos = await video_manager.list_videos(
            filters={"status": "completed"},
            limit=100,
            offset=0
        )
        
        # Assert
        assert len(videos) == 2
        mock_postgres.list_videos.assert_called_once()
```

---

## Phase 1: Core Pipeline (Week 1)

### Day 3-4: Video Downloader

#### Test File: `tests/unit/pipeline/extractors/test_video_downloader.py`

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.pipeline.extractors.video_downloader import VideoDownloader, VideoAsset
from app.repositories.minio import MinIORepository


class TestVideoDownloader:
    """Unit tests for VideoDownloader."""
    
    @pytest.fixture
    def mock_minio(self):
        """Mock MinIO repository."""
        return Mock(spec=MinIORepository)
    
    @pytest.fixture
    def downloader(self, mock_minio):
        """Create VideoDownloader with mocked dependencies."""
        return VideoDownloader(minio_repository=mock_minio)
    
    # Test 1: Download succeeds with valid URL
    @pytest.mark.asyncio
    async def test_download_video_success(self, downloader, mock_minio):
        """RED: Test downloading a valid video."""
        # Arrange
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        expected_video_id = "dQw4w9WgXcQ"
        
        # Mock yt-dlp response
        mock_info = {
            "id": expected_video_id,
            "title": "Test Video",
            "duration": 300,
        }
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = mock_info
            mock_minio.upload_file.return_value = f"youtube-videos/{expected_video_id}/original.mp4"
            
            # Act
            result = await downloader.download_video(url)
            
            # Assert
            assert isinstance(result, VideoAsset)
            assert result.video_id == expected_video_id
            assert result.minio_path.startswith("youtube-videos/")
            assert result.title == "Test Video"
            assert result.duration == 300
            mock_minio.upload_file.assert_called_once()
    
    # Test 2: Download fails with invalid URL
    @pytest.mark.asyncio
    async def test_download_video_invalid_url(self, downloader):
        """RED: Test downloading with invalid URL raises error."""
        url = "not-a-valid-url"
        
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            await downloader.download_video(url)
    
    # Test 3: Download retries on network failure
    @pytest.mark.asyncio
    async def test_download_video_retries(self, downloader, mock_minio):
        """RED: Test automatic retry on network failure."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            # First two attempts fail, third succeeds
            mock_ytdl.return_value.__enter__.return_value.extract_info.side_effect = [
                ConnectionError("Network error"),
                ConnectionError("Network error"),
                {"id": "dQw4w9WgXcQ", "title": "Test"},
            ]
            mock_minio.upload_file.return_value = "youtube-videos/dQw4w9WgXcQ/original.mp4"
            
            result = await downloader.download_video(url)
            
            assert result.video_id == "dQw4w9WgXcQ"
            assert mock_ytdl.return_value.__enter__.return_value.extract_info.call_count == 3
    
    # Test 4: Download audio only
    @pytest.mark.asyncio
    async def test_download_audio_only(self, downloader, mock_minio):
        """RED: Test downloading audio-only format."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = {
                "id": "dQw4w9WgXcQ",
                "title": "Test",
            }
            mock_minio.upload_file.return_value = "youtube-audio/dQw4w9WgXcQ/audio.mp3"
            
            result = await downloader.download_audio_only(url)
            
            assert result.minio_path.startswith("youtube-audio/")
            # Verify audio-only format was requested
            call_args = mock_ytdl.call_args[0][0]
            assert "format" in call_args
            assert "bestaudio" in call_args["format"]
    
    # Test 5: Progress callback
    @pytest.mark.asyncio
    async def test_download_with_progress(self, downloader):
        """RED: Test progress callback during download."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        progress_calls = []
        
        def progress_callback(downloaded: int, total: int):
            progress_calls.append((downloaded, total))
        
        with patch("yt_dlp.YoutubeDL"):
            await downloader.download_video(url, progress_callback=progress_callback)
            
            # Should have received progress updates
            assert len(progress_calls) > 0
    
    # Test 6: Quality selection
    @pytest.mark.asyncio
    async def test_download_quality_selection(self, downloader, mock_minio):
        """RED: Test downloading with specific quality."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = {
                "id": "dQw4w9WgXcQ",
            }
            
            await downloader.download_video(url, quality="720p")
            
            # Verify quality was specified
            call_args = mock_ytdl.call_args[0][0]
            assert "720" in call_args["format"]
    
    # Test 7: Resume capability
    @pytest.mark.asyncio
    async def test_download_with_resume(self, downloader, mock_minio):
        """RED: Test resuming interrupted download."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Simulate partial download exists
        mock_minio.file_exists.return_value = True
        mock_minio.get_file_size.return_value = 500000  # 500KB partial
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = {
                "id": "dQw4w9WgXcQ",
            }
            
            await downloader.download_with_resume(url)
            
            # Should pass resume options to yt-dlp
            call_args = mock_ytdl.call_args[0][0]
            assert call_args.get("continuedl") is True


class TestVideoAsset:
    """Unit tests for VideoAsset dataclass."""
    
    def test_video_asset_creation(self):
        """RED: Test creating VideoAsset."""
        asset = VideoAsset(
            video_id="test123",
            title="Test Video",
            minio_path="youtube-videos/test123/original.mp4",
            duration=300,
            file_size=1000000,
        )
        
        assert asset.video_id == "test123"
        assert asset.duration == 300
    
    def test_video_asset_url_property(self):
        """RED: Test VideoAsset generates correct URL."""
        asset = VideoAsset(
            video_id="test123",
            minio_path="youtube-videos/test123/original.mp4",
        )
        
        expected_url = "https://www.youtube.com/watch?v=test123"
        assert asset.url == expected_url
```

#### Implementation File: `app/pipeline/extractors/video_downloader.py`

```python
"""Video downloader using yt-dlp with MinIO storage."""

from dataclasses import dataclass
from typing import Optional, Callable
import asyncio
from pathlib import Path
import tempfile

import yt_dlp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.repositories.minio import MinIORepository


@dataclass
class VideoAsset:
    """Represents a downloaded video asset."""
    
    video_id: str
    minio_path: str
    title: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    resolution: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Generate YouTube URL from video ID."""
        return f"https://www.youtube.com/watch?v={self.video_id}"


class VideoDownloader:
    """Downloads YouTube videos using yt-dlp and stores in MinIO."""
    
    def __init__(self, minio_repository: MinIORepository):
        """Initialize downloader.
        
        Args:
            minio_repository: MinIO repository for storage
        """
        self.minio_repo = minio_repository
    
    def _validate_url(self, url: str) -> str:
        """Validate and extract video ID from URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID
            
        Raises:
            ValueError: If URL is invalid
        """
        # Extract video ID using yt-dlp
        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                info = ydl.extract_info(url, download=False, process=False)
                return info["id"]
        except Exception as e:
            raise ValueError(f"Invalid YouTube URL: {url}") from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(ConnectionError)
    )
    async def download_video(
        self,
        url: str,
        quality: str = "best",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> VideoAsset:
        """Download video and store in MinIO.
        
        Args:
            url: YouTube URL
            quality: Video quality (best/1080p/720p/480p)
            progress_callback: Optional callback for progress updates
            
        Returns:
            VideoAsset with metadata
            
        Raises:
            ValueError: If URL is invalid
            ConnectionError: If download fails (triggers retry)
        """
        # Validate URL
        video_id = self._validate_url(url)
        
        # Configure yt-dlp options
        ydl_opts = {
            "format": self._get_format_string(quality),
            "outtmpl": "%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }
        
        # Add progress hook if callback provided
        if progress_callback:
            def progress_hook(d):
                if d["status"] == "downloading":
                    downloaded = d.get("downloaded_bytes", 0)
                    total = d.get("total_bytes", 0)
                    progress_callback(downloaded, total)
            
            ydl_opts["progress_hooks"] = [progress_hook]
        
        # Download to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts["outtmpl"] = str(Path(temp_dir) / ydl_opts["outtmpl"])
            
            # Download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            # Upload to MinIO
            video_path = Path(temp_dir) / f"{video_id}.{info['ext']}"
            minio_path = f"youtube-videos/{video_id}/original.{info['ext']}"
            
            await self.minio_repo.upload_file(
                str(video_path),
                minio_path,
                bucket="youtube-videos"
            )
        
        # Create VideoAsset
        return VideoAsset(
            video_id=video_id,
            minio_path=minio_path,
            title=info.get("title"),
            duration=info.get("duration"),
            file_size=info.get("filesize"),
            resolution=f"{info.get('width')}x{info.get('height')}",
        )
    
    async def download_audio_only(
        self,
        url: str,
        format: str = "mp3"
    ) -> VideoAsset:
        """Download audio track only.
        
        Args:
            url: YouTube URL
            format: Audio format (mp3/wav/flac)
            
        Returns:
            VideoAsset with audio file
        """
        video_id = self._validate_url(url)
        
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": format,
            }],
            "outtmpl": "%(id)s.%(ext)s",
            "quiet": True,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts["outtmpl"] = str(Path(temp_dir) / ydl_opts["outtmpl"])
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            audio_path = Path(temp_dir) / f"{video_id}.{format}"
            minio_path = f"youtube-audio/{video_id}/audio.{format}"
            
            await self.minio_repo.upload_file(
                str(audio_path),
                minio_path,
                bucket="youtube-audio"
            )
        
        return VideoAsset(
            video_id=video_id,
            minio_path=minio_path,
            title=info.get("title"),
            duration=info.get("duration"),
        )
    
    async def download_with_resume(self, url: str) -> VideoAsset:
        """Download with resume capability.
        
        Args:
            url: YouTube URL
            
        Returns:
            VideoAsset
        """
        video_id = self._validate_url(url)
        
        ydl_opts = {
            "format": "best",
            "continuedl": True,  # Enable resume
            "noprogress": False,
            "outtmpl": "%(id)s.%(ext)s",
        }
        
        # Check if partial download exists
        partial_path = f"youtube-videos/{video_id}/original.partial"
        if await self.minio_repo.file_exists(partial_path):
            # Download partial file to temp and resume
            pass  # Implementation details
        
        return await self.download_video(url)
    
    def _get_format_string(self, quality: str) -> str:
        """Get yt-dlp format string for quality.
        
        Args:
            quality: Quality string (best/1080p/720p/480p)
            
        Returns:
            Format string for yt-dlp
        """
        quality_map = {
            "best": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best",
            "720p": "bestvideo[height<=720]+bestaudio/best",
            "480p": "bestvideo[height<=480]+bestaudio/best",
        }
        return quality_map.get(quality, "best")
```

#### TDD Workflow:

1. **RED:** Write test `test_download_video_success` (fails - class doesn't exist)
2. **GREEN:** Create minimal `VideoDownloader` class
3. **RED:** Write test `test_download_video_invalid_url` (fails)
4. **GREEN:** Add URL validation
5. **RED:** Write test `test_download_video_retries` (fails)
6. **GREEN:** Add retry logic
7. **REFACTOR:** Extract methods, improve code quality
8. **REPEAT:** For each feature

---

### Day 3-4: Transcription Engine

#### Test File: `tests/unit/pipeline/extractors/test_transcription_engine.py`

```python
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from app.pipeline.extractors.transcription_engine import (
    TranscriptionEngine,
    TranscriptionResult,
    TranscriptionSegment,
)


class TestTranscriptionEngine:
    """Unit tests for TranscriptionEngine with faster-whisper."""
    
    @pytest.fixture
    def engine(self):
        """Create TranscriptionEngine with test model."""
        return TranscriptionEngine(
            model_size="tiny",  # Use tiny for faster tests
            device="cpu",
            compute_type="int8"
        )
    
    # Test 1: Initialize engine
    def test_engine_initialization(self, engine):
        """RED: Test engine initializes correctly."""
        assert engine.model_size == "tiny"
        assert engine.device == "cpu"
        assert engine.model is not None
    
    # Test 2: Transcribe short audio
    @pytest.mark.asyncio
    async def test_transcribe_short_audio(self, engine, tmp_path):
        """RED: Test transcribing short audio file."""
        # Create dummy audio file (in real test, use fixture)
        audio_path = tmp_path / "test_audio.mp3"
        audio_path.write_bytes(b"dummy audio data")
        
        # Mock faster-whisper transcribe
        with patch.object(engine.model, "transcribe") as mock_transcribe:
            mock_transcribe.return_value = (
                [
                    Mock(
                        text="Hello world",
                        start=0.0,
                        end=2.0,
                        avg_logprob=-0.5
                    ),
                    Mock(
                        text="This is a test",
                        start=2.0,
                        end=4.5,
                        avg_logprob=-0.3
                    ),
                ],
                {"language": "en", "language_probability": 0.98}
            )
            
            result = await engine.transcribe(str(audio_path))
            
            assert isinstance(result, TranscriptionResult)
            assert result.full_text == "Hello world This is a test"
            assert len(result.segments) == 2
            assert result.language == "en"
            assert result.confidence > 0.9
    
    # Test 3: Transcribe with timestamps
    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps(self, engine, tmp_path):
        """RED: Test transcript includes accurate timestamps."""
        audio_path = tmp_path / "test.mp3"
        audio_path.write_bytes(b"dummy")
        
        with patch.object(engine.model, "transcribe") as mock_transcribe:
            mock_transcribe.return_value = (
                [
                    Mock(text="First", start=0.0, end=1.5, avg_logprob=-0.2),
                    Mock(text="Second", start=1.5, end=3.0, avg_logprob=-0.3),
                ],
                {"language": "en"}
            )
            
            result = await engine.transcribe(str(audio_path))
            
            assert result.segments[0].start_time == 0.0
            assert result.segments[0].end_time == 1.5
            assert result.segments[1].start_time == 1.5
            assert result.segments[1].end_time == 3.0
    
    # Test 4: Language detection
    @pytest.mark.asyncio
    async def test_language_detection(self, engine, tmp_path):
        """RED: Test automatic language detection."""
        audio_path = tmp_path / "test.mp3"
        audio_path.write_bytes(b"dummy")
        
        with patch.object(engine.model, "transcribe") as mock_transcribe:
            mock_transcribe.return_value = (
                [Mock(text="Bonjour", start=0.0, end=1.0, avg_logprob=-0.2)],
                {"language": "fr", "language_probability": 0.95}
            )
            
            result = await engine.transcribe(str(audio_path), language=None)
            
            assert result.language == "fr"
            assert result.language_probability >= 0.95
    
    # Test 5: Confidence scoring
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, engine, tmp_path):
        """RED: Test confidence scores are calculated."""
        audio_path = tmp_path / "test.mp3"
        audio_path.write_bytes(b"dummy")
        
        with patch.object(engine.model, "transcribe") as mock_transcribe:
            # Low confidence segment
            mock_transcribe.return_value = (
                [Mock(text="unclear", start=0.0, end=1.0, avg_logprob=-2.0)],
                {"language": "en"}
            )
            
            result = await engine.transcribe(str(audio_path))
            
            assert result.segments[0].confidence < 0.5
            assert result.confidence < 0.5
    
    # Test 6: Transcribe long audio in segments
    @pytest.mark.asyncio
    async def test_transcribe_long_audio(self, engine):
        """RED: Test long audio is processed efficiently."""
        audio_segments = ["segment1.mp3", "segment2.mp3", "segment3.mp3"]
        
        results = await engine.transcribe_long_video(audio_segments)
        
        assert isinstance(results, TranscriptionResult)
        assert results.full_text != ""
        # Should combine all segments
        assert len(results.segments) >= 3
    
    # Test 7: Handle transcription errors gracefully
    @pytest.mark.asyncio
    async def test_transcription_error_handling(self, engine):
        """RED: Test error handling for corrupt audio."""
        with pytest.raises(Exception):  # Specific exception type
            await engine.transcribe("nonexistent.mp3")
    
    # Test 8: Model size selection
    def test_model_size_selection(self):
        """RED: Test different model sizes can be selected."""
        tiny_engine = TranscriptionEngine(model_size="tiny")
        assert tiny_engine.model_size == "tiny"
        
        # Note: Don't actually load large models in tests
        # Just verify configuration
    
    # Test 9: GPU vs CPU device selection
    def test_device_selection(self):
        """RED: Test device (GPU/CPU) selection."""
        cpu_engine = TranscriptionEngine(device="cpu")
        assert cpu_engine.device == "cpu"
        
        # Mock CUDA availability
        with patch("torch.cuda.is_available", return_value=True):
            gpu_engine = TranscriptionEngine(device="cuda")
            assert gpu_engine.device == "cuda"


class TestTranscriptionResult:
    """Unit tests for TranscriptionResult dataclass."""
    
    def test_result_creation(self):
        """RED: Test creating TranscriptionResult."""
        segments = [
            TranscriptionSegment(
                text="Hello",
                start_time=0.0,
                end_time=1.0,
                confidence=0.95
            )
        ]
        
        result = TranscriptionResult(
            full_text="Hello",
            segments=segments,
            language="en",
            confidence=0.95
        )
        
        assert result.full_text == "Hello"
        assert len(result.segments) == 1
    
    def test_result_to_dict(self):
        """RED: Test converting result to dictionary."""
        result = TranscriptionResult(
            full_text="Test",
            segments=[],
            language="en",
            confidence=0.9
        )
        
        data = result.to_dict()
        
        assert data["full_text"] == "Test"
        assert data["language"] == "en"
        assert "confidence" in data
```

**Continue this pattern for:**
- `test_subtitle_extractor.py`
- `test_audio_extractor.py`
- `test_metadata_extractor.py`
- `test_comment_extractor.py`
- `test_chapter_detector.py`

---

## Phase 2: Integration Tests

### Integration Test: `tests/integration/test_youtube_full_pipeline.py`

```python
import pytest
from app.pipeline.youtube_pipeline import YouTubePipeline
from app.repositories.minio import MinIORepository
from app.repositories.postgres import PostgresRepository
from app.repositories.neo4j import Neo4jRepository


@pytest.mark.integration
class TestYouTubeFullPipeline:
    """Integration tests for complete YouTube processing pipeline."""
    
    @pytest.fixture(scope="class")
    async def pipeline(self):
        """Create pipeline with real services."""
        minio = MinIORepository()
        postgres = PostgresRepository()
        neo4j = Neo4jRepository()
        
        pipeline = YouTubePipeline(
            minio_repo=minio,
            postgres_repo=postgres,
            neo4j_repo=neo4j
        )
        
        yield pipeline
        
        # Cleanup
        await pipeline.cleanup()
    
    @pytest.mark.asyncio
    async def test_process_short_video(self, pipeline):
        """Test processing 5-min video end-to-end."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        result = await pipeline.process_video(url)
        
        # Verify all stages completed
        assert result.video_downloaded
        assert result.audio_extracted
        assert result.transcript_created
        assert result.metadata_extracted
        
        # Verify transcript quality
        assert len(result.transcript.full_text) > 100
        assert result.transcript.confidence > 0.85
        
        # Verify storage
        assert await pipeline.minio_repo.file_exists(result.video_path)
        assert await pipeline.minio_repo.file_exists(result.audio_path)
        
        # Verify database
        video_in_db = await pipeline.postgres_repo.get_video(result.video_id)
        assert video_in_db is not None
        assert video_in_db.title == result.title
        
        # Verify graph
        video_in_graph = await pipeline.neo4j_repo.get_node(
            "Video",
            {"video_id": result.video_id}
        )
        assert video_in_graph is not None
    
    @pytest.mark.asyncio
    async def test_process_video_with_subtitles(self, pipeline):
        """Test video that has subtitles (faster path)."""
        url = "https://www.youtube.com/watch?v=..."  # Video with subs
        
        result = await pipeline.process_video(url)
        
        # Should use subtitle extraction (fast)
        assert result.transcript.method == "ytdlp-subtitle"
        assert result.processing_time < 30  # Should be fast
    
    @pytest.mark.asyncio
    async def test_process_video_without_subtitles(self, pipeline):
        """Test video without subtitles (transcription path)."""
        url = "https://www.youtube.com/watch?v=..."  # No subs
        
        result = await pipeline.process_video(url)
        
        # Should use faster-whisper
        assert result.transcript.method == "faster-whisper"
        assert result.transcript.confidence > 0.90
    
    @pytest.mark.asyncio
    async def test_parallel_video_processing(self, pipeline):
        """Test processing multiple videos concurrently."""
        urls = [
            "https://www.youtube.com/watch?v=video1",
            "https://www.youtube.com/watch?v=video2",
            "https://www.youtube.com/watch?v=video3",
        ]
        
        results = await pipeline.process_batch(urls, max_concurrent=3)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_video_reprocessing(self, pipeline):
        """Test reprocessing video with better algorithm."""
        url = "https://www.youtube.com/watch?v=..."
        
        # First process
        result1 = await pipeline.process_video(url)
        
        # Reprocess with better transcription
        result2 = await pipeline.reprocess_video(
            url,
            force_whisper=True,
            model_size="large-v3"
        )
        
        # Should have better quality
        assert result2.transcript.confidence >= result1.transcript.confidence
        # Should use stored video (no re-download)
        assert result2.used_cached_video
```

---

## Phase 3: E2E Tests

### E2E Test: `tests/e2e/test_youtube_end_to_end.py`

```python
import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestYouTubeEndToEnd:
    """End-to-end tests simulating real user workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_full_workflow_import_search_retrieve(self, client):
        """Test complete workflow: import video → search → retrieve."""
        # Step 1: Import video
        response = client.post(
            "/api/import",
            json={"url": "https://www.youtube.com/watch?v=..."}
        )
        assert response.status_code == 200
        content_id = response.json()["content_id"]
        
        # Step 2: Wait for processing
        import time
        time.sleep(30)  # Or poll status endpoint
        
        # Step 3: Search for content
        response = client.get(
            "/api/search",
            params={"query": "machine learning", "limit": 10}
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert any(r["content_id"] == content_id for r in results)
        
        # Step 4: Retrieve full content
        response = client.get(f"/api/content/{content_id}")
        assert response.status_code == 200
        content = response.json()
        assert content["title"] is not None
        assert content["transcript"] is not None
        assert len(content["transcript"]) > 100
        
        # Step 5: Ask question (RAG)
        response = client.post(
            "/api/ask",
            json={
                "question": "What is discussed about neural networks?",
                "content_ids": [content_id]
            }
        )
        assert response.status_code == 200
        answer = response.json()["answer"]
        assert len(answer) > 50
        assert "citations" in response.json()
```

---

## Test Configuration

### conftest.py

```python
# tests/conftest.py
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_compose_file():
    """Path to docker-compose file."""
    return "docker-compose.yml"


@pytest.fixture(scope="session")
def docker_services():
    """Ensure Docker services are running."""
    # Will be handled by pytest-docker
    pass


# Markers
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
```

---

## Running Tests

### Quick Test (Unit Only)

```bash
# Run only unit tests (fast, no external deps)
pytest tests/unit -v

# Expected: ~200-300 tests, < 30 seconds
```

### Full Test Suite

```bash
# Run all tests
pytest tests/ -v

# Expected: ~300-400 tests, 5-10 minutes
```

### With Coverage

```bash
# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Target: >95% coverage
```

### Specific Test Categories

```bash
# Only integration tests
pytest -m integration -v

# Only E2E tests
pytest -m e2e -v

# Exclude slow tests
pytest -m "not slow" -v
```

---

## Coverage Goals

### Phase 1 Targets

```
Component                Coverage Target
─────────────────────────────────────────
VideoDownloader         95%
SubtitleExtractor       95%
AudioExtractor          95%
TranscriptionEngine     95%
MetadataExtractor       95%
─────────────────────────────────────────
Overall Phase 1         95%
```

### Final Targets

```
Module                  Coverage Target
─────────────────────────────────────────
app/pipeline/          95%+
app/repositories/      90%+
app/services/          90%+
app/core/              85%+
─────────────────────────────────────────
Overall System         95%+
```

---

## TDD Best Practices

### 1. Write Tests First
```python
# ❌ Don't do this
def implement_feature():
    # Write code
    pass

def test_feature():
    # Write test after
    pass

# ✅ Do this
def test_feature():
    # Write test first (RED)
    pass

def implement_feature():
    # Write code to pass test (GREEN)
    pass
```

### 2. One Test, One Assertion (mostly)
```python
# ❌ Too many assertions
def test_download():
    result = download_video(url)
    assert result.video_id == "abc"
    assert result.title == "Test"
    assert result.duration == 300
    assert result.file_size > 0
    # ... 10 more assertions

# ✅ Focused test
def test_download_extracts_video_id():
    result = download_video(url)
    assert result.video_id == "abc"

def test_download_extracts_title():
    result = download_video(url)
    assert result.title == "Test"
```

### 3. Use Descriptive Test Names
```python
# ❌ Vague
def test_download():
    pass

# ✅ Descriptive
def test_download_video_success_with_valid_url():
    pass

def test_download_video_raises_error_with_invalid_url():
    pass
```

### 4. Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange - Set up test data
    url = "https://youtube.com/watch?v=abc"
    downloader = VideoDownloader()
    
    # Act - Execute the behavior
    result = downloader.download(url)
    
    # Assert - Verify the outcome
    assert result.success
```

### 5. Mock External Dependencies
```python
# ✅ Mock external calls
@patch("yt_dlp.YoutubeDL")
def test_download(mock_ytdl):
    mock_ytdl.return_value.extract_info.return_value = {"id": "abc"}
    # Test uses mock, not real YouTube API
```

---

## Success Criteria

### Phase 1 Complete When:
- ✅ All unit tests written (200-300 tests)
- ✅ All unit tests passing (100%)
- ✅ Code coverage >95%
- ✅ Integration tests written (50-100 tests)
- ✅ Integration tests passing (100%)
- ✅ E2E tests written (5-10 tests)
- ✅ E2E tests passing (100%)
- ✅ CI/CD pipeline running tests automatically

### Quality Gates:
- ✅ No test skips or x-fails
- ✅ No flaky tests (retry 3x, all pass)
- ✅ Test execution time < 10 minutes
- ✅ All tests documented
- ✅ Code reviewed and approved

---

## Next Steps

1. **Review this TDD plan** with team
2. **Set up test environment** (Docker services)
3. **Start Day 1: VideoDownloader** (Red-Green-Refactor)
4. **Daily standup** to review progress
5. **Iterate** until Phase 1 complete

**Ready to start TDD development?** 🧪🚀
