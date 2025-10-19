"""Unit tests for ExportPlugin base class."""
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.plugins.base.export_plugin import (
    ExportFormat,
    ExportPlugin,
    ExportStatus,
)


# Concrete test implementation of ExportPlugin
class MockExportPlugin(ExportPlugin):
    """Mock implementation of ExportPlugin for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_load_called = False
        self.before_query_called = False
        self.after_query_called = False
        self.before_generate_called = False
        self.after_generate_called = False
        self.on_scene_complete_called = False
        self.on_error_called = False
        self.on_complete_called = False
        
    async def query_sources(self, source_ids: list, parameters: dict) -> dict:
        """Mock query sources."""
        return {
            "sources": [{"id": sid, "content": f"Content from {sid}"} for sid in source_ids],
            "total": len(source_ids),
        }
        
    async def generate_script(self, queried_data: dict, parameters: dict) -> dict:
        """Mock script generation."""
        return {
            "title": "Test Export",
            "scenes": [
                {"index": 0, "text": "Scene 1", "source_ids": ["src1"]},
                {"index": 1, "text": "Scene 2", "source_ids": ["src2"]},
            ],
        }
        
    async def generate_content(self, script: dict, parameters: dict) -> dict:
        """Mock content generation."""
        # Track AI model usage
        self.track_ai_model("test-model-1.0")
        
        # Track scene completion
        for scene in script["scenes"]:
            await self.on_scene_complete(
                scene["index"],
                scene,
                scene["source_ids"]
            )
            
        return {
            "scenes": [
                {"index": 0, "file": "/tmp/scene1.mp4"},
                {"index": 1, "file": "/tmp/scene2.mp4"},
            ],
        }
        
    async def compose_output(self, generated_content: dict, parameters: dict) -> dict:
        """Mock output composition."""
        return {
            "file_path": "/tmp/final.mp4",
            "duration": 120,
            "size": 10240,
        }
        
    async def on_load(self) -> None:
        """Track on_load call."""
        self.on_load_called = True
        
    async def before_query(self, source_ids: list, parameters: dict) -> None:
        """Track before_query call."""
        self.before_query_called = True
        
    async def after_query(self, source_ids: list, queried_data: dict) -> None:
        """Track after_query call."""
        self.after_query_called = True
        
    async def before_generate(self, script: dict, parameters: dict) -> None:
        """Track before_generate call."""
        self.before_generate_called = True
        
    async def after_generate(self, script: dict, generated_content: dict) -> None:
        """Track after_generate call."""
        self.after_generate_called = True
        
    async def on_error(self, error: Exception, stage: str) -> None:
        """Track on_error call."""
        self.on_error_called = True
        
    async def on_complete(self, result: dict) -> None:
        """Track on_complete call."""
        self.on_complete_called = True
        
    @classmethod
    def get_supported_formats(cls):
        """Return test formats."""
        return [ExportFormat.PODCAST, ExportFormat.VIDEO]
        
    @classmethod
    def get_required_parameters(cls):
        """Return required parameters."""
        return ["source_ids", "format"]
        
    @classmethod
    def get_optional_parameters(cls):
        """Return optional parameters."""
        return {"quality": "high", "duration": 300}


class TestExportPluginBase:
    """Test suite for ExportPlugin base class."""
    
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
        tracker.track_export = AsyncMock(return_value="prov123")
        return tracker
        
    @pytest.fixture
    def plugin(self, mock_job_manager, mock_provenance_tracker):
        """Create test plugin instance."""
        return MockExportPlugin(
            job_manager=mock_job_manager,
            provenance_tracker=mock_provenance_tracker,
        )
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_full_lifecycle(self, plugin, mock_job_manager):
        """Test complete export lifecycle."""
        # Arrange
        source_ids = ["src1", "src2"]
        parameters = {"format": "video"}
        job_id = str(uuid4())
        
        # Act
        result = await plugin.export_content(source_ids, parameters, job_id)
        
        # Assert
        assert result["source_ids"] == source_ids
        assert result["status"] == ExportStatus.COMPLETED.value
        assert "export_id" in result
        assert "script" in result
        assert "content" in result
        assert "scene_attributions" in result
        assert "ai_models_used" in result
        assert "provenance_id" in result
        assert result["script"]["title"] == "Test Export"
        assert len(result["scene_attributions"]) == 2
        assert "test-model-1.0" in result["ai_models_used"]
        
        # Verify lifecycle hooks were called
        assert plugin.on_load_called is True
        assert plugin.before_query_called is True
        assert plugin.after_query_called is True
        assert plugin.before_generate_called is True
        assert plugin.after_generate_called is True
        assert plugin.on_complete_called is True
        assert plugin.on_error_called is False
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_tracks_progress(self, plugin, mock_job_manager):
        """Test that export tracks progress throughout lifecycle."""
        # Arrange
        source_ids = ["src1"]
        job_id = str(uuid4())
        
        # Act
        await plugin.export_content(source_ids, {}, job_id)
        
        # Assert
        # Should have been called multiple times (20%, 40%, 60%, 80%, 90%, 100%)
        assert mock_job_manager.update_job_progress.call_count >= 5
        
        # Check first progress update
        first_call = mock_job_manager.update_job_progress.call_args_list[0]
        assert first_call[1]["job_id"] == job_id
        assert first_call[1]["percentage"] == 20
        assert "Querying" in first_call[1]["current_step"]
        
        # Check last progress update
        last_call = mock_job_manager.update_job_progress.call_args_list[-1]
        assert last_call[1]["percentage"] == 100
        assert "complete" in last_call[1]["current_step"].lower()
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_tracks_provenance(
        self,
        plugin,
        mock_provenance_tracker,
    ):
        """Test that export tracks provenance."""
        # Arrange
        source_ids = ["src1", "src2"]
        
        # Act
        result = await plugin.export_content(source_ids, {})
        
        # Assert
        assert result["provenance_id"] == "prov123"
        assert mock_provenance_tracker.track_export.called
        
        # Check provenance data
        call_args = mock_provenance_tracker.track_export.call_args
        prov_data = call_args[0][0]
        assert prov_data["export_id"] == result["export_id"]
        assert prov_data["source_ids"] == source_ids
        assert prov_data["export_type"] == "mock"
        assert len(prov_data["scene_attributions"]) == 2
        assert "test-model-1.0" in prov_data["ai_models_used"]
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_tracks_scene_attribution(self, plugin):
        """Test scene-level attribution tracking."""
        # Arrange
        source_ids = ["src1", "src2"]
        
        # Act
        result = await plugin.export_content(source_ids, {})
        
        # Assert
        scene_attrs = result["scene_attributions"]
        assert len(scene_attrs) == 2
        
        # Check first scene attribution
        scene1 = scene_attrs[0]
        assert scene1["scene_index"] == 0
        assert scene1["source_ids"] == ["src1"]
        assert "timestamp" in scene1
        
        # Check second scene attribution
        scene2 = scene_attrs[1]
        assert scene2["scene_index"] == 1
        assert scene2["source_ids"] == ["src2"]
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_tracks_ai_models(self, plugin):
        """Test AI model tracking."""
        # Arrange
        source_ids = ["src1"]
        
        # Act
        result = await plugin.export_content(source_ids, {})
        
        # Assert
        assert "test-model-1.0" in result["ai_models_used"]
        assert len(result["ai_models_used"]) == 1
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_without_job_manager(
        self,
        mock_provenance_tracker,
    ):
        """Test export works without job manager."""
        # Arrange
        plugin = MockExportPlugin(
            job_manager=None,
            provenance_tracker=mock_provenance_tracker,
        )
        source_ids = ["src1"]
        
        # Act
        result = await plugin.export_content(source_ids, {})
        
        # Assert
        assert result["status"] == ExportStatus.COMPLETED.value
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_without_provenance_tracker(
        self,
        mock_job_manager,
    ):
        """Test export works without provenance tracker."""
        # Arrange
        plugin = MockExportPlugin(
            job_manager=mock_job_manager,
            provenance_tracker=None,
        )
        source_ids = ["src1"]
        
        # Act
        result = await plugin.export_content(source_ids, {})
        
        # Assert
        assert result["status"] == ExportStatus.COMPLETED.value
        assert "provenance_id" not in result
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_empty_source_ids(self, plugin):
        """Test export fails with empty source_ids."""
        # Arrange
        source_ids = []
        
        # Act & Assert
        with pytest.raises(ValueError, match="source_ids cannot be empty"):
            await plugin.export_content(source_ids, {})
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_handles_query_error(self, plugin):
        """Test error handling during query stage."""
        # Arrange
        source_ids = ["src1"]
        
        # Override query_sources to raise error
        async def failing_query(*args, **kwargs):
            raise ValueError("Query failed")
            
        plugin.query_sources = failing_query
        
        # Act & Assert
        with pytest.raises(ValueError, match="Query failed"):
            await plugin.export_content(source_ids, {})
            
        # Verify error callback was called
        assert plugin.on_error_called is True
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_content_handles_generation_error(self, plugin):
        """Test error handling during generation stage."""
        # Arrange
        source_ids = ["src1"]
        
        # Override generate_content to raise error
        async def failing_generate(*args, **kwargs):
            raise ValueError("Generation failed")
            
        plugin.generate_content = failing_generate
        
        # Act & Assert
        with pytest.raises(ValueError, match="Generation failed"):
            await plugin.export_content(source_ids, {})
            
        # Verify error callback was called
        assert plugin.on_error_called is True
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_parameters_success(self, plugin):
        """Test parameter validation with valid parameters."""
        # Arrange
        parameters = {
            "source_ids": ["src1"],
            "format": "video",
        }
        
        # Act & Assert (should not raise)
        plugin.validate_parameters(parameters)
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_parameters_missing_required(self, plugin):
        """Test parameter validation with missing required parameter."""
        # Arrange
        parameters = {
            "source_ids": ["src1"],
            # Missing 'format'
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Missing required parameter: format"):
            plugin.validate_parameters(parameters)
            
    @pytest.mark.unit
    def test_get_plugin_name(self):
        """Test plugin name extraction."""
        # Act
        name = MockExportPlugin.get_plugin_name()
        
        # Assert
        assert name == "mock"
        
    @pytest.mark.unit
    def test_get_plugin_version(self):
        """Test plugin version."""
        # Act
        version = MockExportPlugin.get_plugin_version()
        
        # Assert
        assert version == "1.0.0"
        
    @pytest.mark.unit
    def test_get_supported_formats(self):
        """Test supported export formats."""
        # Act
        formats = MockExportPlugin.get_supported_formats()
        
        # Assert
        assert ExportFormat.PODCAST in formats
        assert ExportFormat.VIDEO in formats
        assert len(formats) == 2
        
    @pytest.mark.unit
    def test_get_required_parameters(self):
        """Test required parameters list."""
        # Act
        params = MockExportPlugin.get_required_parameters()
        
        # Assert
        assert "source_ids" in params
        assert "format" in params
        
    @pytest.mark.unit
    def test_get_optional_parameters(self):
        """Test optional parameters with defaults."""
        # Act
        params = MockExportPlugin.get_optional_parameters()
        
        # Assert
        assert params["quality"] == "high"
        assert params["duration"] == 300
        
    @pytest.mark.unit
    def test_track_ai_model_no_duplicates(self, plugin):
        """Test AI model tracking prevents duplicates."""
        # Act
        plugin.track_ai_model("gpt-4")
        plugin.track_ai_model("gpt-4")  # Duplicate
        plugin.track_ai_model("claude-3")
        
        # Assert
        assert len(plugin._ai_models_used) == 2
        assert "gpt-4" in plugin._ai_models_used
        assert "claude-3" in plugin._ai_models_used
        
    @pytest.mark.unit
    def test_plugin_repr(self, plugin):
        """Test plugin string representation."""
        # Act
        repr_str = repr(plugin)
        
        # Assert
        assert "MockExportPlugin" in repr_str
        assert "1.0.0" in repr_str
        assert "podcast" in repr_str
        assert "video" in repr_str
