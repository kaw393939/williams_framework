"""
PostgreSQL Metadata Repository for Williams-Librarian.

Handles persistence of ProcessingRecord and MaintenanceTask metadata
using asyncpg for async database operations with connection pooling.
"""
import asyncpg
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any


class PostgresRepository:
    """
    Async PostgreSQL repository using asyncpg.
    
    Manages:
    - ProcessingRecord: Track content processing operations
    - MaintenanceTask: Schedule and track maintenance operations
    
    Features:
    - Connection pooling for performance
    - Async operations (non-blocking)
    - Transaction support
    - CRUD operations for both entities
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_pool_size: int = 2,
        max_pool_size: int = 10
    ):
        """
        Initialize PostgreSQL repository.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_pool_size: Minimum connections in pool
            max_pool_size: Maximum connections in pool
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool: asyncpg.Pool | None = None
    
    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=self.min_pool_size,
            max_size=self.max_pool_size
        )
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def create_tables(self):
        """Create required database tables."""
        async with self.pool.acquire() as conn:
            # Create processing_records table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_records (
                    record_id VARCHAR(255) PRIMARY KEY,
                    content_url TEXT NOT NULL,
                    operation VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    metadata JSONB
                )
            """)
            
            # Create maintenance_tasks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_tasks (
                    task_id VARCHAR(255) PRIMARY KEY,
                    task_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    scheduled_for TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    metadata JSONB
                )
            """)
            
            # Create indexes for common queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_records_status 
                ON processing_records(status)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_records_operation 
                ON processing_records(operation)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_maintenance_tasks_status 
                ON maintenance_tasks(status)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_maintenance_tasks_scheduled 
                ON maintenance_tasks(scheduled_for)
            """)
    
    async def execute(self, query: str, *args):
        """Execute a query without returning results."""
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> dict | None:
        """Fetch one row as a dictionary."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args) -> list[dict]:
        """Fetch all rows as list of dictionaries."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn
    
    # ========== ProcessingRecord Operations ==========
    
    async def create_processing_record(
        self,
        record_id: str,
        content_url: str,
        operation: str,
        status: str,
        metadata: dict | None = None
    ):
        """
        Create a new processing record.
        
        Args:
            record_id: Unique record identifier
            content_url: URL of content being processed
            operation: Operation type (extract, screen, process, etc.)
            status: Current status (started, completed, failed)
            metadata: Optional metadata
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_records 
                (record_id, content_url, operation, status, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, record_id, content_url, operation, status, metadata)
    
    async def get_processing_record(self, record_id: str) -> dict | None:
        """
        Get a processing record by ID.
        
        Args:
            record_id: Record identifier
            
        Returns:
            Record dictionary or None if not found
        """
        return await self.fetch_one("""
            SELECT * FROM processing_records WHERE record_id = $1
        """, record_id)
    
    async def update_processing_record_status(
        self,
        record_id: str,
        status: str,
        error_message: str | None = None
    ):
        """
        Update processing record status.
        
        Args:
            record_id: Record identifier
            status: New status
            error_message: Optional error message for failed status
        """
        async with self.pool.acquire() as conn:
            if status == "completed" or status == "failed":
                await conn.execute("""
                    UPDATE processing_records
                    SET status = $1, completed_at = NOW(), error_message = $2
                    WHERE record_id = $3
                """, status, error_message, record_id)
            else:
                await conn.execute("""
                    UPDATE processing_records
                    SET status = $1, error_message = $2
                    WHERE record_id = $3
                """, status, error_message, record_id)
    
    async def list_processing_records(
        self,
        status: str | None = None,
        operation: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """
        List processing records with optional filters.
        
        Args:
            status: Filter by status
            operation: Filter by operation type
            limit: Maximum records to return
            
        Returns:
            List of record dictionaries
        """
        query_parts = ["SELECT * FROM processing_records WHERE 1=1"]
        params = []
        param_count = 1
        
        if status:
            query_parts.append(f"AND status = ${param_count}")
            params.append(status)
            param_count += 1
        
        if operation:
            query_parts.append(f"AND operation = ${param_count}")
            params.append(operation)
            param_count += 1
        
        query_parts.append("ORDER BY started_at DESC")
        query_parts.append(f"LIMIT ${param_count}")
        params.append(limit)
        
        query = " ".join(query_parts)
        return await self.fetch_all(query, *params)
    
    async def delete_processing_record(self, record_id: str):
        """
        Delete a processing record.
        
        Args:
            record_id: Record identifier
        """
        await self.execute("""
            DELETE FROM processing_records WHERE record_id = $1
        """, record_id)
    
    async def get_processing_stats(self) -> dict[str, int]:
        """
        Get statistics about processing records.
        
        Returns:
            Dictionary with counts by status
        """
        rows = await self.fetch_all("""
            SELECT status, COUNT(*) as count
            FROM processing_records
            GROUP BY status
        """)
        
        stats = {}
        for row in rows:
            stats[row['status']] = row['count']
        
        return stats
    
    async def get_recent_processing_records(self, limit: int = 10) -> list[dict]:
        """
        Get most recent processing records.
        
        Args:
            limit: Number of records to return
            
        Returns:
            List of recent records
        """
        return await self.fetch_all("""
            SELECT * FROM processing_records
            ORDER BY started_at DESC
            LIMIT $1
        """, limit)
    
    # ========== MaintenanceTask Operations ==========
    
    async def create_maintenance_task(
        self,
        task_id: str,
        task_type: str,
        status: str,
        scheduled_for: datetime,
        metadata: dict | None = None
    ):
        """
        Create a new maintenance task.
        
        Args:
            task_id: Unique task identifier
            task_type: Task type (rescreen, cleanup, digest, backup)
            status: Initial status (pending, running, completed, failed)
            scheduled_for: When task should run
            metadata: Optional metadata
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO maintenance_tasks
                (task_id, task_type, status, scheduled_for, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, task_id, task_type, status, scheduled_for, metadata)
    
    async def get_maintenance_task(self, task_id: str) -> dict | None:
        """
        Get a maintenance task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task dictionary or None if not found
        """
        return await self.fetch_one("""
            SELECT * FROM maintenance_tasks WHERE task_id = $1
        """, task_id)
    
    async def update_maintenance_task_status(
        self,
        task_id: str,
        status: str
    ):
        """
        Update maintenance task status.
        
        Args:
            task_id: Task identifier
            status: New status
        """
        async with self.pool.acquire() as conn:
            if status == "completed" or status == "failed":
                await conn.execute("""
                    UPDATE maintenance_tasks
                    SET status = $1, completed_at = NOW()
                    WHERE task_id = $2
                """, status, task_id)
            else:
                await conn.execute("""
                    UPDATE maintenance_tasks
                    SET status = $1
                    WHERE task_id = $2
                """, status, task_id)
    
    async def list_maintenance_tasks(
        self,
        status: str | None = None,
        task_type: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """
        List maintenance tasks with optional filters.
        
        Args:
            status: Filter by status
            task_type: Filter by task type
            limit: Maximum tasks to return
            
        Returns:
            List of task dictionaries
        """
        query_parts = ["SELECT * FROM maintenance_tasks WHERE 1=1"]
        params = []
        param_count = 1
        
        if status:
            query_parts.append(f"AND status = ${param_count}")
            params.append(status)
            param_count += 1
        
        if task_type:
            query_parts.append(f"AND task_type = ${param_count}")
            params.append(task_type)
            param_count += 1
        
        query_parts.append("ORDER BY scheduled_for ASC")
        query_parts.append(f"LIMIT ${param_count}")
        params.append(limit)
        
        query = " ".join(query_parts)
        return await self.fetch_all(query, *params)
    
    async def list_overdue_maintenance_tasks(self) -> list[dict]:
        """
        List maintenance tasks that are overdue (scheduled in the past).
        
        Returns:
            List of overdue task dictionaries
        """
        return await self.fetch_all("""
            SELECT * FROM maintenance_tasks
            WHERE scheduled_for < NOW()
            AND status = 'pending'
            ORDER BY scheduled_for ASC
        """)
    
    async def delete_maintenance_task(self, task_id: str):
        """
        Delete a maintenance task.
        
        Args:
            task_id: Task identifier
        """
        await self.execute("""
            DELETE FROM maintenance_tasks WHERE task_id = $1
        """, task_id)
