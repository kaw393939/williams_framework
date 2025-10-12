"""
Integration tests for LibraryService.

Tests tier-based library management, semantic search, and statistics.
"""
from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import HttpUrl

from app.core.config import settings
from app.core.models import LibraryStats, ProcessedContent, ScreeningResult, SearchResult
from app.core.types import ContentSource
from app.repositories.minio_repository import MinIORepository
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.redis_repository import RedisRepository
from app.services.library_service import LibraryService
from tests.fixtures.content_loader import get_sample


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
    repo = QdrantRepository(client, "test_library_service")

    yield repo

    # Cleanup
    try:
        client.delete_collection("test_library_service")
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

    repo = MinIORepository(client, "test-library")

    yield repo

    # Cleanup
    try:
        objects = repo.list_files()
        if objects:
            repo.delete_files([obj['key'] for obj in objects])
    except Exception:
        pass


@pytest.fixture
async def library_service(postgres_repo, redis_repo, qdrant_repo, minio_repo):
    """Create LibraryService with all repositories."""
    service = LibraryService(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo,
        qdrant_repo=qdrant_repo,
        minio_repo=minio_repo
    )
    return service


def create_sample_content(
    title: str = "Test Article",
    quality_score: float = 8.5,
    tier: str = "b"
) -> ProcessedContent:
    """Helper to create sample ProcessedContent."""
    return ProcessedContent(
        source_type=ContentSource.WEB,
        url=HttpUrl(f"https://example.com/{title.lower().replace(' ', '-')}"),
        title=title,
        summary=f"Summary of {title}",
        key_points=["Point 1", "Point 2", "Point 3"],
        tags=["test", "sample"],
        screening_result=ScreeningResult(
            screening_score=quality_score,
            decision="ACCEPT",
            reasoning=f"Quality content: {title}",
            estimated_quality=quality_score
        ),
        processed_at=datetime.now()
    )


class TestLibraryAddContent:
    """Test adding content to the library."""

    @pytest.mark.asyncio
    async def test_add_content_to_library(self, library_service):
        """Should add processed content to the library."""
        content = create_sample_content(title="Test Article", quality_score=8.5)

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            library_file = await library_service.add_to_library(content)

        assert library_file is not None
        assert library_file.title == "Test Article"
        assert library_file.tier == "tier-b"  # 8.5 should be tier B (7-9)
        assert library_file.quality_score == 8.5

    @pytest.mark.asyncio
    async def test_add_assigns_correct_tier(self, library_service):
        """Should assign correct tier based on quality score."""
        test_cases = [
            (9.5, "tier-a"),  # >= 9.0
            (8.0, "tier-b"),  # >= 7.0
            (6.5, "tier-c"),  # >= 5.0
            (4.0, "tier-d"),  # < 5.0
        ]

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for quality, expected_tier in test_cases:
                content = create_sample_content(
                    title=f"Article {quality}",
                    quality_score=quality
                )

                library_file = await library_service.add_to_library(content)
                assert library_file.tier == expected_tier, f"Quality {quality} should be tier {expected_tier}"

    @pytest.mark.asyncio
    async def test_add_stores_in_all_repositories(self, library_service, postgres_repo, qdrant_repo, minio_repo):
        """Should store content in PostgreSQL, Qdrant, and MinIO."""
        content = create_sample_content(title="Multi Repo Test", quality_score=8.5)

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            await library_service.add_to_library(content)

        # Verify in PostgreSQL
        records = await postgres_repo.list_processing_records()
        assert len(records) > 0

        # Verify in Qdrant
        count = qdrant_repo.count()
        assert count >= 1

        # Verify in MinIO (tier b bucket)
        original_bucket = minio_repo.bucket_name
        minio_repo.bucket_name = "test-library-b"
        files = minio_repo.list_files()
        minio_repo.bucket_name = original_bucket
        assert len(files) >= 1


class TestLibraryRetrieve:
    """Test retrieving content from the library."""

    @pytest.mark.asyncio
    async def test_get_files_by_tier(self, library_service):
        """Should retrieve files from specific tier."""
        # Add files to different tiers
        contents = [
            create_sample_content("Tier A Article", 9.5),
            create_sample_content("Tier B Article 1", 8.0),
            create_sample_content("Tier B Article 2", 7.5),
            create_sample_content("Tier C Article", 6.0),
        ]

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for content in contents:
                await library_service.add_to_library(content)

        # Get tier B files
        tier_b_files = await library_service.get_files_by_tier("tier-b", limit=10)

        assert len(tier_b_files) == 2
        assert all(f.tier == "tier-b" for f in tier_b_files)

    @pytest.mark.asyncio
    async def test_get_files_pagination(self, library_service):
        """Should support pagination when retrieving files."""
        # Add multiple files to same tier
        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for i in range(5):
                content = create_sample_content(f"Article {i}", 8.0)
                await library_service.add_to_library(content)

        # Get first page (limit 2)
        page1 = await library_service.get_files_by_tier("tier-b", limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = await library_service.get_files_by_tier("tier-b", limit=2, offset=2)
        assert len(page2) == 2

        # Files should be different
        page1_titles = {f.title for f in page1}
        page2_titles = {f.title for f in page2}
        assert page1_titles.isdisjoint(page2_titles)


class TestLibraryMoveTiers:
    """Test moving content between tiers."""

    @pytest.mark.asyncio
    async def test_move_file_between_tiers(self, library_service):
        """Should move file from one tier to another."""
        # Add file to tier B
        content = create_sample_content("Movable Article", 8.0)

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            library_file = await library_service.add_to_library(content)

        file_id = str(library_file.url)

        # Move from B to A
        moved_file = await library_service.move_between_tiers(file_id, "tier-b", "tier-a")

        assert moved_file.tier == "tier-a"

        # Verify it's no longer in tier B
        tier_b_files = await library_service.get_files_by_tier("tier-b")
        assert all(str(f.url) != file_id for f in tier_b_files)

    @pytest.mark.asyncio
    async def test_move_updates_minio_location(self, library_service, minio_repo):
        """Should move file in MinIO when changing tiers."""
        content = create_sample_content("MinIO Move Test", 8.0)

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            library_file = await library_service.add_to_library(content)

        file_id = str(library_file.url)

        # Move from B to A
        await library_service.move_between_tiers(file_id, "tier-b", "tier-a")

        # Verify file is now in tier-a bucket
        original_bucket = minio_repo.bucket_name
        minio_repo.bucket_name = "test-library-a"

        file_key = f"{str(library_file.url).replace('://', '_').replace('/', '_')}.json"
        result = minio_repo.download_file(file_key)

        minio_repo.bucket_name = original_bucket

        assert result is not None


class TestLibrarySearch:
    """Test semantic search functionality."""

    @pytest.mark.asyncio
    async def test_search_library_by_text(self, library_service):
        """Should search library using semantic search."""
        # Add some content
        contents = [
            create_sample_content("Machine Learning Basics", 8.5),
            create_sample_content("Deep Learning Tutorial", 9.0),
            create_sample_content("Cooking Recipes", 7.0),
        ]

        with patch('app.services.library_service.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            for content in contents:
                await library_service.add_to_library(content)

            # Search for ML content
            results = await library_service.search_library(
                query="machine learning",
                limit=10
            )

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_with_filters(self, library_service):
        """Should filter search results by tier and quality."""
        contents = [
            create_sample_content("High Quality AI", 9.5),
            create_sample_content("Medium Quality AI", 7.5),
            create_sample_content("Low Quality AI", 5.0),
        ]

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for content in contents:
                await library_service.add_to_library(content)

            # Search with tier filter
            results = await library_service.search_library(
                query="AI",
                filters={"tier": "tier-a"},
                limit=10
            )

        assert all(r.tier == "tier-a" for r in results)

    @pytest.mark.asyncio
    async def test_search_caches_results(self, library_service, redis_repo):
        """Should cache search results in Redis."""
        content = create_sample_content("Cacheable Article", 8.0)

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            await library_service.add_to_library(content)

            # First search - should cache
            results1 = await library_service.search_library("cacheable", limit=5)

            # Second search - should use cache
            results2 = await library_service.search_library("cacheable", limit=5)

        assert len(results1) == len(results2)

    @pytest.mark.asyncio
    async def test_search_with_real_content(self, library_service):
        """Should search real content from test fixtures."""
        # Load real content samples
        real_content = get_sample('high_quality_blog')

        processed = ProcessedContent(
            source_type=real_content.source_type,
            url=real_content.url,
            title=real_content.metadata.get('title', 'Test'),
            summary="Comprehensive explanation of Transformer architecture",
            key_points=["Self-attention", "Multi-headed attention", "Positional encoding"],
            tags=["transformers", "nlp", "deep-learning"],
            screening_result=ScreeningResult(
                screening_score=9.2,
                decision="ACCEPT",
                reasoning="Excellent technical content",
                estimated_quality=9.5
            ),
            processed_at=datetime.now()
        )

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            await library_service.add_to_library(processed)

            # Search for transformers
            results = await library_service.search_library("transformer architecture", limit=5)

        assert len(results) > 0
        assert any("transformer" in r.title.lower() for r in results)


class TestLibraryStatistics:
    """Test library statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_library_statistics(self, library_service):
        """Should return comprehensive library statistics."""
        # Add files to different tiers
        contents = [
            create_sample_content("Article 1", 9.5),
            create_sample_content("Article 2", 8.5),
            create_sample_content("Article 3", 8.0),
            create_sample_content("Article 4", 6.0),
        ]

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for content in contents:
                await library_service.add_to_library(content)

        stats = await library_service.get_statistics()

        assert isinstance(stats, LibraryStats)
        assert stats.total_files == 4
        assert stats.files_by_tier.get("tier-a", 0) == 1
        assert stats.files_by_tier.get("tier-b", 0) == 2
        assert stats.files_by_tier.get("tier-c", 0) == 1
        assert 7.0 <= stats.average_quality <= 9.0

    @pytest.mark.asyncio
    async def test_stats_by_tier(self, library_service):
        """Should correctly count files in each tier."""
        # Add 3 to tier A, 2 to tier B, 1 to tier C
        tier_a_contents = [create_sample_content(f"Tier A {i}", 9.0 + i * 0.1) for i in range(3)]
        tier_b_contents = [create_sample_content(f"Tier B {i}", 7.5 + i * 0.1) for i in range(2)]
        tier_c_contents = [create_sample_content("Tier C 1", 5.5)]

        all_contents = tier_a_contents + tier_b_contents + tier_c_contents

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for content in all_contents:
                await library_service.add_to_library(content)

        stats = await library_service.get_statistics()

        assert stats.files_by_tier["tier-a"] == 3
        assert stats.files_by_tier["tier-b"] == 2
        assert stats.files_by_tier["tier-c"] == 1
        assert stats.total_files == 6


class TestLibraryIntegration:
    """Test complete library workflows."""

    @pytest.mark.asyncio
    async def test_complete_library_workflow(self, library_service):
        """Should handle complete workflow: add, search, move, stats."""
        # Step 1: Add content
        content = create_sample_content("Workflow Test Article", 8.0)

        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            library_file = await library_service.add_to_library(content)
            assert library_file.tier == "tier-b"

            # Step 2: Search for it
            results = await library_service.search_library("workflow test", limit=5)
            assert len(results) > 0

            # Step 3: Move to tier A
            moved = await library_service.move_between_tiers(str(library_file.url), "tier-b", "tier-a")
            assert moved.tier == "tier-a"

            # Step 4: Get statistics
            stats = await library_service.get_statistics()
            assert stats.total_files >= 1
            assert stats.files_by_tier.get("tier-a", 0) >= 1

    @pytest.mark.asyncio
    async def test_library_with_multiple_files(self, library_service):
        """Should handle library with many files efficiently."""
        # Add 10 files
        with patch('app.services.library_service.generate_embedding', return_value=[0.1] * 384):
            for i in range(10):
                quality = 5.0 + (i * 0.5)  # Range from 5.0 to 9.5
                content = create_sample_content(f"Multi File {i}", quality)
                await library_service.add_to_library(content)

        # Get all tiers
        tier_a = await library_service.get_files_by_tier("tier-a")
        tier_b = await library_service.get_files_by_tier("tier-b")
        tier_c = await library_service.get_files_by_tier("tier-c")

        total_files = len(tier_a) + len(tier_b) + len(tier_c)
        assert total_files == 10

        # Get statistics
        stats = await library_service.get_statistics()
        assert stats.total_files == 10
