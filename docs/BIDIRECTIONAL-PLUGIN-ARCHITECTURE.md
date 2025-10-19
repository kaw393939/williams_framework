# Bidirectional Plugin Architecture

**Version:** 1.0  
**Date:** October 12, 2025  
**Status:** Proposed Architecture for Import/Export Plugins

---

## 🎯 Executive Summary

**Vision**: Create a **bidirectional plugin system** where the librarian can both **import content from external sources** AND **generate/export content to various formats**.

**Pattern Recognition**:
- **Import** (YouTube → Library): Download video → Extract audio → Transcribe → Store
- **Export** (Library → Podcast): Retrieve content → Generate script → Text-to-Speech → Publish

**Key Insight**: Both directions use the **same infrastructure** (job queue, status tracking, retry, CRUD) but in reverse!

---

## 🏗️ Architecture Overview

### Bidirectional Flow

```
┌────────────────────────────────────────────────────────────────────┐
│  External Content Sources                                           │
│  (YouTube, PDFs, Web Pages, Podcasts, RSS, etc.)                  │
└──────────────────┬─────────────────────────────────────────────────┘
                   │
                   │ IMPORT PLUGINS (Ingestion)
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                         LIBRARY STORAGE                             │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  PostgreSQL + MinIO + Neo4j + Qdrant + Redis             │     │
│  │  - Documents, Videos, Articles, Transcripts              │     │
│  │  - Metadata, Embeddings, Relationships                   │     │
│  │  - Cached data, Processing history                       │     │
│  └──────────────────────────────────────────────────────────┘     │
└──────────────────┬─────────────────────────────────────────────────┘
                   │
                   │ EXPORT PLUGINS (Generation)
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  Generated Content Artifacts                                        │
│  (Podcasts, Videos, Ebooks, Reports, Slidedecks, etc.)           │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│              SHARED INFRASTRUCTURE (Both Directions)                │
├────────────────────────────────────────────────────────────────────┤
│  - JobManager: Async processing queue (Celery)                    │
│  - StatusTracker: Real-time progress updates (Redis pub/sub)      │
│  - RetryManager: Automatic failure recovery                        │
│  - ArtifactManager: CRUD for inputs/outputs                        │
│  - PluginRegistry: Dynamic plugin loading                          │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Plugin Types

### 1. Import Plugins (Ingestion)

**Purpose**: Bring external content INTO the library

**Examples**:
- `YouTubeImportPlugin` - Import YouTube videos
- `PDFImportPlugin` - Import PDF documents
- `WebPageImportPlugin` - Import web articles
- `SpotifyPodcastImportPlugin` - Import podcasts from Spotify
- `RSSFeedImportPlugin` - Import RSS feed articles
- `TwitterThreadImportPlugin` - Import Twitter threads
- `GitHubRepoImportPlugin` - Import GitHub repositories
- `ArXivImportPlugin` - Import academic papers

**Common Tasks**:
1. **Download**: Fetch content from external source
2. **Extract**: Parse and extract structured data
3. **Transform**: Convert to internal format
4. **Enrich**: Add metadata, tags, relationships
5. **Store**: Save to all storage layers

### 2. Export Plugins (Generation)

**Purpose**: Generate new content FROM the library

**Examples**:
- `PodcastExportPlugin` - Generate podcast episodes from documents
- `VideoExportPlugin` - Generate explainer videos from articles
- `EbookExportPlugin` - Compile ebooks from curated collections
- `SlidedeckExportPlugin` - Generate presentations from summaries
- `BlogPostExportPlugin` - Generate blog posts from research
- `NewsletterExportPlugin` - Generate newsletters from weekly highlights
- `SummaryReportExportPlugin` - Generate PDF reports on topics
- `FlashcardExportPlugin` - Generate study flashcards from content

**Common Tasks**:
1. **Query**: Find relevant content from library
2. **Aggregate**: Combine multiple sources
3. **Transform**: Convert to target format
4. **Generate**: Create new content (TTS, video, layout)
5. **Publish**: Export to MinIO or external services

---

## 📐 Plugin Base Classes

### ImportPlugin (Base)

```python
# app/plugins/base/import_plugin.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

class ImportType(Enum):
    """Types of content that can be imported."""
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    WEBPAGE = "webpage"
    SOCIAL_MEDIA = "social_media"
    REPOSITORY = "repository"
    ACADEMIC_PAPER = "academic_paper"
    FEED = "feed"

@dataclass
class ImportResult:
    """Result of import operation."""
    content_id: str
    import_type: ImportType
    url: str
    metadata: Dict
    artifacts: Dict[str, str]  # {"video": "path/to/video.mp4", "audio": "path/to/audio.mp3"}
    status: str
    error: Optional[str] = None

class ImportPlugin(ABC):
    """
    Base class for all import plugins.
    
    Import plugins bring external content INTO the library.
    They handle downloading, extraction, transformation, and storage.
    """
    
    # Plugin metadata (must be defined by subclass)
    plugin_id: str
    name: str
    version: str
    import_type: ImportType
    
    def __init__(
        self,
        job_manager: 'JobManager',
        minio_repo: 'MinIORepository',
        postgres_repo: 'PostgresRepository',
        neo4j_repo: 'Neo4jRepository',
        redis_repo: 'RedisRepository',
        qdrant_repo: 'QdrantRepository'
    ):
        self.job_manager = job_manager
        self.minio = minio_repo
        self.postgres = postgres_repo
        self.neo4j = neo4j_repo
        self.redis = redis_repo
        self.qdrant = qdrant_repo
    
    # ============================================================
    # Lifecycle Hooks
    # ============================================================
    
    async def on_load(self, context: Dict) -> Dict:
        """Called when plugin is loaded. Override for custom initialization."""
        return {
            "plugin_id": self.plugin_id,
            "event": "on_load",
            "status": "initialized"
        }
    
    # ============================================================
    # Abstract Methods (must be implemented)
    # ============================================================
    
    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """
        Check if this plugin can handle the given URL.
        
        Args:
            url: Source URL to check
            
        Returns:
            True if plugin can import from this URL
            
        Example:
            >>> plugin = YouTubeImportPlugin()
            >>> await plugin.can_handle("https://youtube.com/watch?v=abc")
            True
            >>> await plugin.can_handle("https://example.com/doc.pdf")
            False
        """
        pass
    
    @abstractmethod
    async def validate_url(self, url: str) -> bool:
        """
        Validate that the URL is accessible and valid.
        
        Args:
            url: Source URL to validate
            
        Returns:
            True if URL is valid and accessible
            
        Raises:
            ValidationError: If URL is invalid or inaccessible
        """
        pass
    
    @abstractmethod
    async def import_content(
        self,
        url: str,
        job_id: str,
        priority: int = 5,
        metadata: Optional[Dict] = None
    ) -> ImportResult:
        """
        Import content from URL.
        
        This is the main entry point for import operations.
        Should update job status at each stage.
        
        Args:
            url: Source URL to import from
            job_id: Job ID for status tracking
            priority: Processing priority (1=highest, 10=lowest)
            metadata: Optional metadata to attach
            
        Returns:
            ImportResult with content_id and details
            
        Raises:
            ImportError: If import fails
        """
        pass
    
    # ============================================================
    # Optional Hooks (can be overridden)
    # ============================================================
    
    async def before_download(self, url: str, job_id: str) -> Dict:
        """Hook called before download starts."""
        return {"url": url, "job_id": job_id}
    
    async def after_download(self, url: str, file_path: str, job_id: str) -> Dict:
        """Hook called after download completes."""
        return {"url": url, "file_path": file_path, "job_id": job_id}
    
    async def before_extract(self, file_path: str, job_id: str) -> Dict:
        """Hook called before extraction starts."""
        return {"file_path": file_path, "job_id": job_id}
    
    async def after_extract(self, extracted_data: Dict, job_id: str) -> Dict:
        """Hook called after extraction completes."""
        return {"extracted_data": extracted_data, "job_id": job_id}
    
    async def before_store(self, content: Dict, job_id: str) -> Dict:
        """Hook called before storing to database."""
        return {"content": content, "job_id": job_id}
    
    async def after_store(self, content_id: str, job_id: str) -> Dict:
        """Hook called after storing completes."""
        return {"content_id": content_id, "job_id": job_id}
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float,
        stage: str,
        message: Optional[str] = None
    ):
        """Update job status during import."""
        await self.job_manager.update_job_status(
            job_id=job_id,
            status=status,
            progress_percent=progress,
            current_stage=stage
        )
        
        # Publish to Redis for real-time updates
        await self.redis.publish(
            f"job:{job_id}",
            {
                "status": status,
                "progress": progress,
                "stage": stage,
                "message": message,
                "plugin": self.plugin_id
            }
        )
    
    async def handle_import_error(
        self,
        job_id: str,
        error: Exception,
        retry_count: int
    ) -> bool:
        """
        Handle import error with retry logic.
        
        Returns:
            True if should retry, False otherwise
        """
        await self.update_job_status(
            job_id=job_id,
            status="failed",
            progress=0.0,
            stage="error",
            message=str(error)
        )
        
        # Retry if under limit
        if retry_count < 3:
            await self.job_manager.retry_job(job_id, manual=False)
            return True
        
        return False
```

### ExportPlugin (Base)

```python
# app/plugins/base/export_plugin.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

class ExportFormat(Enum):
    """Types of content that can be exported/generated."""
    PODCAST = "podcast"
    VIDEO = "video"
    EBOOK = "ebook"
    SLIDEDECK = "slidedeck"
    BLOG_POST = "blog_post"
    NEWSLETTER = "newsletter"
    REPORT = "report"
    FLASHCARDS = "flashcards"
    INFOGRAPHIC = "infographic"

@dataclass
class ExportRequest:
    """Request to generate/export content."""
    source_ids: List[str]  # Content IDs from library
    format: ExportFormat
    parameters: Dict  # Format-specific parameters
    metadata: Optional[Dict] = None

@dataclass
class ExportResult:
    """Result of export operation."""
    artifact_id: str
    format: ExportFormat
    source_ids: List[str]
    artifacts: Dict[str, str]  # {"audio": "path/to/podcast.mp3", "transcript": "..."}
    metadata: Dict
    status: str
    error: Optional[str] = None

class ExportPlugin(ABC):
    """
    Base class for all export plugins.
    
    Export plugins generate new content FROM the library.
    They handle retrieval, aggregation, transformation, and generation.
    """
    
    # Plugin metadata (must be defined by subclass)
    plugin_id: str
    name: str
    version: str
    export_format: ExportFormat
    
    def __init__(
        self,
        job_manager: 'JobManager',
        minio_repo: 'MinIORepository',
        postgres_repo: 'PostgresRepository',
        neo4j_repo: 'Neo4jRepository',
        redis_repo: 'RedisRepository',
        qdrant_repo: 'QdrantRepository'
    ):
        self.job_manager = job_manager
        self.minio = minio_repo
        self.postgres = postgres_repo
        self.neo4j = neo4j_repo
        self.redis = redis_repo
        self.qdrant = qdrant_repo
    
    # ============================================================
    # Lifecycle Hooks
    # ============================================================
    
    async def on_load(self, context: Dict) -> Dict:
        """Called when plugin is loaded. Override for custom initialization."""
        return {
            "plugin_id": self.plugin_id,
            "event": "on_load",
            "status": "initialized"
        }
    
    # ============================================================
    # Abstract Methods (must be implemented)
    # ============================================================
    
    @abstractmethod
    async def can_generate(
        self,
        source_ids: List[str],
        parameters: Dict
    ) -> bool:
        """
        Check if this plugin can generate from these sources.
        
        Args:
            source_ids: List of content IDs from library
            parameters: Generation parameters
            
        Returns:
            True if plugin can generate from these sources
            
        Example:
            >>> plugin = PodcastExportPlugin()
            >>> await plugin.can_generate(["doc1", "doc2"], {"voice": "male"})
            True
        """
        pass
    
    @abstractmethod
    async def validate_sources(self, source_ids: List[str]) -> bool:
        """
        Validate that all source content exists and is accessible.
        
        Args:
            source_ids: List of content IDs to validate
            
        Returns:
            True if all sources are valid
            
        Raises:
            ValidationError: If any source is invalid
        """
        pass
    
    @abstractmethod
    async def generate_content(
        self,
        request: ExportRequest,
        job_id: str
    ) -> ExportResult:
        """
        Generate/export content from library sources.
        
        This is the main entry point for export operations.
        Should update job status at each stage.
        
        Args:
            request: Export request with sources and parameters
            job_id: Job ID for status tracking
            
        Returns:
            ExportResult with artifact_id and details
            
        Raises:
            ExportError: If generation fails
        """
        pass
    
    # ============================================================
    # Optional Hooks (can be overridden)
    # ============================================================
    
    async def before_query(self, source_ids: List[str], job_id: str) -> Dict:
        """Hook called before querying library."""
        return {"source_ids": source_ids, "job_id": job_id}
    
    async def after_query(self, sources: List[Dict], job_id: str) -> Dict:
        """Hook called after querying library."""
        return {"sources": sources, "job_id": job_id}
    
    async def before_transform(self, sources: List[Dict], job_id: str) -> Dict:
        """Hook called before transformation."""
        return {"sources": sources, "job_id": job_id}
    
    async def after_transform(self, transformed: Dict, job_id: str) -> Dict:
        """Hook called after transformation."""
        return {"transformed": transformed, "job_id": job_id}
    
    async def before_generate(self, data: Dict, job_id: str) -> Dict:
        """Hook called before generation."""
        return {"data": data, "job_id": job_id}
    
    async def after_generate(self, artifact_id: str, job_id: str) -> Dict:
        """Hook called after generation."""
        return {"artifact_id": artifact_id, "job_id": job_id}
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float,
        stage: str,
        message: Optional[str] = None
    ):
        """Update job status during export."""
        await self.job_manager.update_job_status(
            job_id=job_id,
            status=status,
            progress_percent=progress,
            current_stage=stage
        )
        
        # Publish to Redis for real-time updates
        await self.redis.publish(
            f"job:{job_id}",
            {
                "status": status,
                "progress": progress,
                "stage": stage,
                "message": message,
                "plugin": self.plugin_id
            }
        )
    
    async def handle_export_error(
        self,
        job_id: str,
        error: Exception,
        retry_count: int
    ) -> bool:
        """
        Handle export error with retry logic.
        
        Returns:
            True if should retry, False otherwise
        """
        await self.update_job_status(
            job_id=job_id,
            status="failed",
            progress=0.0,
            stage="error",
            message=str(error)
        )
        
        # Retry if under limit
        if retry_count < 3:
            await self.job_manager.retry_job(job_id, manual=False)
            return True
        
        return False
```

---

## 🔧 Example Implementations

### Example 1: YouTubeImportPlugin

```python
# app/plugins/import/youtube.py

from app.plugins.base.import_plugin import ImportPlugin, ImportType, ImportResult
from urllib.parse import urlparse, parse_qs
import yt_dlp
from faster_whisper import WhisperModel

class YouTubeImportPlugin(ImportPlugin):
    """Import videos from YouTube."""
    
    plugin_id = "import.youtube"
    name = "YouTube Video Importer"
    version = "1.0.0"
    import_type = ImportType.VIDEO
    
    async def can_handle(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        parsed = urlparse(url)
        return "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc
    
    async def validate_url(self, url: str) -> bool:
        """Validate YouTube URL is accessible."""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return info is not None
        except Exception:
            return False
    
    async def import_content(
        self,
        url: str,
        job_id: str,
        priority: int = 5,
        metadata: Optional[Dict] = None
    ) -> ImportResult:
        """Import YouTube video."""
        
        # Extract video ID
        video_id = self._extract_video_id(url)
        
        try:
            # Stage 1: Download video
            await self.update_job_status(
                job_id, "downloading", 10.0, "Downloading video"
            )
            video_path = await self._download_video(url, video_id)
            
            # Stage 2: Extract audio
            await self.update_job_status(
                job_id, "extracting_audio", 30.0, "Extracting audio"
            )
            audio_path = await self._extract_audio(video_path)
            
            # Stage 3: Transcribe
            await self.update_job_status(
                job_id, "transcribing", 50.0, "Transcribing audio"
            )
            transcript = await self._transcribe_audio(audio_path)
            
            # Stage 4: Extract metadata
            await self.update_job_status(
                job_id, "extracting_metadata", 70.0, "Extracting metadata"
            )
            video_metadata = await self._extract_metadata(url, video_id)
            
            # Stage 5: Store everything
            await self.update_job_status(
                job_id, "storing", 90.0, "Storing data"
            )
            await self._store_video(
                video_id, video_path, audio_path,
                transcript, video_metadata
            )
            
            # Complete
            await self.update_job_status(
                job_id, "completed", 100.0, "Import complete"
            )
            
            return ImportResult(
                content_id=video_id,
                import_type=ImportType.VIDEO,
                url=url,
                metadata=video_metadata,
                artifacts={
                    "video": video_path,
                    "audio": audio_path,
                    "transcript": transcript
                },
                status="completed"
            )
            
        except Exception as e:
            await self.handle_import_error(job_id, e, 0)
            raise
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc:
            return parse_qs(parsed.query)['v'][0]
        elif "youtu.be" in parsed.netloc:
            return parsed.path[1:]
        raise ValueError(f"Invalid YouTube URL: {url}")
    
    async def _download_video(self, url: str, video_id: str) -> str:
        """Download video using yt-dlp."""
        # Implementation here...
        pass
    
    async def _extract_audio(self, video_path: str) -> str:
        """Extract audio using ffmpeg."""
        # Implementation here...
        pass
    
    async def _transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using faster-whisper."""
        model = WhisperModel("base")
        segments, _ = model.transcribe(audio_path)
        return " ".join([seg.text for seg in segments])
    
    async def _extract_metadata(self, url: str, video_id: str) -> Dict:
        """Extract video metadata."""
        # Implementation here...
        pass
    
    async def _store_video(
        self,
        video_id: str,
        video_path: str,
        audio_path: str,
        transcript: str,
        metadata: Dict
    ):
        """Store video in all repositories."""
        # MinIO: Store files
        await self.minio.upload_file(video_path, f"videos/{video_id}/original.mp4")
        await self.minio.upload_file(audio_path, f"videos/{video_id}/audio.mp3")
        
        # PostgreSQL: Store metadata + transcript
        await self.postgres.execute(
            """
            INSERT INTO video_metadata (video_id, title, description, duration)
            VALUES ($1, $2, $3, $4)
            """,
            video_id, metadata['title'], metadata['description'], metadata['duration']
        )
        
        await self.postgres.execute(
            """
            INSERT INTO transcriptions (video_id, text, language)
            VALUES ($1, $2, $3)
            """,
            video_id, transcript, "en"
        )
        
        # Neo4j: Create video node
        await self.neo4j.execute(
            """
            CREATE (v:Video {video_id: $video_id, title: $title})
            """,
            {"video_id": video_id, "title": metadata['title']}
        )
        
        # Qdrant: Store embeddings
        embedding = await self._generate_embedding(transcript)
        await self.qdrant.add(
            content_id=video_id,
            vector=embedding,
            metadata=metadata
        )
```

### Example 2: PodcastExportPlugin

```python
# app/plugins/export/podcast.py

from app.plugins.base.export_plugin import (
    ExportPlugin, ExportFormat, ExportRequest, ExportResult
)
from elevenlabs import generate, Voice
from pydub import AudioSegment
import openai

class PodcastExportPlugin(ExportPlugin):
    """Generate podcast episodes from library content."""
    
    plugin_id = "export.podcast"
    name = "Podcast Generator"
    version = "1.0.0"
    export_format = ExportFormat.PODCAST
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tts_engine = "elevenlabs"  # or "openai", "google"
        self.default_voice = "professional_male"
    
    async def can_generate(
        self,
        source_ids: List[str],
        parameters: Dict
    ) -> bool:
        """Check if we can generate podcast from these sources."""
        # Can generate from documents, articles, or videos
        for source_id in source_ids:
            content_type = await self._get_content_type(source_id)
            if content_type not in ["document", "article", "video"]:
                return False
        return True
    
    async def validate_sources(self, source_ids: List[str]) -> bool:
        """Validate all source content exists."""
        for source_id in source_ids:
            exists = await self.postgres.execute(
                "SELECT 1 FROM content WHERE content_id = $1",
                source_id
            )
            if not exists:
                return False
        return True
    
    async def generate_content(
        self,
        request: ExportRequest,
        job_id: str
    ) -> ExportResult:
        """Generate podcast episode."""
        
        try:
            # Stage 1: Query library for content
            await self.update_job_status(
                job_id, "querying", 10.0, "Retrieving content"
            )
            sources = await self._query_sources(request.source_ids)
            
            # Stage 2: Aggregate and summarize
            await self.update_job_status(
                job_id, "processing", 25.0, "Generating podcast script"
            )
            script = await self._generate_script(sources, request.parameters)
            
            # Stage 3: Generate speech segments
            await self.update_job_status(
                job_id, "generating", 50.0, "Converting text to speech"
            )
            audio_segments = await self._generate_speech(
                script,
                voice=request.parameters.get("voice", self.default_voice)
            )
            
            # Stage 4: Combine audio with intro/outro
            await self.update_job_status(
                job_id, "composing", 75.0, "Composing final audio"
            )
            final_audio = await self._compose_audio(
                audio_segments,
                intro=request.parameters.get("intro"),
                outro=request.parameters.get("outro"),
                music=request.parameters.get("background_music")
            )
            
            # Stage 5: Store podcast
            await self.update_job_status(
                job_id, "storing", 90.0, "Storing podcast"
            )
            artifact_id = await self._store_podcast(
                final_audio,
                script,
                request.source_ids,
                request.metadata or {}
            )
            
            # Complete
            await self.update_job_status(
                job_id, "completed", 100.0, "Podcast generated"
            )
            
            return ExportResult(
                artifact_id=artifact_id,
                format=ExportFormat.PODCAST,
                source_ids=request.source_ids,
                artifacts={
                    "audio": f"podcasts/{artifact_id}/episode.mp3",
                    "transcript": script,
                    "metadata": request.metadata
                },
                metadata={
                    "duration": final_audio.duration_seconds,
                    "file_size": final_audio.frame_count(),
                    "voice": request.parameters.get("voice")
                },
                status="completed"
            )
            
        except Exception as e:
            await self.handle_export_error(job_id, e, 0)
            raise
    
    async def _query_sources(self, source_ids: List[str]) -> List[Dict]:
        """Retrieve content from library."""
        sources = []
        for source_id in source_ids:
            content = await self.postgres.execute(
                """
                SELECT content_id, title, summary, full_text, metadata
                FROM content
                WHERE content_id = $1
                """,
                source_id
            )
            sources.append(content)
        return sources
    
    async def _generate_script(
        self,
        sources: List[Dict],
        parameters: Dict
    ) -> str:
        """Generate podcast script using LLM."""
        # Combine all content
        combined_text = "\n\n".join([
            f"# {source['title']}\n{source['summary']}"
            for source in sources
        ])
        
        # Generate script with OpenAI
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional podcast script writer. "
                        "Create an engaging podcast script from the provided content. "
                        "Include natural transitions, engaging intro/outro, "
                        "and conversational tone."
                    )
                },
                {
                    "role": "user",
                    "content": f"Create a podcast script from:\n\n{combined_text}"
                }
            ],
            max_tokens=parameters.get("max_length", 2000),
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    async def _generate_speech(
        self,
        script: str,
        voice: str
    ) -> List[AudioSegment]:
        """Generate speech using TTS engine."""
        segments = []
        
        # Split script into paragraphs
        paragraphs = script.split("\n\n")
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Generate audio for paragraph
            if self.tts_engine == "elevenlabs":
                audio_data = generate(
                    text=paragraph,
                    voice=Voice(voice_id=voice)
                )
                segment = AudioSegment.from_mp3(audio_data)
            
            segments.append(segment)
        
        return segments
    
    async def _compose_audio(
        self,
        segments: List[AudioSegment],
        intro: Optional[str] = None,
        outro: Optional[str] = None,
        music: Optional[str] = None
    ) -> AudioSegment:
        """Compose final audio with intro, segments, outro, and music."""
        final = AudioSegment.empty()
        
        # Add intro
        if intro:
            intro_audio = AudioSegment.from_file(intro)
            final += intro_audio
        
        # Add content segments with pauses
        for segment in segments:
            final += segment
            final += AudioSegment.silent(duration=500)  # 500ms pause
        
        # Add outro
        if outro:
            outro_audio = AudioSegment.from_file(outro)
            final += outro_audio
        
        # Add background music (if provided)
        if music:
            music_audio = AudioSegment.from_file(music)
            # Loop music to match content length
            music_looped = music_audio * (len(final) // len(music_audio) + 1)
            music_looped = music_looped[:len(final)]
            # Lower volume and mix
            music_looped = music_looped - 20  # Reduce volume by 20dB
            final = final.overlay(music_looped)
        
        return final
    
    async def _store_podcast(
        self,
        audio: AudioSegment,
        transcript: str,
        source_ids: List[str],
        metadata: Dict
    ) -> str:
        """Store generated podcast."""
        artifact_id = f"podcast_{uuid4().hex[:12]}"
        
        # MinIO: Store audio file
        audio_path = f"podcasts/{artifact_id}/episode.mp3"
        audio.export(audio_path, format="mp3", bitrate="192k")
        await self.minio.upload_file(audio_path, audio_path)
        
        # PostgreSQL: Store metadata
        await self.postgres.execute(
            """
            INSERT INTO generated_content (
                artifact_id, format, source_ids, transcript, metadata, created_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            """,
            artifact_id, "podcast", source_ids, transcript, metadata
        )
        
        # Redis: Cache for quick access
        await self.redis.set_json(
            f"artifact:{artifact_id}",
            {
                "audio_path": audio_path,
                "transcript": transcript,
                "metadata": metadata
            },
            ttl=3600
        )
        
        return artifact_id
    
    async def _get_content_type(self, source_id: str) -> str:
        """Get content type for source."""
        result = await self.postgres.execute(
            "SELECT content_type FROM content WHERE content_id = $1",
            source_id
        )
        return result[0]["content_type"] if result else None
```

---

## 🎛️ Plugin Configuration

### Configuration File

```yaml
# config/plugins.yml

# ============================================================
# Import Plugins (Ingestion)
# ============================================================
import_plugins:
  - name: youtube
    enabled: true
    plugin_id: import.youtube
    class: app.plugins.import.youtube.YouTubeImportPlugin
    priority: 1
    config:
      quality: best
      audio_format: mp3
      transcription_model: base
      extract_comments: true
      extract_chapters: true
  
  - name: pdf
    enabled: true
    plugin_id: import.pdf
    class: app.plugins.import.pdf.PDFImportPlugin
    priority: 2
    config:
      extract_images: true
      ocr_enabled: true
  
  - name: webpage
    enabled: true
    plugin_id: import.webpage
    class: app.plugins.import.webpage.WebPageImportPlugin
    priority: 3
    config:
      javascript_enabled: false
      timeout: 10
  
  - name: spotify_podcast
    enabled: false  # Not implemented yet
    plugin_id: import.spotify_podcast
    class: app.plugins.import.spotify_podcast.SpotifyPodcastImportPlugin
    config:
      api_key: ${SPOTIFY_API_KEY}

# ============================================================
# Export Plugins (Generation)
# ============================================================
export_plugins:
  - name: podcast
    enabled: true
    plugin_id: export.podcast
    class: app.plugins.export.podcast.PodcastExportPlugin
    priority: 1
    config:
      tts_engine: elevenlabs
      voice: professional_male
      quality: high
      include_music: true
      api_key: ${ELEVENLABS_API_KEY}
  
  - name: video
    enabled: false  # Not ready yet
    plugin_id: export.video
    class: app.plugins.export.video.VideoExportPlugin
    config:
      resolution: 1080p
      fps: 30
  
  - name: ebook
    enabled: true
    plugin_id: export.ebook
    class: app.plugins.export.ebook.EbookExportPlugin
    config:
      format: epub
      include_toc: true
      include_cover: true
  
  - name: slidedeck
    enabled: false
    plugin_id: export.slidedeck
    class: app.plugins.export.slidedeck.SlidedeckExportPlugin
    config:
      template: modern
      theme: dark
```

---

## 🔄 Plugin Registry (Enhanced)

```python
# app/plugins/registry.py

from typing import Dict, List, Optional, Type
from enum import Enum
import yaml
from pathlib import Path

class PluginType(Enum):
    IMPORT = "import"
    EXPORT = "export"

class BidirectionalPluginRegistry:
    """Enhanced plugin registry for import/export plugins."""
    
    def __init__(self, config_path: str = "config/plugins.yml"):
        self.import_plugins: Dict[str, ImportPlugin] = {}
        self.export_plugins: Dict[str, ExportPlugin] = {}
        self.config_path = config_path
    
    async def load_plugins(self):
        """Load all enabled plugins from configuration."""
        config = self._load_config()
        
        # Load import plugins
        for plugin_config in config.get("import_plugins", []):
            if plugin_config.get("enabled", True):
                plugin = await self._load_plugin(
                    plugin_config,
                    PluginType.IMPORT
                )
                if plugin:
                    self.register_import_plugin(plugin)
        
        # Load export plugins
        for plugin_config in config.get("export_plugins", []):
            if plugin_config.get("enabled", True):
                plugin = await self._load_plugin(
                    plugin_config,
                    PluginType.EXPORT
                )
                if plugin:
                    self.register_export_plugin(plugin)
    
    def register_import_plugin(self, plugin: ImportPlugin):
        """Register an import plugin."""
        if plugin.plugin_id in self.import_plugins:
            raise PluginError(f"Import plugin '{plugin.plugin_id}' already registered")
        
        self.import_plugins[plugin.plugin_id] = plugin
        print(f"✅ Registered import plugin: {plugin.name} v{plugin.version}")
    
    def register_export_plugin(self, plugin: ExportPlugin):
        """Register an export plugin."""
        if plugin.plugin_id in self.export_plugins:
            raise PluginError(f"Export plugin '{plugin.plugin_id}' already registered")
        
        self.export_plugins[plugin.plugin_id] = plugin
        print(f"✅ Registered export plugin: {plugin.name} v{plugin.version}")
    
    async def find_import_plugin(self, url: str) -> Optional[ImportPlugin]:
        """Find appropriate import plugin for URL."""
        for plugin in self.import_plugins.values():
            if await plugin.can_handle(url):
                return plugin
        return None
    
    async def find_export_plugin(
        self,
        format: ExportFormat
    ) -> Optional[ExportPlugin]:
        """Find export plugin for format."""
        for plugin in self.export_plugins.values():
            if plugin.export_format == format:
                return plugin
        return None
    
    def get_import_plugin(self, plugin_id: str) -> Optional[ImportPlugin]:
        """Get import plugin by ID."""
        return self.import_plugins.get(plugin_id)
    
    def get_export_plugin(self, plugin_id: str) -> Optional[ExportPlugin]:
        """Get export plugin by ID."""
        return self.export_plugins.get(plugin_id)
    
    def list_import_plugins(self) -> List[ImportPlugin]:
        """List all registered import plugins."""
        return list(self.import_plugins.values())
    
    def list_export_plugins(self) -> List[ExportPlugin]:
        """List all registered export plugins."""
        return list(self.export_plugins.values())
    
    def _load_config(self) -> Dict:
        """Load plugin configuration from YAML."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def _load_plugin(
        self,
        config: Dict,
        plugin_type: PluginType
    ):
        """Dynamically load plugin from class path."""
        class_path = config["class"]
        module_path, class_name = class_path.rsplit(".", 1)
        
        # Import module dynamically
        import importlib
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        
        # Instantiate plugin with dependencies
        plugin = plugin_class(
            job_manager=self.job_manager,
            minio_repo=self.minio_repo,
            postgres_repo=self.postgres_repo,
            neo4j_repo=self.neo4j_repo,
            redis_repo=self.redis_repo,
            qdrant_repo=self.qdrant_repo
        )
        
        # Call on_load hook
        await plugin.on_load(config.get("config", {}))
        
        return plugin
```

---

## 🌐 Unified API Endpoints

```python
# app/api/plugin_endpoints.py

from fastapi import APIRouter, HTTPException
from typing import List, Optional

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# ============================================================
# IMPORT (Ingestion)
# ============================================================

@router.post("/import")
async def import_content(
    url: str,
    plugin_id: Optional[str] = None,
    priority: int = 5,
    metadata: Optional[dict] = None
):
    """
    Import content using appropriate plugin.
    
    If plugin_id not specified, auto-detect from URL.
    """
    # Find plugin
    if plugin_id:
        plugin = registry.get_import_plugin(plugin_id)
        if not plugin:
            raise HTTPException(404, f"Import plugin not found: {plugin_id}")
    else:
        plugin = await registry.find_import_plugin(url)
        if not plugin:
            raise HTTPException(400, f"No plugin can handle URL: {url}")
    
    # Create job
    job_id = f"import_{uuid4().hex[:12]}"
    
    # Start import (async)
    asyncio.create_task(
        plugin.import_content(url, job_id, priority, metadata)
    )
    
    return {
        "job_id": job_id,
        "plugin": plugin.plugin_id,
        "status": "queued",
        "url": url
    }

# ============================================================
# EXPORT (Generation)
# ============================================================

@router.post("/export")
async def export_content(
    source_ids: List[str],
    format: str,
    parameters: Optional[dict] = None,
    metadata: Optional[dict] = None
):
    """
    Generate/export content from library.
    
    Examples:
        - Podcast: format="podcast", source_ids=["doc1", "doc2"]
        - Video: format="video", source_ids=["article1"]
        - Ebook: format="ebook", source_ids=["doc1", "doc2", "doc3"]
    """
    # Find plugin
    export_format = ExportFormat(format)
    plugin = await registry.find_export_plugin(export_format)
    if not plugin:
        raise HTTPException(404, f"No export plugin for format: {format}")
    
    # Validate sources
    valid = await plugin.validate_sources(source_ids)
    if not valid:
        raise HTTPException(400, "Invalid source IDs")
    
    # Create job
    job_id = f"export_{uuid4().hex[:12]}"
    
    # Create request
    request = ExportRequest(
        source_ids=source_ids,
        format=export_format,
        parameters=parameters or {},
        metadata=metadata
    )
    
    # Start generation (async)
    asyncio.create_task(
        plugin.generate_content(request, job_id)
    )
    
    return {
        "job_id": job_id,
        "plugin": plugin.plugin_id,
        "format": format,
        "status": "queued",
        "source_ids": source_ids
    }

# ============================================================
# PLUGIN MANAGEMENT
# ============================================================

@router.get("/import")
async def list_import_plugins():
    """List all registered import plugins."""
    plugins = registry.list_import_plugins()
    return [
        {
            "plugin_id": p.plugin_id,
            "name": p.name,
            "version": p.version,
            "import_type": p.import_type.value
        }
        for p in plugins
    ]

@router.get("/export")
async def list_export_plugins():
    """List all registered export plugins."""
    plugins = registry.list_export_plugins()
    return [
        {
            "plugin_id": p.plugin_id,
            "name": p.name,
            "version": p.version,
            "export_format": p.export_format.value
        }
        for p in plugins
    ]

@router.get("/import/{plugin_id}")
async def get_import_plugin_info(plugin_id: str):
    """Get detailed information about import plugin."""
    plugin = registry.get_import_plugin(plugin_id)
    if not plugin:
        raise HTTPException(404, "Plugin not found")
    
    return {
        "plugin_id": plugin.plugin_id,
        "name": plugin.name,
        "version": plugin.version,
        "import_type": plugin.import_type.value,
        "description": plugin.__doc__
    }

@router.get("/export/{plugin_id}")
async def get_export_plugin_info(plugin_id: str):
    """Get detailed information about export plugin."""
    plugin = registry.get_export_plugin(plugin_id)
    if not plugin:
        raise HTTPException(404, "Plugin not found")
    
    return {
        "plugin_id": plugin.plugin_id,
        "name": plugin.name,
        "version": plugin.version,
        "export_format": plugin.export_format.value,
        "description": plugin.__doc__
    }
```

---

## 🎯 Benefits of Bidirectional Plugin System

### 1. **Extensibility**
- ✅ Add new import sources by creating import plugin
- ✅ Add new export formats by creating export plugin
- ✅ No changes to core system required

### 2. **Consistency**
- ✅ All imports use same infrastructure (JobManager, status tracking, retry)
- ✅ All exports use same infrastructure
- ✅ Same API patterns for all operations

### 3. **Decoupling**
- ✅ Core system doesn't know about specific formats
- ✅ Plugins are independent and testable
- ✅ Easy to disable/enable plugins

### 4. **Marketplace Potential**
- ✅ Community can create plugins
- ✅ Commercial plugins possible
- ✅ Plugin versioning and updates

### 5. **Configuration-Driven**
- ✅ Enable/disable via YAML config
- ✅ Plugin-specific configuration
- ✅ Environment-specific settings

---

## 📝 Summary

**Bidirectional Plugin Architecture** creates:
- **Import Plugins**: External → Library (YouTube, PDFs, web pages)
- **Export Plugins**: Library → External (Podcasts, videos, ebooks)
- **Shared Infrastructure**: Job queue, status tracking, retry, CRUD
- **Unified API**: Single interface for all operations

**Result**: Scalable, extensible, maintainable system where adding new import/export capabilities is as simple as creating a new plugin! 🚀
