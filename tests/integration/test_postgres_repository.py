"""
Integration tests for PostgreSQL Metadata Repository.

Tests use a REAL PostgreSQL instance running in Docker (NO MOCKS).
Following TDD methodology: RED-GREEN-REFACTOR.
Uses async/await with asyncpg.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import settings
from app.repositories.postgres_repository import PostgresRepository


@pytest.fixture
async def postgres_repo():
    """Create PostgresRepository instance and setup tables."""
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

    # Cleanup: drop test data
    await repo.execute("DELETE FROM processing_records")
    await repo.execute("DELETE FROM maintenance_tasks")
    await repo.close()


class TestPostgresRepositoryConnection:
    """Test database connection and initialization."""

    @pytest.mark.asyncio
    async def test_connection_successful(self):
        """Should connect to PostgreSQL successfully."""
        repo = PostgresRepository(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )

        await repo.connect()
        assert repo.pool is not None

        await repo.close()

    @pytest.mark.asyncio
    async def test_create_tables(self, postgres_repo):
        """Should create required tables."""
        # Tables created in fixture
        # Verify by querying table existence
        result = await postgres_repo.fetch_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'processing_records'
            )
        """)
        assert result['exists'] is True

        result = await postgres_repo.fetch_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'maintenance_tasks'
            )
        """)
        assert result['exists'] is True


class TestProcessingRecordOperations:
    """Test CRUD operations for ProcessingRecord."""

    @pytest.mark.asyncio
    async def test_create_processing_record(self, postgres_repo):
        """Should create a new processing record."""
        record_id = str(uuid4())
        url = "https://example.com/article"

        await postgres_repo.create_processing_record(
            record_id=record_id,
            content_url=url,
            operation="extract",
            status="started"
        )

        # Verify created
        record = await postgres_repo.get_processing_record(record_id)
        assert record is not None
        assert record['record_id'] == record_id
        assert record['content_url'] == url
        assert record['operation'] == "extract"
        assert record['status'] == "started"
        assert record['started_at'] is not None

    @pytest.mark.asyncio
    async def test_get_processing_record_not_found(self, postgres_repo):
        """Should return None for non-existent record."""
        record = await postgres_repo.get_processing_record("nonexistent-id")
        assert record is None

    @pytest.mark.asyncio
    async def test_update_processing_record_status(self, postgres_repo):
        """Should update record status and completion time."""
        record_id = str(uuid4())

        # Create record
        await postgres_repo.create_processing_record(
            record_id=record_id,
            content_url="https://example.com/test",
            operation="process",
            status="started"
        )

        # Update to completed
        await postgres_repo.update_processing_record_status(
            record_id=record_id,
            status="completed"
        )

        # Verify updated
        record = await postgres_repo.get_processing_record(record_id)
        assert record['status'] == "completed"
        assert record['completed_at'] is not None

    @pytest.mark.asyncio
    async def test_update_processing_record_with_error(self, postgres_repo):
        """Should update record with error message."""
        record_id = str(uuid4())

        await postgres_repo.create_processing_record(
            record_id=record_id,
            content_url="https://example.com/test",
            operation="extract",
            status="started"
        )

        error_message = "Connection timeout"
        await postgres_repo.update_processing_record_status(
            record_id=record_id,
            status="failed",
            error_message=error_message
        )

        record = await postgres_repo.get_processing_record(record_id)
        assert record['status'] == "failed"
        assert record['error_message'] == error_message

    @pytest.mark.asyncio
    async def test_list_processing_records_by_status(self, postgres_repo):
        """Should list records filtered by status."""
        # Create records with different statuses
        for i in range(3):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"https://example.com/{i}",
                operation="extract",
                status="completed"
            )

        for i in range(2):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"https://example.com/fail{i}",
                operation="extract",
                status="failed"
            )

        # List completed records
        completed = await postgres_repo.list_processing_records(status="completed")
        assert len(completed) == 3

        # List failed records
        failed = await postgres_repo.list_processing_records(status="failed")
        assert len(failed) == 2

    @pytest.mark.asyncio
    async def test_list_processing_records_by_operation(self, postgres_repo):
        """Should list records filtered by operation type."""
        await postgres_repo.create_processing_record(
            record_id=str(uuid4()),
            content_url="https://example.com/1",
            operation="extract",
            status="completed"
        )

        await postgres_repo.create_processing_record(
            record_id=str(uuid4()),
            content_url="https://example.com/2",
            operation="screen",
            status="completed"
        )

        # Filter by operation
        extract_ops = await postgres_repo.list_processing_records(operation="extract")
        assert len(extract_ops) == 1
        assert extract_ops[0]['operation'] == "extract"

    @pytest.mark.asyncio
    async def test_delete_processing_record(self, postgres_repo):
        """Should delete a processing record."""
        record_id = str(uuid4())

        await postgres_repo.create_processing_record(
            record_id=record_id,
            content_url="https://example.com/test",
            operation="extract",
            status="completed"
        )

        # Delete
        await postgres_repo.delete_processing_record(record_id)

        # Verify deleted
        record = await postgres_repo.get_processing_record(record_id)
        assert record is None


class TestMaintenanceTaskOperations:
    """Test CRUD operations for MaintenanceTask."""

    @pytest.mark.asyncio
    async def test_create_maintenance_task(self, postgres_repo):
        """Should create a new maintenance task."""
        task_id = str(uuid4())
        scheduled_for = datetime.now() + timedelta(hours=1)

        await postgres_repo.create_maintenance_task(
            task_id=task_id,
            task_type="rescreen",
            status="pending",
            scheduled_for=scheduled_for
        )

        # Verify created
        task = await postgres_repo.get_maintenance_task(task_id)
        assert task is not None
        assert task['task_id'] == task_id
        assert task['task_type'] == "rescreen"
        assert task['status'] == "pending"

    @pytest.mark.asyncio
    async def test_get_maintenance_task_not_found(self, postgres_repo):
        """Should return None for non-existent task."""
        task = await postgres_repo.get_maintenance_task("nonexistent-id")
        assert task is None

    @pytest.mark.asyncio
    async def test_update_maintenance_task_status(self, postgres_repo):
        """Should update task status."""
        task_id = str(uuid4())

        await postgres_repo.create_maintenance_task(
            task_id=task_id,
            task_type="cleanup",
            status="pending",
            scheduled_for=datetime.now()
        )

        # Start task
        await postgres_repo.update_maintenance_task_status(
            task_id=task_id,
            status="running"
        )

        task = await postgres_repo.get_maintenance_task(task_id)
        assert task['status'] == "running"

        # Complete task
        await postgres_repo.update_maintenance_task_status(
            task_id=task_id,
            status="completed"
        )

        task = await postgres_repo.get_maintenance_task(task_id)
        assert task['status'] == "completed"
        assert task['completed_at'] is not None

    @pytest.mark.asyncio
    async def test_list_pending_maintenance_tasks(self, postgres_repo):
        """Should list all pending tasks."""
        # Create tasks with different statuses
        for i in range(3):
            await postgres_repo.create_maintenance_task(
                task_id=str(uuid4()),
                task_type="digest",
                status="pending",
                scheduled_for=datetime.now() + timedelta(hours=i)
            )

        await postgres_repo.create_maintenance_task(
            task_id=str(uuid4()),
            task_type="backup",
            status="completed",
            scheduled_for=datetime.now()
        )

        # List pending tasks
        pending = await postgres_repo.list_maintenance_tasks(status="pending")
        assert len(pending) == 3

    @pytest.mark.asyncio
    async def test_list_overdue_maintenance_tasks(self, postgres_repo):
        """Should list tasks scheduled in the past."""
        # Create overdue task
        await postgres_repo.create_maintenance_task(
            task_id=str(uuid4()),
            task_type="cleanup",
            status="pending",
            scheduled_for=datetime.now() - timedelta(hours=1)
        )

        # Create future task
        await postgres_repo.create_maintenance_task(
            task_id=str(uuid4()),
            task_type="digest",
            status="pending",
            scheduled_for=datetime.now() + timedelta(hours=1)
        )

        # Get overdue tasks
        overdue = await postgres_repo.list_overdue_maintenance_tasks()
        assert len(overdue) >= 1
        assert overdue[0]['scheduled_for'] < datetime.now()

    @pytest.mark.asyncio
    async def test_delete_maintenance_task(self, postgres_repo):
        """Should delete a maintenance task."""
        task_id = str(uuid4())

        await postgres_repo.create_maintenance_task(
            task_id=task_id,
            task_type="cleanup",
            status="completed",
            scheduled_for=datetime.now()
        )

        # Delete
        await postgres_repo.delete_maintenance_task(task_id)

        # Verify deleted
        task = await postgres_repo.get_maintenance_task(task_id)
        assert task is None


class TestTransactionOperations:
    """Test transaction support."""

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, postgres_repo):
        """Should rollback transaction on error."""
        record_id = str(uuid4())

        try:
            async with postgres_repo.transaction() as conn:
                # Create record within transaction
                await conn.execute("""
                    INSERT INTO processing_records
                    (record_id, content_url, operation, status)
                    VALUES ($1, $2, $3, $4)
                """, record_id, "https://example.com/test", "extract", "started")

                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify record was not created (transaction rolled back)
        record = await postgres_repo.get_processing_record(record_id)
        assert record is None

    @pytest.mark.asyncio
    async def test_transaction_commit_on_success(self, postgres_repo):
        """Should commit transaction on success."""
        record_id = str(uuid4())

        async with postgres_repo.transaction() as conn:
            # Create record within transaction
            await conn.execute("""
                INSERT INTO processing_records
                (record_id, content_url, operation, status)
                VALUES ($1, $2, $3, $4)
            """, record_id, "https://example.com/test", "extract", "started")

        # Verify record was created (transaction committed)
        record = await postgres_repo.get_processing_record(record_id)
        assert record is not None


class TestQueryStatistics:
    """Test statistical queries."""

    @pytest.mark.asyncio
    async def test_count_records_by_status(self, postgres_repo):
        """Should count records grouped by status."""
        # Create test data
        for _ in range(5):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"https://example.com/{uuid4()}",
                operation="extract",
                status="completed"
            )

        for _ in range(3):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"https://example.com/{uuid4()}",
                operation="extract",
                status="failed"
            )

        # Get counts
        stats = await postgres_repo.get_processing_stats()
        assert stats['completed'] >= 5
        assert stats['failed'] >= 3

    @pytest.mark.asyncio
    async def test_get_recent_processing_records(self, postgres_repo):
        """Should get most recent records."""
        # Create records
        for i in range(10):
            await postgres_repo.create_processing_record(
                record_id=str(uuid4()),
                content_url=f"https://example.com/{i}",
                operation="extract",
                status="completed"
            )

        # Get recent 5
        recent = await postgres_repo.get_recent_processing_records(limit=5)
        assert len(recent) == 5
