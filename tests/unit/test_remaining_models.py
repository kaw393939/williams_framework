"""Unit tests for remaining domain models: DigestItem, MaintenanceTask, ProcessingRecord."""
from datetime import datetime

from app.core.models import DigestItem, MaintenanceTask, ProcessingRecord


class TestDigestItem:
    """Test suite for DigestItem."""

    def test_digest_item_valid(self):
        """Test creating valid DigestItem."""
        item = DigestItem(
            url="https://example.com/article",
            title="Great Article",
            summary="This is a great article",
            quality_score=8.5,
            tier="tier-b",
            tags=["tech", "ai"],
            added_date=datetime(2025, 10, 10)
        )
        assert item.title == "Great Article"
        assert item.quality_score == 8.5
        assert item.tier == "tier-b"
        assert len(item.tags) == 2

    def test_digest_item_tier_validation(self):
        """Test tier validation."""
        # Valid tiers
        for tier in ["tier-a", "tier-b", "tier-c", "tier-d"]:
            item = DigestItem(
                url="https://example.com/article",
                title="Article",
                summary="Summary",
                quality_score=9.0,
                tier=tier,
                tags=[],
                added_date=datetime.now()
            )
            assert item.tier == tier


class TestMaintenanceTask:
    """Test suite for MaintenanceTask."""

    def test_maintenance_task_valid(self):
        """Test creating valid MaintenanceTask."""
        task = MaintenanceTask(
            task_id="task-123",
            task_type="rescreen",
            scheduled_for=datetime(2025, 10, 10, 2, 0)
        )
        assert task.task_id == "task-123"
        assert task.status == "pending"
        assert task.completed_at is None

    def test_maintenance_task_types(self):
        """Test valid task types."""
        types = ["rescreen", "quality_update", "cleanup", "digest", "backup"]
        for task_type in types:
            task = MaintenanceTask(
                task_id=f"task-{task_type}",
                task_type=task_type,
                scheduled_for=datetime.now()
            )
            assert task.task_type == task_type

    def test_maintenance_task_statuses(self):
        """Test valid task statuses."""
        statuses = ["pending", "running", "completed", "failed"]
        for status in statuses:
            task = MaintenanceTask(
                task_id="task-test",
                task_type="cleanup",
                status=status,
                scheduled_for=datetime.now()
            )
            assert task.status == status

    def test_maintenance_task_completion(self):
        """Test task completion."""
        task = MaintenanceTask(
            task_id="task-complete",
            task_type="backup",
            status="completed",
            scheduled_for=datetime.now(),
            completed_at=datetime.now()
        )
        assert task.completed_at is not None


class TestProcessingRecord:
    """Test suite for ProcessingRecord."""

    def test_processing_record_valid(self):
        """Test creating valid ProcessingRecord."""
        record = ProcessingRecord(
            record_id="rec-123",
            content_url="https://example.com/page",
            operation="extract",
            status="completed"
        )
        assert record.record_id == "rec-123"
        assert record.operation == "extract"
        assert record.status == "completed"

    def test_processing_record_operations(self):
        """Test valid operations."""
        operations = ["extract", "screen", "process", "store", "index"]
        for op in operations:
            record = ProcessingRecord(
                record_id=f"rec-{op}",
                content_url="https://example.com",
                operation=op,
                status="completed"
            )
            assert record.operation == op

    def test_processing_record_statuses(self):
        """Test valid statuses."""
        statuses = ["started", "completed", "failed"]
        for status in statuses:
            record = ProcessingRecord(
                record_id="rec-test",
                content_url="https://example.com",
                operation="extract",
                status=status
            )
            assert record.status == status

    def test_processing_record_with_error(self):
        """Test record with error message."""
        record = ProcessingRecord(
            record_id="rec-error",
            content_url="https://example.com",
            operation="extract",
            status="failed",
            error_message="Connection timeout"
        )
        assert record.error_message == "Connection timeout"

    def test_processing_record_with_metadata(self):
        """Test record with metadata."""
        record = ProcessingRecord(
            record_id="rec-meta",
            content_url="https://example.com",
            operation="process",
            status="completed",
            metadata={"duration": 1.5, "tokens": 1000}
        )
        assert record.metadata["duration"] == 1.5
        assert record.metadata["tokens"] == 1000
