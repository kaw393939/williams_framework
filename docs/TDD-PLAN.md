# Williams Librarian - Definitive TDD Plan

**Version:** 2.0  
**Last Updated:** October 12, 2025  
**Test Coverage Goal:** >95%  
**Current Coverage:** 90.59%

---

## 🎯 Testing Philosophy

**Test-Driven Development (TDD) Approach:**
1. **RED**: Write failing test first
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Clean up while keeping tests green

**Test Pyramid:**
```
     ╱╲
    ╱E2E╲        10% - End-to-end tests
   ╱────╲
  ╱ INT  ╲       30% - Integration tests
 ╱────────╲
╱   UNIT   ╲     60% - Unit tests
────────────
```

---

## 📊 Test Coverage Requirements

### Overall Coverage Target: >95%

```
Component                    Target    Priority
─────────────────────────────────────────────────
Core Plugin System           98%       Critical
Job Manager                  98%       Critical
Import Plugins               95%       High
Export Plugins               95%       High
Provenance Tracking          95%       High
API Endpoints                90%       Medium
CLI Commands                 85%       Medium
Background Tasks             90%       Medium
```

---

## 🧪 Phase 0: Foundation (Week 1-2)

### Objective
Implement core infrastructure: Job Manager, Plugin Registry, Base Classes

### Test Structure

```
tests/
├── unit/
│   ├── queue/
│   │   ├── test_job_manager.py              # 15 tests
│   │   ├── test_job_lifecycle.py            # 10 tests
│   │   └── test_retry_logic.py              # 8 tests
│   │
│   ├── plugins/
│   │   ├── base/
│   │   │   ├── test_import_plugin_base.py   # 12 tests
│   │   │   └── test_export_plugin_base.py   # 12 tests
│   │   ├── test_plugin_registry.py          # 10 tests
│   │   └── test_plugin_loader.py            # 8 tests
│   │
│   └── provenance/
│       ├── test_provenance_tracker.py       # 15 tests
│       └── test_genealogy_builder.py        # 10 tests
│
├── integration/
│   ├── queue/
│   │   ├── test_job_processing.py           # 8 tests
│   │   └── test_celery_integration.py       # 6 tests
│   │
│   ├── plugins/
│   │   └── test_plugin_lifecycle.py         # 10 tests
│   │
│   └── provenance/
│       └── test_neo4j_tracking.py           # 8 tests
│
└── e2e/
    ├── test_import_export_workflow.py       # 5 tests
    └── test_provenance_end_to_end.py        # 4 tests
```

### JobManager Tests (15 unit tests)

```python
# tests/unit/queue/test_job_manager.py

import pytest
from app.queue.job_manager import JobManager, ProcessingJob, JobStatus

class TestJobManager:
    """Test suite for JobManager - async job processing."""
    
    @pytest.fixture
    async def job_manager(self, mock_redis, mock_postgres, mock_celery):
        """Create JobManager with mocked dependencies."""
        return JobManager(
            redis=mock_redis,
            postgres=mock_postgres,
            celery=mock_celery
        )
    
    # Test 1: Job Creation
    async def test_create_job_success(self, job_manager):
        """Test creating a new job."""
        # Arrange
        url = "https://youtube.com/watch?v=test"
        content_type = "video"
        priority = 5
        
        # Act
        job_id = await job_manager.create_job(
            url=url,
            content_type=content_type,
            priority=priority
        )
        
        # Assert
        assert job_id is not None
        assert len(job_id) == 32  # UUID format
        
        # Verify stored in database
        job = await job_manager.get_job_status(job_id)
        assert job.url == url
        assert job.content_type == content_type
        assert job.status == JobStatus.PENDING
        assert job.priority == priority
    
    # Test 2: Job ID Generation
    async def test_generate_unique_job_ids(self, job_manager):
        """Test that job IDs are unique."""
        # Act
        job_id_1 = await job_manager.create_job("url1", "video")
        job_id_2 = await job_manager.create_job("url2", "video")
        
        # Assert
        assert job_id_1 != job_id_2
    
    # Test 3: Priority Queue Assignment
    async def test_job_priority_queue_assignment(self, job_manager, mock_celery):
        """Test jobs are assigned to correct priority queue."""
        # Arrange
        high_priority_url = "url1"
        low_priority_url = "url2"
        
        # Act
        job_id_high = await job_manager.create_job(
            high_priority_url, "video", priority=10
        )
        job_id_low = await job_manager.create_job(
            low_priority_url, "video", priority=1
        )
        
        # Assert
        # Verify high priority job went to priority_10 queue
        high_task = mock_celery.get_task(job_id_high)
        assert high_task.queue == "priority_10"
        
        # Verify low priority job went to priority_1 queue
        low_task = mock_celery.get_task(job_id_low)
        assert low_task.queue == "priority_1"
    
    # Test 4: Get Job Status
    async def test_get_job_status_from_cache(self, job_manager, mock_redis):
        """Test retrieving job status from Redis cache."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act
        job = await job_manager.get_job_status(job_id)
        
        # Assert
        assert job.job_id == job_id
        assert job.status == JobStatus.PENDING
        
        # Verify Redis was checked
        mock_redis.assert_get_called_with(f"job:{job_id}")
    
    # Test 5: Get Job Status - Cache Miss
    async def test_get_job_status_cache_miss(self, job_manager, mock_redis, mock_postgres):
        """Test fallback to database when cache misses."""
        # Arrange
        job_id = "nonexistent_job"
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        job = await job_manager.get_job_status(job_id)
        
        # Assert
        mock_postgres.fetch_job.assert_called_once_with(job_id)
    
    # Test 6: Update Job Status
    async def test_update_job_status(self, job_manager):
        """Test updating job status."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act
        await job_manager.update_job_status(
            job_id=job_id,
            status="downloading",
            progress=25.5,
            stage="Downloading video"
        )
        
        # Assert
        job = await job_manager.get_job_status(job_id)
        assert job.status == JobStatus.DOWNLOADING
        assert job.progress_percent == 25.5
        assert job.current_stage == "Downloading video"
    
    # Test 7: WebSocket Broadcasting
    async def test_job_update_broadcasts_websocket(
        self, job_manager, mock_websocket
    ):
        """Test job updates are broadcast via WebSocket."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act
        await job_manager.update_job_status(
            job_id, "downloading", 50.0, "Downloading"
        )
        
        # Assert
        mock_websocket.assert_broadcast_called(
            channel=f"job:{job_id}",
            message={
                "job_id": job_id,
                "status": "downloading",
                "progress": 50.0,
                "stage": "Downloading"
            }
        )
    
    # Test 8: Automatic Retry (First Attempt)
    async def test_automatic_retry_on_failure(self, job_manager):
        """Test automatic retry when job fails."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        await job_manager.update_job_status(job_id, "failed", 0, "Error occurred")
        
        # Act
        retry_job_id = await job_manager.retry_job(job_id, manual=False)
        
        # Assert
        assert retry_job_id == job_id
        
        job = await job_manager.get_job_status(job_id)
        assert job.retry_count == 1
        assert job.status == JobStatus.RETRYING
    
    # Test 9: Automatic Retry (Max Retries Exceeded)
    async def test_automatic_retry_max_exceeded(self, job_manager):
        """Test max automatic retries (3) are enforced."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Fail 3 times
        for i in range(3):
            await job_manager.update_job_status(job_id, "failed", 0, "Error")
            await job_manager.retry_job(job_id, manual=False)
        
        # Act & Assert
        with pytest.raises(MaxRetriesExceeded):
            await job_manager.retry_job(job_id, manual=False)
    
    # Test 10: Manual Retry
    async def test_manual_retry_higher_limit(self, job_manager):
        """Test manual retry allows up to 10 attempts."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Fail 9 times manually
        for i in range(9):
            await job_manager.update_job_status(job_id, "failed", 0, "Error")
            await job_manager.retry_job(job_id, manual=True)
        
        # Act - 10th retry should succeed
        retry_job_id = await job_manager.retry_job(job_id, manual=True)
        
        # Assert
        assert retry_job_id == job_id
        job = await job_manager.get_job_status(job_id)
        assert job.retry_count == 10
    
    # Test 11: Exponential Backoff
    async def test_retry_exponential_backoff(self, job_manager, mock_celery):
        """Test retry uses exponential backoff."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act - Retry 3 times
        await job_manager.retry_job(job_id, manual=False)  # 2s delay
        task_1 = mock_celery.get_task(job_id)
        assert task_1.countdown == 2
        
        await job_manager.retry_job(job_id, manual=False)  # 4s delay
        task_2 = mock_celery.get_task(job_id)
        assert task_2.countdown == 4
        
        await job_manager.retry_job(job_id, manual=False)  # 8s delay
        task_3 = mock_celery.get_task(job_id)
        assert task_3.countdown == 8
    
    # Test 12: Priority Boost on Manual Retry
    async def test_manual_retry_boosts_priority(self, job_manager, mock_celery):
        """Test manual retry increases priority by 2."""
        # Arrange
        job_id = await job_manager.create_job("url", "video", priority=5)
        await job_manager.update_job_status(job_id, "failed", 0, "Error")
        
        # Act
        await job_manager.retry_job(job_id, manual=True)
        
        # Assert
        task = mock_celery.get_task(job_id)
        assert task.priority == 7  # 5 + 2
        assert task.queue == "priority_7"
    
    # Test 13: Job Cancellation
    async def test_cancel_job(self, job_manager, mock_celery):
        """Test cancelling a running job."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act
        await job_manager.cancel_job(job_id)
        
        # Assert
        job = await job_manager.get_job_status(job_id)
        assert job.status == JobStatus.CANCELLED
        
        # Verify Celery task was revoked
        mock_celery.assert_task_revoked(job_id)
    
    # Test 14: Job Completion
    async def test_complete_job_success(self, job_manager):
        """Test marking job as completed."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act
        await job_manager.complete_job(
            job_id,
            content_id="video_123",
            status="completed"
        )
        
        # Assert
        job = await job_manager.get_job_status(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.progress_percent == 100.0
        assert job.content_id == "video_123"
        assert job.completed_at is not None
    
    # Test 15: Job History Tracking
    async def test_job_history_preserved(self, job_manager, mock_postgres):
        """Test job history is preserved in database."""
        # Arrange
        job_id = await job_manager.create_job("url", "video")
        
        # Act - Update status multiple times
        await job_manager.update_job_status(job_id, "downloading", 10, "Downloading")
        await job_manager.update_job_status(job_id, "extracting", 50, "Extracting")
        await job_manager.update_job_status(job_id, "completed", 100, "Done")
        
        # Assert
        history = await mock_postgres.get_job_history(job_id)
        assert len(history) >= 3
        assert history[0]["status"] == "downloading"
        assert history[1]["status"] == "extracting"
        assert history[2]["status"] == "completed"
```

### Import Plugin Base Tests (12 unit tests)

```python
# tests/unit/plugins/base/test_import_plugin_base.py

import pytest
from app.plugins.base.import_plugin import ImportPlugin

class TestImportPluginBase:
    """Test suite for ImportPlugin base class."""
    
    @pytest.fixture
    def mock_plugin(self):
        """Create a mock import plugin for testing."""
        class MockImportPlugin(ImportPlugin):
            plugin_id = "import.test"
            name = "Test Importer"
            version = "1.0.0"
            
            async def can_handle(self, url):
                return "test.com" in url
            
            async def validate_url(self, url):
                return url.startswith("https://")
            
            async def import_content(self, url, job_id, priority=5, metadata=None):
                return f"content_{job_id}"
        
        return MockImportPlugin(
            redis=Mock(),
            postgres=Mock(),
            neo4j=Mock(),
            minio=Mock(),
            qdrant=Mock()
        )
    
    # Test 1: Plugin Lifecycle - on_load
    async def test_plugin_on_load_called(self, mock_plugin):
        """Test on_load hook is called during initialization."""
        # Arrange
        mock_plugin.on_load = AsyncMock()
        
        # Act
        await mock_plugin.load()
        
        # Assert
        mock_plugin.on_load.assert_called_once()
    
    # Test 2: can_handle Method
    async def test_can_handle_returns_true_for_matching_url(self, mock_plugin):
        """Test can_handle identifies compatible URLs."""
        # Act & Assert
        assert await mock_plugin.can_handle("https://test.com/resource")
        assert not await mock_plugin.can_handle("https://other.com/resource")
    
    # Test 3: validate_url Method
    async def test_validate_url_checks_format(self, mock_plugin):
        """Test URL validation."""
        # Act & Assert
        assert await mock_plugin.validate_url("https://test.com/resource")
        assert not await mock_plugin.validate_url("http://test.com/resource")
    
    # Test 4: before_download Hook
    async def test_before_download_hook_called(self, mock_plugin):
        """Test before_download hook is invoked."""
        # Arrange
        mock_plugin.before_download = AsyncMock()
        url = "https://test.com/resource"
        
        # Act
        await mock_plugin.import_content(url, "job123")
        
        # Assert
        mock_plugin.before_download.assert_called_with(url)
    
    # Test 5: after_download Hook
    async def test_after_download_hook_called(self, mock_plugin):
        """Test after_download hook receives content."""
        # Arrange
        mock_plugin.after_download = AsyncMock()
        
        # Act
        await mock_plugin.import_content("https://test.com/resource", "job123")
        
        # Assert
        mock_plugin.after_download.assert_called_once()
    
    # Test 6: Progress Tracking
    async def test_update_job_status_called_during_import(self, mock_plugin, mocker):
        """Test job status is updated during import."""
        # Arrange
        update_spy = mocker.spy(mock_plugin, 'update_job_status')
        
        # Act
        await mock_plugin.import_content("https://test.com/resource", "job123")
        
        # Assert
        assert update_spy.call_count >= 3  # At least 3 progress updates
    
    # Test 7: Error Handling
    async def test_handle_import_error_on_exception(self, mock_plugin):
        """Test errors are properly handled."""
        # Arrange
        mock_plugin.import_content = AsyncMock(side_effect=Exception("Download failed"))
        mock_plugin.handle_import_error = AsyncMock()
        
        # Act
        with pytest.raises(Exception):
            await mock_plugin.import_content("https://test.com/resource", "job123")
        
        # Assert
        mock_plugin.handle_import_error.assert_called_once()
    
    # Test 8: Provenance Tracking
    async def test_provenance_node_created(self, mock_plugin, mock_neo4j):
        """Test provenance node is created in Neo4j."""
        # Act
        content_id = await mock_plugin.import_content(
            "https://test.com/resource", "job123"
        )
        
        # Assert
        mock_neo4j.assert_node_created(
            label="Content",
            properties={"content_id": content_id}
        )
    
    # Test 9: Repository Injection
    async def test_repositories_injected(self, mock_plugin):
        """Test all repositories are available."""
        # Assert
        assert mock_plugin.redis is not None
        assert mock_plugin.postgres is not None
        assert mock_plugin.neo4j is not None
        assert mock_plugin.minio is not None
        assert mock_plugin.qdrant is not None
    
    # Test 10: Metadata Handling
    async def test_custom_metadata_preserved(self, mock_plugin):
        """Test custom metadata is preserved during import."""
        # Arrange
        metadata = {"source": "api", "quality": "high"}
        
        # Act
        content_id = await mock_plugin.import_content(
            "https://test.com/resource",
            "job123",
            metadata=metadata
        )
        
        # Assert
        stored_metadata = await mock_plugin.postgres.get_metadata(content_id)
        assert stored_metadata["source"] == "api"
        assert stored_metadata["quality"] == "high"
    
    # Test 11: Priority Handling
    async def test_priority_affects_processing(self, mock_plugin, mock_celery):
        """Test priority is respected in job queue."""
        # Act
        await mock_plugin.import_content(
            "https://test.com/resource",
            "job123",
            priority=10
        )
        
        # Assert
        task = mock_celery.get_task("job123")
        assert task.priority == 10
        assert task.queue == "priority_10"
    
    # Test 12: Cleanup on Failure
    async def test_cleanup_on_failure(self, mock_plugin, mock_minio):
        """Test resources are cleaned up when import fails."""
        # Arrange
        mock_plugin.import_content = AsyncMock(
            side_effect=Exception("Import failed")
        )
        
        # Act
        with pytest.raises(Exception):
            await mock_plugin.import_content("https://test.com/resource", "job123")
        
        # Assert
        mock_minio.assert_cleanup_called()
```

### Export Plugin Base Tests (12 unit tests)

```python
# tests/unit/plugins/base/test_export_plugin_base.py

import pytest
from app.plugins.base.export_plugin import ExportPlugin, ExportFormat

class TestExportPluginBase:
    """Test suite for ExportPlugin base class."""
    
    @pytest.fixture
    def mock_plugin(self):
        """Create a mock export plugin for testing."""
        class MockExportPlugin(ExportPlugin):
            plugin_id = "export.test"
            name = "Test Exporter"
            version = "1.0.0"
            export_format = ExportFormat.AUDIO
            
            async def can_generate(self, source_ids, parameters):
                return len(source_ids) > 0
            
            async def validate_sources(self, source_ids):
                return all(id.startswith("doc_") for id in source_ids)
            
            async def generate_content(self, request, job_id):
                return ExportResult(
                    artifact_id=f"artifact_{job_id}",
                    format=ExportFormat.AUDIO,
                    source_ids=request.source_ids
                )
        
        return MockExportPlugin(
            redis=Mock(),
            postgres=Mock(),
            neo4j=Mock(),
            minio=Mock(),
            qdrant=Mock()
        )
    
    # Test 1: Plugin Initialization
    async def test_export_plugin_initialization(self, mock_plugin):
        """Test export plugin initializes correctly."""
        # Assert
        assert mock_plugin.plugin_id == "export.test"
        assert mock_plugin.name == "Test Exporter"
        assert mock_plugin.export_format == ExportFormat.AUDIO
    
    # Test 2: can_generate Check
    async def test_can_generate_validates_sources(self, mock_plugin):
        """Test can_generate checks source compatibility."""
        # Act & Assert
        assert await mock_plugin.can_generate(["doc_1"], {})
        assert not await mock_plugin.can_generate([], {})
    
    # Test 3: validate_sources
    async def test_validate_sources_format(self, mock_plugin):
        """Test source validation."""
        # Act & Assert
        assert await mock_plugin.validate_sources(["doc_1", "doc_2"])
        assert not await mock_plugin.validate_sources(["invalid"])
    
    # Test 4: before_query Hook
    async def test_before_query_hook_called(self, mock_plugin):
        """Test before_query hook is invoked."""
        # Arrange
        mock_plugin.before_query = AsyncMock()
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_plugin.before_query.assert_called_with(["doc_1"])
    
    # Test 5: Query Library Sources
    async def test_query_sources_from_library(self, mock_plugin, mock_postgres):
        """Test sources are queried from library."""
        # Arrange
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_postgres.fetch_content.assert_called_with(["doc_1"])
    
    # Test 6: Progress Updates During Generation
    async def test_progress_updates_during_generation(self, mock_plugin, mocker):
        """Test progress is tracked during generation."""
        # Arrange
        update_spy = mocker.spy(mock_plugin, 'update_job_status')
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        await mock_plugin.generate_content(request, "job123")
        
        # Assert
        assert update_spy.call_count >= 5  # Multiple progress updates
    
    # Test 7: Provenance Tracking
    async def test_provenance_tracked_for_export(self, mock_plugin, mock_neo4j):
        """Test provenance is created for generated artifact."""
        # Arrange
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        result = await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_type="Artifact",
            from_id=result.artifact_id,
            to_type="Document",
            to_id="doc_1",
            relationship="GENERATED_FROM"
        )
    
    # Test 8: Artifact Storage
    async def test_artifact_stored_in_minio(self, mock_plugin, mock_minio):
        """Test generated artifact is stored in MinIO."""
        # Arrange
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        result = await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_minio.assert_file_uploaded(
            bucket="artifacts",
            key=f"{result.artifact_id}/output.mp3"
        )
    
    # Test 9: Error Handling
    async def test_handle_export_error_on_exception(self, mock_plugin):
        """Test errors are properly handled."""
        # Arrange
        mock_plugin.generate_content = AsyncMock(
            side_effect=Exception("Generation failed")
        )
        mock_plugin.handle_export_error = AsyncMock()
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        with pytest.raises(Exception):
            await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_plugin.handle_export_error.assert_called_once()
    
    # Test 10: Scene Attribution Tracking
    async def test_scene_level_attribution_tracked(self, mock_plugin, mock_neo4j):
        """Test scene-level source attribution is tracked."""
        # Arrange
        request = ExportRequest(
            source_ids=["doc_1", "doc_2"],
            format=ExportFormat.VIDEO
        )
        
        # Act
        result = await mock_plugin.generate_content(request, "job123")
        
        # Assert - Scene 1 from doc_1
        mock_neo4j.assert_relationship_created(
            from_type="Scene",
            from_id="scene_1",
            to_type="Document",
            to_id="doc_1",
            relationship="SOURCED_FROM"
        )
    
    # Test 11: AI Model Tracking
    async def test_ai_model_usage_tracked(self, mock_plugin, mock_neo4j):
        """Test AI models used are tracked in provenance."""
        # Arrange
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_type="Artifact",
            to_type="AIModel",
            relationship="GENERATED_BY"
        )
    
    # Test 12: Cleanup on Failure
    async def test_cleanup_on_generation_failure(self, mock_plugin, mock_minio):
        """Test partial artifacts are cleaned up on failure."""
        # Arrange
        mock_plugin.generate_content = AsyncMock(
            side_effect=Exception("Generation failed")
        )
        request = ExportRequest(source_ids=["doc_1"], format=ExportFormat.AUDIO)
        
        # Act
        with pytest.raises(Exception):
            await mock_plugin.generate_content(request, "job123")
        
        # Assert
        mock_minio.assert_cleanup_called()
```

### Provenance Tracker Tests (15 unit tests)

```python
# tests/unit/provenance/test_provenance_tracker.py

import pytest
from app.provenance.tracker import ProvenanceTracker

class TestProvenanceTracker:
    """Test suite for provenance tracking system."""
    
    @pytest.fixture
    def tracker(self, mock_neo4j):
        """Create ProvenanceTracker with mocked Neo4j."""
        return ProvenanceTracker(neo4j=mock_neo4j)
    
    # Test 1: Create Content Node
    async def test_create_content_node(self, tracker, mock_neo4j):
        """Test creating a content node in provenance graph."""
        # Act
        content_id = await tracker.create_content_node(
            content_type="document",
            url="https://example.com/paper.pdf",
            metadata={"title": "Test Paper"}
        )
        
        # Assert
        mock_neo4j.assert_node_created(
            label="Document",
            properties={
                "content_id": content_id,
                "url": "https://example.com/paper.pdf",
                "title": "Test Paper"
            }
        )
    
    # Test 2: Track Import Source
    async def test_track_import_source(self, tracker, mock_neo4j):
        """Test tracking import provenance."""
        # Arrange
        content_id = "doc_123"
        url = "https://example.com/paper.pdf"
        
        # Act
        await tracker.track_import(
            content_id=content_id,
            url=url,
            plugin_id="import.pdf"
        )
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_id=content_id,
            to_id=url,
            relationship="IMPORTED_FROM"
        )
    
    # Test 3: Track Generation Provenance
    async def test_track_generation_provenance(self, tracker, mock_neo4j):
        """Test tracking artifact generation."""
        # Arrange
        artifact_id = "podcast_123"
        source_ids = ["doc_1", "doc_2"]
        
        # Act
        await tracker.track_generation(
            artifact_id=artifact_id,
            source_ids=source_ids,
            plugin_id="export.podcast"
        )
        
        # Assert
        for source_id in source_ids:
            mock_neo4j.assert_relationship_created(
                from_id=artifact_id,
                to_id=source_id,
                relationship="GENERATED_FROM"
            )
    
    # Test 4: Track Scene Attribution
    async def test_track_scene_attribution(self, tracker, mock_neo4j):
        """Test tracking scene-level source attribution."""
        # Arrange
        video_id = "video_123"
        scene_num = 1
        source_ids = ["doc_1"]
        
        # Act
        await tracker.track_scene_attribution(
            video_id=video_id,
            scene_num=scene_num,
            source_ids=source_ids
        )
        
        # Assert
        mock_neo4j.assert_node_created(
            label="VideoScene",
            properties={"video_id": video_id, "scene_num": scene_num}
        )
        mock_neo4j.assert_relationship_created(
            from_type="VideoScene",
            to_type="Document",
            relationship="SOURCED_FROM"
        )
    
    # Test 5: Track AI Model Usage
    async def test_track_ai_model_usage(self, tracker, mock_neo4j):
        """Test tracking which AI models were used."""
        # Arrange
        artifact_id = "video_123"
        model_name = "Kling AI"
        model_version = "1.2.0"
        
        # Act
        await tracker.track_ai_model(
            artifact_id=artifact_id,
            model_name=model_name,
            model_version=model_version
        )
        
        # Assert
        mock_neo4j.assert_node_created(
            label="AIModel",
            properties={"name": model_name, "version": model_version}
        )
        mock_neo4j.assert_relationship_created(
            from_id=artifact_id,
            to_type="AIModel",
            relationship="GENERATED_BY"
        )
    
    # Test 6: Get Content Genealogy
    async def test_get_content_genealogy(self, tracker, mock_neo4j):
        """Test retrieving complete content genealogy."""
        # Arrange
        artifact_id = "video_123"
        mock_neo4j.set_genealogy_result(
            artifact_id,
            sources=["doc_1", "doc_2"],
            models=["Kling AI"],
            creator="user_456"
        )
        
        # Act
        genealogy = await tracker.get_genealogy(artifact_id)
        
        # Assert
        assert genealogy["artifact_id"] == artifact_id
        assert len(genealogy["sources"]) == 2
        assert genealogy["models"][0] == "Kling AI"
    
    # Test 7: Get Attribution Text
    async def test_get_attribution_text(self, tracker, mock_neo4j):
        """Test generating human-readable attribution."""
        # Arrange
        artifact_id = "video_123"
        mock_neo4j.set_sources([
            {"title": "Paper A", "authors": "Smith et al.", "year": 2024},
            {"title": "Paper B", "authors": "Johnson", "year": 2023}
        ])
        
        # Act
        attribution = await tracker.get_attribution_text(artifact_id)
        
        # Assert
        assert "Smith et al. (2024)" in attribution
        assert "Johnson (2023)" in attribution
    
    # Test 8: Track Version History
    async def test_track_version_history(self, tracker, mock_neo4j):
        """Test tracking artifact versions."""
        # Arrange
        original_id = "video_v1"
        new_version_id = "video_v2"
        
        # Act
        await tracker.track_version(
            new_version_id=new_version_id,
            previous_version_id=original_id,
            reason="Bug fix: improved transitions"
        )
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_id=new_version_id,
            to_id=original_id,
            relationship="VERSION_OF",
            properties={"reason": "Bug fix: improved transitions"}
        )
    
    # Test 9: Track License Information
    async def test_track_license_information(self, tracker, mock_neo4j):
        """Test tracking content licenses."""
        # Arrange
        content_id = "doc_123"
        license_type = "CC-BY-4.0"
        
        # Act
        await tracker.track_license(
            content_id=content_id,
            license_type=license_type
        )
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_id=content_id,
            to_type="License",
            relationship="HAS_LICENSE"
        )
    
    # Test 10: Check License Compliance
    async def test_check_license_compliance(self, tracker, mock_neo4j):
        """Test checking license compatibility."""
        # Arrange
        source_ids = ["doc_1", "doc_2"]
        mock_neo4j.set_licenses({
            "doc_1": "CC-BY-4.0",
            "doc_2": "CC-BY-NC-4.0"
        })
        
        # Act
        compliance = await tracker.check_license_compliance(
            source_ids,
            commercial_use=True
        )
        
        # Assert
        assert not compliance["compliant"]  # NC license prohibits commercial
        assert "CC-BY-NC-4.0" in compliance["violations"]
    
    # Test 11: Track Citation Network
    async def test_track_citation_network(self, tracker, mock_neo4j):
        """Test tracking citation relationships."""
        # Arrange
        citing_doc = "doc_1"
        cited_doc = "doc_2"
        
        # Act
        await tracker.track_citation(
            citing_doc=citing_doc,
            cited_doc=cited_doc
        )
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_id=citing_doc,
            to_id=cited_doc,
            relationship="CITES"
        )
    
    # Test 12: Get Impact Metrics
    async def test_get_impact_metrics(self, tracker, mock_neo4j):
        """Test retrieving content impact metrics."""
        # Arrange
        artifact_id = "video_123"
        mock_neo4j.set_impact_data(
            artifact_id,
            views=1250,
            shares=87,
            derivatives=3
        )
        
        # Act
        impact = await tracker.get_impact_metrics(artifact_id)
        
        # Assert
        assert impact["views"] == 1250
        assert impact["shares"] == 87
        assert impact["derivative_works"] == 3
    
    # Test 13: Track User Creation
    async def test_track_user_creation(self, tracker, mock_neo4j):
        """Test tracking which user created content."""
        # Arrange
        artifact_id = "video_123"
        user_id = "user_456"
        
        # Act
        await tracker.track_creator(
            artifact_id=artifact_id,
            user_id=user_id
        )
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_id=user_id,
            to_id=artifact_id,
            relationship="CREATED"
        )
    
    # Test 14: Get Related Content
    async def test_get_related_content(self, tracker, mock_neo4j):
        """Test finding related content via shared sources."""
        # Arrange
        artifact_id = "video_123"
        mock_neo4j.set_related_content([
            {"id": "video_456", "shared_sources": 3},
            {"id": "podcast_789", "shared_sources": 2}
        ])
        
        # Act
        related = await tracker.get_related_content(artifact_id, limit=10)
        
        # Assert
        assert len(related) == 2
        assert related[0]["id"] == "video_456"
        assert related[0]["shared_sources"] == 3
    
    # Test 15: Cascade Delete Provenance
    async def test_cascade_delete_provenance(self, tracker, mock_neo4j):
        """Test deleting content removes provenance nodes."""
        # Arrange
        content_id = "doc_123"
        
        # Act
        await tracker.delete_provenance(content_id)
        
        # Assert
        mock_neo4j.assert_node_deleted(content_id)
        mock_neo4j.assert_relationships_deleted(content_id)
```

---

## 🧪 Phase 1: Import Plugins (Week 3-4)

### Objective
Implement concrete import plugins: YouTube, PDF, WebPage

### YouTube Import Plugin Tests (20 tests)

```python
# tests/unit/plugins/import/test_youtube_plugin.py

class TestYouTubeImportPlugin:
    """Test suite for YouTube import plugin."""
    
    # Test 1: URL Detection
    async def test_can_handle_youtube_urls(self, youtube_plugin):
        """Test YouTube URL detection."""
        assert await youtube_plugin.can_handle("https://youtube.com/watch?v=abc")
        assert await youtube_plugin.can_handle("https://youtu.be/abc")
        assert not await youtube_plugin.can_handle("https://vimeo.com/abc")
    
    # Test 2: Video ID Extraction
    async def test_extract_video_id_from_url(self, youtube_plugin):
        """Test extracting video ID from various URL formats."""
        assert youtube_plugin._extract_video_id("https://youtube.com/watch?v=abc123") == "abc123"
        assert youtube_plugin._extract_video_id("https://youtu.be/abc123") == "abc123"
    
    # Test 3: Metadata Fetching
    async def test_fetch_video_metadata(self, youtube_plugin, mock_yt_dlp):
        """Test fetching video metadata."""
        # Arrange
        mock_yt_dlp.set_video_info({
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 600
        })
        
        # Act
        metadata = await youtube_plugin._fetch_metadata("abc123")
        
        # Assert
        assert metadata["title"] == "Test Video"
        assert metadata["duration"] == 600
    
    # Test 4: Transcript Extraction (Success)
    async def test_transcript_extraction_success(self, youtube_plugin, mock_transcript_api):
        """Test successful transcript extraction."""
        # Arrange
        mock_transcript_api.set_transcript([
            {"text": "Hello world", "start": 0.0, "duration": 2.0}
        ])
        
        # Act
        transcript = await youtube_plugin._get_transcript("abc123")
        
        # Assert
        assert len(transcript) == 1
        assert transcript[0]["text"] == "Hello world"
    
    # Test 5: Transcript Fallback (Whisper)
    async def test_transcript_fallback_to_whisper(
        self, youtube_plugin, mock_transcript_api, mock_whisper
    ):
        """Test fallback to Whisper when transcript API fails."""
        # Arrange
        mock_transcript_api.set_error("No transcript available")
        mock_whisper.set_transcription("Whisper transcribed text")
        
        # Act
        transcript = await youtube_plugin._get_transcript("abc123")
        
        # Assert
        assert "Whisper transcribed text" in transcript
        mock_whisper.assert_called_once()
    
    # Test 6: Audio Download
    async def test_download_audio(self, youtube_plugin, mock_yt_dlp):
        """Test audio extraction from video."""
        # Arrange
        mock_yt_dlp.set_audio_path("/tmp/audio.mp3")
        
        # Act
        audio_path = await youtube_plugin._download_audio("abc123")
        
        # Assert
        assert audio_path == "/tmp/audio.mp3"
        assert os.path.exists(audio_path)
    
    # Test 7: Full Import Flow
    async def test_full_import_flow(self, youtube_plugin, job_manager):
        """Test complete import workflow."""
        # Arrange
        url = "https://youtube.com/watch?v=abc123"
        job_id = await job_manager.create_job(url, "video")
        
        # Act
        content_id = await youtube_plugin.import_content(url, job_id)
        
        # Assert
        assert content_id is not None
        
        # Verify stored in PostgreSQL
        content = await youtube_plugin.postgres.get_content(content_id)
        assert content["url"] == url
        assert content["content_type"] == "video"
        
        # Verify stored in MinIO
        assert await youtube_plugin.minio.file_exists(f"videos/{content_id}/video.mp4")
        
        # Verify provenance in Neo4j
        genealogy = await youtube_plugin.neo4j.get_genealogy(content_id)
        assert genealogy["source_url"] == url
    
    # ... (13 more tests covering error cases, rate limiting, etc.)
```

---

## 🧪 Phase 2: Export Plugins (Week 5-6)

### Objective
Implement concrete export plugins: Podcast, Video (Kling/Veo3)

### Podcast Export Plugin Tests (18 tests)

```python
# tests/unit/plugins/export/test_podcast_plugin.py

class TestPodcastExportPlugin:
    """Test suite for podcast generation plugin."""
    
    # Test 1: Script Generation
    async def test_generate_podcast_script(self, podcast_plugin, mock_openai):
        """Test generating podcast script from sources."""
        # Arrange
        sources = [
            {"content": "Document 1 content"},
            {"content": "Document 2 content"}
        ]
        mock_openai.set_response("Generated podcast script")
        
        # Act
        script = await podcast_plugin._generate_script(sources, style="conversational")
        
        # Assert
        assert "Generated podcast script" in script
        mock_openai.assert_called_with_prompt_containing("conversational")
    
    # Test 2: Text-to-Speech
    async def test_text_to_speech_conversion(self, podcast_plugin, mock_elevenlabs):
        """Test converting script to audio."""
        # Arrange
        script = "This is a test script"
        mock_elevenlabs.set_audio_data(b"audio_data")
        
        # Act
        audio = await podcast_plugin._text_to_speech(script, voice="professional_male")
        
        # Assert
        assert audio == b"audio_data"
        mock_elevenlabs.assert_called_with_voice("professional_male")
    
    # Test 3: Audio Composition
    async def test_compose_podcast_with_intro(self, podcast_plugin):
        """Test composing podcast with intro/outro."""
        # Arrange
        segments = [b"intro", b"main_content", b"outro"]
        
        # Act
        composed = await podcast_plugin._compose_podcast(
            segments,
            add_intro=True,
            add_music=True
        )
        
        # Assert
        assert composed is not None
        assert len(composed) > sum(len(s) for s in segments)  # Music added
    
    # Test 4: Full Generation Flow with Provenance
    async def test_full_podcast_generation_with_provenance(
        self, podcast_plugin, job_manager, mock_neo4j
    ):
        """Test complete podcast generation with provenance tracking."""
        # Arrange
        request = ExportRequest(
            source_ids=["doc_1", "doc_2"],
            format=ExportFormat.AUDIO,
            parameters={"voice": "professional_female"}
        )
        job_id = await job_manager.create_job("export", "podcast")
        
        # Act
        result = await podcast_plugin.generate_content(request, job_id)
        
        # Assert
        assert result.artifact_id is not None
        
        # Verify provenance tracked
        genealogy = await mock_neo4j.get_genealogy(result.artifact_id)
        assert len(genealogy["sources"]) == 2
        assert genealogy["sources"][0]["id"] == "doc_1"
        
        # Verify AI model tracked
        assert "ElevenLabs" in genealogy["models"][0]["name"]
    
    # ... (14 more tests)
```

### Video Export Plugin Tests (25 tests)

```python
# tests/unit/plugins/export/test_video_plugin.py

class TestVideoExportPlugin:
    """Test suite for video generation plugin (Kling/Veo3)."""
    
    # Test 1: Backend Selection (Kling)
    async def test_select_kling_for_short_cinematic(self, video_plugin):
        """Test Kling selected for short cinematic videos."""
        # Arrange
        parameters = {"duration": 30, "style": "cinematic"}
        
        # Act
        backend = video_plugin._select_backend(parameters)
        
        # Assert
        assert backend.name == "Kling AI"
    
    # Test 2: Backend Selection (Veo3)
    async def test_select_veo3_for_long_form(self, video_plugin):
        """Test Veo 3 selected for long-form videos."""
        # Arrange
        parameters = {"duration": 180}  # 3 minutes
        
        # Act
        backend = video_plugin._select_backend(parameters)
        
        # Assert
        assert backend.name == "Veo 3"
    
    # Test 3: Scene Script Generation with Attribution
    async def test_generate_script_with_scene_attribution(
        self, video_plugin, mock_openai
    ):
        """Test generating video script with scene-level attribution."""
        # Arrange
        sources = [
            {"id": "doc_1", "content": "Content from paper 1"},
            {"id": "doc_2", "content": "Content from paper 2"}
        ]
        
        # Act
        script, attributions = await video_plugin._generate_video_script(sources, {})
        
        # Assert
        assert len(attributions) >= 2  # At least 2 scenes
        assert attributions[0]["source_ids"] == ["doc_1"]
        assert attributions[1]["source_ids"] == ["doc_2"]
    
    # Test 4: Kling API Integration
    async def test_kling_clip_generation(self, video_plugin, mock_kling_api):
        """Test generating clip with Kling AI."""
        # Arrange
        scene = {"text": "A beautiful sunset", "duration": 10}
        mock_kling_api.set_video_url("https://kling.ai/video123.mp4")
        
        # Act
        clip_path = await video_plugin.kling._generate_clip(scene)
        
        # Assert
        assert clip_path.endswith(".mp4")
        assert os.path.exists(clip_path)
    
    # Test 5: Veo3 API Integration
    async def test_veo3_clip_generation(self, video_plugin, mock_veo3_api):
        """Test generating clip with Veo 3."""
        # Arrange
        scene = {"text": "Photorealistic city", "duration": 20}
        mock_veo3_api.set_video_url("gs://veo3/video456.mp4")
        
        # Act
        clip_path = await video_plugin.veo3._generate_clip(scene)
        
        # Assert
        assert clip_path.endswith(".mp4")
        assert os.path.exists(clip_path)
    
    # Test 6: Scene-Level Provenance Tracking
    async def test_scene_provenance_tracked(self, video_plugin, mock_neo4j):
        """Test each scene's sources are tracked."""
        # Arrange
        scene_attributions = [
            {"scene_num": 1, "source_ids": ["doc_1"]},
            {"scene_num": 2, "source_ids": ["doc_2"]}
        ]
        video_id = "video_123"
        
        # Act
        await video_plugin._track_scene_provenance(video_id, scene_attributions)
        
        # Assert
        mock_neo4j.assert_relationship_created(
            from_type="VideoScene",
            from_id="scene_1",
            to_type="Document",
            to_id="doc_1",
            relationship="SOURCED_FROM"
        )
    
    # Test 7: Full Video Generation with Attribution
    async def test_full_video_generation_with_attribution(
        self, video_plugin, job_manager, mock_neo4j
    ):
        """Test complete video generation with provenance."""
        # Arrange
        request = ExportRequest(
            source_ids=["doc_1", "doc_2"],
            format=ExportFormat.VIDEO,
            parameters={
                "duration": 60,
                "style": "educational",
                "backend": "smart"
            }
        )
        job_id = await job_manager.create_job("export", "video")
        
        # Act
        result = await video_plugin.generate_content(request, job_id)
        
        # Assert
        assert result.artifact_id is not None
        
        # Verify complete genealogy
        genealogy = await mock_neo4j.get_genealogy(result.artifact_id)
        assert len(genealogy["sources"]) == 2
        assert len(genealogy["scenes"]) >= 2
        assert genealogy["scenes"][0]["sources"] is not None
        
        # Verify AI model tracked
        assert "Kling AI" in [m["name"] for m in genealogy["models"]]
    
    # ... (18 more tests)
```

---

## 📦 Integration Tests

### End-to-End Import/Export Flow (8 tests)

```python
# tests/e2e/test_import_export_workflow.py

class TestImportExportWorkflow:
    """End-to-end tests for complete import/export workflows."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_youtube_to_podcast_workflow(
        self, client, youtube_plugin, podcast_plugin
    ):
        """
        Test complete workflow:
        1. Import YouTube video
        2. Extract transcript
        3. Generate podcast from transcript
        4. Verify provenance chain
        """
        # Step 1: Import YouTube video
        response = await client.post(
            "/api/content/import",
            json={
                "url": "https://youtube.com/watch?v=test123",
                "type": "video",
                "priority": 10
            }
        )
        assert response.status_code == 200
        import_job_id = response.json()["job_id"]
        
        # Wait for import to complete
        await self._wait_for_job(client, import_job_id, timeout=300)
        
        # Verify import succeeded
        import_job = await client.get(f"/api/jobs/{import_job_id}")
        assert import_job.json()["status"] == "completed"
        video_id = import_job.json()["content_id"]
        
        # Step 2: Generate podcast from video transcript
        response = await client.post(
            "/api/content/export",
            json={
                "source_ids": [video_id],
                "format": "podcast",
                "parameters": {
                    "voice": "professional_male",
                    "style": "conversational"
                }
            }
        )
        assert response.status_code == 200
        export_job_id = response.json()["job_id"]
        
        # Wait for generation to complete
        await self._wait_for_job(client, export_job_id, timeout=300)
        
        # Verify generation succeeded
        export_job = await client.get(f"/api/jobs/{export_job_id}")
        assert export_job.json()["status"] == "completed"
        podcast_id = export_job.json()["artifact_id"]
        
        # Step 3: Verify provenance chain
        genealogy = await client.get(
            f"/api/provenance/podcast/{podcast_id}/genealogy"
        )
        assert genealogy.status_code == 200
        prov = genealogy.json()["provenance"]
        
        # Verify chain: YouTube → Video → Podcast
        assert prov["sources"][0]["content_id"] == video_id
        assert prov["sources"][0]["original_url"] == "https://youtube.com/watch?v=test123"
        
        # Verify attribution generated
        attribution = await client.get(
            f"/api/provenance/podcast/{podcast_id}/attribution"
        )
        assert attribution.status_code == 200
        assert "youtube.com/watch?v=test123" in attribution.json()["attribution_text"]
    
    # ... (7 more E2E tests)
```

---

## 🎯 Coverage Goals by Component

```
Phase 0 (Foundation):
├─ JobManager: 98% (target: 98%)
├─ ImportPlugin Base: 95% (target: 95%)
├─ ExportPlugin Base: 95% (target: 95%)
└─ ProvenanceTracker: 96% (target: 95%)

Phase 1 (Import Plugins):
├─ YouTubeImportPlugin: 94% (target: 95%)
├─ PDFImportPlugin: 93% (target: 95%)
└─ WebPageImportPlugin: 92% (target: 95%)

Phase 2 (Export Plugins):
├─ PodcastExportPlugin: 93% (target: 95%)
├─ VideoExportPlugin: 92% (target: 95%)
└─ SmartVideoRouter: 94% (target: 95%)

Overall Target: >95%
```

---

## 📋 Implementation Checklist

### Week 1-2: Foundation
- [ ] Implement JobManager with 15 unit tests
- [ ] Implement ImportPlugin base with 12 unit tests
- [ ] Implement ExportPlugin base with 12 unit tests
- [ ] Implement ProvenanceTracker with 15 unit tests
- [ ] Integration tests for job processing (8 tests)
- [ ] Integration tests for plugin lifecycle (10 tests)
- [ ] E2E test for basic import/export (2 tests)
- [ ] Coverage report: >95% for Phase 0

### Week 3-4: Import Plugins
- [ ] Implement YouTubeImportPlugin with 20 unit tests
- [ ] Implement PDFImportPlugin with 18 unit tests
- [ ] Implement WebPageImportPlugin with 15 unit tests
- [ ] Integration tests for each plugin (5 tests each)
- [ ] E2E test for multi-source import (3 tests)
- [ ] Coverage report: >95% for Phase 1

### Week 5-6: Export Plugins
- [ ] Implement PodcastExportPlugin with 18 unit tests
- [ ] Implement VideoExportPlugin with 25 unit tests
- [ ] Implement SmartVideoRouter with 10 unit tests
- [ ] Integration tests for generation (8 tests)
- [ ] E2E test for import→export workflow (4 tests)
- [ ] Coverage report: >95% for Phase 2

---

## 🔄 Continuous Testing

### Pre-Commit Hook
```bash
#!/bin/bash
# Run before every commit

pytest tests/unit/ --cov=app --cov-report=term-missing --cov-fail-under=95
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml

name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Unit Tests
        run: pytest tests/unit/ --cov=app --cov-report=xml
      - name: Run Integration Tests
        run: pytest tests/integration/
      - name: Run E2E Tests (on main only)
        if: github.ref == 'refs/heads/main'
        run: pytest tests/e2e/ --slow
      - name: Upload Coverage
        uses: codecov/codecov-action@v2
```

---

## 📚 Testing Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/
- **AsyncIO Testing**: https://docs.python.org/3/library/asyncio-dev.html
- **Mocking**: https://docs.python.org/3/library/unittest.mock.html

---

**Last Updated:** October 12, 2025  
**Version:** 2.0 (Definitive)
