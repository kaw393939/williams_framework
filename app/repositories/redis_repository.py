"""
Redis Cache Repository for Williams-Librarian.

Handles caching of screening results, processed content, and other
frequently accessed data using redis-py with async support.
"""
import json
from typing import Any
import redis.asyncio as redis


class RedisRepository:
    """
    Async Redis cache repository using redis-py.
    
    Provides:
    - Basic cache operations (get, set, delete)
    - JSON serialization for complex objects
    - TTL (Time To Live) management
    - Batch operations (mget, mset)
    - Pattern-based key operations
    - Cache statistics
    
    Features:
    - Async operations (non-blocking)
    - Connection pooling for performance
    - JSON serialization/deserialization
    - Flexible TTL support
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        db: int = 0,
        password: str | None = None,
        decode_responses: bool = False,
        max_connections: int = 10
    ):
        """
        Initialize Redis repository.
        
        Args:
            host: Redis host
            port: Redis port
            db: Database number (0-15)
            password: Optional password
            decode_responses: Decode byte responses to strings
            max_connections: Maximum connections in pool
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self.client: redis.Redis | None = None
    
    async def connect(self):
        """Create Redis client with connection pool."""
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
            max_connections=self.max_connections
        )
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
    
    async def ping(self) -> bool:
        """
        Ping Redis server to check connection.
        
        Returns:
            True if connected
        """
        return await self.client.ping()
    
    # ========== Basic Cache Operations ==========
    
    async def get(self, key: str) -> str | None:
        """
        Get value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Value or None if not found
        """
        result = await self.client.get(key)
        if result and not self.decode_responses:
            return result.decode('utf-8')
        return result
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None
    ):
        """
        Set value with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = no expiration)
        """
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.
        
        Args:
            keys: Keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        return await self.client.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        result = await self.client.exists(key)
        return result > 0
    
    # ========== JSON Operations ==========
    
    async def get_json(self, key: str) -> dict | list | None:
        """
        Get JSON value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized JSON or None if not found
        """
        value = await self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    
    async def set_json(
        self,
        key: str,
        value: dict | list,
        ttl: int | None = None
    ):
        """
        Set JSON value with optional TTL.
        
        Args:
            key: Cache key
            value: Dictionary or list to cache
            ttl: Time to live in seconds
        """
        json_str = json.dumps(value)
        await self.set(key, json_str, ttl=ttl)
    
    # ========== Batch Operations ==========
    
    async def mget(self, keys: list[str]) -> list[str | None]:
        """
        Get multiple values at once.
        
        Args:
            keys: List of keys
            
        Returns:
            List of values (None for missing keys)
        """
        if not keys:
            return []
        
        results = await self.client.mget(keys)
        
        if not self.decode_responses:
            return [r.decode('utf-8') if r else None for r in results]
        return results
    
    async def mset(self, mapping: dict[str, str]):
        """
        Set multiple key-value pairs at once.
        
        Args:
            mapping: Dictionary of key-value pairs
        """
        if mapping:
            await self.client.mset(mapping)
    
    # ========== TTL Operations ==========
    
    async def ttl(self, key: str) -> int:
        """
        Get time to live for key.
        
        Args:
            key: Cache key
            
        Returns:
            Seconds until expiration, -1 if no expiration, -2 if key doesn't exist
        """
        return await self.client.ttl(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on existing key.
        
        Args:
            key: Cache key
            seconds: Seconds until expiration
            
        Returns:
            True if expiration was set
        """
        return await self.client.expire(key, seconds)
    
    # ========== Pattern Operations ==========
    
    async def keys(self, pattern: str) -> list[str]:
        """
        Find keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            List of matching keys
        """
        keys = await self.client.keys(pattern)
        
        if not self.decode_responses:
            return [k.decode('utf-8') for k in keys]
        return keys
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern
            
        Returns:
            Number of keys deleted
        """
        keys = await self.keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0
    
    # ========== Cache Statistics ==========
    
    async def dbsize(self) -> int:
        """
        Get number of keys in current database.
        
        Returns:
            Key count
        """
        return await self.client.dbsize()
    
    async def info(self, section: str | None = None) -> dict:
        """
        Get Redis server information.
        
        Args:
            section: Optional info section (e.g., "memory", "stats")
            
        Returns:
            Server info dictionary
        """
        return await self.client.info(section)
    
    async def flush_all(self):
        """Flush all keys from current database. Use with caution!"""
        await self.client.flushdb()
