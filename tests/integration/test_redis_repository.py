"""
Integration tests for Redis Cache Repository.

Tests use a REAL Redis instance running in Docker (NO MOCKS).
Following TDD methodology: RED-GREEN-REFACTOR.
Uses async/await with redis-py.
"""
import pytest
from datetime import timedelta
from uuid import uuid4

from app.repositories.redis_repository import RedisRepository
from app.core.config import settings


@pytest.fixture
async def redis_repo():
    """Create RedisRepository instance."""
    repo = RedisRepository(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True
    )
    
    await repo.connect()
    
    yield repo
    
    # Cleanup: flush all keys from test database
    await repo.flush_all()
    await repo.close()


class TestRedisRepositoryConnection:
    """Test Redis connection and initialization."""
    
    @pytest.mark.asyncio
    async def test_connection_successful(self):
        """Should connect to Redis successfully."""
        repo = RedisRepository(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        
        await repo.connect()
        assert repo.client is not None
        
        # Verify with ping
        result = await repo.ping()
        assert result is True
        
        await repo.close()
    
    @pytest.mark.asyncio
    async def test_connection_with_pool(self, redis_repo):
        """Should use connection pool."""
        # Connection pool created in fixture
        result = await redis_repo.ping()
        assert result is True


class TestBasicCacheOperations:
    """Test basic cache get/set/delete operations."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_string(self, redis_repo):
        """Should set and retrieve a string value."""
        key = f"test:{uuid4()}"
        value = "test-value"
        
        await redis_repo.set(key, value)
        
        # Retrieve value
        result = await redis_repo.get(key)
        assert result == value
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, redis_repo):
        """Should return None for non-existent key."""
        result = await redis_repo.get("nonexistent-key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_with_ttl(self, redis_repo):
        """Should set value with expiration time."""
        key = f"test:{uuid4()}"
        value = "expires-soon"
        ttl_seconds = 60
        
        await redis_repo.set(key, value, ttl=ttl_seconds)
        
        # Verify value exists
        result = await redis_repo.get(key)
        assert result == value
        
        # Check TTL
        ttl = await redis_repo.ttl(key)
        assert 50 < ttl <= 60  # Should be close to 60 seconds
    
    @pytest.mark.asyncio
    async def test_delete_key(self, redis_repo):
        """Should delete a key."""
        key = f"test:{uuid4()}"
        value = "to-be-deleted"
        
        await redis_repo.set(key, value)
        
        # Delete key
        deleted = await redis_repo.delete(key)
        assert deleted == 1
        
        # Verify deleted
        result = await redis_repo.get(key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, redis_repo):
        """Should return 0 when deleting non-existent key."""
        deleted = await redis_repo.delete("nonexistent-key")
        assert deleted == 0
    
    @pytest.mark.asyncio
    async def test_exists_key(self, redis_repo):
        """Should check if key exists."""
        key = f"test:{uuid4()}"
        
        # Key should not exist
        exists = await redis_repo.exists(key)
        assert exists is False
        
        # Set key
        await redis_repo.set(key, "value")
        
        # Key should exist
        exists = await redis_repo.exists(key)
        assert exists is True


class TestJSONOperations:
    """Test JSON serialization/deserialization."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_dict(self, redis_repo):
        """Should serialize and deserialize dictionary."""
        key = f"test:{uuid4()}"
        data = {
            "title": "Test Article",
            "quality_score": 8.5,
            "tags": ["python", "testing"]
        }
        
        await redis_repo.set_json(key, data)
        
        # Retrieve and deserialize
        result = await redis_repo.get_json(key)
        assert result == data
        assert result["quality_score"] == 8.5
        assert "python" in result["tags"]
    
    @pytest.mark.asyncio
    async def test_get_json_nonexistent(self, redis_repo):
        """Should return None for non-existent JSON key."""
        result = await redis_repo.get_json("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_json_with_ttl(self, redis_repo):
        """Should cache JSON with TTL."""
        key = f"test:{uuid4()}"
        data = {"cached": True}
        
        await redis_repo.set_json(key, data, ttl=30)
        
        # Verify cached
        result = await redis_repo.get_json(key)
        assert result == data
        
        # Check TTL
        ttl = await redis_repo.ttl(key)
        assert 20 < ttl <= 30


class TestBatchOperations:
    """Test batch get/set/delete operations."""
    
    @pytest.mark.asyncio
    async def test_mset_and_mget(self, redis_repo):
        """Should set and get multiple keys at once."""
        data = {
            f"test:{uuid4()}": "value1",
            f"test:{uuid4()}": "value2",
            f"test:{uuid4()}": "value3"
        }
        
        # Set multiple keys
        await redis_repo.mset(data)
        
        # Get multiple keys
        keys = list(data.keys())
        results = await redis_repo.mget(keys)
        
        assert len(results) == 3
        assert "value1" in results
        assert "value2" in results
        assert "value3" in results
    
    @pytest.mark.asyncio
    async def test_delete_multiple_keys(self, redis_repo):
        """Should delete multiple keys at once."""
        keys = [f"test:{uuid4()}" for _ in range(5)]
        
        # Set keys
        for key in keys:
            await redis_repo.set(key, "value")
        
        # Delete all
        deleted = await redis_repo.delete(*keys)
        assert deleted == 5
        
        # Verify all deleted
        for key in keys:
            exists = await redis_repo.exists(key)
            assert exists is False


class TestCachePatterns:
    """Test common cache patterns."""
    
    @pytest.mark.asyncio
    async def test_cache_screening_result(self, redis_repo):
        """Should cache content screening result."""
        url = "https://example.com/article"
        cache_key = f"screening:{url}"
        
        screening_data = {
            "screening_score": 8.5,
            "decision": "approved",
            "reasoning": "High-quality content"
        }
        
        # Cache result with 1 hour TTL
        await redis_repo.set_json(cache_key, screening_data, ttl=3600)
        
        # Retrieve from cache
        cached = await redis_repo.get_json(cache_key)
        assert cached["screening_score"] == 8.5
        assert cached["decision"] == "approved"
    
    @pytest.mark.asyncio
    async def test_cache_processed_content(self, redis_repo):
        """Should cache processed content."""
        url = "https://example.com/article"
        cache_key = f"processed:{url}"
        
        content_data = {
            "title": "Test Article",
            "summary": "This is a test",
            "key_points": ["Point 1", "Point 2"],
            "tags": ["python", "testing"]
        }
        
        # Cache for 30 minutes
        await redis_repo.set_json(cache_key, content_data, ttl=1800)
        
        cached = await redis_repo.get_json(cache_key)
        assert cached["title"] == "Test Article"
        assert len(cached["key_points"]) == 2
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_by_pattern(self, redis_repo):
        """Should delete keys matching a pattern."""
        # Create keys with pattern
        prefix = f"user:123"
        keys = [
            f"{prefix}:session",
            f"{prefix}:profile",
            f"{prefix}:settings"
        ]
        
        for key in keys:
            await redis_repo.set(key, "value")
        
        # Invalidate all keys for user
        deleted = await redis_repo.delete_pattern(f"{prefix}:*")
        assert deleted >= 3
        
        # Verify all deleted
        for key in keys:
            exists = await redis_repo.exists(key)
            assert exists is False


class TestTTLOperations:
    """Test TTL (Time To Live) operations."""
    
    @pytest.mark.asyncio
    async def test_set_expire(self, redis_repo):
        """Should set expiration on existing key."""
        key = f"test:{uuid4()}"
        
        # Set key without TTL
        await redis_repo.set(key, "value")
        
        # Set expiration
        await redis_repo.expire(key, 120)
        
        # Check TTL
        ttl = await redis_repo.ttl(key)
        assert 110 < ttl <= 120
    
    @pytest.mark.asyncio
    async def test_ttl_for_key_without_expiry(self, redis_repo):
        """Should return -1 for key without expiration."""
        key = f"test:{uuid4()}"
        
        await redis_repo.set(key, "value")
        
        ttl = await redis_repo.ttl(key)
        assert ttl == -1  # No expiration set
    
    @pytest.mark.asyncio
    async def test_ttl_for_nonexistent_key(self, redis_repo):
        """Should return -2 for non-existent key."""
        ttl = await redis_repo.ttl("nonexistent-key")
        assert ttl == -2


class TestCacheStatistics:
    """Test cache statistics and info."""
    
    @pytest.mark.asyncio
    async def test_dbsize(self, redis_repo):
        """Should get number of keys in database."""
        # Add some keys
        for i in range(5):
            await redis_repo.set(f"test:{i}", f"value{i}")
        
        # Get database size
        size = await redis_repo.dbsize()
        assert size >= 5
    
    @pytest.mark.asyncio
    async def test_keys_by_pattern(self, redis_repo):
        """Should find keys matching pattern."""
        prefix = f"test:{uuid4()}"
        
        # Create keys
        for i in range(3):
            await redis_repo.set(f"{prefix}:{i}", f"value{i}")
        
        # Find keys
        keys = await redis_repo.keys(f"{prefix}:*")
        assert len(keys) == 3
    
    @pytest.mark.asyncio
    async def test_info(self, redis_repo):
        """Should get Redis server info."""
        info = await redis_repo.info()
        assert info is not None
        assert "redis_version" in info
