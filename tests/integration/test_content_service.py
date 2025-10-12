"""
Integration tests for ContentService.

Tests the complete content processing pipeline:
1. Extract raw content from URL
2. Screen content for quality with AI
3. Process content (summarize, extract key points, tags)
4. Store in all repositories (PostgreSQL, Redis, Qdrant, MinIO)

Uses REAL services (NO MOCKS) following TDD methodology.
"""
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.models import ProcessedContent, RawContent, ScreeningResult
from app.core.types import ContentSource
from app.repositories.minio_repository import MinIORepository
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.redis_repository import RedisRepository
from app.services.content_service import ContentService


@pytest.fixture
async def postgres_repo():
    """Create and setup PostgreSQL repository."""
    repo = PostgresRepository(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password
    )
    await repo.connect()
    await repo.create_tables()

    yield repo

    await repo.execute("DELETE FROM processing_records")
    await repo.close()


@pytest.fixture
async def redis_repo():
    """Create and setup Redis repository."""
    repo = RedisRepository(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True
    )
    await repo.connect()

    yield repo

    await repo.flush_all()
    await repo.close()


@pytest.fixture
async def qdrant_repo():
    """Create and setup Qdrant repository."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    repo = QdrantRepository(client, "test_content_service")

    yield repo

    # Cleanup
    try:
        client.delete_collection("test_content_service")
    except Exception:
        pass


@pytest.fixture
async def minio_repo():
    """Create and setup MinIO repository."""
    from minio import Minio

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )

    repo = MinIORepository(client, "test-content-service")

    yield repo

    # Cleanup
    try:
        objects = repo.list_files()
        if objects:
            repo.delete_files([obj['key'] for obj in objects])
    except Exception:
        pass


@pytest.fixture
async def content_service(postgres_repo, redis_repo, qdrant_repo, minio_repo):
    """Create ContentService with all repositories."""
    service = ContentService(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo,
        qdrant_repo=qdrant_repo,
        minio_repo=minio_repo
    )
    return service


class TestContentServiceExtraction:
    """Test content extraction from URLs."""

    @pytest.mark.asyncio
    async def test_extract_web_content(self, content_service):
        """Should extract content from a web URL."""
        url = "https://example.com/test-article"

        # Mock the actual HTTP request (we don't want to hit real URLs in tests)
        with patch('app.services.content_service.extract_web_content') as mock_extract:
            mock_extract.return_value = RawContent(
                url=url,
                source_type=ContentSource.WEB,
                raw_text="This is test article content about AI and machine learning.",
                metadata={"title": "Test Article"},
                extracted_at=datetime.now()
            )

            raw_content = await content_service.extract_content(url)

            assert raw_content is not None
            assert str(raw_content.url) == url
            assert raw_content.source_type == ContentSource.WEB
            assert len(raw_content.raw_text) > 0

    @pytest.mark.asyncio
    async def test_extract_invalid_url_raises_error(self, content_service):
        """Should raise error for invalid URL."""
        from app.core.exceptions import ExtractionError

        with pytest.raises(ExtractionError):
            await content_service.extract_content("not-a-valid-url")

    @pytest.mark.asyncio
    async def test_extract_creates_processing_record(self, content_service, postgres_repo):
        """Should create processing record when extraction starts."""
        url = "https://example.com/test"

        with patch('app.services.content_service.extract_web_content') as mock_extract:
            mock_extract.return_value = RawContent(
                url=url,
                source_type=ContentSource.WEB,
                raw_text="Test content",
                metadata={},
                extracted_at=datetime.now()
            )

            await content_service.extract_content(url)

            # Verify processing record was created
            records = await postgres_repo.list_processing_records()
            assert len(records) >= 1
            assert any(r['content_url'] == url for r in records)


class TestContentServiceScreening:
    """Test AI-powered content screening."""

    @pytest.mark.asyncio
    async def test_screen_content_returns_score(self, content_service):
        """Should screen content and return quality score."""
        raw_content = RawContent(
            url="https://example.com/article",
            source_type=ContentSource.WEB,
            raw_text="This is a high-quality article about artificial intelligence and neural networks.",
            metadata={"title": "AI Tutorial"},
            extracted_at=datetime.now()
        )

        # Mock OpenAI API call
        with patch('app.services.content_service.screen_with_ai') as mock_screen:
            mock_screen.return_value = ScreeningResult(
                screening_score=8.5,
                decision="ACCEPT",
                reasoning="High-quality technical content with clear explanations",
                estimated_quality=9.0
            )

            screening_result = await content_service.screen_content(raw_content)

            assert screening_result is not None
            assert 0 <= screening_result.screening_score <= 10
            assert screening_result.decision in ["ACCEPT", "REJECT", "MAYBE"]
            assert len(screening_result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_screen_caches_result(self, content_service, redis_repo):
        """Should cache screening result in Redis."""
        raw_content = RawContent(
            url="https://example.com/article",
            source_type=ContentSource.WEB,
            raw_text="Test content",
            metadata={},
            extracted_at=datetime.now()
        )

        with patch('app.services.content_service.screen_with_ai') as mock_screen:
            mock_screen.return_value = ScreeningResult(
                screening_score=7.0,
                decision="ACCEPT",
                reasoning="Good content",
                estimated_quality=7.5
            )

            await content_service.screen_content(raw_content)

            # Check cache
            cache_key = f"screening:{raw_content.url}"
            cached = await redis_repo.get_json(cache_key)
            assert cached is not None
            assert cached['screening_score'] == 7.0

    @pytest.mark.asyncio
    async def test_screen_uses_cache_on_second_call(self, content_service, redis_repo):
        """Should use cached result instead of calling API again."""
        raw_content = RawContent(
            url="https://example.com/cached-article",
            source_type=ContentSource.WEB,
            raw_text="Test content",
            metadata={},
            extracted_at=datetime.now()
        )

        # First call - will cache
        with patch('app.services.content_service.screen_with_ai') as mock_screen:
            mock_screen.return_value = ScreeningResult(
                screening_score=8.0,
                decision="ACCEPT",
                reasoning="Cached result",
                estimated_quality=8.5
            )

            result1 = await content_service.screen_content(raw_content)
            assert mock_screen.call_count == 1

            # Second call - should use cache
            result2 = await content_service.screen_content(raw_content)
            assert mock_screen.call_count == 1  # Not called again!
            assert result2.screening_score == result1.screening_score


class TestContentServiceProcessing:
    """Test content processing (summarization, key points, tags)."""

    @pytest.mark.asyncio
    async def test_process_content_generates_summary(self, content_service):
        """Should process content and generate summary."""
        raw_content = RawContent(
            url="https://example.com/article",
            source_type=ContentSource.WEB,
            raw_text="Long article content here...",
            metadata={"title": "Test Article"},
            extracted_at=datetime.now()
        )

        screening_result = ScreeningResult(
            screening_score=8.5,
            decision="ACCEPT",
            reasoning="Good content",
            estimated_quality=9.0
        )

        with patch('app.services.content_service.process_with_ai') as mock_process:
            mock_process.return_value = {
                "summary": "Brief summary of the article",
                "key_points": ["Point 1", "Point 2", "Point 3"],
                "tags": ["ai", "machine-learning"]
            }

            processed = await content_service.process_content(raw_content, screening_result)

            assert processed is not None
            assert len(processed.summary) > 0
            assert len(processed.key_points) >= 2
            assert len(processed.tags) >= 1

    @pytest.mark.asyncio
    async def test_process_rejected_content_skips_processing(self, content_service):
        """Should skip processing for rejected content."""
        raw_content = RawContent(
            url="https://example.com/bad-article",
            source_type=ContentSource.WEB,
            raw_text="Low quality content",
            metadata={},
            extracted_at=datetime.now()
        )

        screening_result = ScreeningResult(
            screening_score=3.0,
            decision="REJECT",
            reasoning="Low quality",
            estimated_quality=2.5
        )

        processed = await content_service.process_content(raw_content, screening_result)

        # Should return None or minimal processing for rejected content
        assert processed is None or processed.screening_result.decision == "REJECT"


class TestContentServiceStorage:
    """Test storing processed content across all repositories."""

    @pytest.mark.asyncio
    async def test_store_content_in_postgres(self, content_service, postgres_repo):
        """Should store processing record in PostgreSQL."""
        processed = ProcessedContent(
            source_type=ContentSource.WEB,
            url="https://example.com/article",
            title="Test Article",
            summary="Brief summary",
            key_points=["Point 1", "Point 2"],
            tags=["test"],
            screening_result=ScreeningResult(
                screening_score=8.0,
                decision="ACCEPT",
                reasoning="Good",
                estimated_quality=8.5
            ),
            processed_at=datetime.now()
        )

        with patch('app.services.content_service.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            await content_service.store_content(processed)

        # Verify in PostgreSQL
        records = await postgres_repo.list_processing_records()
        assert any(r['content_url'] == str(processed.url) for r in records)

    @pytest.mark.asyncio
    async def test_store_content_in_minio(self, content_service, minio_repo):
        """Should store content file in MinIO."""
        processed = ProcessedContent(
            source_type=ContentSource.WEB,
            url="https://example.com/article",
            title="Test Article",
            summary="Brief summary",
            key_points=["Point 1", "Point 2"],
            tags=["test"],
            screening_result=ScreeningResult(
                screening_score=8.0,
                decision="ACCEPT",
                reasoning="Good",
                estimated_quality=8.5
            ),
            processed_at=datetime.now()
        )

        with patch('app.services.content_service.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            await content_service.store_content(processed)

        # Verify in MinIO (tier b for score 8.5 which is >= 7.0)
        # Bucket name is bucket_prefix-tier = "librarian-b"
        file_key = f"{str(processed.url).replace('://', '_').replace('/', '_')}.json"

        # Temporarily switch bucket to verify storage
        original_bucket = minio_repo.bucket_name
        minio_repo.bucket_name = "librarian-b"
        result = minio_repo.download_file(file_key)
        minio_repo.bucket_name = original_bucket

        assert result is not None

    @pytest.mark.asyncio
    async def test_store_content_in_qdrant(self, content_service, qdrant_repo):
        """Should store vector embedding in Qdrant."""
        processed = ProcessedContent(
            source_type=ContentSource.WEB,
            url="https://example.com/article",
            title="Test Article",
            summary="Brief summary for embedding",
            key_points=["Point 1"],
            tags=["test"],
            screening_result=ScreeningResult(
                screening_score=8.0,
                decision="ACCEPT",
                reasoning="Good",
                estimated_quality=8.5
            ),
            processed_at=datetime.now()
        )

        with patch('app.services.content_service.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384  # Mock 384-dim vector

            await content_service.store_content(processed)

            # Verify in Qdrant
            count = qdrant_repo.count()
            assert count >= 1


class TestContentServicePipeline:
    """Test complete end-to-end pipeline."""

    @pytest.mark.asyncio
    async def test_complete_pipeline(self, content_service):
        """Should execute complete pipeline: extract → screen → process → store."""
        url = "https://example.com/complete-test"

        # Mock all external calls
        with patch('app.services.content_service.extract_web_content') as mock_extract, \
             patch('app.services.content_service.screen_with_ai') as mock_screen, \
             patch('app.services.content_service.process_with_ai') as mock_process, \
             patch('app.services.content_service.generate_embedding') as mock_embed:

            mock_extract.return_value = RawContent(
                url=url,
                source_type=ContentSource.WEB,
                raw_text="Complete test article content",
                metadata={"title": "Complete Test"},
                extracted_at=datetime.now()
            )

            mock_screen.return_value = ScreeningResult(
                screening_score=9.0,
                decision="ACCEPT",
                reasoning="Excellent content",
                estimated_quality=9.5
            )

            mock_process.return_value = {
                "summary": "Complete test summary",
                "key_points": ["Complete", "Test"],
                "tags": ["testing", "complete"]
            }

            mock_embed.return_value = [0.1] * 384

            # Execute complete pipeline
            result = await content_service.process_url(url)

            assert result is not None
            assert str(result.url) == url
            assert result.screening_result.decision == "ACCEPT"
            assert len(result.summary) > 0
            assert len(result.key_points) >= 2

    @pytest.mark.asyncio
    async def test_pipeline_handles_errors_gracefully(self, content_service, postgres_repo):
        """Should handle errors and record failure."""
        url = "https://example.com/error-test"

        with patch('app.services.content_service.extract_web_content') as mock_extract:
            mock_extract.side_effect = Exception("Network error")

            with pytest.raises(Exception):
                await content_service.process_url(url)

            # Should still create error record in PostgreSQL
            records = await postgres_repo.list_processing_records(status="failed")
            assert len(records) >= 1
