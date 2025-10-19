# Unified Content Ingestion Architecture

**Version:** 1.0  
**Date:** October 12, 2025  
**Status:** Proposed Standard for All Content Types

---

## 🎯 Executive Summary

**Problem**: The librarian system handles multiple content types (PDFs, web pages, YouTube videos), but each has been implemented differently. This creates:
- Inconsistent APIs
- Duplicated logic
- Hard to add new content types
- No unified status tracking
- No retry mechanisms for failures

**Solution**: Standardize ALL content ingestion using the **job queue + status tracking + CRUD** pattern developed for YouTube processing.

**Benefits**:
- ✅ **Consistent**: Same API for all content types
- ✅ **Scalable**: Add new content types easily
- ✅ **Resilient**: Automatic retry for all content
- ✅ **Observable**: Unified status tracking and monitoring
- ✅ **Maintainable**: Shared code, single source of truth
- ✅ **Testable**: Same test patterns everywhere

---

## 📊 Current State vs Proposed

### Current Architecture (Inconsistent)

```
┌─────────────────────────────────────────────────────────────┐
│  Different Implementations per Content Type                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PDF Processing:                                             │
│  ├── PDFDocumentExtractor                                    │
│  ├── ContentPipeline                                         │
│  └── Direct processing (no queue, no status tracking)       │
│                                                              │
│  Web Page Processing:                                        │
│  ├── HTMLWebExtractor                                        │
│  ├── ContentService.process_url()                           │
│  └── Direct processing (no queue, no status tracking)       │
│                                                              │
│  YouTube Processing:                                         │
│  ├── VideoManager (with job queue!)                          │
│  ├── Celery queue + Redis status tracking                   │
│  └── Retry + CRUD + WebSocket streaming                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘

❌ Problems:
- PDF and web processing blocks API requests
- No status tracking for PDFs or web pages
- No retry on failures
- No unified CRUD operations
- Different code paths for each content type
```

### Proposed Architecture (Unified)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Unified Content Ingestion System                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  JobManager (Shared Infrastructure)                         │    │
│  │  - Creates jobs for ANY content type                        │    │
│  │  - Tracks status (11 states)                                │    │
│  │  - Handles retry (automatic + manual)                       │    │
│  │  - Publishes real-time updates (Redis pub/sub)             │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ContentManager (Base Class)                                │    │
│  │  - Unified CRUD operations                                  │    │
│  │  - Caching (Redis)                                          │    │
│  │  - Cascading deletes                                        │    │
│  │  - Reprocessing support                                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                   ▲                                                  │
│                   │ Inherits                                         │
│         ┌─────────┴─────────┬─────────────┬──────────────┐         │
│         │                   │             │              │          │
│  ┌──────▼──────┐    ┌──────▼──────┐  ┌──▼──────┐  ┌────▼─────┐   │
│  │VideoManager │    │DocumentMgr  │  │WebPageMgr│  │PodcastMgr│   │
│  │(YouTube)    │    │(PDFs,DOCX) │  │(HTML,RSS)│  │(Audio)   │   │
│  └─────────────┘    └─────────────┘  └──────────┘  └──────────┘   │
│         │                   │             │              │          │
│         │                   │             │              │          │
│  ┌──────▼───────────────────▼─────────────▼──────────────▼──────┐ │
│  │  Celery Task Queue                                             │ │
│  │  - process_video_task()                                        │ │
│  │  - process_document_task()                                     │ │
│  │  - process_webpage_task()                                      │ │
│  │  - process_podcast_task()                                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

✅ Benefits:
- Single API for all content types
- Unified status tracking
- Automatic retry for everything
- Easy to add new content types
- Shared infrastructure reduces code duplication
```

---

## 🏗️ Unified Architecture Components

### Component 1: JobManager (Shared Infrastructure)

**Responsibility**: Manage processing jobs for ALL content types

**Code**:
```python
@dataclass
class ProcessingJob:
    """Universal job for any content type."""
    job_id: str
    content_id: Optional[str]  # video_id, document_id, webpage_id, etc.
    url: str
    content_type: ContentType  # VIDEO, DOCUMENT, WEBPAGE, PODCAST
    status: JobStatus
    progress_percent: float
    current_stage: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 5

class ContentType(Enum):
    """All supported content types."""
    VIDEO = "video"
    DOCUMENT = "document"
    WEBPAGE = "webpage"
    PODCAST = "podcast"
    EBOOK = "ebook"
    ACADEMIC_PAPER = "academic_paper"

class JobStatus(Enum):
    """Universal job statuses (same for all content types)."""
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"  # Video/Podcast only
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class JobManager:
    """Manages jobs for ALL content types."""
    
    async def create_job(
        self,
        url: str,
        content_type: ContentType,
        priority: int = 5
    ) -> ProcessingJob:
        """Create job for ANY content type."""
        job_id = f"{content_type.value}_{uuid4().hex[:12]}"
        
        job = ProcessingJob(
            job_id=job_id,
            content_id=None,  # Set after processing
            url=url,
            content_type=content_type,
            status=JobStatus.PENDING,
            progress_percent=0.0,
            current_stage="queued",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            error_message=None,
            priority=priority
        )
        
        # Save to PostgreSQL
        await self.postgres.save_job(job)
        
        # Queue in Celery (routes to appropriate task)
        task_name = f"process_{content_type.value}_task"
        self.celery.send_task(
            task_name,
            args=[job_id, url],
            priority=priority
        )
        
        # Update Redis for real-time access
        await self.redis.hset(
            f"job:{job_id}",
            mapping={
                "status": job.status.value,
                "progress": job.progress_percent,
                "content_type": content_type.value
            }
        )
        
        return job
    
    # ... other methods same as YouTube JobManager
```

---

### Component 2: ContentManager (Base Class)

**Responsibility**: Unified CRUD for all content types

**Code**:
```python
from abc import ABC, abstractmethod

class ContentManager(ABC):
    """
    Base class for managing ANY content type.
    
    Provides:
    - Unified CRUD operations
    - Caching (Redis)
    - Cascading deletes
    - Reprocessing support
    """
    
    def __init__(
        self,
        minio_repo: MinIORepository,
        postgres_repo: PostgresRepository,
        neo4j_repo: Neo4jRepository,
        redis_repo: RedisRepository,
        job_manager: JobManager,
        qdrant_repo: QdrantRepository
    ):
        self.minio = minio_repo
        self.postgres = postgres_repo
        self.neo4j = neo4j_repo
        self.redis = redis_repo
        self.job_manager = job_manager
        self.qdrant = qdrant_repo
    
    @property
    @abstractmethod
    def content_type(self) -> ContentType:
        """Return the content type this manager handles."""
        pass
    
    @property
    @abstractmethod
    def storage_prefix(self) -> str:
        """MinIO storage prefix (e.g., 'videos/', 'documents/')."""
        pass
    
    async def create_content(
        self,
        url: str,
        priority: int = 5,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Start processing content (universal for all types).
        
        Returns:
            job_id for tracking
        """
        # Create job via shared JobManager
        job = await self.job_manager.create_job(
            url=url,
            content_type=self.content_type,
            priority=priority
        )
        
        return job.job_id
    
    async def get_content(self, content_id: str) -> Optional[Dict]:
        """
        Get content by ID with caching.
        
        Pattern:
        1. Check Redis cache
        2. If miss, fetch from PostgreSQL
        3. Cache result
        """
        cache_key = f"{self.content_type.value}:{content_id}"
        
        # Try cache first
        cached = await self.redis.get_json(cache_key)
        if cached:
            return cached
        
        # Fetch from database
        content = await self._fetch_from_database(content_id)
        if not content:
            return None
        
        # Cache for 1 hour
        await self.redis.set_json(cache_key, content, ttl=3600)
        
        return content
    
    @abstractmethod
    async def _fetch_from_database(self, content_id: str) -> Optional[Dict]:
        """Fetch content from PostgreSQL (implementation-specific)."""
        pass
    
    async def update_content(
        self,
        content_id: str,
        updates: Dict
    ) -> bool:
        """Update content metadata."""
        # Update PostgreSQL
        success = await self._update_in_database(content_id, updates)
        if not success:
            return False
        
        # Invalidate cache
        cache_key = f"{self.content_type.value}:{content_id}"
        await self.redis.delete(cache_key)
        
        # Update Neo4j if needed
        await self._update_in_neo4j(content_id, updates)
        
        return True
    
    @abstractmethod
    async def _update_in_database(
        self,
        content_id: str,
        updates: Dict
    ) -> bool:
        """Update in PostgreSQL (implementation-specific)."""
        pass
    
    async def _update_in_neo4j(
        self,
        content_id: str,
        updates: Dict
    ):
        """Update Neo4j node (can be overridden)."""
        await self.neo4j.execute(
            f"""
            MATCH (c:{self.content_type.value.capitalize()} {{content_id: $content_id}})
            SET c += $updates
            """,
            {"content_id": content_id, "updates": updates}
        )
    
    async def delete_content(
        self,
        content_id: str,
        hard_delete: bool = False
    ):
        """Delete content with cascading (soft or hard)."""
        if hard_delete:
            await self._hard_delete_content(content_id)
        else:
            await self._soft_delete_content(content_id)
    
    async def _soft_delete_content(self, content_id: str):
        """Soft delete: mark as deleted, keep data."""
        await self.postgres.execute(
            f"""
            UPDATE {self._table_name()}
            SET deleted_at = NOW()
            WHERE content_id = $1
            """,
            content_id
        )
        
        # Invalidate cache
        cache_key = f"{self.content_type.value}:{content_id}"
        await self.redis.delete(cache_key)
    
    async def _hard_delete_content(self, content_id: str):
        """
        Hard delete: cascading removal from all systems.
        
        Order: Redis → Neo4j → PostgreSQL → Qdrant → MinIO
        """
        # 1. Clear cache
        cache_key = f"{self.content_type.value}:{content_id}"
        await self.redis.delete(cache_key)
        
        # 2. Delete from Neo4j
        await self.neo4j.execute(
            f"""
            MATCH (c:{self.content_type.value.capitalize()} {{content_id: $content_id}})
            DETACH DELETE c
            """,
            {"content_id": content_id}
        )
        
        # 3. Delete from PostgreSQL (with transaction)
        async with self.postgres.transaction():
            await self._delete_from_database(content_id)
        
        # 4. Delete from Qdrant
        await self.qdrant.delete_by_metadata(
            "content",
            {"content_id": content_id}
        )
        
        # 5. Delete from MinIO
        await self.minio.delete_folder(
            f"{self.storage_prefix}{content_id}"
        )
    
    @abstractmethod
    async def _delete_from_database(self, content_id: str):
        """Delete from PostgreSQL tables (implementation-specific)."""
        pass
    
    @abstractmethod
    def _table_name(self) -> str:
        """Primary table name for this content type."""
        pass
    
    async def reprocess_content(
        self,
        content_id: str,
        force: bool = False
    ) -> str:
        """
        Reprocess content using stored files.
        
        Returns:
            job_id for new processing job
        """
        # Get original URL
        content = await self.get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")
        
        # Check if files stored
        has_files = await self._has_stored_files(content_id)
        if not has_files and not force:
            raise ValueError(
                f"No stored files for {content_id}. "
                "Use force=True to re-download."
            )
        
        # Create reprocessing job
        job = await self.job_manager.create_job(
            url=content["url"],
            content_type=self.content_type,
            priority=1  # High priority for reprocessing
        )
        
        return job.job_id
    
    @abstractmethod
    async def _has_stored_files(self, content_id: str) -> bool:
        """Check if original files are stored in MinIO."""
        pass
    
    async def list_content(
        self,
        filters: Optional[Dict] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """List content with filtering."""
        return await self._list_from_database(filters, limit, offset)
    
    @abstractmethod
    async def _list_from_database(
        self,
        filters: Optional[Dict],
        limit: int,
        offset: int
    ) -> List[Dict]:
        """List from PostgreSQL (implementation-specific)."""
        pass
```

---

### Component 3: Concrete Implementations

#### VideoManager (YouTube)

```python
class VideoManager(ContentManager):
    """Manages YouTube videos (already implemented)."""
    
    @property
    def content_type(self) -> ContentType:
        return ContentType.VIDEO
    
    @property
    def storage_prefix(self) -> str:
        return "youtube-videos/"
    
    async def _fetch_from_database(self, content_id: str) -> Optional[Dict]:
        """Fetch video metadata from PostgreSQL."""
        return await self.postgres.execute(
            """
            SELECT v.*, t.text as transcript
            FROM video_metadata v
            LEFT JOIN transcriptions t ON v.video_id = t.video_id
            WHERE v.video_id = $1 AND v.deleted_at IS NULL
            """,
            content_id
        )
    
    # ... other implementations
```

#### DocumentManager (PDFs, DOCX, etc.)

```python
class DocumentManager(ContentManager):
    """Manages documents (PDFs, DOCX, TXT, etc.)."""
    
    @property
    def content_type(self) -> ContentType:
        return ContentType.DOCUMENT
    
    @property
    def storage_prefix(self) -> str:
        return "documents/"
    
    async def _fetch_from_database(self, content_id: str) -> Optional[Dict]:
        """Fetch document metadata from PostgreSQL."""
        return await self.postgres.execute(
            """
            SELECT d.*, c.chunks
            FROM document_metadata d
            LEFT JOIN document_chunks c ON d.document_id = c.document_id
            WHERE d.document_id = $1 AND d.deleted_at IS NULL
            """,
            content_id
        )
    
    async def _update_in_database(
        self,
        content_id: str,
        updates: Dict
    ) -> bool:
        """Update document metadata in PostgreSQL."""
        await self.postgres.execute(
            """
            UPDATE document_metadata
            SET title = COALESCE($2, title),
                author = COALESCE($3, author),
                updated_at = NOW()
            WHERE document_id = $1
            """,
            content_id,
            updates.get("title"),
            updates.get("author")
        )
        return True
    
    async def _delete_from_database(self, content_id: str):
        """Delete document and related data from PostgreSQL."""
        await self.postgres.execute(
            "DELETE FROM document_chunks WHERE document_id = $1",
            content_id
        )
        await self.postgres.execute(
            "DELETE FROM document_metadata WHERE document_id = $1",
            content_id
        )
    
    def _table_name(self) -> str:
        return "document_metadata"
    
    async def _has_stored_files(self, content_id: str) -> bool:
        """Check if original document is stored."""
        return await self.minio.file_exists(
            f"{self.storage_prefix}{content_id}/original.pdf"
        )
    
    async def _list_from_database(
        self,
        filters: Optional[Dict],
        limit: int,
        offset: int
    ) -> List[Dict]:
        """List documents with filtering."""
        query = "SELECT * FROM document_metadata WHERE deleted_at IS NULL"
        
        if filters:
            if "author" in filters:
                query += f" AND author = '{filters['author']}'"
            if "min_pages" in filters:
                query += f" AND page_count >= {filters['min_pages']}"
        
        query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
        
        return await self.postgres.execute(query)
```

#### WebPageManager (HTML, RSS, etc.)

```python
class WebPageManager(ContentManager):
    """Manages web pages and RSS feeds."""
    
    @property
    def content_type(self) -> ContentType:
        return ContentType.WEBPAGE
    
    @property
    def storage_prefix(self) -> str:
        return "webpages/"
    
    async def _fetch_from_database(self, content_id: str) -> Optional[Dict]:
        """Fetch webpage metadata from PostgreSQL."""
        return await self.postgres.execute(
            """
            SELECT w.*, c.content as html_content
            FROM webpage_metadata w
            LEFT JOIN webpage_content c ON w.webpage_id = c.webpage_id
            WHERE w.webpage_id = $1 AND w.deleted_at IS NULL
            """,
            content_id
        )
    
    # ... similar implementations to DocumentManager
```

#### PodcastManager (Audio files)

```python
class PodcastManager(ContentManager):
    """Manages podcasts and audio files."""
    
    @property
    def content_type(self) -> ContentType:
        return ContentType.PODCAST
    
    @property
    def storage_prefix(self) -> str:
        return "podcasts/"
    
    async def _fetch_from_database(self, content_id: str) -> Optional[Dict]:
        """Fetch podcast metadata from PostgreSQL."""
        return await self.postgres.execute(
            """
            SELECT p.*, t.text as transcript
            FROM podcast_metadata p
            LEFT JOIN transcriptions t ON p.podcast_id = t.content_id
            WHERE p.podcast_id = $1 AND p.deleted_at IS NULL
            """,
            content_id
        )
    
    # ... similar implementations, but with transcription support
```

---

### Component 4: Unified Celery Tasks

**All content types use same pattern**:

```python
# app/workers/content_tasks.py

@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, job_id: str, url: str):
    """Process YouTube video (existing implementation)."""
    # ... existing YouTube processing logic

@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, job_id: str, url: str):
    """Process document (PDF, DOCX, etc.)."""
    try:
        # Update status: downloading
        job_manager.update_job_status(
            job_id,
            JobStatus.DOWNLOADING,
            10.0,
            "Downloading document"
        )
        
        # Download document
        doc_path = await download_document(url)
        document_id = extract_document_id(url, doc_path)
        
        # Update status: extracting
        job_manager.update_job_status(
            job_id,
            JobStatus.EXTRACTING,
            30.0,
            "Extracting text"
        )
        
        # Extract text (PDFDocumentExtractor)
        extractor = PDFDocumentExtractor()
        raw_content = await extractor.extract(url)
        
        # Update status: processing
        job_manager.update_job_status(
            job_id,
            JobStatus.PROCESSING,
            50.0,
            "Processing content"
        )
        
        # Transform content
        transformer = BasicContentTransformer()
        processed = await transformer.transform(raw_content)
        
        # Update status: embedding
        job_manager.update_job_status(
            job_id,
            JobStatus.EMBEDDING,
            70.0,
            "Generating embeddings"
        )
        
        # Generate embeddings
        embeddings = await generate_embeddings(processed.summary)
        
        # Update status: storing
        job_manager.update_job_status(
            job_id,
            JobStatus.STORING,
            90.0,
            "Storing data"
        )
        
        # Store in all systems
        await store_document(
            document_id,
            raw_content,
            processed,
            embeddings,
            doc_path
        )
        
        # Complete
        job_manager.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            100.0,
            "Processing complete"
        )
        
    except Exception as e:
        # Handle failure with retry
        job_manager.update_job_status(
            job_id,
            JobStatus.FAILED,
            0.0,
            f"Error: {str(e)}"
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=4 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def process_webpage_task(self, job_id: str, url: str):
    """Process web page (similar pattern)."""
    # ... similar implementation

@celery_app.task(bind=True, max_retries=3)
def process_podcast_task(self, job_id: str, url: str):
    """Process podcast (similar pattern + transcription)."""
    # ... similar implementation with transcription step
```

---

## 🔌 Unified API Endpoints

**Single consistent API for ALL content types**:

```python
# app/api/content_endpoints.py

from fastapi import APIRouter, HTTPException
from enum import Enum

router = APIRouter(prefix="/api/content", tags=["content"])

class ContentTypeEnum(str, Enum):
    VIDEO = "video"
    DOCUMENT = "document"
    WEBPAGE = "webpage"
    PODCAST = "podcast"

# ============================================================
# CREATE: Start processing any content type
# ============================================================

@router.post("/process")
async def process_content(
    url: str,
    content_type: ContentTypeEnum,
    priority: int = 5
):
    """
    Universal endpoint to process ANY content type.
    
    Examples:
        - Video: /api/content/process?url=https://youtube.com/...&content_type=video
        - PDF: /api/content/process?url=https://example.com/doc.pdf&content_type=document
        - Webpage: /api/content/process?url=https://example.com&content_type=webpage
    """
    manager = get_manager(content_type)
    job_id = await manager.create_content(url, priority)
    
    return {
        "job_id": job_id,
        "content_type": content_type,
        "status": "queued",
        "message": f"Processing started for {content_type}"
    }

# ============================================================
# READ: Get content by ID
# ============================================================

@router.get("/{content_type}/{content_id}")
async def get_content(
    content_type: ContentTypeEnum,
    content_id: str
):
    """
    Universal endpoint to get ANY content type.
    
    Examples:
        - Video: /api/content/video/dQw4w9WgXcQ
        - Document: /api/content/document/abc123
        - Webpage: /api/content/webpage/xyz789
    """
    manager = get_manager(content_type)
    content = await manager.get_content(content_id)
    
    if not content:
        raise HTTPException(404, f"{content_type} not found")
    
    return content

# ============================================================
# UPDATE: Update content metadata
# ============================================================

@router.patch("/{content_type}/{content_id}")
async def update_content(
    content_type: ContentTypeEnum,
    content_id: str,
    updates: dict
):
    """Universal endpoint to update ANY content type."""
    manager = get_manager(content_type)
    success = await manager.update_content(content_id, updates)
    
    if not success:
        raise HTTPException(404, f"{content_type} not found")
    
    return {"success": True, "content_id": content_id}

# ============================================================
# DELETE: Delete content
# ============================================================

@router.delete("/{content_type}/{content_id}")
async def delete_content(
    content_type: ContentTypeEnum,
    content_id: str,
    hard_delete: bool = False
):
    """Universal endpoint to delete ANY content type."""
    manager = get_manager(content_type)
    await manager.delete_content(content_id, hard_delete)
    
    return {
        "deleted": True,
        "content_id": content_id,
        "hard_delete": hard_delete
    }

# ============================================================
# LIST: List content with filters
# ============================================================

@router.get("/{content_type}")
async def list_content(
    content_type: ContentTypeEnum,
    limit: int = 50,
    offset: int = 0,
    # Dynamic filters
    status: Optional[str] = None,
    author: Optional[str] = None,
    min_duration: Optional[int] = None
):
    """Universal endpoint to list ANY content type."""
    filters = {}
    if status:
        filters["status"] = status
    if author:
        filters["author"] = author
    if min_duration:
        filters["min_duration"] = min_duration
    
    manager = get_manager(content_type)
    content_list = await manager.list_content(filters, limit, offset)
    
    return {
        "content_type": content_type,
        "total": len(content_list),
        "items": content_list
    }

# ============================================================
# JOB STATUS: Track processing (same for all types)
# ============================================================

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Universal job status endpoint."""
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "job_id": job.job_id,
        "content_type": job.content_type,
        "status": job.status,
        "progress": job.progress_percent,
        "current_stage": job.current_stage,
        "error": job.error_message
    }

@router.websocket("/status/{job_id}/stream")
async def stream_job_status(websocket: WebSocket, job_id: str):
    """Universal WebSocket for real-time status (all content types)."""
    await websocket.accept()
    
    # Subscribe to Redis pub/sub
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"job:{job_id}")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
                
                if data["status"] in ["completed", "failed", "cancelled"]:
                    break
    finally:
        await pubsub.unsubscribe(f"job:{job_id}")
        await websocket.close()

# ============================================================
# REPROCESS: Reprocess content
# ============================================================

@router.post("/{content_type}/{content_id}/reprocess")
async def reprocess_content(
    content_type: ContentTypeEnum,
    content_id: str,
    force: bool = False
):
    """Universal endpoint to reprocess ANY content type."""
    manager = get_manager(content_type)
    job_id = await manager.reprocess_content(content_id, force)
    
    return {
        "job_id": job_id,
        "content_id": content_id,
        "status": "queued",
        "message": f"Reprocessing started for {content_type}"
    }

# ============================================================
# Helper function
# ============================================================

def get_manager(content_type: ContentTypeEnum) -> ContentManager:
    """Factory function to get appropriate manager."""
    managers = {
        ContentTypeEnum.VIDEO: video_manager,
        ContentTypeEnum.DOCUMENT: document_manager,
        ContentTypeEnum.WEBPAGE: webpage_manager,
        ContentTypeEnum.PODCAST: podcast_manager,
    }
    return managers[content_type]
```

---

## 🗄️ Unified Database Schema

**Single `processing_jobs` table for all content types**:

```sql
CREATE TABLE processing_jobs (
    -- Universal fields
    job_id VARCHAR(32) PRIMARY KEY,
    content_id VARCHAR(50),         -- video_id, document_id, webpage_id, etc.
    url TEXT NOT NULL,
    content_type VARCHAR(20) NOT NULL,  -- 'video', 'document', 'webpage', 'podcast'
    
    -- Status tracking
    status VARCHAR(20) NOT NULL,
    progress_percent FLOAT DEFAULT 0.0,
    current_stage TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- File paths (content-type specific)
    file_paths JSONB,  -- {"original": "...", "audio": "...", "thumbnail": "..."}
    
    -- Error handling
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    
    -- Metadata
    priority INT DEFAULT 5,
    user_id VARCHAR(50),
    metadata JSONB,  -- Content-type specific metadata
    
    -- Indexes
    INDEX idx_content_type (content_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_content_id (content_id)
);

-- Content-specific tables (existing + new)
CREATE TABLE video_metadata (...);        -- YouTube videos
CREATE TABLE document_metadata (...);     -- PDFs, DOCX
CREATE TABLE webpage_metadata (...);      -- Web pages
CREATE TABLE podcast_metadata (...);      -- Podcasts
```

---

## 🧪 Unified Testing Strategy

**Same test patterns for ALL content types**:

### Unit Tests (Per Content Type)

```python
# tests/unit/managers/test_document_manager.py

class TestDocumentManager:
    """Unit tests for DocumentManager (mirrors VideoManager tests)."""
    
    @pytest.mark.asyncio
    async def test_create_document(self):
        """Test creating document starts job."""
        manager = DocumentManager(...)
        
        job_id = await manager.create_content(
            "https://example.com/paper.pdf",
            priority=5
        )
        
        assert job_id.startswith("document_")
        # Verify job created in PostgreSQL
        # Verify Celery task queued
    
    @pytest.mark.asyncio
    async def test_get_document_from_cache(self):
        """Test getting document from cache."""
        # Same pattern as VideoManager test
    
    @pytest.mark.asyncio
    async def test_hard_delete_document(self):
        """Test cascading delete removes all data."""
        # Same pattern as VideoManager test
    
    # ... 9 tests total (same as VideoManager)
```

### Integration Tests (Cross-System)

```python
# tests/integration/test_unified_content_processing.py

@pytest.mark.integration
class TestUnifiedContentProcessing:
    """Test all content types use same infrastructure."""
    
    @pytest.mark.asyncio
    async def test_process_multiple_content_types(self):
        """Test processing video + document + webpage simultaneously."""
        # Create jobs for different content types
        video_job = await video_manager.create_content(
            "https://youtube.com/watch?v=..."
        )
        doc_job = await document_manager.create_content(
            "https://example.com/paper.pdf"
        )
        webpage_job = await webpage_manager.create_content(
            "https://example.com/article"
        )
        
        # All should be in same queue
        jobs = await job_manager.list_jobs()
        assert len(jobs) >= 3
        
        # Wait for processing
        await asyncio.sleep(60)
        
        # All should complete
        for job_id in [video_job, doc_job, webpage_job]:
            job = await job_manager.get_job(job_id)
            assert job.status == JobStatus.COMPLETED
```

---

## 📈 Benefits Summary

### 1. **Consistency**
- ✅ Same API for all content types
- ✅ Same status tracking
- ✅ Same retry logic
- ✅ Same CRUD operations
- ✅ Same monitoring

### 2. **Scalability**
- ✅ Add new content types by extending `ContentManager`
- ✅ Horizontal scaling (add Celery workers)
- ✅ Independent processing per content type

### 3. **Maintainability**
- ✅ Single source of truth (`JobManager`, `ContentManager`)
- ✅ Shared code reduces duplication
- ✅ Easier to debug (same patterns everywhere)

### 4. **Observability**
- ✅ Unified monitoring dashboard
- ✅ Single queue to monitor
- ✅ Consistent metrics for all content types

### 5. **User Experience**
- ✅ Same interface for all content
- ✅ Real-time status updates for everything
- ✅ Consistent error messages
- ✅ Unified search and filtering

---

## 🚀 Migration Plan

### Phase 1: Add Infrastructure (Week 1)
1. ✅ Implement `JobManager` (already done for YouTube)
2. ✅ Create `ContentManager` base class
3. ✅ Update database schema
4. ✅ Set up Celery + Redis

### Phase 2: Migrate Existing Content (Week 2)
1. 🔄 Wrap `PDFDocumentExtractor` in `DocumentManager`
2. 🔄 Wrap `HTMLWebExtractor` in `WebPageManager`
3. 🔄 Update existing APIs to use managers
4. 🔄 Add job queue for documents and web pages

### Phase 3: Add New Content Types (Week 3+)
1. 📋 Implement `PodcastManager`
2. 📋 Implement `EbookManager`
3. 📋 Implement `AcademicPaperManager`

### Phase 4: Testing & Optimization (Ongoing)
1. 📋 Write unit tests for all managers
2. 📋 Write integration tests
3. 📋 Performance testing
4. 📋 Monitor and optimize

---

## 🎯 Success Criteria

**System is unified when**:
- ✅ All content types use `JobManager`
- ✅ All content types use `ContentManager` pattern
- ✅ Single API for all content types
- ✅ Unified status tracking
- ✅ Unified retry logic
- ✅ Unified CRUD operations
- ✅ >95% test coverage for all content types
- ✅ Same patterns in all tests

---

## 📚 Related Documentation

- `YOUTUBE-PRODUCTION-ARCHITECTURE.md` - Original design (video-specific)
- `YOUTUBE-TDD-PLAN.md` - Testing patterns (reusable for all content)
- `architecture.md` - Overall system architecture
- `FASTAPI-INGESTION-ARCHITECTURE.md` - API design patterns

---

## 🎉 Conclusion

**YES** - The job queue + status tracking + CRUD pattern should be the **standard way** to handle ALL content in the librarian system!

**Key Benefits**:
1. **One API** for everything (videos, documents, web pages, podcasts)
2. **One queue** for all processing
3. **One status tracker** for all jobs
4. **One retry mechanism** for all failures
5. **One CRUD pattern** for all content types

**Implementation**: Extend `ContentManager` base class for each new content type. All infrastructure is shared.

**Result**: Scalable, maintainable, testable system with consistent UX! 🚀
