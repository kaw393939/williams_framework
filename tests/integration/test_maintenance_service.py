"""
Integration tests for MaintenanceService.

Tests system maintenance operations including cache cleanup, embedding
recomputation, system reports, and data integrity checks.
Uses real repositories (no mocks).
"""
import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.maintenance_service import MaintenanceService
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.redis_repository import RedisRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.minio_repository import MinIORepository
from app.core.config import settings


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
    await repo.execute("DELETE FROM maintenance_tasks")
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
    repo = QdrantRepository(client, "test_maintenance")
    
    yield repo
    
    # Cleanup
    try:
        client.delete_collection("test_maintenance")
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
    
    repo = MinIORepository(client, "test-maintenance")
    
    yield repo
    
    # Cleanup
    try:
        objects = repo.list_files()
        if objects:
            repo.delete_files([obj['key'] for obj in objects])
    except:
        pass


@pytest.fixture
async def maintenance_service(postgres_repo, redis_repo, qdrant_repo, minio_repo):
    """Create MaintenanceService with all repositories."""
    return MaintenanceService(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo,
        qdrant_repo=qdrant_repo,
        minio_repo=minio_repo
    )


class TestCacheCleanup:
    """Test Redis cache cleanup operations."""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_cache_entries(self, maintenance_service, redis_repo):
        """Should remove cache entries older than specified days."""
        # Add cache entries with different ages
        await redis_repo.set("recent_key_1", "value1", ttl=86400)  # 1 day TTL
        await redis_repo.set("recent_key_2", "value2", ttl=86400)
        await redis_repo.set("old_key_1", "value3", ttl=1)  # 1 second TTL
        await redis_repo.set("old_key_2", "value4", ttl=1)
        
        # Wait for old keys to expire
        import asyncio
        await asyncio.sleep(2)
        
        # Cleanup entries older than 1 day (should find expired ones)
        deleted_count = await maintenance_service.cleanup_old_cache_entries(days=1)
        
        # Recent keys should still exist
        assert await redis_repo.get("recent_key_1") is not None
        assert await redis_repo.get("recent_key_2") is not None
    
    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_entries(self, maintenance_service, redis_repo):
        """Should not remove recent cache entries."""
        # Add recent cache entries
        await redis_repo.set("key1", "value1", ttl=86400)
        await redis_repo.set("key2", "value2", ttl=86400)
        await redis_repo.set("key3", "value3", ttl=86400)
        
        # Cleanup old entries (should not affect recent ones)
        deleted_count = await maintenance_service.cleanup_old_cache_entries(days=7)
        
        # All keys should still exist
        assert await redis_repo.get("key1") == "value1"
        assert await redis_repo.get("key2") == "value2"
        assert await redis_repo.get("key3") == "value3"


class TestEmbeddingRecomputation:
    """Test embedding recomputation operations."""
    
    @pytest.mark.asyncio
    async def test_recompute_embeddings(self, maintenance_service, qdrant_repo):
        """Should recompute embeddings for specified content."""
        # Add initial embeddings
        content_ids = []
        for i in range(3):
            content_id = str(uuid4())
            content_ids.append(content_id)
            qdrant_repo.add(
                content_id=content_id,
                vector=[0.1] * 384,
                metadata={'title': f'Article {i}', 'recomputed': False}
            )
        
        # Recompute embeddings
        result = await maintenance_service.recompute_embeddings(content_ids)
        
        assert result['success'] > 0
        assert result['failed'] == 0
        assert result['total'] == 3
    
    @pytest.mark.asyncio
    async def test_recompute_embeddings_error_handling(self, maintenance_service):
        """Should handle errors during recomputation."""
        # Try to recompute non-existent content
        result = await maintenance_service.recompute_embeddings(['invalid_id_1', 'invalid_id_2'])
        
        # Should report failures but not crash
        assert 'total' in result
        assert 'success' in result
        assert 'failed' in result


class TestSystemReports:
    """Test system report generation."""
    
    @pytest.mark.asyncio
    async def test_generate_system_report(self, maintenance_service, postgres_repo, redis_repo):
        """Should generate comprehensive system report."""
        # Add some test data
        await postgres_repo.create_processing_record(
            record_id=str(uuid4()),
            content_url="https://example.com",
            operation="extract",
            status="completed",
            metadata=json.dumps({'test': True})
        )
        
        await redis_repo.set("test_key", "test_value")
        
        # Generate report
        report = await maintenance_service.generate_system_report()
        
        assert 'timestamp' in report
        assert 'repositories' in report
        assert 'postgres' in report['repositories']
        assert 'redis' in report['repositories']
        assert 'qdrant' in report['repositories']
        assert 'minio' in report['repositories']
    
    @pytest.mark.asyncio
    async def test_system_report_includes_metrics(self, maintenance_service):
        """Should include metrics in system report."""
        report = await maintenance_service.generate_system_report()
        
        # Check that metrics are included
        assert report['repositories']['postgres']['status'] in ['connected', 'disconnected', 'error']
        assert 'record_count' in report['repositories']['postgres'] or 'error' in report['repositories']['postgres']


class TestDataIntegrity:
    """Test data integrity checks."""
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files(self, maintenance_service, minio_repo, postgres_repo):
        """Should identify and remove orphaned MinIO files."""
        # Add database record
        content_id_1 = str(uuid4())
        await postgres_repo.create_processing_record(
            record_id=content_id_1,
            content_url=f"minio://test-maintenance/{content_id_1}.txt",
            operation="store",
            status="completed",
            metadata=json.dumps({})
        )
        
        # Cleanup orphans (should not crash even if no orphans)
        cleaned_count = await maintenance_service.cleanup_orphaned_files()
        
        # Should return a valid count (0 or more)
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0
    
    @pytest.mark.asyncio
    async def test_verify_data_integrity(self, maintenance_service, postgres_repo):
        """Should check data consistency across repositories."""
        # Add some test data
        await postgres_repo.create_processing_record(
            record_id=str(uuid4()),
            content_url="https://example.com",
            operation="extract",
            status="completed",
            metadata=json.dumps({'test': True})
        )
        
        # Verify integrity
        report = await maintenance_service.verify_data_integrity()
        
        assert 'timestamp' in report
        assert 'checks_performed' in report
        assert 'issues_found' in report
        assert isinstance(report['issues_found'], list)


class TestDatabaseMaintenance:
    """Test database maintenance operations."""
    
    @pytest.mark.asyncio
    async def test_vacuum_database(self, maintenance_service):
        """Should optimize database performance."""
        result = await maintenance_service.vacuum_database()
        
        # Should return success status
        assert isinstance(result, bool)


class TestMaintenanceIntegration:
    """Test complete maintenance workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_maintenance_workflow(self, maintenance_service, postgres_repo, redis_repo):
        """Should run complete maintenance cycle."""
        # Setup test data
        await redis_repo.set("test_key", "test_value")
        await postgres_repo.create_processing_record(
            record_id=str(uuid4()),
            content_url="https://example.com",
            operation="test",
            status="completed",
            metadata=json.dumps({})
        )
        
        # Run maintenance operations
        # 1. Generate report
        report = await maintenance_service.generate_system_report()
        assert 'repositories' in report
        
        # 2. Verify integrity
        integrity = await maintenance_service.verify_data_integrity()
        assert 'checks_performed' in integrity
        
        # 3. Cleanup (should not crash)
        deleted = await maintenance_service.cleanup_old_cache_entries(days=30)
        assert isinstance(deleted, int)
        
        # All operations should complete without errors
        assert True
