"""
ContentService: Orchestrates the complete content processing pipeline.

Responsibilities:
1. Extract content from URLs (web scraping)
2. Screen content for quality using AI
3. Process content (summarize, extract key points, generate tags)
4. Store content across all repositories (PostgreSQL, Redis, Qdrant, MinIO)
5. Track processing status and handle errors

This is the main service that ties everything together!
"""
import asyncio
import hashlib
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.repositories.postgres_repository import PostgresRepository
from app.repositories.redis_repository import RedisRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.minio_repository import MinIORepository
from app.core.models import RawContent, ProcessedContent, ScreeningResult
from app.core.types import ContentSource
from app.core.exceptions import ExtractionError, ScreeningError, ValidationError


class ContentService:
    """
    Content processing service that orchestrates the complete pipeline.
    
    Pipeline stages:
    1. Extract: Fetch raw content from URL
    2. Screen: AI quality assessment
    3. Process: Summarize, extract key points, generate tags
    4. Store: Save to all repositories
    """
    
    def __init__(
        self,
        postgres_repo: PostgresRepository,
        redis_repo: RedisRepository,
        qdrant_repo: QdrantRepository,
        minio_repo: MinIORepository
    ):
        """
        Initialize ContentService with all required repositories.
        
        Args:
            postgres_repo: PostgreSQL for metadata
            redis_repo: Redis for caching
            qdrant_repo: Qdrant for vector search
            minio_repo: MinIO for file storage
        """
        self.postgres_repo = postgres_repo
        self.redis_repo = redis_repo
        self.qdrant_repo = qdrant_repo
        self.minio_repo = minio_repo
    
    async def extract_content(self, url: str) -> RawContent:
        """
        Extract raw content from a URL.
        
        Args:
            url: URL to extract content from
            
        Returns:
            RawContent object with extracted data
            
        Raises:
            ExtractionError: If extraction fails
        """
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise ExtractionError(f"Invalid URL: {url}")
        
        record_id = str(uuid4())
        
        try:
            # Create processing record
            await self.postgres_repo.create_processing_record(
                record_id=record_id,
                content_url=url,
                operation="extract",
                status="started"
            )
            
            # Extract content (will be mocked in tests)
            raw_content = await extract_web_content(url)
            
            # Update processing record
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="completed"
            )
            
            return raw_content
            
        except Exception as e:
            # Record failure
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="failed",
                error_message=str(e)
            )
            raise ExtractionError(f"Failed to extract content from {url}: {e}")
    
    async def screen_content(self, raw_content: RawContent) -> ScreeningResult:
        """
        Screen content for quality using AI.
        
        Implements caching to avoid redundant API calls.
        
        Args:
            raw_content: Raw content to screen
            
        Returns:
            ScreeningResult with quality score and decision
            
        Raises:
            ScreeningError: If screening fails
        """
        cache_key = f"screening:{str(raw_content.url)}"
        
        # Check cache first
        cached = await self.redis_repo.get_json(cache_key)
        if cached:
            return ScreeningResult(
                screening_score=cached['screening_score'],
                decision=cached['decision'],
                reasoning=cached['reasoning'],
                estimated_quality=cached['estimated_quality']
            )
        
        record_id = str(uuid4())
        
        try:
            # Create processing record
            await self.postgres_repo.create_processing_record(
                record_id=record_id,
                content_url=str(raw_content.url),
                operation="screen",
                status="started"
            )
            
            # Screen with AI (will be mocked in tests)
            screening_result = await screen_with_ai(raw_content)
            
            # Cache result (1 hour TTL)
            await self.redis_repo.set_json(
                cache_key,
                {
                    'screening_score': screening_result.screening_score,
                    'decision': screening_result.decision,
                    'reasoning': screening_result.reasoning,
                    'estimated_quality': screening_result.estimated_quality
                },
                ttl=3600
            )
            
            # Update processing record
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="completed"
            )
            
            return screening_result
            
        except Exception as e:
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="failed",
                error_message=str(e)
            )
            raise ScreeningError(f"Failed to screen content: {e}")
    
    async def process_content(
        self,
        raw_content: RawContent,
        screening_result: ScreeningResult
    ) -> Optional[ProcessedContent]:
        """
        Process approved content: summarize, extract key points, generate tags.
        
        Args:
            raw_content: Raw content to process
            screening_result: Screening result
            
        Returns:
            ProcessedContent or None if rejected
            
        Raises:
            ValidationError: If processing fails
        """
        # Skip processing for rejected content
        if screening_result.decision == "REJECT":
            return None
        
        record_id = str(uuid4())
        
        try:
            # Create processing record
            await self.postgres_repo.create_processing_record(
                record_id=record_id,
                content_url=str(raw_content.url),
                operation="process",
                status="started"
            )
            
            # Process with AI (will be mocked in tests)
            processed_data = await process_with_ai(raw_content)
            
            # Create ProcessedContent object
            processed = ProcessedContent(
                url=raw_content.url,
                source_type=raw_content.source_type,
                title=raw_content.metadata.get('title', 'Untitled'),
                summary=processed_data['summary'],
                key_points=processed_data['key_points'],
                tags=processed_data['tags'],
                screening_result=screening_result,
                processed_at=datetime.now()
            )
            
            # Update processing record
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="completed"
            )
            
            return processed
            
        except Exception as e:
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="failed",
                error_message=str(e)
            )
            raise ValidationError(f"Failed to process content: {e}")
    
    async def store_content(self, processed: ProcessedContent):
        """
        Store processed content across all repositories.
        
        Storage locations:
        - PostgreSQL: Metadata and processing records
        - Redis: Cache for quick access
        - Qdrant: Vector embeddings for semantic search
        - MinIO: Full content in tier-based buckets
        
        Args:
            processed: Processed content to store
        """
        record_id = str(uuid4())
        
        try:
            # Create processing record
            await self.postgres_repo.create_processing_record(
                record_id=record_id,
                content_url=str(processed.url),
                operation="store",
                status="started"
            )
            
            # Determine tier based on quality score
            quality = processed.screening_result.estimated_quality
            if quality >= 9.0:
                tier = "a"
            elif quality >= 7.0:
                tier = "b"
            elif quality >= 5.0:
                tier = "c"
            else:
                tier = "d"
            
            # Store in MinIO (tier-based)
            content_json = processed.model_dump_json()
            file_key = f"{str(processed.url).replace('://', '_').replace('/', '_')}.json"
            
            await asyncio.to_thread(
                self.minio_repo.upload_to_tier,
                key=file_key,
                content=content_json,
                tier=tier,
                bucket_prefix="librarian",
                metadata={
                    'quality_score': str(quality),
                    'title': processed.title
                }
            )
            
            # Generate embedding for vector search
            embedding = await generate_embedding(processed.summary)
            
            # Store in Qdrant
            content_id = hashlib.md5(str(processed.url).encode()).hexdigest()
            await asyncio.to_thread(
                self.qdrant_repo.add,
                content_id=content_id,
                vector=embedding,
                metadata={
                    'url': str(processed.url),
                    'title': processed.title,
                    'quality_score': quality,
                    'tags': processed.tags,
                    'tier': tier
                }
            )
            
            # Update processing record
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="completed"
            )
            
        except Exception as e:
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="failed",
                error_message=str(e)
            )
            raise
    
    async def process_url(self, url: str) -> ProcessedContent:
        """
        Complete pipeline: extract → screen → process → store.
        
        This is the main entry point for processing a URL.
        
        Args:
            url: URL to process
            
        Returns:
            ProcessedContent with all processing complete
        """
        # Step 1: Extract
        raw_content = await self.extract_content(url)
        
        # Step 2: Screen
        screening_result = await self.screen_content(raw_content)
        
        # Step 3: Process
        processed = await self.process_content(raw_content, screening_result)
        
        if processed is None:
            raise ValidationError(f"Content rejected: {screening_result.reasoning}")
        
        # Step 4: Store
        await self.store_content(processed)
        
        return processed


# Helper functions (will be implemented later, mocked in tests)

async def extract_web_content(url: str) -> RawContent:
    """
    Extract content from a web URL.
    
    TODO: Implement with BeautifulSoup/Playwright.
    For now, this is a placeholder that will be mocked in tests.
    """
    raise NotImplementedError("Web extraction not yet implemented")


async def screen_with_ai(raw_content: RawContent) -> ScreeningResult:
    """
    Screen content using OpenAI API.
    
    TODO: Implement with OpenAI client.
    For now, this is a placeholder that will be mocked in tests.
    """
    raise NotImplementedError("AI screening not yet implemented")


async def process_with_ai(raw_content: RawContent) -> dict:
    """
    Process content using OpenAI API.
    
    TODO: Implement with OpenAI client.
    For now, this is a placeholder that will be mocked in tests.
    """
    raise NotImplementedError("AI processing not yet implemented")


async def generate_embedding(text: str) -> list[float]:
    """
    Generate vector embedding for text.
    
    TODO: Implement with OpenAI embeddings API.
    For now, this is a placeholder that will be mocked in tests.
    """
    raise NotImplementedError("Embedding generation not yet implemented")
