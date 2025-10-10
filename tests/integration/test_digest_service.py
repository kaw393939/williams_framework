"""
Integration tests for DigestService.

Tests daily digest generation, email rendering, and delivery tracking.
Uses real repositories (no mocks except for SMTP).
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.services.digest_service import DigestService
from app.core.models import DigestItem, Digest
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.redis_repository import RedisRepository
from app.core.config import settings


def create_sample_library_content(title: str, quality: float, days_ago: int = 0) -> dict:
    """Helper to create sample library content metadata."""
    date = datetime.now() - timedelta(days=days_ago)
    return {
        'url': f'https://example.com/{title.lower().replace(" ", "-")}',
        'title': title,
        'summary': f'Summary of {title}',
        'quality_score': quality,
        'tier': 'tier-a' if quality >= 9.0 else 'tier-b' if quality >= 7.0 else 'tier-c',
        'tags': ['ai', 'ml'],
        'added_date': date,
        'days_ago': days_ago
    }


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
    
    # Cleanup
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
    
    # Cleanup
    await repo.flush_all()
    await repo.close()


@pytest.fixture
async def digest_service(postgres_repo, redis_repo):
    """Create DigestService with real repositories."""
    return DigestService(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo
    )


class TestDigestSelection:
    """Test content selection for digests."""
    
    @pytest.mark.asyncio
    async def test_select_content_by_quality(self, digest_service, postgres_repo):
        """Should select high-quality content for digest."""
        # Add some library records to PostgreSQL
        records = [
            create_sample_library_content("Great Article", 9.5, days_ago=1),
            create_sample_library_content("Good Article", 8.0, days_ago=1),
            create_sample_library_content("Poor Article", 5.0, days_ago=1),
        ]
        
        # Insert into processing_records as library items
        for record in records:
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=record['url'],
                operation='add_to_library',
                status='completed',
                metadata=json.dumps({
                    'title': record['title'],
                    'quality_score': record['quality_score'],
                    'tier': record['tier'],
                    'summary': record['summary'],
                    'tags': record['tags']
                })
            )
        
        # Select content (should prefer high quality)
        items = await digest_service.select_content_for_digest(
            date=datetime.now(),
            min_quality=7.0,
            limit=10
        )
        
        assert len(items) >= 2
        assert all(item.quality_score >= 7.0 for item in items)
        assert any(item.title == "Great Article" for item in items)
    
    @pytest.mark.asyncio
    async def test_select_recent_content(self, digest_service, postgres_repo):
        """Should select content from recent days."""
        # Add content from different dates
        records = [
            create_sample_library_content("Today Article", 9.0, days_ago=0),
            create_sample_library_content("Yesterday Article", 8.5, days_ago=1),
            create_sample_library_content("Old Article", 9.0, days_ago=10),
        ]
        
        for record in records:
            # Insert with custom started_at timestamp
            started_at = datetime.now() - timedelta(days=record['days_ago'])
            await postgres_repo.execute("""
                INSERT INTO processing_records 
                (record_id, content_url, operation, status, started_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
                str(uuid4()),
                record['url'],
                'add_to_library',
                'completed',
                started_at,
                json.dumps({
                    'title': record['title'],
                    'quality_score': record['quality_score'],
                    'tier': record['tier'],
                    'summary': record['summary'],
                    'tags': record['tags']
                })
            )
        
        # Select only recent content (last 3 days)
        items = await digest_service.select_content_for_digest(
            date=datetime.now(),
            days_back=3,
            limit=10
        )
        
        assert len(items) >= 2
        assert any(item.title == "Today Article" for item in items)
        assert any(item.title == "Yesterday Article" for item in items)
        # Old article should not be included
        assert not any(item.title == "Old Article" for item in items)
    
    @pytest.mark.asyncio
    async def test_select_with_tier_preference(self, digest_service, postgres_repo):
        """Should respect tier preferences in selection."""
        records = [
            create_sample_library_content("Tier A Article", 9.5, days_ago=1),
            create_sample_library_content("Tier B Article", 8.0, days_ago=1),
            create_sample_library_content("Tier C Article", 6.0, days_ago=1),
        ]
        
        for record in records:
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=record['url'],
                operation='add_to_library',
                status='completed',
                metadata=json.dumps({
                    'title': record['title'],
                    'quality_score': record['quality_score'],
                    'tier': record['tier'],
                    'summary': record['summary'],
                    'tags': record['tags']
                })
            )
        
        # Select only tier A and B
        items = await digest_service.select_content_for_digest(
            date=datetime.now(),
            preferred_tiers=['tier-a', 'tier-b'],
            limit=10
        )
        
        assert len(items) >= 2
        assert all(item.tier in ['tier-a', 'tier-b'] for item in items)


class TestDigestGeneration:
    """Test digest HTML and text generation."""
    
    @pytest.mark.asyncio
    async def test_generate_html_digest(self, digest_service):
        """Should generate HTML email from digest items."""
        items = [
            DigestItem(
                url='https://example.com/article1',
                title='Test Article 1',
                summary='Summary 1',
                quality_score=9.5,
                tier='tier-a',
                tags=['ai', 'ml'],
                added_date=datetime.now()
            ),
            DigestItem(
                url='https://example.com/article2',
                title='Test Article 2',
                summary='Summary 2',
                quality_score=8.5,
                tier='tier-b',
                tags=['python'],
                added_date=datetime.now()
            )
        ]
        
        html = await digest_service.generate_digest_html(
            items=items,
            date=datetime.now(),
            subject="Daily Digest"
        )
        
        assert html is not None
        assert 'Test Article 1' in html
        assert 'Test Article 2' in html
        assert 'https://example.com/article1' in html
        assert 'Summary 1' in html
        assert '<html' in html.lower()
    
    @pytest.mark.asyncio
    async def test_generate_text_digest(self, digest_service):
        """Should generate plain text email from digest items."""
        items = [
            DigestItem(
                url='https://example.com/article',
                title='Test Article',
                summary='Test Summary',
                quality_score=9.0,
                tier='tier-a',
                tags=['test'],
                added_date=datetime.now()
            )
        ]
        
        text = await digest_service.generate_digest_text(
            items=items,
            date=datetime.now(),
            subject="Daily Digest"
        )
        
        assert text is not None
        assert 'Test Article' in text
        assert 'https://example.com/article' in text
        assert 'Test Summary' in text
        # Should not contain HTML tags
        assert '<html' not in text.lower()
    
    @pytest.mark.asyncio
    async def test_generate_empty_digest(self, digest_service):
        """Should handle empty digest gracefully."""
        html = await digest_service.generate_digest_html(
            items=[],
            date=datetime.now(),
            subject="Daily Digest"
        )
        
        assert html is not None
        assert 'no new content' in html.lower() or 'empty' in html.lower()


class TestDigestDelivery:
    """Test digest email delivery."""
    
    @pytest.mark.asyncio
    async def test_send_digest_email(self, digest_service):
        """Should send digest via SMTP (mocked)."""
        digest = Digest(
            digest_id=str(uuid4()),
            date=datetime.now(),
            subject="Test Digest",
            items=[],
            html_content="<html><body>Test</body></html>",
            text_content="Test",
            recipients=["test@example.com"]
        )
        
        # Mock SMTP to avoid actual email sending
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await digest_service.send_digest_email(digest)
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_digest_to_multiple_recipients(self, digest_service):
        """Should send digest to multiple recipients."""
        digest = Digest(
            digest_id=str(uuid4()),
            date=datetime.now(),
            subject="Test Digest",
            items=[],
            html_content="<html><body>Test</body></html>",
            text_content="Test",
            recipients=["user1@example.com", "user2@example.com"]
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await digest_service.send_digest_email(digest)
            
            assert result is True
            assert mock_server.send_message.call_count == 1
    
    @pytest.mark.asyncio
    async def test_send_digest_failure_handling(self, digest_service):
        """Should handle SMTP failures gracefully."""
        digest = Digest(
            digest_id=str(uuid4()),
            date=datetime.now(),
            subject="Test Digest",
            items=[],
            html_content="<html><body>Test</body></html>",
            text_content="Test",
            recipients=["test@example.com"]
        )
        
        # Mock SMTP to raise an error
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP Error")
            
            result = await digest_service.send_digest_email(digest)
            
            assert result is False


class TestDigestTracking:
    """Test digest history and tracking."""
    
    @pytest.mark.asyncio
    async def test_mark_digest_as_sent(self, digest_service, postgres_repo):
        """Should mark digest as sent in database."""
        digest_id = str(uuid4())
        
        await digest_service.mark_digest_as_sent(
            digest_id=digest_id,
            recipients=["test@example.com"],
            items_count=5
        )
        
        # Verify record was created
        record = await postgres_repo.get_processing_record(digest_id)
        assert record is not None
        assert record['operation'] == 'send_digest'
        assert record['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_get_digest_history(self, digest_service, postgres_repo):
        """Should retrieve digest history."""
        # Create some digest records
        for i in range(3):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"digest_{i}",
                operation='send_digest',
                status='completed',
                metadata=json.dumps({'items_count': i + 1})
            )
        
        history = await digest_service.get_digest_history(limit=10)
        
        assert len(history) >= 3
        assert all(isinstance(d, Digest) for d in history)
    
    @pytest.mark.asyncio
    async def test_digest_history_pagination(self, digest_service, postgres_repo):
        """Should support pagination in history."""
        # Create several digest records
        for i in range(5):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"digest_{i}",
                operation='send_digest',
                status='completed',
                metadata=json.dumps({'items_count': i + 1})
            )
        
        # Get first page
        page1 = await digest_service.get_digest_history(limit=2, offset=0)
        assert len(page1) == 2
        
        # Get second page
        page2 = await digest_service.get_digest_history(limit=2, offset=2)
        assert len(page2) == 2
        
        # Ensure different results
        page1_ids = {d.digest_id for d in page1}
        page2_ids = {d.digest_id for d in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestDigestIntegration:
    """Test complete digest workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_digest_workflow(self, digest_service, postgres_repo):
        """Should handle complete digest workflow: select, generate, send, track."""
        # Add library content
        records = [
            create_sample_library_content("Workflow Article 1", 9.0, days_ago=1),
            create_sample_library_content("Workflow Article 2", 8.5, days_ago=1),
        ]
        
        for record in records:
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=record['url'],
                operation='add_to_library',
                status='completed',
                metadata=json.dumps({
                    'title': record['title'],
                    'quality_score': record['quality_score'],
                    'tier': record['tier'],
                    'summary': record['summary'],
                    'tags': record['tags']
                })
            )
        
        # Step 1: Select content
        items = await digest_service.select_content_for_digest(
            date=datetime.now(),
            min_quality=7.0,
            limit=10
        )
        assert len(items) >= 2
        
        # Step 2: Generate HTML
        html = await digest_service.generate_digest_html(
            items=items,
            date=datetime.now(),
            subject="Test Workflow Digest"
        )
        assert html is not None
        
        # Step 3: Generate text
        text = await digest_service.generate_digest_text(
            items=items,
            date=datetime.now(),
            subject="Test Workflow Digest"
        )
        assert text is not None
        
        # Step 4: Create digest
        digest = Digest(
            digest_id=str(uuid4()),
            date=datetime.now(),
            subject="Test Workflow Digest",
            items=items,
            html_content=html,
            text_content=text,
            recipients=["test@example.com"]
        )
        
        # Step 5: Send (mocked)
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = await digest_service.send_digest_email(digest)
            assert result is True
        
        # Step 6: Mark as sent
        await digest_service.mark_digest_as_sent(
            digest_id=digest.digest_id,
            recipients=digest.recipients,
            items_count=len(items)
        )
        
        # Step 7: Verify in history
        history = await digest_service.get_digest_history(limit=5)
        assert any(d.digest_id == digest.digest_id for d in history)
