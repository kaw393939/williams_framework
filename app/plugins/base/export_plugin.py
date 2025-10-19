"""Base class for export plugins with lifecycle hooks."""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ExportStatus(str, Enum):
    """Export status enumeration."""
    
    PENDING = "pending"
    QUERYING = "querying"
    GENERATING = "generating"
    COMPOSING = "composing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    
    PODCAST = "podcast"
    VIDEO = "video"
    DOCUMENT = "document"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"
    SUMMARY = "summary"
    UNKNOWN = "unknown"


class ExportPlugin(ABC):
    """
    Abstract base class for export plugins.
    
    Provides lifecycle hooks for generating content from library sources.
    Subclasses must implement abstract methods to handle specific export formats.
    """
    
    def __init__(
        self,
        job_manager=None,
        provenance_tracker=None,
    ):
        """
        Initialize export plugin.
        
        Args:
            job_manager: JobManager instance for progress updates
            provenance_tracker: ProvenanceTracker for tracking generated content
        """
        self.job_manager = job_manager
        self.provenance_tracker = provenance_tracker
        self._progress_total_steps = 0
        self._progress_completed_steps = 0
        self._current_job_id: Optional[str] = None
        self._scene_attributions: List[Dict[str, Any]] = []
        self._ai_models_used: List[str] = []
        
    # Abstract methods (must be implemented by subclasses)
    
    @abstractmethod
    async def query_sources(
        self,
        source_ids: List[str],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Query library sources for content generation.
        
        Args:
            source_ids: List of content IDs to use as sources
            parameters: Query parameters (topics, keywords, etc.)
            
        Returns:
            Queried content data (documents, sections, etc.)
            
        Raises:
            ValueError: If query fails
        """
        pass
        
    @abstractmethod
    async def generate_script(
        self,
        queried_data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate script/outline for the export.
        
        Args:
            queried_data: Data returned from query_sources()
            parameters: Generation parameters (style, length, etc.)
            
        Returns:
            Generated script with scenes/sections
            
        Raises:
            ValueError: If generation fails
        """
        pass
        
    @abstractmethod
    async def generate_content(
        self,
        script: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate the actual export content (audio, video, etc.).
        
        Args:
            script: Script data from generate_script()
            parameters: Generation parameters (voice, quality, etc.)
            
        Returns:
            Generated content (file paths, URLs, etc.)
            
        Raises:
            ValueError: If content generation fails
        """
        pass
        
    @abstractmethod
    async def compose_output(
        self,
        generated_content: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compose/finalize the output (combine scenes, add metadata, etc.).
        
        Args:
            generated_content: Content from generate_content()
            parameters: Composition parameters
            
        Returns:
            Final composed output with metadata
            
        Raises:
            ValueError: If composition fails
        """
        pass
        
    # Lifecycle hook methods (optional override)
    
    async def on_load(self) -> None:
        """
        Called when plugin is loaded.
        
        Override to perform initialization (load models, connect to APIs, etc.).
        """
        pass
        
    async def before_query(
        self,
        source_ids: List[str],
        parameters: Dict[str, Any],
    ) -> None:
        """
        Called before querying sources.
        
        Override to perform pre-query validation or setup.
        
        Args:
            source_ids: Source IDs to query
            parameters: Query parameters
            
        Raises:
            ValueError: If validation fails
        """
        pass
        
    async def after_query(
        self,
        source_ids: List[str],
        queried_data: Dict[str, Any],
    ) -> None:
        """
        Called after querying sources.
        
        Override to perform post-query processing or validation.
        
        Args:
            source_ids: Queried source IDs
            queried_data: Queried data
        """
        pass
        
    async def before_generate(
        self,
        script: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> None:
        """
        Called before generating content.
        
        Override to perform pre-generation setup.
        
        Args:
            script: Script to generate from
            parameters: Generation parameters
        """
        pass
        
    async def after_generate(
        self,
        script: Dict[str, Any],
        generated_content: Dict[str, Any],
    ) -> None:
        """
        Called after content generation.
        
        Override to perform post-generation processing.
        
        Args:
            script: Original script
            generated_content: Generated content
        """
        pass
        
    async def on_scene_complete(
        self,
        scene_index: int,
        scene_data: Dict[str, Any],
        source_ids: List[str],
    ) -> None:
        """
        Called when a scene/section completes generation.
        
        Override to track scene-level attribution.
        
        Args:
            scene_index: Index of completed scene
            scene_data: Scene data
            source_ids: Source IDs used for this scene
        """
        # Default implementation: track attribution
        self._scene_attributions.append({
            "scene_index": scene_index,
            "scene_data": scene_data,
            "source_ids": source_ids,
            "timestamp": datetime.now().isoformat(),
        })
        
    async def on_error(self, error: Exception, stage: str) -> None:
        """
        Called when an error occurs during export.
        
        Override to perform custom error handling or cleanup.
        
        Args:
            error: Exception that occurred
            stage: Export stage where error occurred (query, generate, etc.)
        """
        pass
        
    async def on_complete(self, result: Dict[str, Any]) -> None:
        """
        Called when export completes successfully.
        
        Override to perform cleanup or final processing.
        
        Args:
            result: Complete export result
        """
        pass
        
    # Main export method (orchestrates lifecycle)
    
    async def export_content(
        self,
        source_ids: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export content from sources with full lifecycle management.
        
        This is the main entry point that orchestrates the entire export process.
        
        Args:
            source_ids: List of content IDs to use as sources
            parameters: Optional parameters for export
            job_id: Optional job ID for progress tracking
            
        Returns:
            Complete export result with content, metadata, and provenance
            
        Raises:
            ValueError: If export fails at any stage
        """
        if parameters is None:
            parameters = {}
            
        if not source_ids:
            raise ValueError("source_ids cannot be empty")
            
        self._current_job_id = job_id
        self._progress_total_steps = 5  # query, script, generate, compose, provenance
        self._progress_completed_steps = 0
        self._scene_attributions = []
        self._ai_models_used = []
        
        # Generate export ID
        export_id = str(uuid4())
        
        result = {
            "export_id": export_id,
            "source_ids": source_ids,
            "status": ExportStatus.PENDING.value,
            "started_at": datetime.now().isoformat(),
        }
        
        try:
            # Stage 0: on_load
            await self.on_load()
            
            # Stage 1: Query sources
            result["status"] = ExportStatus.QUERYING.value
            await self._update_progress(20, "Querying sources")
            await self.before_query(source_ids, parameters)
            
            queried_data = await self.query_sources(source_ids, parameters)
            await self.after_query(source_ids, queried_data)
            self._progress_completed_steps += 1
            
            # Stage 2: Generate script
            await self._update_progress(40, "Generating script")
            script = await self.generate_script(queried_data, parameters)
            self._progress_completed_steps += 1
            
            # Stage 3: Generate content
            result["status"] = ExportStatus.GENERATING.value
            await self._update_progress(60, "Generating content")
            await self.before_generate(script, parameters)
            
            generated_content = await self.generate_content(script, parameters)
            await self.after_generate(script, generated_content)
            self._progress_completed_steps += 1
            
            # Stage 4: Compose output
            result["status"] = ExportStatus.COMPOSING.value
            await self._update_progress(80, "Composing output")
            composed_output = await self.compose_output(generated_content, parameters)
            self._progress_completed_steps += 1
            
            # Stage 5: Track provenance
            await self._update_progress(90, "Tracking provenance")
            if self.provenance_tracker:
                provenance_id = await self._track_provenance(
                    export_id=export_id,
                    source_ids=source_ids,
                    script=script,
                    parameters=parameters,
                )
                result["provenance_id"] = provenance_id
            self._progress_completed_steps += 1
            
            # Complete
            result["status"] = ExportStatus.COMPLETED.value
            result["script"] = script
            result["content"] = composed_output
            result["scene_attributions"] = self._scene_attributions
            result["ai_models_used"] = self._ai_models_used
            result["completed_at"] = datetime.now().isoformat()
            await self._update_progress(100, "Export complete")
            
            await self.on_complete(result)
            
            return result
            
        except Exception as e:
            result["status"] = ExportStatus.FAILED.value
            result["error"] = str(e)
            result["failed_at"] = datetime.now().isoformat()
            
            await self.on_error(e, result.get("status", "unknown"))
            raise
            
    # Helper methods
    
    async def _update_progress(self, percentage: int, current_step: str) -> None:
        """
        Update job progress if job_manager is available.
        
        Args:
            percentage: Progress percentage (0-100)
            current_step: Description of current step
        """
        if self.job_manager and self._current_job_id:
            await self.job_manager.update_job_progress(
                job_id=self._current_job_id,
                percentage=percentage,
                current_step=current_step,
                total_steps=self._progress_total_steps,
                completed_steps=self._progress_completed_steps,
            )
            
    async def _track_provenance(
        self,
        export_id: str,
        source_ids: List[str],
        script: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Optional[str]:
        """
        Track export provenance if tracker is available.
        
        Args:
            export_id: Generated export ID
            source_ids: Source content IDs
            script: Generated script
            parameters: Export parameters
            
        Returns:
            Provenance ID if tracked, None otherwise
        """
        if not self.provenance_tracker:
            return None
            
        provenance_data = {
            "export_id": export_id,
            "source_ids": source_ids,
            "export_type": self.get_plugin_name(),
            "script": script,
            "scene_attributions": self._scene_attributions,
            "ai_models_used": self._ai_models_used,
            "export_parameters": parameters,
            "exported_at": datetime.now().isoformat(),
        }
        
        return await self.provenance_tracker.track_export(provenance_data)
        
    def track_ai_model(self, model_name: str) -> None:
        """
        Track AI model usage.
        
        Args:
            model_name: Name of AI model used (e.g., 'gpt-4', 'kling-1.0')
        """
        if model_name not in self._ai_models_used:
            self._ai_models_used.append(model_name)
            
    # Plugin metadata methods
    
    @classmethod
    def get_plugin_name(cls) -> str:
        """
        Get the plugin name.
        
        Returns:
            Plugin name (lowercase, e.g., 'podcast', 'video', 'flashcards')
        """
        return cls.__name__.replace("ExportPlugin", "").lower()
        
    @classmethod
    def get_plugin_version(cls) -> str:
        """
        Get the plugin version.
        
        Returns:
            Version string (e.g., '1.0.0')
        """
        return "1.0.0"
        
    @classmethod
    def get_supported_formats(cls) -> List[ExportFormat]:
        """
        Get list of export formats this plugin supports.
        
        Returns:
            List of ExportFormat enums
        """
        return [ExportFormat.UNKNOWN]
        
    @classmethod
    def get_required_parameters(cls) -> List[str]:
        """
        Get list of required parameters for this plugin.
        
        Returns:
            List of parameter names (e.g., ['sources', 'length'])
        """
        return ["source_ids"]
        
    @classmethod
    def get_optional_parameters(cls) -> Dict[str, Any]:
        """
        Get dictionary of optional parameters with default values.
        
        Returns:
            Dictionary of parameter names to default values
        """
        return {}
        
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Validate export parameters.
        
        Args:
            parameters: Parameters to validate
            
        Raises:
            ValueError: If validation fails
        """
        required = self.get_required_parameters()
        
        for param in required:
            if param not in parameters:
                raise ValueError(f"Missing required parameter: {param}")
                
    def __repr__(self) -> str:
        """String representation of plugin."""
        return (
            f"<{self.__class__.__name__} "
            f"version={self.get_plugin_version()} "
            f"formats={[f.value for f in self.get_supported_formats()]}>"
        )
