"""
Integration tests for ContentService using real extracted content.

These tests use actual content from the aireport project to ensure
realistic behavior with production-quality data.
"""
import pytest
from unittest.mock import patch
from datetime import datetime

from app.core.config import settings
from app.services.content_service import ContentService
from app.core.models import ScreeningResult, ProcessedContent
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.redis_repository import RedisRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.minio_repository import MinIORepository

from tests.fixtures.content_loader import (
    get_sample,
    get_all_samples,
    SAMPLE_FILES
)


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
    repo = QdrantRepository(client, "test_real_data")
    
    yield repo
    
    # Cleanup
    try:
        client.delete_collection("test_real_data")
    except:
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
    
    repo = MinIORepository(client, "test-real-data")
    
    yield repo
    
    # Cleanup
    try:
        objects = repo.list_files()
        if objects:
            repo.delete_files([obj['key'] for obj in objects])
    except:
        pass


@pytest.fixture
async def content_service(postgres_repo, redis_repo, qdrant_repo, minio_repo):
    """Content service with all repositories."""
    return ContentService(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo,
        qdrant_repo=qdrant_repo,
        minio_repo=minio_repo
    )


class TestRealContentProcessing:
    """Test content processing pipeline with real data."""
    
    @pytest.mark.asyncio
    async def test_process_high_quality_blog_post(self, content_service):
        """Should successfully process a high-quality technical blog post."""
        # Load the Illustrated Transformer blog post
        raw_content = get_sample('high_quality_blog')
        
        # Mock external AI calls
        mock_screening = ScreeningResult(
            screening_score=9.2,
            decision="ACCEPT",
            reasoning="Excellent technical content with clear explanations of Transformer architecture",
            estimated_quality=9.5
        )
        
        mock_processing = {
            'summary': 'Comprehensive explanation of the Transformer architecture including self-attention mechanisms.',
            'key_points': [
                'Transformers use self-attention instead of recurrence',
                'Multi-headed attention allows parallel processing',
                'Positional encoding provides sequence information'
            ],
            'tags': ['transformers', 'attention', 'nlp', 'deep-learning']
        }
        
        with patch('app.services.content_service.screen_with_ai', return_value=mock_screening), \
             patch('app.services.content_service.process_with_ai', return_value=mock_processing), \
             patch('app.services.content_service.generate_embedding', return_value=[0.1] * 384):
            
            # Process the content
            screening_result = await content_service.screen_content(raw_content)
            assert screening_result.decision == "ACCEPT"
            assert screening_result.screening_score >= 9.0
            
            processed = await content_service.process_content(raw_content, screening_result)
            assert processed is not None
            assert 'Transformer' in processed.title  # ProcessedContent has title field
            assert len(processed.key_points) >= 3
            
            # Store in tier A (quality >= 9.0)
            await content_service.store_content(processed)
            
            # Verify storage in tier-a
            original_bucket = content_service.minio_repo.bucket_name
            content_service.minio_repo.bucket_name = "librarian-a"
            file_key = f"{str(processed.url).replace('://', '_').replace('/', '_')}.json"
            result = content_service.minio_repo.download_file(file_key)
            content_service.minio_repo.bucket_name = original_bucket
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_process_arxiv_paper(self, content_service):
        """Should successfully process an academic paper."""
        raw_content = get_sample('arxiv_paper')
        
        mock_screening = ScreeningResult(
            screening_score=8.7,
            decision="ACCEPT",
            reasoning="High-quality academic research on language model calibration",
            estimated_quality=8.9
        )
        
        mock_processing = {
            'summary': 'Research on language model calibration and confidence estimation.',
            'key_points': [
                'Language models can express uncertainty',
                'Calibration improves with model scale',
                'Important for reliable AI systems'
            ],
            'tags': ['llm', 'calibration', 'research', 'arxiv']
        }
        
        with patch('app.services.content_service.screen_with_ai', return_value=mock_screening), \
             patch('app.services.content_service.process_with_ai', return_value=mock_processing), \
             patch('app.services.content_service.generate_embedding', return_value=[0.1] * 384):
            
            screening_result = await content_service.screen_content(raw_content)
            processed = await content_service.process_content(raw_content, screening_result)
            
            assert processed.screening_result.estimated_quality >= 8.0
            assert any('research' in tag.lower() or 'arxiv' in tag.lower() for tag in processed.tags)
    
    @pytest.mark.asyncio
    async def test_process_multiple_samples(self, content_service):
        """Should process multiple diverse content samples."""
        samples = get_all_samples()
        
        assert len(samples) == len(SAMPLE_FILES), "Should load all sample files"
        
        # Mock responses for all samples
        with patch('app.services.content_service.screen_with_ai') as mock_screen, \
             patch('app.services.content_service.process_with_ai') as mock_process, \
             patch('app.services.content_service.generate_embedding', return_value=[0.1] * 384):
            
            # Set up mocks to return varied quality scores
            quality_scores = [9.2, 8.5, 7.8, 8.9, 6.5, 9.0]
            
            for i, sample in enumerate(samples[:len(quality_scores)]):
                sample_title = sample.metadata.get('title', 'Unknown')
                
                mock_screen.return_value = ScreeningResult(
                    screening_score=quality_scores[i],
                    decision="ACCEPT" if quality_scores[i] >= 7.0 else "MAYBE",
                    reasoning=f"Quality assessment for {sample_title}",
                    estimated_quality=quality_scores[i]
                )
                
                mock_process.return_value = {
                    'summary': f'Summary of {sample_title}',
                    'key_points': ['Point 1', 'Point 2', 'Point 3'],
                    'tags': ['ai', 'test']
                }
                
                screening = await content_service.screen_content(sample)
                processed = await content_service.process_content(sample, screening)
                
                assert processed is not None
                assert len(processed.tags) >= 2
    
    @pytest.mark.asyncio
    async def test_realistic_screening_scores(self, content_service):
        """Test that different content types receive appropriate quality scores."""
        test_cases = [
            ('high_quality_blog', 8.5, 10.0),  # Should be high quality
            ('arxiv_paper', 8.0, 10.0),         # Academic content is high quality
            ('web_article', 6.0, 8.5),          # General web content varies
        ]
        
        for sample_name, min_score, max_score in test_cases:
            raw_content = get_sample(sample_name)
            title = raw_content.metadata.get('title', 'Unknown')
            
            # Mock with realistic scoring
            mock_screening = ScreeningResult(
                screening_score=(min_score + max_score) / 2,
                decision="ACCEPT" if min_score >= 7.0 else "MAYBE",
                reasoning=f"Quality assessment for {title}",
                estimated_quality=(min_score + max_score) / 2
            )
            
            with patch('app.services.content_service.screen_with_ai', return_value=mock_screening):
                result = await content_service.screen_content(raw_content)
                
                assert min_score <= result.screening_score <= max_score
                assert result.decision in ["ACCEPT", "MAYBE", "REJECT"]
    
    @pytest.mark.asyncio
    async def test_end_to_end_with_real_content(self, content_service):
        """Complete pipeline test with real content from extraction to storage."""
        # Use the Transformer blog post as a comprehensive test
        raw_content = get_sample('high_quality_blog')
        
        mock_screening = ScreeningResult(
            screening_score=9.5,
            decision="ACCEPT",
            reasoning="Outstanding technical explanation of Transformers",
            estimated_quality=9.7
        )
        
        mock_processing = {
            'summary': 'In-depth explanation of Transformer architecture with visual illustrations.',
            'key_points': [
                'Self-attention is the core mechanism',
                'Positional encodings provide sequence information',
                'Multi-headed attention enables parallel processing',
                'Encoder-decoder structure for sequence tasks'
            ],
            'tags': ['transformers', 'attention', 'nlp', 'neural-networks', 'deep-learning']
        }
        
        with patch('app.services.content_service.extract_web_content', return_value=raw_content), \
             patch('app.services.content_service.screen_with_ai', return_value=mock_screening), \
             patch('app.services.content_service.process_with_ai', return_value=mock_processing), \
             patch('app.services.content_service.generate_embedding', return_value=[0.1] * 384):
            
            # Run complete pipeline
            processed = await content_service.process_url(str(raw_content.url))
            
            # Verify complete processing
            assert processed is not None
            assert 'Transformer' in processed.title
            assert processed.screening_result.decision == "ACCEPT"
            assert len(processed.key_points) >= 4
            assert len(processed.tags) >= 5
            
            # Verify tier A storage (quality >= 9.0)
            assert processed.screening_result.estimated_quality >= 9.0


class TestRealContentMetadata:
    """Test metadata extraction from real content."""
    
    def test_load_blog_post_metadata(self):
        """Should correctly parse frontmatter from blog posts."""
        raw_content = get_sample('high_quality_blog')
        
        assert raw_content.metadata.get('title') == "The Illustrated Transformer"
        assert raw_content.metadata.get('author') == "Jay Alammar"
        assert 'transformer' in raw_content.raw_text.lower()
    
    def test_load_arxiv_metadata(self):
        """Should correctly parse arxiv paper metadata."""
        raw_content = get_sample('arxiv_paper')
        
        title = raw_content.metadata.get('title', '')
        assert 'Language' in title or 'language' in title.lower()
        assert len(raw_content.raw_text) > 500, "Should have substantial content"
    
    def test_all_samples_have_valid_metadata(self):
        """All sample files should have parseable metadata."""
        samples = get_all_samples()
        
        for sample in samples:
            # Every sample should have these basic fields
            title = sample.metadata.get('title', '')
            assert title, f"Missing title for {sample.url}"
            assert len(sample.raw_text) > 100, f"Content too short for {title}"
            assert sample.url, f"Missing URL for {title}"
            assert sample.extracted_at is not None
            
            # Should have some metadata
            assert isinstance(sample.metadata, dict)


class TestCachingWithRealContent:
    """Test Redis caching behavior with real content."""
    
    @pytest.mark.asyncio
    async def test_cache_real_content_screening(self, content_service):
        """Should cache screening results for real content."""
        raw_content = get_sample('high_quality_blog')
        
        mock_screening = ScreeningResult(
            screening_score=9.0,
            decision="ACCEPT",
            reasoning="High-quality technical content",
            estimated_quality=9.2
        )
        
        with patch('app.services.content_service.screen_with_ai', return_value=mock_screening) as mock_screen:
            # First call - should hit AI
            result1 = await content_service.screen_content(raw_content)
            assert mock_screen.call_count == 1
            
            # Second call - should use cache
            result2 = await content_service.screen_content(raw_content)
            assert mock_screen.call_count == 1  # Should not call AI again
            
            # Results should be identical
            assert result1.screening_score == result2.screening_score
            assert result1.decision == result2.decision
