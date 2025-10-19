# Production-Grade YouTube Processing Architecture

**Version:** 2.0 (Production-Ready)
**Date:** October 12, 2025
**Grade Target:** A (95%+ reliability, research-grade quality)

---

## Executive Summary

This architecture delivers a **production-grade YouTube processing system** that:
- ✅ **95%+ reliability** through multi-strategy transcription
- ✅ **Zero API lock-in** using local faster-whisper
- ✅ **Complete storage** in MinIO for archival and reprocessing
- ✅ **Long video support** for 3+ hour academic content
- ✅ **Community intelligence** through comment extraction
- ✅ **Research-grade metadata** with chapters, speakers, and structure

**Key Decision:** Use **faster-whisper** (local, free, fast) instead of OpenAI Whisper API.

---

## Core Architecture Principles

### 1. Storage-First Design
**Principle:** Download once, process forever

```
Video → MinIO Storage → Multiple Processing Pipelines
  ↓
  ├─→ Transcription (can retry/upgrade)
  ├─→ Chapter Detection (can add later)
  ├─→ Speaker Analysis (can enhance)
  └─→ Visual Analysis (future)
```

**Benefits:**
- Reprocess with better algorithms without re-downloading
- Archival for long-term research
- Enable future enhancements
- Offline processing capability

### 2. Multi-Strategy Transcription
**Principle:** Try cheap/fast first, fall back to expensive/slow

```
┌────────────────────────────────────────┐
│ Strategy 1: yt-dlp Subtitle Download  │ ← FREE, FAST (5 sec)
│ Success Rate: 70%                      │
└─────────────┬──────────────────────────┘
              ↓ (if fails)
┌────────────────────────────────────────┐
│ Strategy 2: faster-whisper (local)     │ ← FREE, RELIABLE (30 sec)
│ Success Rate: 99%                      │
└─────────────┬──────────────────────────┘
              ↓ (if needed)
┌────────────────────────────────────────┐
│ Strategy 3: OpenAI Whisper API         │ ← PAID, BEST QUALITY
│ For critical content only              │
└─────────────┬──────────────────────────┘
              ↓ (last resort)
┌────────────────────────────────────────┐
│ Strategy 4: Description Fallback       │ ← ALWAYS AVAILABLE
└────────────────────────────────────────┘
```

### 3. Async Job Queue System
**Principle:** Decouple request from processing

```
User Request → FastAPI → Redis Queue → Celery Workers → Update Status
                ↓                           ↓                ↓
           Job Created              Process Video      PostgreSQL
           (Pending)                (In Progress)      (Completed/Failed)
                ↓                           ↓                ↓
           Return Job ID            Track Progress    Notify User
```

**Benefits:**
- Non-blocking API (immediate response)
- Horizontal scaling (add more workers)
- Automatic retry on failure
- Persistent job state
- Priority queues (urgent vs batch)
- Progress tracking

### 4. Modular Processing Pipeline
**Principle:** Independent, composable processors

```python
VideoDownload → AudioExtraction → Transcription
     ↓              ↓                   ↓
   MinIO         MinIO              PostgreSQL
     ↓              ↓                   ↓
MetadataExtract  ChapterDetect    EntityExtraction
     ↓              ↓                   ↓
   Neo4j          Neo4j              Neo4j
```

Each stage is independent and can be:
- Retried independently (automatic or manual)
- Upgraded without affecting others
- Tested in isolation
- Parallelized for performance
- Tracked with status updates

---

## System Components

### Component 0: Job Queue & Status Tracking System

**Responsibility:** Manage async processing, track status, enable retries

```python
from celery import Celery
from enum import Enum
from datetime import datetime

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
    video_id: Optional[str]
    url: str
    status: JobStatus
    progress_percent: float
    current_stage: str
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Results
    video_path: Optional[str]
    audio_path: Optional[str]
    transcript_id: Optional[str]
    
    # Error handling
    error_message: Optional[str]
    retry_count: int = 0
    max_retries: int = 3
    
    # Priority
    priority: int = 5  # 1 (highest) to 10 (lowest)


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
        """Create new processing job.
        
        Args:
            url: YouTube URL to process
            priority: Job priority (1=highest, 10=lowest)
            user_id: User who initiated the job
            
        Returns:
            ProcessingJob with job_id
        """
        job = ProcessingJob(
            job_id=uuid4().hex,
            video_id=None,  # Set after download
            url=url,
            status=JobStatus.PENDING,
            progress_percent=0.0,
            current_stage="Created",
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None,
            priority=priority,
        )
        
        # Save to PostgreSQL
        await self.postgres.save_job(job)
        
        # Queue in Celery
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
        """Update job status and progress.
        
        Args:
            job_id: Job identifier
            status: New status
            progress: Progress percentage (0-100)
            stage: Human-readable stage description
            error: Error message if failed
        """
        await self.postgres.update_job(
            job_id=job_id,
            status=status.value,
            progress_percent=progress,
            current_stage=stage,
            error_message=error
        )
        
        # Also update Redis for real-time tracking
        await self.redis.hset(
            f"job:{job_id}",
            mapping={
                "status": status.value,
                "progress": progress,
                "stage": stage,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        # Publish to pub/sub for real-time updates
        await self.redis.publish(
            f"job_updates:{job_id}",
            json.dumps({
                "job_id": job_id,
                "status": status.value,
                "progress": progress,
                "stage": stage
            })
        )
    
    async def retry_job(
        self,
        job_id: str,
        manual: bool = False
    ) -> bool:
        """Retry failed job.
        
        Args:
            job_id: Job to retry
            manual: True if manually triggered, False if automatic
            
        Returns:
            True if retry queued, False if max retries exceeded
        """
        job = await self.get_job(job_id)
        if not job:
            return False
        
        # Check retry limit (higher for manual retries)
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
        
        # Reset status and requeue
        await self.update_job_status(
            job_id,
            JobStatus.RETRYING,
            0.0,
            f"Retrying (attempt {job.retry_count + 1}/{max_retries})"
        )
        
        # Requeue with higher priority for manual retries
        priority = 1 if manual else job.priority
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
        
        # Can only cancel if not completed
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


# Celery task
@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, job_id: str, url: str):
    """Celery task to process video.
    
    Args:
        job_id: Job identifier
        url: YouTube URL
    """
    job_manager = JobManager(postgres_repo, redis_client, celery_app)
    pipeline = YouTubePipeline(minio_repo, postgres_repo, neo4j_repo)
    
    try:
        # Update: Started
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.DOWNLOADING,
            10.0,
            "Downloading video"
        ))
        
        # Download video
        video_asset = asyncio.run(pipeline.download_video(url))
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.EXTRACTING_AUDIO,
            30.0,
            "Extracting audio"
        ))
        
        # Extract audio
        audio_asset = asyncio.run(pipeline.extract_audio(video_asset))
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.TRANSCRIBING,
            50.0,
            "Transcribing audio"
        ))
        
        # Transcribe
        transcript = asyncio.run(pipeline.transcribe(audio_asset))
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.EXTRACTING_METADATA,
            70.0,
            "Extracting metadata"
        ))
        
        # Extract metadata
        metadata = asyncio.run(pipeline.extract_metadata(url))
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.EXTRACTING_COMMENTS,
            85.0,
            "Extracting comments"
        ))
        
        # Extract comments
        comments = asyncio.run(pipeline.extract_comments(video_asset.video_id))
        
        # Complete
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            100.0,
            "Processing complete"
        ))
        
        return {
            "job_id": job_id,
            "video_id": video_asset.video_id,
            "status": "completed"
        }
        
    except Exception as e:
        # Log error
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        
        # Update status
        asyncio.run(job_manager.update_job_status(
            job_id,
            JobStatus.FAILED,
            0.0,
            f"Failed: {str(e)}",
            error=str(e)
        ))
        
        # Automatic retry
        asyncio.run(job_manager.retry_job(job_id, manual=False))
        
        raise
```

**Features:**
- ✅ Async job queue (Celery + Redis)
- ✅ Persistent status tracking (PostgreSQL)
- ✅ Real-time progress updates (Redis pub/sub)
- ✅ Automatic retry with exponential backoff
- ✅ Manual retry capability
- ✅ Job cancellation
- ✅ Priority queues (urgent vs batch)
- ✅ Job statistics and monitoring

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
    user_id VARCHAR(50),
    
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_video_id (video_id)
);
```

---

### Component 1: CRUD Operations & Data Lifecycle

**Responsibility:** Manage complete video lifecycle with cascading operations

```python
class VideoManager:
    """Manages complete video lifecycle."""
    
    def __init__(
        self,
        minio_repo: MinIORepository,
        postgres_repo: PostgresRepository,
        neo4j_repo: Neo4jRepository,
        redis_client: Redis
    ):
        self.minio = minio_repo
        self.postgres = postgres_repo
        self.neo4j = neo4j_repo
        self.redis = redis_client
    
    async def create_video(self, url: str, priority: int = 5) -> str:
        """Create new video processing job.
        
        Args:
            url: YouTube URL
            priority: Processing priority
            
        Returns:
            job_id for tracking
        """
        job_manager = JobManager(self.postgres, self.redis, celery_app)
        job = await job_manager.create_job(url, priority)
        return job.job_id
    
    async def get_video(self, video_id: str) -> Optional[VideoData]:
        """Get complete video data.
        
        Args:
            video_id: Video identifier
            
        Returns:
            VideoData with all associated information
        """
        # Get from cache first
        cached = await self.redis.get(f"video:{video_id}")
        if cached:
            return VideoData.parse_raw(cached)
        
        # Fetch from databases
        metadata = await self.postgres.get_video_metadata(video_id)
        if not metadata:
            return None
        
        transcript = await self.postgres.get_transcript(video_id)
        comments = await self.postgres.get_comments(video_id)
        chapters = await self.postgres.get_chapters(video_id)
        
        # Get graph data
        relationships = await self.neo4j.get_video_relationships(video_id)
        
        # Combine
        video_data = VideoData(
            metadata=metadata,
            transcript=transcript,
            comments=comments,
            chapters=chapters,
            relationships=relationships
        )
        
        # Cache for 1 hour
        await self.redis.setex(
            f"video:{video_id}",
            3600,
            video_data.json()
        )
        
        return video_data
    
    async def update_video(
        self,
        video_id: str,
        updates: dict
    ) -> bool:
        """Update video metadata.
        
        Args:
            video_id: Video to update
            updates: Fields to update
            
        Returns:
            True if successful
        """
        # Update PostgreSQL
        success = await self.postgres.update_video_metadata(video_id, updates)
        
        if success:
            # Invalidate cache
            await self.redis.delete(f"video:{video_id}")
            
            # Update Neo4j if needed
            if "title" in updates or "description" in updates:
                await self.neo4j.update_video_node(video_id, updates)
        
        return success
    
    async def delete_video(self, video_id: str, hard_delete: bool = False):
        """Delete video and all associated data.
        
        Args:
            video_id: Video to delete
            hard_delete: If True, permanently delete. If False, soft delete.
        """
        if hard_delete:
            await self._hard_delete_video(video_id)
        else:
            await self._soft_delete_video(video_id)
    
    async def _soft_delete_video(self, video_id: str):
        """Soft delete (mark as deleted, keep data)."""
        # Mark as deleted in PostgreSQL
        await self.postgres.execute(
            "UPDATE video_metadata SET deleted_at = NOW() WHERE video_id = $1",
            video_id
        )
        
        # Invalidate cache
        await self.redis.delete(f"video:{video_id}")
    
    async def _hard_delete_video(self, video_id: str):
        """Hard delete (permanently remove all data).
        
        Cascading delete order:
        1. Redis cache
        2. Neo4j relationships
        3. PostgreSQL data (transcripts, comments, chapters, metadata)
        4. MinIO storage (video, audio, thumbnails)
        """
        # Step 1: Clear cache
        await self.redis.delete(f"video:{video_id}")
        
        # Step 2: Delete from Neo4j (relationships first)
        await self.neo4j.execute(
            """
            MATCH (v:Video {video_id: $video_id})
            OPTIONAL MATCH (v)-[r]-()
            DELETE r, v
            """,
            {"video_id": video_id}
        )
        
        # Step 3: Delete from PostgreSQL (cascading)
        async with self.postgres.transaction():
            # Delete comments
            await self.postgres.execute(
                "DELETE FROM comments WHERE video_id = $1",
                video_id
            )
            
            # Delete chapters
            await self.postgres.execute(
                "DELETE FROM chapters WHERE video_id = $1",
                video_id
            )
            
            # Delete transcriptions
            await self.postgres.execute(
                "DELETE FROM transcriptions WHERE video_id = $1",
                video_id
            )
            
            # Delete processing jobs
            await self.postgres.execute(
                "DELETE FROM processing_jobs WHERE video_id = $1",
                video_id
            )
            
            # Delete metadata (last)
            await self.postgres.execute(
                "DELETE FROM video_metadata WHERE video_id = $1",
                video_id
            )
        
        # Step 4: Delete from MinIO
        try:
            # Delete video files
            await self.minio.delete_folder(f"youtube-videos/{video_id}")
            
            # Delete audio files
            await self.minio.delete_folder(f"youtube-audio/{video_id}")
            
            # Delete thumbnails
            await self.minio.delete_folder(f"youtube-thumbnails/{video_id}")
        except Exception as e:
            logger.error(f"Error deleting MinIO files for {video_id}: {e}")
            # Continue even if MinIO delete fails
    
    async def list_videos(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> list[VideoMetadata]:
        """List videos with filtering and pagination."""
        return await self.postgres.list_videos(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by
        )
    
    async def reprocess_video(
        self,
        video_id: str,
        force_whisper: bool = False,
        model_size: str = "large-v3"
    ) -> str:
        """Reprocess video with better algorithms.
        
        Uses stored video/audio, doesn't re-download.
        
        Args:
            video_id: Video to reprocess
            force_whisper: Force Whisper even if subtitles exist
            model_size: Whisper model size
            
        Returns:
            job_id for tracking
        """
        # Check if video exists in MinIO
        video_path = await self.minio.get_file_path(
            f"youtube-videos/{video_id}/original.mp4"
        )
        
        if not video_path:
            raise ValueError(f"Video {video_id} not found in storage")
        
        # Create reprocessing job
        job_manager = JobManager(self.postgres, self.redis, celery_app)
        job = await job_manager.create_job(
            url=f"reprocess:{video_id}",
            priority=3  # Higher priority
        )
        
        # Queue reprocessing task
        reprocess_video_task.apply_async(
            args=[job.job_id, video_id, force_whisper, model_size],
            priority=3
        )
        
        return job.job_id
```

**Features:**
- ✅ Complete CRUD operations
- ✅ Cascading deletes (all related data removed)
- ✅ Soft delete (mark as deleted, keep data)
- ✅ Hard delete (permanent removal)
- ✅ Reprocessing capability (uses stored files)
- ✅ Cache invalidation
- ✅ Transaction support

**Cascading Delete Order:**
```
1. Redis (cache)
   └─ video:{video_id}

2. Neo4j (graph)
   └─ (:Video {video_id})-[relationships]-()

3. PostgreSQL (relational, with foreign keys)
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

---

### Component 2: Video Downloader

**Responsibility:** Download and store complete videos

```python
class VideoDownloader:
    """Downloads videos using yt-dlp and stores in MinIO."""
    
    async def download_video(self, url: str, quality: str = "best") -> VideoAsset:
        """Download video and store in MinIO.
        
        Args:
            url: YouTube URL
            quality: Video quality (best, 1080p, 720p, 480p)
            
        Returns:
            VideoAsset with MinIO path and metadata
        """
        
    async def download_audio_only(self, url: str) -> AudioAsset:
        """Download audio track only (more efficient for transcription)."""
        
    async def download_with_resume(self, url: str) -> VideoAsset:
        """Download with resume capability for large files."""
```

**Features:**
- ✅ Automatic quality selection
- ✅ Resume capability for interrupted downloads
- ✅ Progress tracking
- ✅ Bandwidth throttling
- ✅ Automatic retry with exponential backoff
- ✅ Checksum verification

**Storage Structure:**
```
MinIO:
  youtube-videos/
    {video_id}/
      original.mp4          # Original video
      metadata.json         # yt-dlp info
      thumbnail.jpg         # Video thumbnail
      chapters.json         # Chapter markers
```

### Component 2: Subtitle Extractor

**Responsibility:** Extract subtitles using yt-dlp

```python
class SubtitleExtractor:
    """Extracts subtitles using yt-dlp (fastest, most reliable)."""
    
    async def extract_subtitles(
        self, 
        url: str, 
        languages: list[str] = ["en"]
    ) -> SubtitleResult:
        """Extract subtitles in specified languages.
        
        Priority:
        1. Manual subtitles (human-created)
        2. Auto-generated subtitles
        3. Translated subtitles
        """
        
    async def get_available_languages(self, url: str) -> list[str]:
        """List all available subtitle languages."""
        
    async def extract_with_timestamps(self, url: str) -> TimestampedSubtitles:
        """Extract subtitles with precise timestamps for syncing."""
```

**Features:**
- ✅ Multi-language support
- ✅ Timestamp preservation
- ✅ Format conversion (WebVTT, SRT, plain text)
- ✅ Confidence scoring (manual > auto)
- ✅ Fallback to auto-generated

### Component 3: Audio Extractor

**Responsibility:** Extract audio for transcription

```python
class AudioExtractor:
    """Extracts audio using ffmpeg."""
    
    async def extract_audio(
        self,
        video_path: str,
        output_format: str = "mp3",
        quality: str = "192k"
    ) -> AudioAsset:
        """Extract audio from video.
        
        Features:
        - Multiple format support (mp3, wav, flac)
        - Quality control
        - Noise reduction
        - Normalization
        """
        
    async def extract_audio_segments(
        self,
        video_path: str,
        segment_duration: int = 1800  # 30 minutes
    ) -> list[AudioAsset]:
        """Extract audio in segments for long videos."""
        
    async def split_by_silence(
        self,
        audio_path: str,
        min_silence_duration: float = 2.0
    ) -> list[AudioAsset]:
        """Smart segmentation at natural pause points."""
```

**Features:**
- ✅ Multiple audio formats
- ✅ Quality control
- ✅ Noise reduction (optional)
- ✅ Volume normalization
- ✅ Smart segmentation for long videos
- ✅ Parallel processing support

**Storage Structure:**
```
MinIO:
  youtube-audio/
    {video_id}/
      full_audio.mp3        # Complete audio track
      segments/             # For long videos
        segment_001.mp3
        segment_002.mp3
      metadata.json         # Audio properties
```

### Component 4: Transcription Engine

**Responsibility:** Transcribe audio using faster-whisper

```python
class TranscriptionEngine:
    """Transcribes audio using faster-whisper (local, fast, free)."""
    
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",  # or "cpu"
        compute_type: str = "float16"
    ):
        """Initialize faster-whisper model.
        
        Model sizes:
        - tiny: Fast, less accurate (good for drafts)
        - base: Balanced
        - small: Good quality, reasonable speed
        - medium: High quality
        - large-v3: Best quality (recommended)
        """
        
    async def transcribe(
        self,
        audio_path: str,
        language: str = "en"
    ) -> TranscriptionResult:
        """Transcribe audio file.
        
        Returns:
        - Full text
        - Segmented text with timestamps
        - Confidence scores per segment
        - Detected language
        """
        
    async def transcribe_with_diarization(
        self,
        audio_path: str
    ) -> DiarizedTranscription:
        """Transcribe with speaker identification.
        
        Uses pyannote.audio for speaker diarization.
        """
        
    async def transcribe_long_video(
        self,
        audio_segments: list[str]
    ) -> TranscriptionResult:
        """Transcribe long video in parallel segments."""
```

**Features:**
- ✅ Local processing (no API costs)
- ✅ GPU acceleration (4x faster)
- ✅ Multiple model sizes
- ✅ Confidence scoring
- ✅ Language detection
- ✅ Speaker diarization
- ✅ Timestamp precision
- ✅ Parallel processing for long videos

**Performance:**
- 15-min video: ~30 seconds (GPU)
- 1-hour video: ~2 minutes (GPU)
- 3-hour video: ~6 minutes (GPU, parallel)

**Storage Structure:**
```
PostgreSQL:
  transcriptions/
    video_id
    transcript_text (full)
    segments (JSONB with timestamps)
    confidence_score
    language
    speakers (JSONB)
    method (ytdlp-subtitle / faster-whisper / openai)
```

### Component 5: Metadata Extractor

**Responsibility:** Extract comprehensive metadata

```python
class MetadataExtractor:
    """Extracts comprehensive video metadata."""
    
    async def extract_full_metadata(self, url: str) -> VideoMetadata:
        """Extract all available metadata.
        
        Includes:
        - Basic info (title, author, duration, date)
        - Engagement (views, likes, comments)
        - Technical (resolution, codec, bitrate)
        - Content (tags, category, description)
        - Structure (chapters, timestamps)
        """
        
    async def extract_chapters(self, info: dict) -> list[Chapter]:
        """Extract chapter information with timestamps."""
        
    async def extract_engagement_metrics(self, video_id: str) -> Engagement:
        """Get view count, likes, comment count."""
```

**Metadata Structure:**
```python
@dataclass
class VideoMetadata:
    # Basic
    video_id: str
    title: str
    description: str
    duration_seconds: int
    published_at: datetime
    
    # Channel
    channel_id: str
    channel_name: str
    channel_url: str
    subscriber_count: int
    
    # Engagement
    view_count: int
    like_count: int
    comment_count: int
    
    # Content
    category: str
    tags: list[str]
    language: str
    
    # Technical
    resolution: str
    fps: int
    codec: str
    bitrate: int
    file_size: int
    
    # Structure
    chapters: list[Chapter]
    has_subtitles: bool
    subtitle_languages: list[str]
    
    # Storage
    video_path: str  # MinIO path
    audio_path: str  # MinIO path
    thumbnail_path: str
```

### Component 6: Comment Extractor

**Responsibility:** Extract YouTube comments with threading

```python
class CommentExtractor:
    """Extracts comments using YouTube Data API v3."""
    
    async def extract_comments(
        self,
        video_id: str,
        max_comments: int = 1000,
        include_replies: bool = True,
        sort_by: str = "relevance"  # or "time"
    ) -> CommentCollection:
        """Extract top-level comments and replies."""
        
    async def extract_with_sentiment(
        self,
        video_id: str
    ) -> SentimentAnalyzedComments:
        """Extract comments with sentiment analysis."""
        
    async def extract_topics(
        self,
        comments: list[Comment]
    ) -> list[Topic]:
        """Extract discussion topics using NLP."""
```

**Features:**
- ✅ Threaded comment extraction (replies)
- ✅ Sentiment analysis
- ✅ Topic modeling
- ✅ Author information
- ✅ Like counts
- ✅ Timestamp tracking
- ✅ Pagination handling

**Storage Structure:**
```
PostgreSQL:
  comments/
    video_id
    comment_id
    text
    author
    like_count
    published_at
    parent_comment_id (for replies)
    sentiment_score
    
Neo4j:
  (:Comment)-[:DISCUSSES]->(:Topic)
  (:Comment)-[:REPLIES_TO]->(:Comment)
  (:Video)-[:HAS_COMMENT]->(:Comment)
```

### Component 7: Chapter Detector

**Responsibility:** Detect and extract chapter structure

```python
class ChapterDetector:
    """Detects chapters from timestamps and content."""
    
    async def extract_from_description(
        self,
        description: str
    ) -> list[Chapter]:
        """Parse timestamp markers from description."""
        
    async def detect_from_transcript(
        self,
        transcript: TranscriptionResult
    ) -> list[Chapter]:
        """Detect topic changes in transcript."""
        
    async def detect_from_video(
        self,
        video_path: str
    ) -> list[Chapter]:
        """Detect scene changes for chapter boundaries."""
```

**Chapter Structure:**
```python
@dataclass
class Chapter:
    start_time: float  # seconds
    end_time: float
    title: str
    description: str
    thumbnail_path: str  # Keyframe at start
    topics: list[str]
    entities: list[str]
```

### Component 8: Long Video Processor

**Responsibility:** Handle videos > 1 hour

```python
class LongVideoProcessor:
    """Specialized processor for long-form content."""
    
    async def process_long_video(
        self,
        url: str,
        segment_duration: int = 1800  # 30 minutes
    ) -> ProcessedLongVideo:
        """Process video in segments with context preservation.
        
        Features:
        - Automatic segmentation
        - Parallel processing
        - Context preservation across segments
        - Smart merging of results
        """
        
    async def segment_by_chapters(
        self,
        video_path: str,
        chapters: list[Chapter]
    ) -> list[VideoSegment]:
        """Segment video by chapter boundaries (natural splits)."""
        
    async def process_segments_parallel(
        self,
        segments: list[VideoSegment]
    ) -> list[ProcessedSegment]:
        """Process multiple segments in parallel."""
```

**Features:**
- ✅ Automatic segmentation (30-min chunks)
- ✅ Smart segmentation (chapter boundaries, silence)
- ✅ Parallel processing
- ✅ Context preservation
- ✅ Progress tracking
- ✅ Partial result saving

---

## Processing Pipeline

### Standard Video Pipeline (< 1 hour)

```
1. Download Video (yt-dlp)
   ├─→ Store in MinIO: youtube-videos/{video_id}/original.mp4
   └─→ Extract metadata
   
2. Extract Subtitles (yt-dlp) [Strategy 1]
   ├─→ If available: Parse and store ✓
   └─→ If not available: Proceed to Strategy 2
   
3. Extract Audio (ffmpeg) [Strategy 2]
   ├─→ Store in MinIO: youtube-audio/{video_id}/full_audio.mp3
   └─→ Transcribe with faster-whisper
   
4. Store Transcript (PostgreSQL)
   ├─→ Full text
   ├─→ Segmented with timestamps
   └─→ Confidence scores
   
5. Extract Metadata (yt-dlp)
   ├─→ Store in PostgreSQL
   └─→ Create Neo4j nodes
   
6. Extract Comments (YouTube API)
   ├─→ Store in PostgreSQL
   └─→ Create Neo4j relationships
   
7. Detect Chapters
   ├─→ Parse from description
   └─→ Store in PostgreSQL + Neo4j
   
8. Extract Entities & Relations
   ├─→ NER on transcript
   └─→ Store in Neo4j graph
```

**Processing Time:**
- 15-min video: ~2 minutes total
- 30-min video: ~3 minutes total
- 1-hour video: ~5 minutes total

### Long Video Pipeline (> 1 hour)

```
1. Download Video
   └─→ Store in MinIO
   
2. Detect Chapters
   └─→ Identify natural segment boundaries
   
3. Segment Video
   ├─→ By chapters (if available)
   └─→ Or by 30-minute chunks
   
4. Process Segments in Parallel
   ├─→ Extract audio per segment
   ├─→ Transcribe per segment
   └─→ Extract entities per segment
   
5. Merge Results
   ├─→ Combine transcripts
   ├─→ Resolve cross-segment entities
   └─→ Build complete graph
   
6. Extract Global Metadata
   └─→ Comments, chapters, overall structure
```

**Processing Time:**
- 2-hour video: ~8 minutes (parallel)
- 3-hour video: ~12 minutes (parallel)
- 5-hour video: ~20 minutes (parallel)

---

## Technology Stack

### Core Technologies

**1. Video Download & Processing:**
- **yt-dlp** (2024.12.23) - Video download, metadata
- **ffmpeg** (6.1.1) - Audio extraction, video processing

**2. Transcription:**
- **faster-whisper** (1.0+) - Local transcription (PRIMARY)
- **openai** (1.109.1) - Fallback for critical content (SECONDARY)
- **pyannote.audio** (3.0+) - Speaker diarization

**3. Storage:**
- **MinIO** - Video/audio storage
- **PostgreSQL** - Metadata, transcripts, comments
- **Neo4j** - Graph relationships
- **Redis** - Caching, job queue

**4. NLP & Analysis:**
- **spaCy** - Entity extraction
- **transformers** - Sentiment analysis
- **scikit-learn** - Topic modeling

**5. API Integration:**
- **google-api-python-client** - YouTube Data API v3 (comments)

### Dependencies

```toml
[tool.poetry.dependencies]
# Existing
python = "^3.11"
yt-dlp = "^2024.12.23"
openai = "^1.109.1"

# New (Transcription)
faster-whisper = "^1.0.0"
pyannote-audio = "^3.0.0"
torch = "^2.0.0"  # For faster-whisper GPU

# New (NLP)
spacy = "^3.7.0"
transformers = "^4.35.0"
scikit-learn = "^1.3.0"

# New (YouTube API)
google-api-python-client = "^2.100.0"

# Existing (keep)
youtube-transcript-api = "^0.6.0"  # Fallback only
```

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...              # Fallback transcription
YOUTUBE_API_KEY=AIza...             # Comment extraction

# Optional
WHISPER_MODEL_SIZE=large-v3         # tiny/base/small/medium/large-v3
WHISPER_DEVICE=cuda                 # cuda/cpu
WHISPER_COMPUTE_TYPE=float16        # float16/int8/int8_float16

# Processing
MAX_SEGMENT_DURATION=1800           # 30 minutes
ENABLE_SPEAKER_DIARIZATION=true
ENABLE_COMMENT_EXTRACTION=true
MAX_COMMENTS_PER_VIDEO=1000

# Performance
MAX_PARALLEL_SEGMENTS=4
DOWNLOAD_BANDWIDTH_LIMIT=10M        # Optional throttling
```

### Storage Configuration

```yaml
minio:
  endpoint: localhost:9000
  buckets:
    - youtube-videos
    - youtube-audio
    - youtube-thumbnails
  retention: 90d  # Auto-delete after 90 days

postgresql:
  tables:
    - video_metadata
    - transcriptions
    - comments
    - chapters

neo4j:
  indexes:
    - Video.video_id
    - Content.content_id
    - Entity.name

redis:
  caches:
    - video-metadata (TTL: 24h)
    - transcripts (TTL: 7d)
```

---

## API Endpoints

### RESTful API for Video Management

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket
from fastapi.responses import StreamingResponse

app = FastAPI()

# ============================================================================
# Video Processing Endpoints
# ============================================================================

@app.post("/api/videos/process")
async def process_video(
    url: str,
    priority: int = 5,
    force_whisper: bool = False
) -> dict:
    """Start processing a YouTube video.
    
    Args:
        url: YouTube video URL
        priority: Processing priority (1=highest, 10=lowest)
        force_whisper: Force Whisper even if subtitles exist
        
    Returns:
        {"job_id": "...", "status": "queued"}
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    job_id = await video_manager.create_video(url, priority)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video processing started"
    }


@app.get("/api/videos/status/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Get processing job status.
    
    Returns:
        {
            "job_id": "...",
            "status": "transcribing",
            "progress": 65.5,
            "stage": "Transcribing audio",
            "video_id": "...",
            "estimated_completion": "2025-10-12T15:30:00Z"
        }
    """
    job_manager = JobManager(postgres_repo, redis_client, celery_app)
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": job.progress_percent,
        "stage": job.current_stage,
        "video_id": job.video_id,
        "created_at": job.created_at.isoformat(),
        "error": job.error_message
    }


@app.websocket("/api/videos/status/{job_id}/stream")
async def stream_job_status(websocket: WebSocket, job_id: str):
    """Stream real-time job status updates via WebSocket.
    
    Client receives JSON updates:
    {"status": "transcribing", "progress": 65.5, "stage": "..."}
    """
    await websocket.accept()
    
    # Subscribe to Redis pub/sub
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"job_updates:{job_id}")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json(json.loads(message["data"]))
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"job_updates:{job_id}")


# ============================================================================
# Video CRUD Endpoints
# ============================================================================

@app.get("/api/videos/{video_id}")
async def get_video(video_id: str, include_comments: bool = False) -> dict:
    """Get complete video data.
    
    Args:
        video_id: Video identifier
        include_comments: Include comments (expensive, default False)
        
    Returns:
        Complete video data with metadata, transcript, chapters
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    video_data = await video_manager.get_video(video_id)
    
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found")
    
    response = {
        "video_id": video_id,
        "metadata": video_data.metadata,
        "transcript": video_data.transcript,
        "chapters": video_data.chapters
    }
    
    if include_comments:
        response["comments"] = video_data.comments
    
    return response


@app.get("/api/videos")
async def list_videos(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "created_at_desc"
) -> dict:
    """List videos with pagination.
    
    Query params:
        status: Filter by status (completed, failed, processing)
        limit: Page size (max 1000)
        offset: Pagination offset
        order_by: Sort order (created_at_desc, views_desc, etc.)
        
    Returns:
        {"videos": [...], "total": 1234, "limit": 100, "offset": 0}
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    
    videos = await video_manager.list_videos(
        filters={"status": status} if status else None,
        limit=min(limit, 1000),
        offset=offset,
        order_by=order_by.replace("_", " ").upper()
    )
    
    total = await postgres_repo.count_videos(filters={"status": status} if status else None)
    
    return {
        "videos": [v.dict() for v in videos],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.patch("/api/videos/{video_id}")
async def update_video(video_id: str, updates: dict) -> dict:
    """Update video metadata.
    
    Body:
        {"title": "New Title", "tags": ["new", "tags"]}
        
    Returns:
        {"success": true, "video_id": "..."}
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    
    success = await video_manager.update_video(video_id, updates)
    
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"success": True, "video_id": video_id}


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str, hard_delete: bool = False) -> dict:
    """Delete video and all associated data.
    
    Query params:
        hard_delete: If true, permanently delete. If false, soft delete.
        
    Returns:
        {"success": true, "deleted": true, "video_id": "..."}
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    
    await video_manager.delete_video(video_id, hard_delete=hard_delete)
    
    return {
        "success": True,
        "deleted": True,
        "hard_delete": hard_delete,
        "video_id": video_id
    }


# ============================================================================
# Job Management Endpoints
# ============================================================================

@app.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str, manual: bool = True) -> dict:
    """Manually retry a failed job.
    
    Args:
        job_id: Job to retry
        manual: Mark as manual retry (higher priority)
        
    Returns:
        {"success": true, "job_id": "...", "retry_count": 2}
    """
    job_manager = JobManager(postgres_repo, redis_client, celery_app)
    
    success = await job_manager.retry_job(job_id, manual=manual)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry job (max retries exceeded or job not found)"
        )
    
    job = await job_manager.get_job(job_id)
    
    return {
        "success": True,
        "job_id": job_id,
        "retry_count": job.retry_count,
        "status": job.status.value
    }


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    """Cancel a pending or running job.
    
    Returns:
        {"success": true, "job_id": "...", "status": "cancelled"}
    """
    job_manager = JobManager(postgres_repo, redis_client, celery_app)
    
    success = await job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel job (not found or already completed)"
        )
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "cancelled"
    }


@app.get("/api/jobs/stats")
async def get_job_stats() -> dict:
    """Get aggregate job statistics.
    
    Returns:
        {
            "total": 1234,
            "completed": 1100,
            "failed": 50,
            "pending": 20,
            "processing": 64,
            "success_rate": 0.956,
            "avg_processing_time": 180.5
        }
    """
    job_manager = JobManager(postgres_repo, redis_client, celery_app)
    return await job_manager.get_job_stats()


# ============================================================================
# Reprocessing Endpoint
# ============================================================================

@app.post("/api/videos/{video_id}/reprocess")
async def reprocess_video(
    video_id: str,
    force_whisper: bool = True,
    model_size: str = "large-v3"
) -> dict:
    """Reprocess video with better algorithms (uses stored files).
    
    Args:
        video_id: Video to reprocess
        force_whisper: Force Whisper transcription
        model_size: Whisper model size
        
    Returns:
        {"job_id": "...", "video_id": "...", "status": "queued"}
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    
    try:
        job_id = await video_manager.reprocess_video(
            video_id,
            force_whisper=force_whisper,
            model_size=model_size
        )
        
        return {
            "job_id": job_id,
            "video_id": video_id,
            "status": "queued",
            "message": "Reprocessing started"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Download Endpoints (for accessing stored files)
# ============================================================================

@app.get("/api/videos/{video_id}/download/video")
async def download_video_file(video_id: str):
    """Download original video file.
    
    Returns:
        StreamingResponse with video file
    """
    video_manager = VideoManager(minio_repo, postgres_repo, neo4j_repo, redis_client)
    
    video_path = f"youtube-videos/{video_id}/original.mp4"
    
    if not await minio_repo.file_exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Stream from MinIO
    file_stream = await minio_repo.get_file_stream(video_path)
    
    return StreamingResponse(
        file_stream,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={video_id}.mp4"}
    )


@app.get("/api/videos/{video_id}/download/audio")
async def download_audio_file(video_id: str):
    """Download extracted audio file."""
    audio_path = f"youtube-audio/{video_id}/audio.mp3"
    
    if not await minio_repo.file_exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    file_stream = await minio_repo.get_file_stream(audio_path)
    
    return StreamingResponse(
        file_stream,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"attachment; filename={video_id}.mp3"}
    )
```

**API Features:**
- ✅ RESTful design
- ✅ WebSocket for real-time updates
- ✅ Pagination & filtering
- ✅ Complete CRUD operations
- ✅ Job management (retry, cancel)
- ✅ Reprocessing capability
- ✅ File downloads
- ✅ Statistics & monitoring

---

## Error Handling & Resilience

### Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
async def download_with_retry(url: str) -> VideoAsset:
    """Download with automatic retry."""
```

### Partial Success Handling

```python
class ProcessingResult:
    video_id: str
    status: ProcessingStatus
    
    # What succeeded
    video_downloaded: bool
    audio_extracted: bool
    transcript_created: bool
    metadata_extracted: bool
    comments_extracted: bool
    
    # Errors encountered
    errors: list[ProcessingError]
    warnings: list[str]
    
    # Allow partial success
    def is_usable(self) -> bool:
        """Check if result is usable despite errors."""
        return self.transcript_created and self.metadata_extracted
```

### Graceful Degradation

```python
# If subtitle extraction fails → Use faster-whisper
# If faster-whisper fails → Use OpenAI Whisper
# If OpenAI fails → Use description
# If comment extraction fails → Continue without comments
# If chapter detection fails → Continue without chapters
```

---

## Performance Optimization

### 1. Parallel Processing

```python
# Process multiple videos concurrently
async def process_batch(urls: list[str], max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(url: str):
        async with semaphore:
            return await process_video(url)
    
    return await asyncio.gather(*[process_with_limit(u) for u in urls])
```

### 2. Caching

```python
# Cache expensive operations
@cache(ttl=timedelta(hours=24))
async def get_video_metadata(video_id: str) -> VideoMetadata:
    """Cached metadata lookup."""
    
@cache(ttl=timedelta(days=7))
async def get_transcript(video_id: str) -> str:
    """Cached transcript lookup."""
```

### 3. Progressive Processing

```python
# Save intermediate results
async def process_video(url: str):
    # Step 1: Download (save immediately)
    video = await download_and_save(url)
    
    # Step 2: Extract audio (save immediately)
    audio = await extract_and_save_audio(video)
    
    # Step 3: Transcribe (save immediately)
    transcript = await transcribe_and_save(audio)
    
    # If process crashes, can resume from last saved step
```

---

## Quality Metrics

### Transcription Quality

```python
class TranscriptionQuality:
    wer: float  # Word Error Rate (target: < 5%)
    confidence: float  # Average confidence (target: > 0.90)
    completeness: float  # % of video transcribed (target: > 98%)
    method: str  # ytdlp-subtitle / faster-whisper / openai
```

### Processing Quality

```python
class ProcessingQuality:
    success_rate: float  # Target: > 95%
    avg_processing_time: float  # Per minute of video
    storage_efficiency: float  # MB per minute
    cost_per_video: float  # Target: < $0.05
```

### System Health

```python
class SystemHealth:
    queue_length: int  # Videos waiting
    processing_rate: float  # Videos per hour
    error_rate: float  # Target: < 5%
    storage_used: int  # GB
    gpu_utilization: float  # %
```

---

## Cost Analysis

### Per-Video Costs (using faster-whisper)

**15-minute video:**
- Storage: ~75MB video + ~5MB audio = 80MB (~$0.00)
- Transcription: FREE (local faster-whisper)
- Comments: FREE (within quota)
- **Total: ~$0.00**

**1-hour video:**
- Storage: ~300MB video + ~20MB audio = 320MB (~$0.00)
- Transcription: FREE (local faster-whisper)
- Comments: FREE (within quota)
- **Total: ~$0.00**

**3-hour video:**
- Storage: ~900MB video + ~60MB audio = 960MB (~$0.00)
- Transcription: FREE (local faster-whisper)
- Comments: FREE (within quota)
- **Total: ~$0.00**

### Monthly Costs (100 videos/month, avg 30 min)

**With faster-whisper (local):**
- Transcription: $0 (runs on your GPU)
- Storage: 100 × 150MB = 15GB ($0 with self-hosted MinIO)
- YouTube API: FREE (within quota)
- **Total: ~$0/month**

**With OpenAI Whisper (API) for comparison:**
- Transcription: 100 × 30min × $0.006/min = $180/month
- Storage: $0
- YouTube API: FREE
- **Total: ~$180/month**

**Savings: $180/month = $2,160/year by using faster-whisper!**

### Infrastructure Costs

**GPU for faster-whisper:**
- One-time: ~$500-1000 (NVIDIA RTX 3060 or better)
- ROI: 3-6 months vs OpenAI Whisper
- After ROI: Pure savings

**Or CPU-only:**
- Slower (4x) but still free
- Good for batch processing overnight

---

## Implementation Roadmap

### Phase 1: Core Pipeline (Week 1) - PRIORITY

**Goal:** Reliable transcription with storage

- [ ] Implement VideoDownloader with MinIO storage
- [ ] Implement SubtitleExtractor with yt-dlp
- [ ] Implement AudioExtractor with ffmpeg
- [ ] Implement TranscriptionEngine with faster-whisper
- [ ] Implement MetadataExtractor
- [ ] Write comprehensive tests (TDD)

**Deliverable:** 95% reliable transcription with complete storage

### Phase 2: Long Video Support (Week 2)

**Goal:** Handle 3+ hour videos

- [ ] Implement LongVideoProcessor
- [ ] Add segmentation logic
- [ ] Add parallel processing
- [ ] Add context preservation
- [ ] Test with 3-hour lecture videos

**Deliverable:** Process any length video efficiently

### Phase 3: Community Intelligence (Week 3)

**Goal:** Extract comment insights

- [ ] Implement CommentExtractor
- [ ] Add sentiment analysis
- [ ] Add topic modeling
- [ ] Create comment-transcript linking
- [ ] Test with high-engagement videos

**Deliverable:** Community insights from discussions

### Phase 4: Advanced Features (Week 4)

**Goal:** Research-grade capabilities

- [ ] Implement ChapterDetector
- [ ] Add speaker diarization
- [ ] Add visual analysis (keyframes)
- [ ] Implement quality scoring
- [ ] Performance optimization

**Deliverable:** Production-ready system

### Phase 5: Scale & Polish (Week 5-6)

**Goal:** Production deployment

- [ ] Add monitoring & alerting
- [ ] Implement job queue (Celery/Redis)
- [ ] Add admin dashboard
- [ ] Performance tuning
- [ ] Documentation
- [ ] Deployment automation

**Deliverable:** Deployed, monitored, maintained system

---

## Success Criteria

### Minimum Viable (Phase 1 Complete):
- ✅ 95%+ transcription success rate
- ✅ Complete storage in MinIO
- ✅ Processing time < 2 min per 15-min video
- ✅ All tests passing (>90% coverage)
- ✅ Cost near zero (using faster-whisper)

### Production Ready (Phase 4 Complete):
- ✅ 98%+ transcription success rate
- ✅ Long video support (3+ hours)
- ✅ Comment extraction working
- ✅ Chapter detection working
- ✅ Speaker diarization working
- ✅ Comprehensive monitoring
- ✅ Complete documentation

### Research Grade (Phase 5 Complete):
- ✅ 99%+ transcription success rate
- ✅ Multi-language support
- ✅ Advanced NLP features
- ✅ Visual analysis
- ✅ Real-time processing capability
- ✅ Production deployment

---

## Monitoring & Observability

### Key Metrics to Track

```python
# Processing Metrics
- videos_processed_total
- videos_processing_duration_seconds
- videos_failed_total
- transcription_success_rate

# Quality Metrics
- transcription_confidence_score
- transcription_word_error_rate
- audio_quality_score

# Resource Metrics
- gpu_utilization_percent
- storage_used_bytes
- queue_length
- processing_rate_per_hour

# Cost Metrics
- api_calls_total (YouTube, OpenAI)
- storage_cost_dollars
- processing_cost_dollars
```

### Alerting Rules

```yaml
alerts:
  - name: HighFailureRate
    condition: videos_failed_total / videos_processed_total > 0.05
    severity: warning
    
  - name: SlowProcessing
    condition: avg(videos_processing_duration_seconds) > 180
    severity: info
    
  - name: StorageFull
    condition: storage_used_bytes > 0.9 * storage_capacity_bytes
    severity: critical
```

---

## Next Steps

1. **Review this architecture** - Ensure it meets your requirements
2. **Set up TDD environment** - Create test structure
3. **Implement Phase 1** - Core pipeline (1 week)
4. **Validate with real videos** - Test with your use cases
5. **Iterate based on results** - Adjust as needed

This architecture provides a **production-grade foundation** that's:
- ✅ Reliable (95%+ success)
- ✅ Cost-effective ($0/month with faster-whisper)
- ✅ Scalable (handles any video length)
- ✅ Research-grade (comprehensive metadata)
- ✅ Maintainable (modular, tested)

**Ready to proceed with TDD implementation?** 🚀
