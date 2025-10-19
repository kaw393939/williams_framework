"""Celery application configuration."""
from celery import Celery
from kombu import Exchange, Queue

# Create Celery app
celery_app = Celery(
    "williams_librarian",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Reject if worker dies
    worker_prefetch_multiplier=1,  # One task at a time per worker
    
    # Priority queue configuration
    task_default_priority=5,
    task_queue_max_priority=10,
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes
    task_retry_jitter=True,
)

# Define priority queues
celery_app.conf.task_routes = {
    "app.workers.tasks.process_import_job": {"queue": "imports"},
    "app.workers.tasks.process_export_job": {"queue": "exports"},
}

# Define queues with priority support
celery_app.conf.task_queues = (
    Queue(
        "imports",
        Exchange("imports"),
        routing_key="imports",
        priority=10,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "exports",
        Exchange("exports"),
        routing_key="exports",
        priority=10,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "celery",  # Default queue
        Exchange("celery"),
        routing_key="celery",
        priority=5,
        queue_arguments={"x-max-priority": 10},
    ),
)

# Task discovery
celery_app.autodiscover_tasks(["app.workers"])
