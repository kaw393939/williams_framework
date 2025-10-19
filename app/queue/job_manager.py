"""Job Manager for async processing with Celery."""
import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app


class JobStatus(str, Enum):
    """Job status enumeration."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(str, Enum):
    """Job type enumeration."""
    
    IMPORT = "import"
    EXPORT = "export"


class JobManager:
    """Manages async job processing with Celery and Redis."""
    
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: Redis,
        celery_app_instance=None,
    ):
        """
        Initialize JobManager.
        
        Args:
            db_session: AsyncIO SQLAlchemy session for database operations
            redis_client: Redis client for caching and real-time updates
            celery_app_instance: Celery app instance (for testing)
        """
        self.db = db_session
        self.redis = redis_client
        self.celery = celery_app_instance or celery_app
        
    async def create_job(
        self,
        job_type: JobType,
        plugin_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Create a new job and queue it for processing.
        
        Args:
            job_type: Type of job (import or export)
            plugin_name: Name of the plugin to use
            parameters: Job parameters (URL, format, etc.)
            priority: Priority level (1-10, higher = more urgent)
            user_id: Optional user ID for tracking
            
        Returns:
            job_id: Unique job identifier
            
        Raises:
            ValueError: If priority is out of range or parameters are invalid
        """
        # Validate priority
        if not 1 <= priority <= 10:
            raise ValueError("Priority must be between 1 and 10")
            
        # Validate parameters
        if not parameters:
            raise ValueError("Parameters cannot be empty")
            
        # Generate job ID
        job_id = str(uuid4())
        
        # Create job record
        job_data = {
            "job_id": job_id,
            "job_type": job_type.value,
            "plugin_name": plugin_name,
            "parameters": parameters,
            "priority": priority,
            "status": JobStatus.PENDING.value,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "max_retries": 3,
        }
        
        # Store in Redis for fast access
        await self._store_job_redis(job_id, job_data)
        
        # Queue in Celery with priority
        queue_name = "imports" if job_type == JobType.IMPORT else "exports"
        task_name = f"app.workers.tasks.process_{job_type.value}_job"
        
        self.celery.send_task(
            task_name,
            args=[job_id],
            kwargs={"job_data": job_data},
            queue=queue_name,
            priority=priority,
            task_id=job_id,
        )
        
        # Update status to queued
        await self._update_job_status(job_id, JobStatus.QUEUED)
        
        return job_id
        
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current job status and progress.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary with metadata
            
        Raises:
            ValueError: If job not found
        """
        # Check Redis first (fast cache)
        job_data = await self._get_job_redis(job_id)
        
        if not job_data:
            raise ValueError(f"Job {job_id} not found")
            
        # Get Celery task status
        task = self.celery.AsyncResult(job_id)
        
        # Merge status
        job_data["celery_state"] = task.state
        job_data["celery_info"] = task.info if task.info else {}
        
        return job_data
        
    async def retry_job(self, job_id: str, is_manual: bool = False) -> bool:
        """
        Retry a failed job.
        
        Args:
            job_id: Job identifier
            is_manual: True if manual retry (increases max_retries to 10)
            
        Returns:
            True if retry was successful
            
        Raises:
            ValueError: If job not found or cannot be retried
        """
        job_data = await self._get_job_redis(job_id)
        
        if not job_data:
            raise ValueError(f"Job {job_id} not found")
            
        # Check if job can be retried
        if job_data["status"] not in [JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
            raise ValueError(f"Job {job_id} is not in a failed state")
            
        # Update retry count
        retry_count = job_data.get("retry_count", 0) + 1
        max_retries = 10 if is_manual else job_data.get("max_retries", 3)
        
        if retry_count > max_retries:
            raise ValueError(f"Job {job_id} has exceeded max retries ({max_retries})")
            
        # Calculate exponential backoff
        backoff_seconds = min(2 ** retry_count, 600)  # Max 10 minutes
        
        # Update job data
        job_data["retry_count"] = retry_count
        job_data["max_retries"] = max_retries
        job_data["status"] = JobStatus.RETRYING.value
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self._store_job_redis(job_id, job_data)
        
        # Boost priority for manual retries
        priority = job_data["priority"]
        if is_manual:
            priority = min(priority + 2, 10)
            
        # Re-queue job
        queue_name = "imports" if job_data["job_type"] == "import" else "exports"
        task_name = f"app.workers.tasks.process_{job_data['job_type']}_job"
        
        self.celery.send_task(
            task_name,
            args=[job_id],
            kwargs={"job_data": job_data},
            queue=queue_name,
            priority=priority,
            task_id=job_id,
            countdown=backoff_seconds,  # Delay before execution
        )
        
        return True
        
    async def cancel_job(self, job_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a running or queued job.
        
        Args:
            job_id: Job identifier
            reason: Optional cancellation reason
            
        Returns:
            True if cancellation was successful
            
        Raises:
            ValueError: If job not found or cannot be cancelled
        """
        job_data = await self._get_job_redis(job_id)
        
        if not job_data:
            raise ValueError(f"Job {job_id} not found")
            
        # Check if job can be cancelled
        if job_data["status"] in [JobStatus.COMPLETED.value, JobStatus.CANCELLED.value]:
            raise ValueError(f"Job {job_id} is already {job_data['status']}")
            
        # Revoke Celery task
        self.celery.control.revoke(job_id, terminate=True, signal="SIGKILL")
        
        # Update job status
        job_data["status"] = JobStatus.CANCELLED.value
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            job_data["cancellation_reason"] = reason
            
        await self._store_job_redis(job_id, job_data)
        
        return True
        
    async def get_job_progress(self, job_id: str) -> Dict[str, Any]:
        """
        Get real-time job progress.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Progress dictionary with percentage and current step
        """
        # Get progress from Redis
        progress_key = f"job:{job_id}:progress"
        progress_data = self.redis.hgetall(progress_key)
        
        if not progress_data:
            return {
                "job_id": job_id,
                "percentage": 0,
                "current_step": "Initializing",
                "total_steps": 0,
                "completed_steps": 0,
            }
            
        # Decode bytes to strings
        return {
            k.decode("utf-8"): v.decode("utf-8")
            for k, v in progress_data.items()
        }
        
    async def update_job_progress(
        self,
        job_id: str,
        percentage: int,
        current_step: str,
        total_steps: int,
        completed_steps: int,
    ) -> None:
        """
        Update job progress (called by workers).
        
        Args:
            job_id: Job identifier
            percentage: Progress percentage (0-100)
            current_step: Description of current step
            total_steps: Total number of steps
            completed_steps: Number of completed steps
        """
        progress_key = f"job:{job_id}:progress"
        
        progress_data = {
            "job_id": job_id,
            "percentage": str(percentage),
            "current_step": current_step,
            "total_steps": str(total_steps),
            "completed_steps": str(completed_steps),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self.redis.hset(progress_key, mapping=progress_data)
        self.redis.expire(progress_key, 3600)  # Expire after 1 hour
        
    # Internal helper methods
    
    async def _store_job_redis(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Store job data in Redis."""
        job_key = f"job:{job_id}"
        
        # Convert dict to flat structure for Redis
        flat_data = {}
        for key, value in job_data.items():
            if isinstance(value, dict):
                # Store nested dicts as JSON strings
                import json
                flat_data[key] = json.dumps(value)
            else:
                flat_data[key] = str(value)
                
        self.redis.hset(job_key, mapping=flat_data)
        self.redis.expire(job_key, 86400)  # Expire after 24 hours
        
    async def _get_job_redis(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data from Redis."""
        job_key = f"job:{job_id}"
        job_data = self.redis.hgetall(job_key)
        
        if not job_data:
            return None
            
        # Decode bytes and parse JSON
        import json
        decoded_data = {}
        for key, value in job_data.items():
            key_str = key.decode("utf-8")
            value_str = value.decode("utf-8")
            
            # Try to parse as JSON (for nested dicts)
            try:
                decoded_data[key_str] = json.loads(value_str)
            except (json.JSONDecodeError, ValueError):
                decoded_data[key_str] = value_str
                
        return decoded_data
        
    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update job status in Redis."""
        job_data = await self._get_job_redis(job_id)
        
        if job_data:
            job_data["status"] = status.value
            job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            if error:
                job_data["error"] = error
                
            await self._store_job_redis(job_id, job_data)
