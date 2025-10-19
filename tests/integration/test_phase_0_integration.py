"""Integration tests for Phase 0 components working together."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from app.queue.job_manager import JobManager, JobType
from app.plugins.base.import_plugin import ImportPlugin, ImportStatus
from app.plugins.base.export_plugin import ExportPlugin, ExportStatus
from app.provenance.tracker import ProvenanceTracker


# Concrete implementations for integration testing
class MockImportPlugin(ImportPlugin):
    """Mock import plugin for integration tests."""
    
    async def can_handle(self, url: str) -> bool:
        return url.startswith("test://")
    
    async def download(self, url: str, parameters: dict) -> dict:
        await asyncio.sleep(0.1)  # Simulate network delay
        return {
            "url": url,
            "data": f"Downloaded content from {url}",
            "size": 1024,
        }
    
    async def extract_metadata(self, downloaded_data: dict) -> dict:
        await asyncio.sleep(0.05)  # Simulate processing
        return {
            "title": "Test Content",
            "author": "Test Author",
            "source_url": downloaded_data["url"],
        }
    
    async def extract_content(self, downloaded_data: dict) -> dict:
        await asyncio.sleep(0.05)  # Simulate processing
        return {
            "text": downloaded_data["data"],
            "chunks": ["chunk1", "chunk2", "chunk3"],
        }


class MockExportPlugin(ExportPlugin):
    """Mock export plugin for integration tests."""
    
    async def query_sources(self, source_ids: list, parameters: dict) -> dict:
        await asyncio.sleep(0.1)  # Simulate database query
        return {
            "sources": [
                {"id": sid, "content": f"Content from {sid}"}
                for sid in source_ids
            ]
        }
    
    async def generate_script(self, queried_data: dict, parameters: dict) -> dict:
        await asyncio.sleep(0.1)  # Simulate AI generation
        scenes = []
        for i, source in enumerate(queried_data["sources"]):
            scenes.append({
                "scene_index": i,
                "content": source["content"],
                "source_id": source["id"],
            })
        return {
            "title": "Test Export",
            "scenes": scenes,
        }
    
    async def generate_content(self, script: dict, parameters: dict) -> dict:
        await asyncio.sleep(0.2)  # Simulate content generation
        
        # Track AI model usage
        self.track_ai_model("test-ai-v1")
        
        # Call on_scene_complete for each scene
        for scene in script["scenes"]:
            await self.on_scene_complete(
                scene_index=scene["scene_index"],
                scene_data=scene,
                source_ids=[scene["source_id"]],
            )
        
        return {
            "generated_content": "Final generated content",
            "scenes_generated": len(script["scenes"]),
        }
    
    async def compose_output(self, generated_content: dict, parameters: dict) -> dict:
        await asyncio.sleep(0.05)  # Simulate composition
        return {
            "output_file": "/tmp/test_export.mp4",
            "metadata": generated_content,
        }


@pytest.fixture
async def mock_db():
    """Create mock database."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = Mock()
    redis.hset = Mock(return_value=True)
    redis.hgetall = Mock(return_value={})
    redis.expire = Mock(return_value=True)
    return redis


@pytest.fixture
def mock_celery():
    """Create mock Celery app."""
    celery = Mock()
    
    # Mock send_task
    task_result = Mock()
    task_result.id = "test-task-id"
    celery.send_task.return_value = task_result
    
    # Mock AsyncResult
    async_result = Mock()
    async_result.state = "SUCCESS"
    async_result.info = {"progress": 100}
    celery.AsyncResult.return_value = async_result
    
    return celery


@pytest.fixture
def mock_neo4j_driver():
    """Create mock Neo4j driver."""
    driver = Mock()
    driver.close = AsyncMock()
    session = AsyncMock()
    result = AsyncMock()
    
    # Mock session as async context manager
    session_context = AsyncMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    driver.session = Mock(return_value=session_context)
    
    # Mock result with genealogy structure and impact metrics
    mock_record = {
        "provenance_id": "prov-integration-test",
        "c": {"content_id": "test123"},
        "sources": [],
        "ancestors": [],
        "derivatives": [],
        "derivative_count": 0,
        "citation_count": 0,
    }
    result.single.return_value = mock_record
    session.run.return_value = result
    
    return driver


@pytest.fixture
async def job_manager(mock_db, mock_redis, mock_celery):
    """Create JobManager with mocks."""
    with patch('app.workers.celery_app.celery_app', mock_celery):
        manager = JobManager(
            db_session=mock_db,
            redis_client=mock_redis,
            celery_app_instance=mock_celery,
        )
        return manager


@pytest.fixture
def provenance_tracker(mock_neo4j_driver):
    """Create ProvenanceTracker with mock driver."""
    return ProvenanceTracker(neo4j_driver=mock_neo4j_driver)


@pytest.fixture
def import_plugin(job_manager, provenance_tracker):
    """Create MockImportPlugin with dependencies."""
    return MockImportPlugin(
        job_manager=job_manager,
        provenance_tracker=provenance_tracker,
    )


@pytest.fixture
def export_plugin(job_manager, provenance_tracker):
    """Create MockExportPlugin with dependencies."""
    return MockExportPlugin(
        job_manager=job_manager,
        provenance_tracker=provenance_tracker,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_lifecycle_end_to_end(job_manager, mock_redis):
    """Test complete job lifecycle: create → queue → process → complete."""
    # Create job
    job_id = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://example.com"},
        priority=5,
    )
    
    assert job_id is not None
    assert len(job_id) > 0
    
    # Verify job was stored in Redis
    assert mock_redis.hset.called
    
    # Get job status
    mock_redis.hgetall.return_value = {
        b"job_id": job_id.encode(),
        b"status": b"queued",
        b"job_type": b"import",
        b"priority": b"5",
    }
    
    status = await job_manager.get_job_status(job_id)
    assert status["job_id"] == job_id
    assert status["status"] == "queued"
    
    # Update progress
    await job_manager.update_job_progress(
        job_id=job_id,
        percentage=50,
        current_step="processing",
        total_steps=5,
        completed_steps=2,
    )
    
    assert mock_redis.hset.called


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_mechanism_integration(job_manager, mock_redis, mock_celery):
    """Test job retry mechanism with exponential backoff."""
    # Create job
    job_id = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://example.com"},
        priority=5,
    )
    
    # Mock job data with retry count
    mock_redis.hgetall.return_value = {
        b"job_id": job_id.encode(),
        b"status": b"failed",
        b"retry_count": b"0",
        b"priority": b"5",
        b"job_type": b"import",
    }
    
    # Retry job (automatic retry)
    await job_manager.retry_job(job_id, is_manual=False)
    
    # Verify retry was called with exponential backoff
    assert mock_celery.send_task.called
    call_kwargs = mock_celery.send_task.call_args[1]
    assert "countdown" in call_kwargs
    
    # Second retry should have longer countdown
    mock_redis.hgetall.return_value = {
        b"job_id": job_id.encode(),
        b"status": b"failed",
        b"retry_count": b"1",
        b"priority": b"5",
        b"job_type": b"import",
    }
    
    await job_manager.retry_job(job_id, is_manual=False)
    
    # Verify exponential backoff (2^1 = 2 seconds)
    second_call_kwargs = mock_celery.send_task.call_args[1]
    assert second_call_kwargs["countdown"] >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_import_plugin_lifecycle(import_plugin, job_manager, provenance_tracker, mock_redis):
    """Test full import plugin lifecycle with progress tracking."""
    # Create job for import
    job_id = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://example.com"},
        priority=5,
    )
    
    # Run import
    result = await import_plugin.import_content(
        url="test://example.com",
        parameters={},
        job_id=job_id,
    )
    
    # Verify import completed
    assert result["status"] == ImportStatus.COMPLETED
    assert result["content_id"] is not None
    assert "downloaded_data" in result
    assert "metadata" in result
    assert "content" in result
    
    # Verify provenance was tracked
    assert "provenance_id" in result
    assert result["provenance_id"] == "prov-integration-test"
    
    # Verify progress updates were made
    assert mock_redis.hset.call_count >= 5  # At least 5 progress updates


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_plugin_lifecycle(export_plugin, job_manager, provenance_tracker, mock_redis):
    """Test full export plugin lifecycle with scene attribution."""
    # Create job for export
    job_id = await job_manager.create_job(
        job_type=JobType.EXPORT,
        plugin_name="test_export_plugin",
        parameters={"source_ids": ["src1", "src2"], "format": "video"},
        priority=7,
    )
    
    # Run export
    result = await export_plugin.export_content(
        source_ids=["src1", "src2"],
        parameters={"format": "video"},
        job_id=job_id,
    )
    
    # Verify export completed
    assert result["status"] == ExportStatus.COMPLETED
    assert result["export_id"] is not None
    assert "script" in result
    assert "content" in result
    
    # Verify scene attributions tracked
    assert "scene_attributions" in result
    assert len(result["scene_attributions"]) == 2
    assert result["scene_attributions"][0]["scene_index"] == 0
    assert result["scene_attributions"][1]["scene_index"] == 1
    
    # Verify AI models tracked
    assert "ai_models_used" in result
    assert "test-ai-v1" in result["ai_models_used"]
    
    # Verify provenance was tracked
    assert "provenance_id" in result
    assert result["provenance_id"] is not None
    assert len(result["provenance_id"]) > 0
    
    # Verify progress updates were made
    assert mock_redis.hset.call_count >= 5  # At least 5 progress updates


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provenance_tracking_integration(import_plugin, export_plugin, provenance_tracker):
    """Test provenance tracking across import and export."""
    # Import content
    import_result = await import_plugin.import_content(
        url="test://example.com",
        parameters={},
        job_id="import-job-123",
    )
    
    content_id = import_result["content_id"]
    
    # Export content
    export_result = await export_plugin.export_content(
        source_ids=[content_id],
        parameters={"format": "video"},
        job_id="export-job-456",
    )
    
    export_id = export_result["export_id"]
    
    # Get genealogy for imported content
    genealogy = await provenance_tracker.get_genealogy(content_id)
    assert genealogy["content_id"] == content_id
    
    # Get genealogy for exported content
    export_genealogy = await provenance_tracker.get_genealogy(export_id)
    assert export_genealogy["content_id"] == export_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_job_processing(job_manager, mock_redis, mock_celery):
    """Test multiple jobs running concurrently."""
    # Create multiple jobs
    job_ids = []
    for i in range(5):
        job_id = await job_manager.create_job(
            job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
            parameters={"url": f"test://example{i}.com"},
            priority=5,
        )
        job_ids.append(job_id)
    
    # Verify all jobs created
    assert len(job_ids) == 5
    assert len(set(job_ids)) == 5  # All unique
    
    # Verify Celery send_task called for each job
    assert mock_celery.send_task.call_count == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_priority_queue_processing(job_manager, mock_celery):
    """Test high priority jobs are queued correctly."""
    # Create low priority job
    low_priority_job = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://low.com"},
        priority=2,
    )
    
    # Create high priority job
    high_priority_job = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://high.com"},
        priority=9,
    )
    
    # Verify both jobs created
    assert low_priority_job is not None
    assert high_priority_job is not None
    
    # Get Celery calls
    calls = mock_celery.send_task.call_args_list
    
    # Verify priorities were set
    assert calls[0][1]["priority"] == 2  # Low priority
    assert calls[1][1]["priority"] == 9  # High priority


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_integration(import_plugin, job_manager, mock_redis):
    """Test error handling across components."""
    # Create job
    job_id = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://example.com"},
        priority=5,
    )
    
    # Mock import failure by patching download
    original_download = import_plugin.download
    
    async def failing_download(url: str, parameters: dict) -> dict:
        raise ValueError("Download failed")
    
    import_plugin.download = failing_download
    
    # Attempt import (should fail)
    with pytest.raises(ValueError, match="Download failed"):
        await import_plugin.import_content(
            url="test://example.com",
            parameters={},
            job_id=job_id,
        )
    
    # Restore original download
    import_plugin.download = original_download


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_workflow(job_manager, import_plugin, export_plugin, provenance_tracker, mock_redis):
    """Test complete end-to-end workflow: import → export → provenance."""
    # Step 1: Create import job
    import_job_id = await job_manager.create_job(
        job_type=JobType.IMPORT,
        plugin_name="test_import_plugin",
        parameters={"url": "test://example.com"},
        priority=5,
    )
    
    # Step 2: Import content
    import_result = await import_plugin.import_content(
        url="test://example.com",
        parameters={},
        job_id=import_job_id,
    )
    
    assert import_result["status"] == ImportStatus.COMPLETED
    content_id = import_result["content_id"]
    
    # Step 3: Create export job
    export_job_id = await job_manager.create_job(
        job_type=JobType.EXPORT,
        plugin_name="test_export_plugin",
        parameters={"source_ids": [content_id], "format": "video"},
        priority=7,
    )
    
    # Step 4: Export content
    export_result = await export_plugin.export_content(
        source_ids=[content_id],
        parameters={"format": "video"},
        job_id=export_job_id,
    )
    
    assert export_result["status"] == ExportStatus.COMPLETED
    export_id = export_result["export_id"]
    
    # Step 5: Get complete genealogy
    genealogy = await provenance_tracker.get_genealogy(export_id)
    assert genealogy["content_id"] == export_id
    
    # Step 6: Generate attribution text
    attribution = await provenance_tracker.get_attribution_text(export_id, format="markdown")
    assert isinstance(attribution, str)
    
    # Step 7: Check license compliance
    compliance = await provenance_tracker.check_license_compliance(export_id, "CC-BY")
    assert "compliant" in compliance
    
    # Step 8: Get impact metrics
    metrics = await provenance_tracker.get_impact_metrics(content_id)
    assert "derivative_count" in metrics
    assert "citation_count" in metrics
    
    # Verify complete workflow
    assert import_result["provenance_id"] is not None
    assert len(import_result["provenance_id"]) > 0
    assert export_result["provenance_id"] is not None
    assert len(export_result["provenance_id"]) > 0
    assert len(export_result["scene_attributions"]) > 0
    assert len(export_result["ai_models_used"]) > 0
