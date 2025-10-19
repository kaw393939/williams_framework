# Williams Librarian - Definitive Architecture

**Version:** 2.0  
**Last Updated:** October 12, 2025  
**Status:** Definitive Reference

---

## 🎯 Executive Summary

Williams Librarian is a **knowledge amplification system** that both **ingests content** and **generates new content** using a bidirectional plugin architecture with complete provenance tracking.

### Core Capabilities

```
Import (Ingest)                    Export (Generate)
─────────────────                  ─────────────────
External → Library                 Library → External

• PDFs                             • Podcasts
• Web Pages                        • Videos (Kling/Veo3)
• YouTube Videos                   • Ebooks
• Academic Papers                  • Flashcards
• Documents                        • Reports
                                   • Newsletters
```

### Key Differentiators

1. **Bidirectional**: Only platform that both imports AND generates
2. **Provenance**: Complete genealogy tracking (no competitor has this)
3. **Plugin-Based**: Extensible architecture for any content type
4. **Async Processing**: Job queue with real-time status tracking
5. **Multi-Modal**: Text, audio, video, structured data

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
│                    (REST API + WebSocket)                        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
         ┌──────────▼──────────┐   ┌─────────▼──────────┐
         │  Import Plugins     │   │  Export Plugins     │
         │  (Ingestion)        │   │  (Generation)       │
         └──────────┬──────────┘   └─────────┬──────────┘
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Job Manager         │
                    │  (Celery + Redis)       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Content Pipeline       │
                    │  (ETL Framework)        │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼────────┐   ┌──────────▼──────────┐   ┌────────▼─────────┐
│  PostgreSQL    │   │      Neo4j          │   │     MinIO        │
│  (Metadata)    │   │  (Provenance Graph) │   │  (Object Store)  │
└────────────────┘   └─────────────────────┘   └──────────────────┘
        │                        │                        │
┌───────▼────────┐   ┌──────────▼──────────┐
│    Qdrant      │   │      Redis          │
│  (Vectors)     │   │  (Cache + Queue)    │
└────────────────┘   └─────────────────────┘
```

---

## 🔌 Bidirectional Plugin Architecture

### Core Concept

**Import and Export are inverse operations sharing the same infrastructure:**

```python
# Import: External → Library
class ImportPlugin(ABC):
    async def import_content(url, job_id):
        # 1. Download from external source
        # 2. Extract content
        # 3. Transform to standard format
        # 4. Store in library
        # 5. Track provenance

# Export: Library → External  
class ExportPlugin(ABC):
    async def generate_content(request, job_id):
        # 1. Query library for sources
        # 2. Aggregate content
        # 3. Transform/generate
        # 4. Produce artifact
        # 5. Track provenance
```

### Plugin Lifecycle

Both import and export plugins share:
- **Job Management**: Async processing with status tracking
- **Progress Updates**: Real-time WebSocket streaming
- **Error Handling**: Automatic retry with exponential backoff
- **Provenance Tracking**: Complete genealogy in Neo4j
- **Resource Management**: Cleanup on success/failure

### Import Plugins

```python
# Base Import Plugin
class ImportPlugin(ABC):
    """Base class for all import plugins."""
    
    # Plugin metadata
    plugin_id: str          # e.g., "import.youtube"
    name: str               # e.g., "YouTube Video Importer"
    version: str            # e.g., "1.0.0"
    
    # Lifecycle hooks
    async def on_load(self):
        """Called when plugin is loaded."""
        pass
    
    async def before_download(self, url: str):
        """Called before downloading content."""
        pass
    
    async def after_download(self, content: bytes):
        """Called after downloading content."""
        pass
    
    async def before_extract(self, content: bytes):
        """Called before extraction."""
        pass
    
    async def after_extract(self, raw_content: RawContent):
        """Called after extraction."""
        pass
    
    async def before_store(self, processed: ProcessedContent):
        """Called before storing."""
        pass
    
    async def after_store(self, content_id: str):
        """Called after successful storage."""
        pass
    
    # Required implementations
    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """Return True if this plugin can handle the URL."""
        pass
    
    @abstractmethod
    async def validate_url(self, url: str) -> bool:
        """Validate URL format and accessibility."""
        pass
    
    @abstractmethod
    async def import_content(
        self,
        url: str,
        job_id: str,
        priority: int = 5,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Import content from external source.
        
        Returns:
            content_id: Unique identifier for stored content
        """
        pass
```

### Export Plugins

```python
# Base Export Plugin
class ExportPlugin(ABC):
    """Base class for all export plugins."""
    
    # Plugin metadata
    plugin_id: str          # e.g., "export.podcast"
    name: str               # e.g., "Podcast Generator"
    version: str            # e.g., "1.0.0"
    export_format: ExportFormat  # VIDEO, AUDIO, DOCUMENT, etc.
    
    # Lifecycle hooks
    async def on_load(self):
        """Called when plugin is loaded."""
        pass
    
    async def before_query(self, source_ids: List[str]):
        """Called before querying library."""
        pass
    
    async def after_query(self, sources: List[Dict]):
        """Called after querying library."""
        pass
    
    async def before_transform(self, sources: List[Dict]):
        """Called before transformation."""
        pass
    
    async def after_transform(self, transformed: Any):
        """Called after transformation."""
        pass
    
    async def before_generate(self, prepared_data: Any):
        """Called before generation."""
        pass
    
    async def after_generate(self, artifact: bytes):
        """Called after successful generation."""
        pass
    
    # Required implementations
    @abstractmethod
    async def can_generate(
        self,
        source_ids: List[str],
        parameters: Dict
    ) -> bool:
        """Return True if can generate from these sources."""
        pass
    
    @abstractmethod
    async def validate_sources(self, source_ids: List[str]) -> bool:
        """Validate source content exists and is accessible."""
        pass
    
    @abstractmethod
    async def generate_content(
        self,
        request: ExportRequest,
        job_id: str
    ) -> ExportResult:
        """
        Generate content from library sources.
        
        Returns:
            ExportResult with artifact_id and metadata
        """
        pass
```

### Concrete Plugin Examples

#### YouTube Import Plugin

```python
class YouTubeImportPlugin(ImportPlugin):
    """Import YouTube videos with transcript extraction."""
    
    plugin_id = "import.youtube"
    name = "YouTube Video Importer"
    version = "1.0.0"
    
    async def can_handle(self, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url
    
    async def import_content(self, url, job_id, priority=5, metadata=None):
        try:
            # Update: Downloading
            await self.update_job_status(job_id, "downloading", 10, "Downloading video")
            video_id = self._extract_video_id(url)
            
            # Download video metadata
            metadata = await self._fetch_metadata(video_id)
            
            # Update: Extracting
            await self.update_job_status(job_id, "extracting", 30, "Extracting transcript")
            
            # Try transcript API first
            transcript = await self._get_transcript(video_id)
            if not transcript:
                # Fallback: download audio + Whisper
                audio_path = await self._download_audio(video_id)
                transcript = await self._transcribe_with_whisper(audio_path)
            
            # Update: Processing
            await self.update_job_status(job_id, "processing", 60, "Processing content")
            
            # Transform to standard format
            processed = await self._transform_content(
                video_id=video_id,
                metadata=metadata,
                transcript=transcript
            )
            
            # Update: Storing
            await self.update_job_status(job_id, "storing", 80, "Storing to library")
            
            # Store in PostgreSQL, MinIO, Qdrant, Neo4j
            content_id = await self._store_content(processed, job_id)
            
            # Update: Complete
            await self.update_job_status(job_id, "completed", 100, "Import complete")
            
            return content_id
            
        except Exception as e:
            await self.handle_import_error(job_id, e)
            raise
```

#### Podcast Export Plugin

```python
class PodcastExportPlugin(ExportPlugin):
    """Generate podcasts from library content."""
    
    plugin_id = "export.podcast"
    name = "Podcast Generator"
    version = "1.0.0"
    export_format = ExportFormat.AUDIO
    
    async def can_generate(self, source_ids, parameters):
        # Can generate from documents, articles, videos
        sources = await self.get_sources(source_ids)
        return all(s["type"] in ["document", "article", "video"] for s in sources)
    
    async def generate_content(self, request, job_id):
        try:
            # Query library
            await self.update_job_status(job_id, "querying", 5, "Retrieving content")
            sources = await self._query_sources(request.source_ids)
            
            # Generate script
            await self.update_job_status(job_id, "scripting", 15, "Generating script")
            script = await self._generate_podcast_script(
                sources,
                request.parameters.get("style", "conversational")
            )
            
            # Text-to-speech
            await self.update_job_status(job_id, "generating", 40, "Generating audio")
            audio_segments = await self._text_to_speech(
                script,
                voice=request.parameters.get("voice", "professional_male")
            )
            
            # Compose audio
            await self.update_job_status(job_id, "composing", 70, "Composing podcast")
            podcast_path = await self._compose_podcast(
                audio_segments,
                add_intro=request.parameters.get("add_intro", True),
                add_music=request.parameters.get("add_music", True)
            )
            
            # Store
            await self.update_job_status(job_id, "storing", 90, "Storing podcast")
            artifact_id = await self._store_podcast(
                podcast_path,
                script,
                request.source_ids,
                job_id
            )
            
            # Complete
            await self.update_job_status(job_id, "completed", 100, "Podcast complete")
            
            return ExportResult(
                artifact_id=artifact_id,
                format=ExportFormat.AUDIO,
                source_ids=request.source_ids,
                artifacts={"audio": podcast_path, "script": script},
                provenance_id=f"podcast_{job_id}"
            )
            
        except Exception as e:
            await self.handle_export_error(job_id, e)
            raise
```

#### Video Export Plugin (Kling/Veo3)

```python
class SmartVideoExportPlugin(ExportPlugin):
    """
    Intelligent video generation with multi-backend support.
    
    Backends:
    - Kling AI: Cinematic short-form (<2 min)
    - Veo 3: Photorealistic long-form (2-10 min)
    - Runway Gen-3: Effects and edits
    - Synthesia: Avatar-based presentations
    """
    
    plugin_id = "export.video.smart"
    name = "Smart Video Generator"
    version = "1.0.0"
    export_format = ExportFormat.VIDEO
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kling = KlingVideoBackend()
        self.veo3 = Veo3VideoBackend()
        self.runway = RunwayGen3Backend()
        self.synthesia = SynthesiaBackend()
    
    async def generate_content(self, request, job_id):
        try:
            # Query sources
            await self.update_job_status(job_id, "querying", 5, "Retrieving content")
            sources = await self._query_sources_with_lineage(request.source_ids)
            
            # Generate video script with attributions
            await self.update_job_status(job_id, "scripting", 15, "Generating script")
            script, scene_attributions = await self._generate_video_script(
                sources,
                request.parameters
            )
            
            # Track script in provenance
            await self._track_script_generation(job_id, script, scene_attributions)
            
            # Route to best backend
            await self.update_job_status(job_id, "routing", 20, "Selecting AI backend")
            backend = self._select_backend(request.parameters)
            
            # Generate video clips
            await self.update_job_status(job_id, "generating", 30, f"Generating with {backend.name}")
            clips = await backend.generate_clips(scene_attributions, request.parameters)
            
            # Track clips in provenance
            await self._track_clip_generation(job_id, clips, backend)
            
            # Compose final video
            await self.update_job_status(job_id, "composing", 70, "Composing video")
            video_path = await self._compose_video(
                clips,
                add_voiceover=request.parameters.get("add_voiceover", False),
                add_music=request.parameters.get("add_music", False)
            )
            
            # Store with provenance
            await self.update_job_status(job_id, "storing", 90, "Storing video")
            artifact_id = await self._store_video_with_provenance(
                video_path,
                job_id,
                script,
                scene_attributions,
                request.source_ids
            )
            
            # Finalize provenance
            await self._finalize_provenance(job_id, video_path, artifact_id)
            
            await self.update_job_status(job_id, "completed", 100, "Video complete")
            
            return ExportResult(
                artifact_id=artifact_id,
                format=ExportFormat.VIDEO,
                source_ids=request.source_ids,
                provenance_id=f"video_{job_id}",
                artifacts={
                    "video": video_path,
                    "script": script,
                    "attributions": scene_attributions
                },
                metadata={
                    "backend": backend.name,
                    "duration": await self._get_duration(video_path),
                    "has_provenance": True
                }
            )
            
        except Exception as e:
            await self._track_generation_failure(job_id, str(e))
            await self.handle_export_error(job_id, e)
            raise
    
    def _select_backend(self, parameters):
        """Route to best backend based on requirements."""
        duration = parameters.get("duration", 60)
        style = parameters.get("style", "realistic")
        has_avatar = parameters.get("has_avatar", False)
        budget = parameters.get("budget", "standard")
        
        if has_avatar:
            return self.synthesia
        elif duration > 120:
            return self.veo3
        elif style == "cinematic" and duration < 30:
            return self.kling
        elif budget == "low":
            return self.runway
        else:
            return self.kling  # Default
```

---

## 📊 Provenance System

### Why Provenance Matters

**Williams Librarian is the ONLY content generation platform with complete provenance tracking.**

Competitors (Synthesia, Runway, Sora, Kling) have NO provenance - you can't:
- Track which sources created which content
- Reproduce generations
- Verify academic integrity
- Check license compliance
- See citation networks

### Provenance Graph Structure

```cypher
# Complete genealogy for every generated artifact

(:Video {video_id: "v123"})
  -[:GENERATED_FROM]-> (:Document {doc_id: "paper1"})
  -[:GENERATED_FROM]-> (:Document {doc_id: "paper2"})
  
  -[:HAS_SCRIPT]-> (:Script)
    -[:HAS_SCENE {scene_num: 1}]-> (:VideoScene)
      -[:SOURCED_FROM]-> (:Document {doc_id: "paper1"})
      -[:USED_PARAGRAPH {para_id: "p5"}]-> (:Paragraph)
  
  -[:GENERATED_BY]-> (:AIModel {name: "Kling", version: "1.2"})
  -[:NARRATED_BY]-> (:Voice {provider: "ElevenLabs"})
  -[:CREATED_BY]-> (:User {user_id: "user456"})
  -[:VERSION_OF]-> (:Video {video_id: "v122"})
  
(:Document {doc_id: "paper1"})
  -[:CITES]-> (:Document {doc_id: "paper_cited"})
  -[:HAS_LICENSE]-> (:License {type: "CC-BY-4.0"})
```

### Key Provenance Features

**1. Source Attribution**
```python
# Every scene knows its sources
GET /api/provenance/video/{video_id}/attribution

Response:
{
  "video_id": "v123",
  "attributions": [
    {
      "scene_num": 1,
      "sources": ["paper1", "paper2"],
      "citation": "Based on Smith et al. (2024) and Johnson (2023)"
    }
  ],
  "full_attribution": "This video was generated from:\n1. Smith et al..."
}
```

**2. Reproducibility**
```python
# Regenerate video from exact same sources
GET /api/provenance/video/{video_id}/genealogy

# Extract sources and parameters
original = response["video"]
sources = [d["doc_id"] for d in response["provenance"]["source_documents"]]
parameters = original["parameters"]

# Regenerate
POST /api/plugins/export
{
  "source_ids": sources,
  "format": "video",
  "parameters": parameters,
  "provenance": {
    "version_of": video_id,
    "reason": "Regeneration with improved model"
  }
}
```

**3. License Compliance**
```python
# Automatic license checking
GET /api/provenance/video/{video_id}/licenses

Response:
{
  "licenses": ["CC-BY-4.0", "CC-BY-NC-4.0"],
  "commercial_use_allowed": false,  # ← NC license!
  "attribution_required": true,
  "share_alike_required": false
}
```

**4. Impact Tracking**
```python
# See how content propagates
GET /api/provenance/video/{video_id}/impact

Response:
{
  "views": 1250,
  "shares": 87,
  "derivative_works": 3,  # Other videos using this as source
  "citations": 12  # Other content referencing this
}
```

**5. Citation Network**
```cypher
# Visualize knowledge flow
MATCH path = (d1:Document)<-[:CITES*]-(d2:Document)
WHERE d2.doc_id IN $source_ids
MATCH (v:Video)-[:GENERATED_FROM]->(d2)
RETURN path, v

# Shows: Paper A ← Paper B ← Paper C
#                    ↑
#                 Used in Video X
```

---

## ⚙️ Job Management System

### Architecture

```
┌─────────────────────────────────────────────────┐
│              Job Manager (Celery)                │
│  • Async task execution                         │
│  • Priority queues                              │
│  • Automatic retry (3x)                         │
│  • Manual retry (10x)                           │
│  • Rate limiting                                │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│         Redis (Message Broker + Cache)          │
│  • Task queue                                   │
│  • Job status cache                             │
│  • Rate limit counters                          │
│  • Pub/Sub for real-time updates               │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│         PostgreSQL (Job Metadata)               │
│  • processing_jobs table                        │
│  • Job history                                  │
│  • Retry tracking                               │
│  • Error logs                                   │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│         WebSocket (Real-Time Updates)           │
│  • Stream job status to clients                 │
│  • Progress percentage                          │
│  • Current stage                                │
│  • Error notifications                          │
└─────────────────────────────────────────────────┘
```

### Job Lifecycle

```python
@dataclass
class ProcessingJob:
    job_id: str              # Unique identifier
    content_id: str          # Content being processed
    url: str                 # Source URL
    content_type: str        # video, document, webpage, podcast
    status: JobStatus        # Current status
    priority: int            # 1-10 (10 = highest)
    progress_percent: float  # 0.0-100.0
    current_stage: str       # "downloading", "extracting", etc.
    created_at: datetime
    started_at: datetime
    completed_at: datetime
    error_message: str
    retry_count: int         # Current retry attempt
    max_retries: int         # Maximum retries allowed

class JobStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
```

### Job Manager API

```python
class JobManager:
    """Manages async job processing with Celery."""
    
    async def create_job(
        self,
        url: str,
        content_type: str,
        priority: int = 5,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create and queue a new job.
        
        Returns:
            job_id: Unique identifier for tracking
        """
        job_id = self._generate_job_id()
        
        job = ProcessingJob(
            job_id=job_id,
            url=url,
            content_type=content_type,
            status=JobStatus.PENDING,
            priority=priority,
            progress_percent=0.0,
            current_stage="pending",
            created_at=datetime.utcnow(),
            retry_count=0,
            max_retries=3
        )
        
        # Store in PostgreSQL
        await self._store_job(job)
        
        # Queue in Celery
        task = import_content.apply_async(
            args=[url, job_id],
            priority=priority,
            queue=f"priority_{priority}"
        )
        
        # Publish to WebSocket
        await self._publish_job_update(job_id, job)
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> ProcessingJob:
        """Get current job status."""
        # Try cache first
        cached = await self.redis.get(f"job:{job_id}")
        if cached:
            return ProcessingJob.from_json(cached)
        
        # Fallback to database
        job = await self.postgres.fetch_job(job_id)
        
        # Cache for 5 minutes
        await self.redis.setex(
            f"job:{job_id}",
            300,
            job.to_json()
        )
        
        return job
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float,
        stage: str
    ):
        """Update job status and broadcast to clients."""
        # Update database
        await self.postgres.update_job(
            job_id,
            status=status,
            progress_percent=progress,
            current_stage=stage
        )
        
        # Update cache
        job = await self.get_job_status(job_id)
        await self.redis.setex(
            f"job:{job_id}",
            300,
            job.to_json()
        )
        
        # Broadcast via WebSocket
        await self._publish_job_update(job_id, job)
    
    async def retry_job(self, job_id: str, manual: bool = False):
        """Retry a failed job."""
        job = await self.get_job_status(job_id)
        
        if manual:
            # Manual retry: allow up to 10 attempts
            max_retries = 10
            priority = min(10, job.priority + 2)  # Boost priority
        else:
            # Automatic retry: 3 attempts
            max_retries = 3
            priority = job.priority
        
        if job.retry_count >= max_retries:
            raise MaxRetriesExceeded(
                f"Job {job_id} exceeded max retries ({max_retries})"
            )
        
        # Increment retry count
        job.retry_count += 1
        job.status = JobStatus.RETRYING
        await self._store_job(job)
        
        # Re-queue with exponential backoff
        delay = 2 ** job.retry_count  # 2s, 4s, 8s, 16s...
        
        task = import_content.apply_async(
            args=[job.url, job_id],
            priority=priority,
            countdown=delay,
            queue=f"priority_{priority}"
        )
        
        return job_id
```

---

## 🗄️ Data Storage Architecture

### Multi-Database Strategy

```
PostgreSQL: Structured metadata, relationships, job tracking
Neo4j: Provenance graph, citation networks, knowledge flow
MinIO: Binary content (videos, audio, PDFs, images)
Qdrant: Vector embeddings for semantic search
Redis: Cache, job queue, rate limiting, pub/sub
```

### PostgreSQL Schema

```sql
-- Content metadata
CREATE TABLE content (
    content_id VARCHAR(50) PRIMARY KEY,
    url TEXT NOT NULL,
    content_type VARCHAR(20) NOT NULL,  -- video, document, webpage
    title TEXT,
    authors TEXT[],
    published_date TIMESTAMP,
    tier VARCHAR(10),  -- top, middle, general
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Processing jobs
CREATE TABLE processing_jobs (
    job_id VARCHAR(32) PRIMARY KEY,
    content_id VARCHAR(50) REFERENCES content(content_id),
    url TEXT NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    priority INTEGER DEFAULT 5,
    progress_percent FLOAT DEFAULT 0.0,
    current_stage TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Generated artifacts (podcasts, videos, etc.)
CREATE TABLE artifacts (
    artifact_id VARCHAR(50) PRIMARY KEY,
    artifact_type VARCHAR(20) NOT NULL,  -- podcast, video, ebook
    format VARCHAR(20),  -- mp3, mp4, pdf
    source_ids TEXT[],  -- Source content IDs
    storage_path TEXT,
    file_size BIGINT,
    duration INTEGER,  -- seconds
    metadata JSONB,
    provenance_id VARCHAR(50),  -- Neo4j node ID
    created_at TIMESTAMP DEFAULT NOW()
);
```

### MinIO Bucket Structure

```
Buckets organized by content type:

williams-librarian/
├─ videos/
│  ├─ {video_id}/
│  │  ├─ video.mp4
│  │  ├─ audio.mp3
│  │  ├─ thumbnail.jpg
│  │  └─ transcript.txt
│
├─ documents/
│  ├─ {doc_id}/
│  │  ├─ document.pdf
│  │  └─ extracted.txt
│
├─ webpages/
│  ├─ {page_id}/
│  │  ├─ page.html
│  │  └─ extracted.txt
│
├─ podcasts/
│  ├─ {podcast_id}/
│  │  ├─ podcast.mp3
│  │  ├─ script.txt
│  │  └─ cover.jpg
│
└─ generated-videos/
   ├─ {video_id}/
   │  ├─ video.mp4
   │  ├─ script.txt
   │  └─ attributions.json
```

---

## 🌐 API Architecture

### RESTful Endpoints

```python
# Content Import
POST   /api/content/import
       Body: {"url": "...", "type": "video", "priority": 5}
       Returns: {"job_id": "abc123", "status": "queued"}

GET    /api/content/{content_id}
       Returns: Content metadata + storage paths

DELETE /api/content/{content_id}
       Query: ?hard_delete=true
       Cascading delete across all databases

# Content Export
POST   /api/content/export
       Body: {
         "source_ids": ["doc1", "doc2"],
         "format": "podcast",
         "parameters": {"voice": "professional_male"}
       }
       Returns: {"job_id": "def456", "status": "queued"}

GET    /api/artifacts/{artifact_id}
       Returns: Artifact metadata + download URL

# Job Management
GET    /api/jobs/{job_id}
       Returns: Job status, progress, stage

POST   /api/jobs/{job_id}/retry
       Body: {"manual": true}
       Retry failed job

DELETE /api/jobs/{job_id}
       Cancel running job

# Provenance
GET    /api/provenance/video/{video_id}/genealogy
       Returns: Complete source tree, citations, AI models

GET    /api/provenance/video/{video_id}/attribution
       Returns: Human-readable attribution text

GET    /api/provenance/video/{video_id}/impact
       Returns: Views, shares, derivatives, citations

GET    /api/provenance/document/{doc_id}/generated-content
       Returns: All artifacts generated from this document

# Plugin Management
GET    /api/plugins/import
       Returns: List of available import plugins

GET    /api/plugins/export
       Returns: List of available export plugins

POST   /api/plugins/{plugin_id}/enable
       Enable a plugin

POST   /api/plugins/{plugin_id}/disable
       Disable a plugin
```

### WebSocket Streaming

```python
# Real-time job updates
WS /ws/jobs/{job_id}

# Server sends:
{
  "job_id": "abc123",
  "status": "downloading",
  "progress": 25.5,
  "stage": "Downloading video",
  "timestamp": "2025-10-12T10:30:00Z"
}

# Client receives updates every 500ms or on status change
```

---

## 🎯 Success Metrics

### Technical Metrics
- **Test Coverage**: >95% (currently 90.59%)
- **API Response Time**: <200ms (p95)
- **Job Processing Time**: Video import <5 min, Podcast gen <3 min
- **Uptime**: 99.9%
- **Error Rate**: <0.1%

### Business Metrics
- **Content Processed**: Track imports per day
- **Artifacts Generated**: Track exports per day
- **User Satisfaction**: >90% positive feedback
- **Cost Per Generation**: <$1 per podcast, <$10 per video
- **Provenance Coverage**: 100% of generated content

---

## 📋 Next Steps

See **TDD-PLAN.md** for comprehensive test-driven development plan.

See **INTEGRATION-EXAMPLES.md** for real-world usage examples.

---

## 📚 Related Documents

- **TDD-PLAN.md**: Comprehensive testing strategy
- **INTEGRATION-EXAMPLES.md**: Real-world use cases
- **plugin-development.md**: How to create custom plugins
- **deployment.md**: Production deployment guide
- **architecture.md**: Original architecture document (legacy)

---

**Last Updated:** October 12, 2025  
**Version:** 2.0 (Definitive)
