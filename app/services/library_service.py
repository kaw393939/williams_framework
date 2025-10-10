"""
LibraryService - Tier-based library management and semantic search.

This service manages the content library with quality-based tier organization,
semantic search capabilities, and comprehensive statistics.
"""
import asyncio
import json
from typing import Optional
from datetime import datetime, timedelta
import uuid
from uuid import uuid4
from pathlib import Path

from pydantic import HttpUrl
from app.core.models import ProcessedContent, LibraryFile, SearchResult, LibraryStats
from app.core.types import ContentSource
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.redis_repository import RedisRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.minio_repository import MinIORepository


# Placeholder function for embedding generation
async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text (placeholder)."""
    raise NotImplementedError("Embedding generation not yet implemented")


class LibraryService:
    """
    Service for managing the quality-tiered content library.
    
    Handles:
    - Adding content to library with tier assignment
    - Retrieving content by tier
    - Moving content between tiers
    - Semantic search across library
    - Library statistics and analytics
    """
    
    def __init__(
        self,
        postgres_repo: PostgresRepository,
        redis_repo: RedisRepository,
        qdrant_repo: QdrantRepository,
        minio_repo: MinIORepository
    ):
        """
        Initialize LibraryService with repositories.
        
        Args:
            postgres_repo: PostgreSQL repository for metadata
            redis_repo: Redis repository for caching
            qdrant_repo: Qdrant repository for vector search
            minio_repo: MinIO repository for file storage
        """
        self.postgres_repo = postgres_repo
        self.redis_repo = redis_repo
        self.qdrant_repo = qdrant_repo
        self.minio_repo = minio_repo
    
    async def add_to_library(self, content: ProcessedContent) -> LibraryFile:
        """
        Add processed content to the library.
        
        Args:
            content: Processed content to add
            
        Returns:
            LibraryFile representing the added content
        """
        # Determine tier based on quality score
        quality = content.screening_result.estimated_quality
        if quality >= 9.0:
            tier = "tier-a"
        elif quality >= 7.0:
            tier = "tier-b"
        elif quality >= 5.0:
            tier = "tier-c"
        else:
            tier = "tier-d"
        
        # Create file key from URL
        file_key = f"{str(content.url).replace('://', '_').replace('/', '_')}.json"
        file_path = f"librarian-{tier}/{file_key}"
        
        # Store in MinIO (tier-based bucket)
        content_json = content.model_dump_json()
        # Extract tier letter (e.g., "tier-b" -> "b") for bucket naming
        tier_letter = tier.split('-')[1]
        await asyncio.to_thread(
            self.minio_repo.upload_to_tier,
            key=file_key,
            content=content_json,
            tier=tier_letter,
            bucket_prefix=self.minio_repo.bucket_name.replace('-tier-a', '').replace('-tier-b', '').replace('-tier-c', '').replace('-tier-d', '').replace('-a', '').replace('-b', '').replace('-c', '').replace('-d', ''),
            metadata={
                'quality_score': str(quality),
                'title': content.title,
                'tier': tier
            }
        )
        
        # Generate embedding for vector search
        embedding_text = f"{content.title} {content.summary} {' '.join(content.key_points)}"
        embedding = await generate_embedding(embedding_text)
        
        # Store in Qdrant (use UUID derived from URL)
        content_uuid = uuid.uuid5(uuid.NAMESPACE_URL, str(content.url))
        await asyncio.to_thread(
            self.qdrant_repo.add,
            content_id=str(content_uuid),
            vector=embedding,
            metadata={
                'url': str(content.url),
                'title': content.title,
                'summary': content.summary,
                'tags': content.tags,
                'tier': tier,
                'quality_score': quality,
                'source_type': content.source_type.value
            }
        )
        
        # Store metadata in PostgreSQL
        record_id = str(uuid4())
        await self.postgres_repo.create_processing_record(
            record_id=record_id,
            content_url=str(content.url),
            operation="add_to_library",
            status="completed",
            metadata=json.dumps({
                'title': content.title,
                'tier': tier,
                'quality_score': quality,
                'file_path': file_path
            })
        )
        
        # Create and return LibraryFile
        return LibraryFile(
            file_path=Path(file_path),
            url=content.url,
            source_type=content.source_type,
            tier=tier,
            quality_score=quality,
            title=content.title,
            summary=content.summary,
            tags=content.tags,
            created_at=datetime.now()
        )
    
    async def get_files_by_tier(
        self,
        tier: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[LibraryFile]:
        """
        Get files from a specific quality tier.
        
        Args:
            tier: Tier to retrieve (a, b, c, d)
            limit: Maximum number of files to return
            offset: Offset for pagination
            
        Returns:
            List of LibraryFile objects
        """
        # Query PostgreSQL for files in the tier
        query = """
            SELECT content_url, metadata
            FROM processing_records
            WHERE operation = 'add_to_library'
            AND status = 'completed'
            AND metadata->>'tier' = $1
            ORDER BY started_at DESC
            LIMIT $2 OFFSET $3
        """
        
        records = await self.postgres_repo.fetch_all(query, tier, limit, offset)
        
        library_files = []
        for record in records:
            # Parse metadata if it's a string
            metadata = record['metadata']
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            library_files.append(LibraryFile(
                file_path=Path(metadata.get('file_path', '')),
                url=HttpUrl(record['content_url']),
                source_type=ContentSource.WEB,  # Default, could be in metadata
                tier=tier,
                quality_score=float(metadata.get('quality_score', 0)),
                title=metadata.get('title', 'Unknown'),
                summary=metadata.get('summary', ''),
                tags=metadata.get('tags', []),
                created_at=datetime.now()  # Could get from record
            ))
        
        return library_files
    
    async def move_between_tiers(
        self,
        file_id: str,
        from_tier: str,
        to_tier: str
    ) -> LibraryFile:
        """
        Move a file from one tier to another.
        
        Args:
            file_id: File identifier (usually URL)
            from_tier: Current tier
            to_tier: Target tier
            
        Returns:
            Updated LibraryFile
        """
        # Get current file metadata from PostgreSQL
        query = """
            SELECT metadata
            FROM processing_records
            WHERE content_url = $1
            AND operation = 'add_to_library'
            AND metadata->>'tier' = $2
            LIMIT 1
        """
        
        record = await self.postgres_repo.fetch_one(query, file_id, from_tier)
        if not record:
            raise ValueError(f"File {file_id} not found in tier {from_tier}")
        
        metadata = record['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        file_key = f"{file_id.replace('://', '_').replace('/', '_')}.json"
        
        # Move file in MinIO
        # Extract tier letters (e.g., "tier-b" -> "b") for bucket naming
        from_tier_letter = from_tier.split('-')[1]
        to_tier_letter = to_tier.split('-')[1]
        # Get bucket prefix - if bucket name ends with a tier letter (a/b/c/d), strip it
        bucket_name = self.minio_repo.bucket_name
        if bucket_name.endswith('-a') or bucket_name.endswith('-b') or bucket_name.endswith('-c') or bucket_name.endswith('-d'):
            bucket_prefix = bucket_name.rsplit('-', 1)[0]
        else:
            bucket_prefix = bucket_name
        from_bucket = f"{bucket_prefix}-{from_tier_letter}"
        to_bucket = f"{bucket_prefix}-{to_tier_letter}"
        
        # Download from old bucket
        original_bucket = self.minio_repo.bucket_name
        self.minio_repo.bucket_name = from_bucket
        content = self.minio_repo.download_file(file_key)
        self.minio_repo.bucket_name = original_bucket
        
        if content:
            # Upload to new bucket
            await asyncio.to_thread(
                self.minio_repo.upload_to_tier,
                key=file_key,
                content=content,
                tier=to_tier_letter,
                bucket_prefix=bucket_prefix,
                metadata={
                    **metadata,
                    'tier': to_tier
                }
            )
            
            # Delete from old bucket
            self.minio_repo.bucket_name = from_bucket
            try:
                self.minio_repo.delete_file(file_key)
            except:
                pass
            self.minio_repo.bucket_name = original_bucket
        
        # Update PostgreSQL metadata
        update_query = """
            UPDATE processing_records
            SET metadata = jsonb_set(metadata, '{tier}', $3::jsonb)
            WHERE content_url = $1
            AND operation = 'add_to_library'
            AND metadata->>'tier' = $2
        """
        
        await self.postgres_repo.execute(update_query, file_id, from_tier, json.dumps(to_tier))
        
        # Update Qdrant metadata
        try:
            # Would need to update Qdrant metadata here
            # For now, just continue
            pass
        except:
            pass
        
        # Return updated LibraryFile
        new_file_path = f"librarian-{to_tier}/{file_key}"
        metadata['tier'] = to_tier
        metadata['file_path'] = new_file_path
        
        return LibraryFile(
            file_path=Path(new_file_path),
            url=HttpUrl(file_id),
            source_type=ContentSource.WEB,
            tier=to_tier,
            quality_score=float(metadata.get('quality_score', 0)),
            title=metadata.get('title', 'Unknown'),
            summary=metadata.get('summary', ''),
            tags=metadata.get('tags', []),
            created_at=datetime.now()
        )
    
    async def search_library(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: int = 10
    ) -> list[SearchResult]:
        """
        Search library using semantic search.
        
        Args:
            query: Search query text
            filters: Optional filters (tier, quality_range, tags)
            limit: Maximum results to return
            
        Returns:
            List of SearchResult objects
        """
        # Check cache first
        cache_key = f"library_search:{query}:{json.dumps(filters or {})}:{limit}"
        cached = await self.redis_repo.get(cache_key)
        if cached:
            results_data = json.loads(cached)
            return [SearchResult(**r) for r in results_data]
        
        # Generate query embedding
        query_embedding = await generate_embedding(query)
        
        # Build Qdrant filter
        qdrant_filter = None
        if filters:
            # Apply tier filter if specified
            if 'tier' in filters:
                qdrant_filter = {'tier': filters['tier']}
        
        # Search in Qdrant
        search_results = await asyncio.to_thread(
            self.qdrant_repo.query,
            query_vector=query_embedding,
            limit=limit,
            filter_conditions=qdrant_filter
        )
        
        # Convert to SearchResult objects
        results = []
        for result in search_results:
            metadata = result.get('metadata', {})
            
            results.append(SearchResult(
                file_path=metadata.get('url', ''),
                url=metadata.get('url', ''),
                title=metadata.get('title', 'Unknown'),
                summary=metadata.get('summary', ''),
                tags=metadata.get('tags', []),
                tier=metadata.get('tier', 'unknown'),
                quality_score=float(metadata.get('quality_score', 0.0)),
                relevance_score=float(result.get('score', 0.0)),
                matched_content=metadata.get('summary', '')[:200] if metadata.get('summary') else ''
            ))
        
        # Cache results for 1 hour
        results_json = [r.model_dump() for r in results]
        await self.redis_repo.set(cache_key, json.dumps(results_json), ttl=3600)
        
        return results
    
    async def get_statistics(self) -> LibraryStats:
        """
        Get comprehensive library statistics.
        
        Returns:
            LibraryStats with counts, averages, and metrics
        """
        # Get all library files from PostgreSQL
        query = """
            SELECT 
                metadata->>'tier' as tier,
                (metadata->>'quality_score')::float as quality_score,
                metadata->>'tags' as tags,
                started_at
            FROM processing_records
            WHERE operation = 'add_to_library'
            AND status = 'completed'
        """
        
        records = await self.postgres_repo.fetch_all(query)
        
        if not records:
            return LibraryStats(
                total_files=0,
                files_by_tier={},
                average_quality=0.0,
                total_tags=0,
                recent_additions=0,
                storage_size_mb=0.0
            )
        
        # Calculate statistics
        total_files = len(records)
        files_by_tier = {}
        quality_scores = []
        all_tags = set()
        recent_additions = 0
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        for record in records:
            # Count by tier
            tier = record.get('tier', 'unknown')
            files_by_tier[tier] = files_by_tier.get(tier, 0) + 1
            
            # Collect quality scores
            if record.get('quality_score') is not None:
                quality_scores.append(float(record['quality_score']))
            
            # Collect unique tags
            tags_str = record.get('tags')
            if tags_str:
                try:
                    if isinstance(tags_str, str):
                        tags = json.loads(tags_str)
                    else:
                        tags = tags_str
                    all_tags.update(tags)
                except:
                    pass
            
            # Count recent additions
            if record.get('started_at'):
                if record['started_at'] >= seven_days_ago:
                    recent_additions += 1
        
        # Calculate average quality
        average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return LibraryStats(
            total_files=total_files,
            files_by_tier=files_by_tier,
            average_quality=average_quality,
            total_tags=len(all_tags),
            recent_additions=recent_additions,
            storage_size_mb=0.0  # Would need MinIO integration for accurate size
        )
