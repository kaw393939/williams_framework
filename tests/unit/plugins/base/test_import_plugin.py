"""Unit tests for ImportPlugin base class."""
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.plugins.base.import_plugin import (
    ContentType,
    ImportPlugin,
    ImportStatus,
)


# Concrete test implementation of ImportPlugin
class MockImportPlugin(ImportPlugin):
    """Mock implementation of ImportPlugin for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_load_called = False
        self.before_download_called = False
        self.after_download_called = False
        self.before_extract_called = False
        self.after_extract_called = False
        self.on_error_called = False
        self.on_complete_called = False
        
    def can_handle(self, url: str) -> bool:
        """Check if URL starts with 'test://'."""
        return url.startswith("test://")
        
    async def download(self, url: str, parameters: dict) -> dict:
        """Mock download."""
        return {
            "url": url,
            "file_path": "/tmp/test.dat",
            "size": 1024,
        }
        
    async def extract_metadata(self, downloaded_data: dict) -> dict:
        """Mock metadata extraction."""
        return {
            "title": "Test Content",
            "author": "Test Author",
            "created_at": "2025-01-01",
        }
        
    async def extract_content(self, downloaded_data: dict) -> dict:
        """Mock content extraction."""
        return {
            "text": "Test content body",
            "sections": ["Introduction", "Body", "Conclusion"],
        }
        
    async def on_load(self) -> None:
        """Track on_load call."""
        self.on_load_called = True
        
    async def before_download(self, url: str, parameters: dict) -> None:
        """Track before_download call."""
        self.before_download_called = True
        
    async def after_download(self, url: str, downloaded_data: dict) -> None:
        """Track after_download call."""
        self.after_download_called = True
        
    async def before_extract(self, downloaded_data: dict) -> None:
        """Track before_extract call."""
        self.before_extract_called = True
        
    async def after_extract(
        self,
        downloaded_data: dict,
        metadata: dict,
        content: dict,
    ) -> None:
        """Track after_extract call."""
        self.after_extract_called = True
        
    async def on_error(self, error: Exception, stage: str) -> None:
        """Track on_error call."""
        self.on_error_called = True
        
    async def on_complete(self, result: dict) -> None:
        """Track on_complete call."""
        self.on_complete_called = True
        
    @classmethod
    def get_supported_content_types(cls):
        """Return test content types."""
        return [ContentType.VIDEO, ContentType.AUDIO]
        
    @classmethod
    def get_required_parameters(cls):
        """Return required parameters."""
        return ["url", "format"]
        
    @classmethod
    def get_optional_parameters(cls):
        """Return optional parameters."""
        return {"quality": "high", "language": "en"}


class TestImportPluginBase:
    """Test suite for ImportPlugin base class."""
    
    @pytest.fixture
    def mock_job_manager(self):
        """Mock JobManager."""
        job_manager = AsyncMock()
        job_manager.update_job_progress = AsyncMock()
        return job_manager
        
    @pytest.fixture
    def mock_provenance_tracker(self):
        """Mock ProvenanceTracker."""
        tracker = AsyncMock()
        tracker.track_import = AsyncMock(return_value="prov123")
        return tracker
        
    @pytest.fixture
    def plugin(self, mock_job_manager, mock_provenance_tracker):
        """Create test plugin instance."""
        return MockImportPlugin(
            job_manager=mock_job_manager,
            provenance_tracker=mock_provenance_tracker,
        )
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_can_handle_valid_url(self, plugin):
        """Test can_handle with valid URL."""
        # Arrange
        url = "test://example.com/content"
        
        # Act
        result = plugin.can_handle(url)
        
        # Assert
        assert result is True
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_can_handle_invalid_url(self, plugin):
        """Test can_handle with invalid URL."""
        # Arrange
        url = "http://example.com/content"
        
        # Act
        result = plugin.can_handle(url)
        
        # Assert
        assert result is False
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_full_lifecycle(self, plugin, mock_job_manager):
        """Test complete import lifecycle."""
        # Arrange
        url = "test://example.com/video"
        parameters = {"format": "mp4"}
        job_id = str(uuid4())
        
        # Act
        result = await plugin.import_content(url, parameters, job_id)
        
        # Assert
        assert result["url"] == url
        assert result["status"] == ImportStatus.COMPLETED.value
        assert "content_id" in result
        assert "metadata" in result
        assert "content" in result
        assert "provenance_id" in result
        assert result["metadata"]["title"] == "Test Content"
        assert result["content"]["text"] == "Test content body"
        
        # Verify lifecycle hooks were called
        assert plugin.on_load_called is True
        assert plugin.before_download_called is True
        assert plugin.after_download_called is True
        assert plugin.before_extract_called is True
        assert plugin.after_extract_called is True
        assert plugin.on_complete_called is True
        assert plugin.on_error_called is False
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_tracks_progress(self, plugin, mock_job_manager):
        """Test that import tracks progress throughout lifecycle."""
        # Arrange
        url = "test://example.com/video"
        job_id = str(uuid4())
        
        # Act
        await plugin.import_content(url, {}, job_id)
        
        # Assert
        # Should have been called multiple times (20%, 40%, 60%, 80%, 90%, 100%)
        assert mock_job_manager.update_job_progress.call_count >= 5
        
        # Check first progress update
        first_call = mock_job_manager.update_job_progress.call_args_list[0]
        assert first_call[1]["job_id"] == job_id
        assert first_call[1]["percentage"] == 20
        assert "Downloading" in first_call[1]["current_step"]
        
        # Check last progress update
        last_call = mock_job_manager.update_job_progress.call_args_list[-1]
        assert last_call[1]["percentage"] == 100
        assert "complete" in last_call[1]["current_step"].lower()
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_tracks_provenance(
        self,
        plugin,
        mock_provenance_tracker,
    ):
        """Test that import tracks provenance."""
        # Arrange
        url = "test://example.com/video"
        
        # Act
        result = await plugin.import_content(url, {})
        
        # Assert
        assert result["provenance_id"] == "prov123"
        assert mock_provenance_tracker.track_import.called
        
        # Check provenance data
        call_args = mock_provenance_tracker.track_import.call_args
        prov_data = call_args[0][0]
        assert prov_data["content_id"] == result["content_id"]
        assert prov_data["source_url"] == url
        assert prov_data["source_type"] == "mock"
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_without_job_manager(
        self,
        mock_provenance_tracker,
    ):
        """Test import works without job manager."""
        # Arrange
        plugin = MockImportPlugin(
            job_manager=None,
            provenance_tracker=mock_provenance_tracker,
        )
        url = "test://example.com/video"
        
        # Act
        result = await plugin.import_content(url, {})
        
        # Assert
        assert result["status"] == ImportStatus.COMPLETED.value
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_without_provenance_tracker(
        self,
        mock_job_manager,
    ):
        """Test import works without provenance tracker."""
        # Arrange
        plugin = MockImportPlugin(
            job_manager=mock_job_manager,
            provenance_tracker=None,
        )
        url = "test://example.com/video"
        
        # Act
        result = await plugin.import_content(url, {})
        
        # Assert
        assert result["status"] == ImportStatus.COMPLETED.value
        assert "provenance_id" not in result
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_handles_download_error(self, plugin):
        """Test error handling during download stage."""
        # Arrange
        url = "test://example.com/video"
        
        # Override download to raise error
        async def failing_download(*args, **kwargs):
            raise ValueError("Download failed")
            
        plugin.download = failing_download
        
        # Act & Assert
        with pytest.raises(ValueError, match="Download failed"):
            await plugin.import_content(url, {})
            
        # Verify error callback was called
        assert plugin.on_error_called is True
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_import_content_handles_extraction_error(self, plugin):
        """Test error handling during extraction stage."""
        # Arrange
        url = "test://example.com/video"
        
        # Override extract_metadata to raise error
        async def failing_extract(*args, **kwargs):
            raise ValueError("Extraction failed")
            
        plugin.extract_metadata = failing_extract
        
        # Act & Assert
        with pytest.raises(ValueError, match="Extraction failed"):
            await plugin.import_content(url, {})
            
        # Verify error callback was called
        assert plugin.on_error_called is True
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_parameters_success(self, plugin):
        """Test parameter validation with valid parameters."""
        # Arrange
        parameters = {
            "url": "test://example.com",
            "format": "mp4",
        }
        
        # Act & Assert (should not raise)
        plugin.validate_parameters(parameters)
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_parameters_missing_required(self, plugin):
        """Test parameter validation with missing required parameter."""
        # Arrange
        parameters = {
            "url": "test://example.com",
            # Missing 'format'
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Missing required parameter: format"):
            plugin.validate_parameters(parameters)
            
    @pytest.mark.unit
    def test_get_plugin_name(self):
        """Test plugin name extraction."""
        # Act
        name = MockImportPlugin.get_plugin_name()
        
        # Assert
        assert name == "mock"
        
    @pytest.mark.unit
    def test_get_plugin_version(self):
        """Test plugin version."""
        # Act
        version = MockImportPlugin.get_plugin_version()
        
        # Assert
        assert version == "1.0.0"
        
    @pytest.mark.unit
    def test_get_supported_content_types(self):
        """Test supported content types."""
        # Act
        types = MockImportPlugin.get_supported_content_types()
        
        # Assert
        assert ContentType.VIDEO in types
        assert ContentType.AUDIO in types
        assert len(types) == 2
        
    @pytest.mark.unit
    def test_get_required_parameters(self):
        """Test required parameters list."""
        # Act
        params = MockImportPlugin.get_required_parameters()
        
        # Assert
        assert "url" in params
        assert "format" in params
        
    @pytest.mark.unit
    def test_get_optional_parameters(self):
        """Test optional parameters with defaults."""
        # Act
        params = MockImportPlugin.get_optional_parameters()
        
        # Assert
        assert params["quality"] == "high"
        assert params["language"] == "en"
        
    @pytest.mark.unit
    def test_plugin_repr(self, plugin):
        """Test plugin string representation."""
        # Act
        repr_str = repr(plugin)
        
        # Assert
        assert "MockImportPlugin" in repr_str
        assert "1.0.0" in repr_str
        assert "video" in repr_str
        assert "audio" in repr_str
