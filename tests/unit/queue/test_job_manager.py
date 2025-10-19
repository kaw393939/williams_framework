"""Unit tests for JobManager."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from redis import Redis

from app.queue.job_manager import JobManager, JobStatus, JobType


class TestJobManager:
    """Test suite for JobManager."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()
        
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = Mock(spec=Redis)
        redis_mock.hset = Mock()
        redis_mock.hgetall = Mock(return_value={})
        redis_mock.expire = Mock()
        return redis_mock
        
    @pytest.fixture
    def mock_celery(self):
        """Mock Celery app."""
        celery_mock = Mock()
        celery_mock.send_task = Mock(return_value=Mock(id="task123"))
        celery_mock.AsyncResult = Mock(return_value=Mock(state="PENDING", info=None))
        celery_mock.control = Mock()
        celery_mock.control.revoke = Mock()
        return celery_mock
        
    @pytest.fixture
    async def job_manager(self, mock_db, mock_redis, mock_celery):
        """Create JobManager instance for testing."""
        return JobManager(
            db_session=mock_db,
            redis_client=mock_redis,
            celery_app_instance=mock_celery
        )
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_job_success(self, job_manager, mock_redis, mock_celery):
        """Test successful job creation."""
        # Arrange
        job_type = JobType.IMPORT
        plugin_name = "youtube"
        parameters = {"url": "https://youtube.com/watch?v=abc123"}
        priority = 8
        
        # Act
        job_id = await job_manager.create_job(
            job_type=job_type,
            plugin_name=plugin_name,
            parameters=parameters,
            priority=priority
        )
        
        # Assert
        assert job_id is not None
        assert len(job_id) == 36  # UUID4 format
        
        # Verify Redis storage was called
        assert mock_redis.hset.called
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == f"job:{job_id}"
        
        # Verify Celery task was queued
        assert mock_celery.send_task.called
        task_call = mock_celery.send_task.call_args
        assert task_call[0][0] == "app.workers.tasks.process_import_job"
        assert task_call[1]["queue"] == "imports"
        assert task_call[1]["priority"] == priority
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_job_invalid_priority(self, job_manager):
        """Test job creation with invalid priority."""
        # Arrange
        job_type = JobType.IMPORT
        plugin_name = "youtube"
        parameters = {"url": "https://youtube.com/watch?v=abc123"}
        invalid_priority = 15  # Out of range
        
        # Act & Assert
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            await job_manager.create_job(
                job_type=job_type,
                plugin_name=plugin_name,
                parameters=parameters,
                priority=invalid_priority
            )
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_job_empty_parameters(self, job_manager):
        """Test job creation with empty parameters."""
        # Arrange
        job_type = JobType.IMPORT
        plugin_name = "youtube"
        parameters = {}  # Empty
        
        # Act & Assert
        with pytest.raises(ValueError, match="Parameters cannot be empty"):
            await job_manager.create_job(
                job_type=job_type,
                plugin_name=plugin_name,
                parameters=parameters,
                priority=5
            )
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_priority_queue_assignment(self, job_manager, mock_celery):
        """Test that high priority jobs are queued with correct priority."""
        # Arrange
        high_priority_params = {"url": "https://example.com/urgent"}
        low_priority_params = {"url": "https://example.com/normal"}
        
        # Act
        job_id_high = await job_manager.create_job(
            job_type=JobType.IMPORT,
            plugin_name="webpage",
            parameters=high_priority_params,
            priority=10  # Highest priority
        )
        
        job_id_low = await job_manager.create_job(
            job_type=JobType.IMPORT,
            plugin_name="webpage",
            parameters=low_priority_params,
            priority=1  # Lowest priority
        )
        
        # Assert
        calls = mock_celery.send_task.call_args_list
        
        # First call (high priority)
        high_call = calls[0]
        assert high_call[1]["priority"] == 10
        
        # Second call (low priority)
        low_call = calls[1]
        assert low_call[1]["priority"] == 1
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_job_status_success(self, job_manager, mock_redis, mock_celery):
        """Test retrieving job status."""
        # Arrange
        job_id = str(uuid4())
        job_data = {
            b"job_id": job_id.encode(),
            b"job_type": b"import",
            b"status": b"running",
            b"priority": b"8",
        }
        mock_redis.hgetall = Mock(return_value=job_data)
        
        mock_celery.AsyncResult = Mock(return_value=Mock(
            state="SUCCESS",
            info={"progress": 75}
        ))
        
        # Act
        status = await job_manager.get_job_status(job_id)
        
        # Assert
        assert status["job_id"] == job_id
        assert status["status"] == "running"
        assert status["celery_state"] == "SUCCESS"
        assert status["celery_info"]["progress"] == 75
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, job_manager, mock_redis):
        """Test retrieving status for non-existent job."""
        # Arrange
        job_id = str(uuid4())
        mock_redis.hgetall = Mock(return_value={})
        
        # Act & Assert
        with pytest.raises(ValueError, match=f"Job {job_id} not found"):
            await job_manager.get_job_status(job_id)
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_job_automatic(self, job_manager, mock_redis, mock_celery):
        """Test automatic retry with exponential backoff."""
        # Arrange
        job_id = str(uuid4())
        job_data = {
            b"job_id": job_id.encode(),
            b"job_type": b"import",
            b"status": JobStatus.FAILED.value.encode(),
            b"priority": b"5",
            b"retry_count": b"0",
            b"max_retries": b"3",
            b"parameters": json.dumps({"url": "test"}).encode(),
        }
        mock_redis.hgetall = Mock(return_value=job_data)
        
        # Act
        result = await job_manager.retry_job(job_id, is_manual=False)
        
        # Assert
        assert result is True
        
        # Verify job was re-queued
        assert mock_celery.send_task.called
        task_call = mock_celery.send_task.call_args
        
        # Check exponential backoff (2^1 = 2 seconds for first retry)
        assert task_call[1]["countdown"] == 2
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, job_manager, mock_redis, mock_celery):
        """Test exponential backoff calculation."""
        # Arrange
        job_id = str(uuid4())
        
        # Simulate multiple retries
        for retry_count in [0, 1, 2]:
            job_data = {
                b"job_id": job_id.encode(),
                b"job_type": b"import",
                b"status": JobStatus.FAILED.value.encode(),
                b"priority": b"5",
                b"retry_count": str(retry_count).encode(),
                b"max_retries": b"3",
                b"parameters": json.dumps({"url": "test"}).encode(),
            }
            mock_redis.hgetall = Mock(return_value=job_data)
            
            # Act
            await job_manager.retry_job(job_id, is_manual=False)
            
            # Assert - Check backoff time
            task_call = mock_celery.send_task.call_args
            expected_backoff = 2 ** (retry_count + 1)
            assert task_call[1]["countdown"] == expected_backoff
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manual_retry_boosts_priority(self, job_manager, mock_redis, mock_celery):
        """Test manual retry increases priority."""
        # Arrange
        job_id = str(uuid4())
        job_data = {
            b"job_id": job_id.encode(),
            b"job_type": b"import",
            b"status": JobStatus.FAILED.value.encode(),
            b"priority": b"5",
            b"retry_count": b"0",
            b"max_retries": b"3",
            b"parameters": json.dumps({"url": "test"}).encode(),
        }
        mock_redis.hgetall = Mock(return_value=job_data)
        
        # Act
        result = await job_manager.retry_job(job_id, is_manual=True)
        
        # Assert
        assert result is True
        
        # Verify priority was boosted (+2)
        task_call = mock_celery.send_task.call_args
        assert task_call[1]["priority"] == 7  # 5 + 2
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_job(self, job_manager, mock_redis, mock_celery):
        """Test cancelling a running job."""
        # Arrange
        job_id = str(uuid4())
        job_data = {
            b"job_id": job_id.encode(),
            b"status": JobStatus.RUNNING.value.encode(),
        }
        mock_redis.hgetall = Mock(return_value=job_data)
        
        # Act
        result = await job_manager.cancel_job(job_id, reason="User requested")
        
        # Assert
        assert result is True
        
        # Verify Celery task was revoked
        mock_celery.control.revoke.assert_called_once_with(
            job_id,
            terminate=True,
            signal="SIGKILL"
        )
        
        # Verify status was updated in Redis
        assert mock_redis.hset.called
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, job_manager, mock_redis):
        """Test that completed jobs cannot be cancelled."""
        # Arrange
        job_id = str(uuid4())
        job_data = {
            b"job_id": job_id.encode(),
            b"status": JobStatus.COMPLETED.value.encode(),
        }
        mock_redis.hgetall = Mock(return_value=job_data)
        
        # Act & Assert
        with pytest.raises(ValueError, match="is already completed"):
            await job_manager.cancel_job(job_id)
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_job_progress(self, job_manager, mock_redis):
        """Test retrieving job progress."""
        # Arrange
        job_id = str(uuid4())
        progress_data = {
            b"job_id": job_id.encode(),
            b"percentage": b"75",
            b"current_step": b"Processing video",
            b"total_steps": b"10",
            b"completed_steps": b"7",
        }
        mock_redis.hgetall = Mock(return_value=progress_data)
        
        # Act
        progress = await job_manager.get_job_progress(job_id)
        
        # Assert
        assert progress["job_id"] == job_id
        assert progress["percentage"] == "75"
        assert progress["current_step"] == "Processing video"
        assert progress["total_steps"] == "10"
        assert progress["completed_steps"] == "7"
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_job_progress(self, job_manager, mock_redis):
        """Test updating job progress."""
        # Arrange
        job_id = str(uuid4())
        
        # Act
        await job_manager.update_job_progress(
            job_id=job_id,
            percentage=50,
            current_step="Extracting audio",
            total_steps=5,
            completed_steps=2
        )
        
        # Assert
        assert mock_redis.hset.called
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == f"job:{job_id}:progress"
        
        # Verify expiration was set
        assert mock_redis.expire.called
        expire_call = mock_redis.expire.call_args
        assert expire_call[0][0] == f"job:{job_id}:progress"
        assert expire_call[0][1] == 3600  # 1 hour
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_exceeds_max_retries(self, job_manager, mock_redis):
        """Test that jobs cannot retry beyond max_retries."""
        # Arrange
        job_id = str(uuid4())
        job_data = {
            b"job_id": job_id.encode(),
            b"job_type": b"import",
            b"status": JobStatus.FAILED.value.encode(),
            b"priority": b"5",
            b"retry_count": b"3",  # Already at max
            b"max_retries": b"3",
            b"parameters": json.dumps({"url": "test"}).encode(),
        }
        mock_redis.hgetall = Mock(return_value=job_data)
        
        # Act & Assert
        with pytest.raises(ValueError, match="has exceeded max retries"):
            await job_manager.retry_job(job_id, is_manual=False)
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_job_uses_correct_queue(self, job_manager, mock_celery):
        """Test that export jobs are routed to exports queue."""
        # Arrange
        parameters = {"format": "podcast", "sources": ["doc1", "doc2"]}
        
        # Act
        job_id = await job_manager.create_job(
            job_type=JobType.EXPORT,
            plugin_name="podcast",
            parameters=parameters,
            priority=7
        )
        
        # Assert
        task_call = mock_celery.send_task.call_args
        assert task_call[0][0] == "app.workers.tasks.process_export_job"
        assert task_call[1]["queue"] == "exports"
