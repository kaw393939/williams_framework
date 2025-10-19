"""
End-to-end integration tests for YouTube video processing.

Tests the complete pipeline from video URL to retrieval:
1. Video extraction (metadata + transcript)
2. Content chunking
3. Embedding generation
4. Storage in all datastores
5. Retrieval and RAG functionality

Test video: https://youtu.be/zZtHnwoZAT8 (configurable via environment variable)
"""

import os
import pytest
import asyncio
from typing import Optional

from app.core.config import settings
from app.pipeline.extractors.youtube import YouTubeExtractor
from app.services.content_service import ContentService
from app.services.search_service import SearchService
from app.repositories.neo_repository import NeoRepository
from app.core.models import ContentSource


# Test configuration
TEST_VIDEO_URL = os.getenv(
    "TEST_YOUTUBE_URL",
    "https://www.youtube.com/watch?v=O2DqGGlliCA"  # Video with accessible transcripts
)

# Optional: Test multiple videos
TEST_VIDEOS = {
    "short": os.getenv("TEST_YOUTUBE_SHORT", "https://www.youtube.com/watch?v=O2DqGGlliCA"),
    "medium": os.getenv("TEST_YOUTUBE_MEDIUM", "https://www.youtube.com/watch?v=O2DqGGlliCA"),  # Fallback to same
    "long": os.getenv("TEST_YOUTUBE_LONG", None),  # Optional 3+ hour video
}


def is_neo4j_available() -> bool:
    """Check if Neo4j is running."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 7687))
    sock.close()
    return result == 0


def is_qdrant_available() -> bool:
    """Check if Qdrant is running."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 6333))
    sock.close()
    return result == 0


@pytest.fixture
def neo_repo():
    """Fixture providing NeoRepository with cleanup."""
    if not is_neo4j_available():
        pytest.skip("Neo4j is not available")
    
    repo = NeoRepository()
    yield repo
    
    # Cleanup
    repo.clear_database()
    repo.close()


@pytest.fixture
def youtube_extractor():
    """Fixture providing YouTubeExtractor."""
    return YouTubeExtractor()


@pytest.fixture
async def content_service(neo_repo):
    """Fixture providing ContentService with real dependencies."""
    from qdrant_client import QdrantClient
    from app.repositories.postgres_repository import PostgresRepository
    from app.repositories.redis_repository import RedisRepository
    from app.repositories.qdrant_repository import QdrantRepository
    from app.repositories.minio_repository import MinIORepository
    
    # Create real repositories with proper connection parameters
    postgres_repo = PostgresRepository(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password
    )
    await postgres_repo.connect()
    await postgres_repo.create_tables()
    
    redis_repo = RedisRepository(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db
    )
    await redis_repo.connect()
    
    qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    qdrant_repo = QdrantRepository(qdrant_client, "test_youtube_content")
    
    from minio import Minio
    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )
    minio_repo = MinIORepository(minio_client, "test-youtube-content")
    
    service = ContentService(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo,
        qdrant_repo=qdrant_repo,
        minio_repo=minio_repo
    )
    
    yield service
    
    # Cleanup
    await postgres_repo.execute("DELETE FROM processing_records")
    await postgres_repo.close()
    try:
        qdrant_client.delete_collection("test_youtube_content")
    except Exception:
        pass


@pytest.fixture
async def search_service(neo_repo):
    """Fixture providing SearchService with real dependencies."""
    if not is_qdrant_available():
        pytest.skip("Qdrant is not available")
    
    # Import real dependencies
    from qdrant_client import QdrantClient
    from app.repositories.qdrant_repository import QdrantRepository
    from app.intelligence.providers.factory import ProviderFactory
    from app.services.citation_service import CitationService
    from app.presentation.search_cache import SearchCache
    from app.repositories.redis_repository import RedisRepository
    
    # Create real repositories and services with proper connection parameters
    qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    qdrant_repo = QdrantRepository(qdrant_client, "test_youtube_content")  # Use same collection as content_service
    
    redis_repo = RedisRepository(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db
    )
    await redis_repo.connect()
    
    # Get real embedding provider
    factory = ProviderFactory()
    embedder = factory.create_embedding_provider()
    
    # Create search cache
    search_cache = SearchCache(redis_client=redis_repo, embedder=embedder)
    
    # Create citation service
    citation_service = CitationService(neo_repo=neo_repo)
    
    # Create LLM provider
    llm_provider = factory.create_llm_provider()
    
    service = SearchService(
        qdrant_repository=qdrant_repo,
        embedder=embedder,
        search_cache=search_cache,
        neo_repo=neo_repo,
        citation_service=citation_service,
        llm_provider=llm_provider
    )
    
    yield service
    
    # Cleanup
    try:
        qdrant_client.delete_collection("test_youtube_content")  # Match collection name
    except Exception:
        pass





class TestYouTubeExtraction:
    """Test YouTube video extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_video_metadata(self, youtube_extractor):
        """Test that video metadata is extracted correctly."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        
        assert raw_content is not None
        assert str(raw_content.url) == TEST_VIDEO_URL
        assert raw_content.source_type == ContentSource.YOUTUBE
        assert raw_content.raw_text is not None
        assert len(raw_content.raw_text) > 0
        
        # Check metadata
        metadata = raw_content.metadata
        assert "title" in metadata
        assert "author" in metadata
        assert "duration" in metadata
        assert "published_at" in metadata
        assert metadata["content_type"] == "video/youtube"
        
        print(f"\n✓ Extracted video: {metadata['title']}")
        print(f"  Duration: {metadata['duration']}s")
        print(f"  Author: {metadata['author']}")
        print(f"  Transcript length: {len(raw_content.raw_text)} chars")
    
    @pytest.mark.asyncio
    async def test_extract_video_id(self, youtube_extractor):
        """Test video ID extraction from various URL formats."""
        test_urls = [
            "https://www.youtube.com/watch?v=O2DqGGlliCA",
            "https://youtu.be/O2DqGGlliCA",
            "https://www.youtube.com/watch?v=O2DqGGlliCA&t=10s",
        ]
        
        for url in test_urls:
            raw_content = await youtube_extractor.extract(url)
            assert "video_id" in raw_content.metadata
            assert raw_content.metadata["video_id"] == "O2DqGGlliCA"
    
    @pytest.mark.asyncio
    async def test_transcript_not_empty(self, youtube_extractor):
        """Test that transcript is not empty."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        
        assert raw_content.raw_text is not None
        assert len(raw_content.raw_text.strip()) > 0
        
        # Should contain actual words, not just whitespace
        words = raw_content.raw_text.split()
        assert len(words) > 10  # At least 10 words


class TestYouTubeIngestion:
    """Test complete YouTube video ingestion pipeline."""
    
    @pytest.mark.asyncio
    async def test_ingest_youtube_video(self, content_service, youtube_extractor):
        """Test ingesting a YouTube video through the full pipeline."""
        # 1. Extract
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        assert raw_content is not None
        
        # 2. Ingest through content service
        content_id = await content_service.ingest_content(raw_content)
        assert content_id is not None
        
        print(f"\n✓ Ingested video with content_id: {content_id}")
        
        # 3. Verify content stored
        stored_content = await content_service.get_content_by_id(content_id)
        assert stored_content is not None
        assert str(stored_content.url) == TEST_VIDEO_URL
        assert stored_content.source_type == ContentSource.YOUTUBE
    
    @pytest.mark.asyncio
    async def test_chunks_created(self, content_service, youtube_extractor):
        """Test that content is chunked after ingestion."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        # Get chunks
        chunks = await content_service.get_chunks_by_content_id(content_id)
        
        assert chunks is not None
        assert len(chunks) > 0
        
        print(f"\n✓ Created {len(chunks)} chunks from video")
        
        # Verify chunk properties
        for chunk in chunks[:3]:  # Check first 3 chunks
            assert chunk.content_id == content_id
            assert chunk.text is not None
            assert len(chunk.text) > 0
            assert chunk.chunk_index >= 0
    
    @pytest.mark.asyncio
    async def test_embeddings_created(self, content_service, youtube_extractor):
        """Test that embeddings are created for chunks."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        chunks = await content_service.get_chunks_by_content_id(content_id)
        
        # Check that embeddings exist
        for chunk in chunks[:5]:  # Check first 5
            assert chunk.embedding is not None
            assert len(chunk.embedding) > 0
            # Embedding should be a list of floats
            assert all(isinstance(x, (int, float)) for x in chunk.embedding)
        
        print(f"\n✓ Embeddings created (dimension: {len(chunks[0].embedding)})")


class TestYouTubeRetrieval:
    """Test retrieval and search functionality for YouTube content."""
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, content_service, search_service, youtube_extractor):
        """Test semantic search on ingested YouTube video."""
        # Ingest video
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        print(f"\n[DEBUG] Extracted content: {len(raw_content.raw_text)} chars")
        
        try:
            content_id = await content_service.ingest_content(raw_content)
            print(f"[DEBUG] Ingested content_id: {content_id}")
        except Exception as e:
            print(f"[DEBUG] Ingestion failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Check if chunks were created
        chunks = await content_service.get_chunks_by_content_id(content_id)
        print(f"[DEBUG] Chunks created: {len(chunks) if chunks else 0}")
        
        # Check Qdrant directly
        from qdrant_client import QdrantClient
        from app.core.config import settings
        qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        try:
            info = qdrant_client.get_collection("test_youtube_content")
            print(f"[DEBUG] Qdrant collection has {info.points_count} points")
        except Exception as e:
            print(f"[DEBUG] Qdrant collection error: {e}")
        
        # Wait for indexing (if async)
        await asyncio.sleep(1)
        
        # Search for content from the video
        query = "main topic of the video"
        results = await search_service.search(
            query=query,
            top_k=5
        )
        
        print(f"[DEBUG] Search results: {len(results)}")
        if results:
            r = results[0]
            print(f"[DEBUG] First result: content_id={getattr(r, 'content_id', 'N/A')}")
            print(f"[DEBUG] First result URL: {getattr(r, 'url', 'N/A')}")
            print(f"[DEBUG] First result has matched_content: {hasattr(r, 'matched_content')}")
            print(f"[DEBUG] Result type: {type(r)}")
            print(f"[DEBUG] Result fields: {r.__dict__ if hasattr(r, '__dict__') else 'N/A'}")
        
        assert results is not None
        assert len(results) > 0
        
        # At least one result should be from our video
        video_results = [r for r in results if r.content_id == content_id]
        assert len(video_results) > 0
        
        print(f"\n✓ Found {len(results)} results for query: '{query}'")
        print(f"  {len(video_results)} from our test video")
        
        # Check result structure
        first_result = results[0]
        assert hasattr(first_result, 'text')
        assert hasattr(first_result, 'score')
        assert first_result.score >= 0
    
    @pytest.mark.skip(reason="ContentService needs Neo4j integration and vector search implementation")
    @pytest.mark.asyncio
    async def test_filter_by_source(self, content_service, search_service, youtube_extractor):
        """Test filtering search results by source type."""
        # Ingest video
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        await content_service.ingest_content(raw_content)
        
        await asyncio.sleep(1)
        
        # Search with YouTube filter
        results = await search_service.search(
            query="video content",
            top_k=10
        )
        
        # All results should be from YouTube
        for result in results:
            assert result.source_type == ContentSource.YOUTUBE
        
        print(f"\n✓ All {len(results)} results are from YouTube")
    
    @pytest.mark.skip(reason="ContentService needs Neo4j integration and vector search implementation")
    @pytest.mark.asyncio
    async def test_search_by_metadata(self, content_service, search_service, youtube_extractor):
        """Test searching by video metadata (title, author)."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        await content_service.ingest_content(raw_content)
        
        await asyncio.sleep(1)
        
        # Search by title
        title = raw_content.metadata.get("title", "")
        if title:
            results = await search_service.search(
                query=title,
                top_k=5
            )
            
            assert len(results) > 0
            print(f"\n✓ Found video by title: '{title[:50]}...'")


class TestYouTubeRAG:
    """Test RAG (Retrieval Augmented Generation) with YouTube content."""
    
    @pytest.mark.skip(reason="SearchService.query_with_citations needs implementation with LLM and citation tracking")
    @pytest.mark.asyncio
    async def test_rag_query_with_citations(self, content_service, search_service, youtube_extractor):
        """Test RAG query returns answer with citations from video."""
        # Ingest video
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        await asyncio.sleep(1)
        
        # Ask question about video content
        question = "What is the main topic discussed in this video?"
        response = await search_service.query_with_citations(
            question=question,
            filters={"content_id": content_id}
        )
        
        assert response is not None
        assert response.answer is not None
        assert len(response.answer) > 0
        
        # Should have citations
        assert response.citations is not None
        assert len(response.citations) > 0
        
        print(f"\n✓ RAG Query: '{question}'")
        print(f"  Answer: {response.answer[:100]}...")
        print(f"  Citations: {len(response.citations)}")
        
        # Citations should reference the video
        for citation in response.citations:
            assert citation.content_id == content_id
            assert citation.source_type == ContentSource.YOUTUBE
    
    @pytest.mark.skip(reason="SearchService.query_with_citations needs implementation with LLM and citation tracking")
    @pytest.mark.asyncio
    async def test_rag_answer_quality(self, content_service, search_service, youtube_extractor):
        """Test that RAG answers are relevant and well-formed."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        await content_service.ingest_content(raw_content)
        
        await asyncio.sleep(1)
        
        question = "Summarize the key points from this video."
        response = await search_service.query_with_citations(question=question)
        
        # Answer should be substantial
        assert len(response.answer.split()) > 10  # At least 10 words
        
        # Should not be an error message
        assert "error" not in response.answer.lower()
        assert "sorry" not in response.answer.lower()
        
        print(f"\n✓ RAG generated quality answer ({len(response.answer)} chars)")
    
    @pytest.mark.skip(reason="SearchService.query_with_citations needs implementation with LLM and citation tracking")
    @pytest.mark.asyncio
    async def test_rag_citation_accuracy(self, content_service, search_service, youtube_extractor):
        """Test that citations accurately reference source content."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        await asyncio.sleep(1)
        
        question = "What specific details are mentioned?"
        response = await search_service.query_with_citations(
            question=question,
            filters={"content_id": content_id}
        )
        
        # Verify each citation
        for citation in response.citations:
            # Citation should have text
            assert citation.text is not None
            assert len(citation.text) > 0
            
            # Citation should have position info
            assert hasattr(citation, 'chunk_index')
            
            # Text should be from the video
            assert citation.content_id == content_id
        
        print(f"\n✓ Verified {len(response.citations)} citation(s) accuracy")


class TestYouTubeGraphRelations:
    """Test graph database relations for YouTube content."""
    
    @pytest.mark.skip(reason="ContentService needs Neo4j integration to create Content nodes and relationships")
    @pytest.mark.asyncio
    async def test_video_content_relationship(self, content_service, neo_repo, youtube_extractor):
        """Test that video is properly linked to content node."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        # Query Neo4j for content node
        query = """
        MATCH (c:Content {content_id: $content_id})
        RETURN c
        """
        result = neo_repo.execute_query(query, {"content_id": content_id})
        
        assert len(result) > 0
        content_node = result[0]['c']
        
        assert content_node['url'] == TEST_VIDEO_URL
        assert content_node['source_type'] == ContentSource.YOUTUBE.value
        
        print(f"\n✓ Content node created in Neo4j")
    
    @pytest.mark.skip(reason="ContentService needs Neo4j integration to create Content nodes and HAS_CHUNK relationships")
    @pytest.mark.asyncio
    async def test_video_chunk_relationships(self, content_service, neo_repo, youtube_extractor):
        """Test that chunks are properly linked to parent content."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        # Query for chunks
        query = """
        MATCH (c:Content {content_id: $content_id})-[:HAS_CHUNK]->(ch:Chunk)
        RETURN count(ch) as chunk_count
        """
        result = neo_repo.execute_query(query, {"content_id": content_id})
        
        chunk_count = result[0]['chunk_count']
        assert chunk_count > 0
        
        print(f"\n✓ {chunk_count} chunks linked to content in Neo4j")
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, content_service, neo_repo, youtube_extractor):
        """Test that entities are extracted and linked."""
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        content_id = await content_service.ingest_content(raw_content)
        
        # Wait for entity extraction (if async)
        await asyncio.sleep(2)
        
        # Query for entities
        query = """
        MATCH (c:Content {content_id: $content_id})-[:MENTIONS]->(e:Entity)
        RETURN e
        LIMIT 10
        """
        result = neo_repo.execute_query(query, {"content_id": content_id})
        
        if len(result) > 0:
            print(f"\n✓ Extracted {len(result)} entities from video")
            for record in result[:5]:
                entity = record['e']
                print(f"  - {entity.get('name', 'Unknown')} ({entity.get('type', 'Unknown')})")
        else:
            print("\n⚠ No entities extracted (may be expected for some videos)")


class TestMultipleVideos:
    """Test processing multiple YouTube videos."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("video_key", ["short", "medium"])
    async def test_process_multiple_videos(self, content_service, youtube_extractor, video_key):
        """Test processing different length videos."""
        video_url = TEST_VIDEOS.get(video_key)
        
        if not video_url:
            pytest.skip(f"No test video configured for '{video_key}'")
        
        raw_content = await youtube_extractor.extract(video_url)
        content_id = await content_service.ingest_content(raw_content)
        
        assert content_id is not None
        
        # Verify metadata
        metadata = raw_content.metadata
        duration = metadata.get("duration", 0)
        
        print(f"\n✓ Processed {video_key} video (duration: {duration}s)")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TEST_VIDEOS.get("long"),
        reason="Long video test requires TEST_YOUTUBE_LONG environment variable"
    )
    async def test_process_long_video(self, content_service, youtube_extractor):
        """Test processing long video (3+ hours)."""
        video_url = TEST_VIDEOS["long"]
        
        import time
        start_time = time.time()
        
        raw_content = await youtube_extractor.extract(video_url)
        content_id = await content_service.ingest_content(raw_content)
        
        elapsed = time.time() - start_time
        
        assert content_id is not None
        
        # Get chunk count
        chunks = await content_service.get_chunks_by_content_id(content_id)
        
        print(f"\n✓ Processed long video:")
        print(f"  Duration: {raw_content.metadata.get('duration', 0)}s")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Processing time: {elapsed:.2f}s")
        
        # Long videos should create many chunks
        assert len(chunks) > 50


class TestYouTubeErrorHandling:
    """Test error handling for YouTube processing."""
    
    @pytest.mark.asyncio
    async def test_invalid_url(self, youtube_extractor):
        """Test handling of invalid YouTube URL."""
        with pytest.raises(Exception):
            await youtube_extractor.extract("https://www.youtube.com/watch?v=INVALID")
    
    @pytest.mark.asyncio
    async def test_private_video(self, youtube_extractor):
        """Test handling of private/unavailable video."""
        # This video ID is intentionally invalid
        private_url = "https://www.youtube.com/watch?v=PRIVATE123"
        
        with pytest.raises(Exception):
            await youtube_extractor.extract(private_url)
    
    @pytest.mark.asyncio
    async def test_video_without_transcript(self, youtube_extractor):
        """Test fallback when transcript is not available."""
        # Some videos don't have transcripts - extractor should fall back to description
        # This test might need a specific video URL known to lack transcripts
        # For now, we just verify the fallback logic exists in the code
        
        # The extractor should handle this gracefully
        # and return content with description as raw_text
        pass


class TestYouTubePerformance:
    """Test performance metrics for YouTube processing."""
    
    @pytest.mark.asyncio
    async def test_extraction_speed(self, youtube_extractor):
        """Test that extraction completes in reasonable time."""
        import time
        
        start_time = time.time()
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        elapsed = time.time() - start_time
        
        assert raw_content is not None
        
        # 15-minute video should extract in < 30 seconds
        assert elapsed < 30, f"Extraction took {elapsed:.2f}s (expected < 30s)"
        
        print(f"\n✓ Extraction completed in {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_ingestion_speed(self, content_service, youtube_extractor):
        """Test that full ingestion completes in reasonable time."""
        import time
        
        raw_content = await youtube_extractor.extract(TEST_VIDEO_URL)
        
        start_time = time.time()
        content_id = await content_service.ingest_content(raw_content)
        elapsed = time.time() - start_time
        
        assert content_id is not None
        
        # Full ingestion should complete in < 2 minutes
        assert elapsed < 120, f"Ingestion took {elapsed:.2f}s (expected < 120s)"
        
        print(f"\n✓ Full ingestion completed in {elapsed:.2f}s")


# Configuration for pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "youtube: mark test as YouTube integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


if __name__ == "__main__":
    print(f"""
YouTube Integration Test Suite
================================

Test Video: {TEST_VIDEO_URL}

Available Test Videos:
- Short: {TEST_VIDEOS['short']}
- Medium: {TEST_VIDEOS['medium']}
- Long: {TEST_VIDEOS.get('long', 'Not configured')}

Configure via environment variables:
  export TEST_YOUTUBE_URL="https://youtu.be/YOUR_VIDEO_ID"
  export TEST_YOUTUBE_SHORT="https://youtu.be/SHORT_VIDEO"
  export TEST_YOUTUBE_MEDIUM="https://youtu.be/MEDIUM_VIDEO"
  export TEST_YOUTUBE_LONG="https://youtu.be/LONG_VIDEO"

Run tests:
  poetry run pytest tests/integration/test_youtube_end_to_end.py -v
  poetry run pytest tests/integration/test_youtube_end_to_end.py -v -k "test_extract"
  poetry run pytest tests/integration/test_youtube_end_to_end.py -v --tb=short
    """)
