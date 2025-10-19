"""Base class for import plugins with lifecycle hooks."""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ImportStatus(str, Enum):
    """Import status enumeration."""
    
    PENDING = "pending"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentType(str, Enum):
    """Content type enumeration."""
    
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    WEBPAGE = "webpage"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ImportPlugin(ABC):
    """
    Abstract base class for import plugins.
    
    Provides lifecycle hooks for importing content from external sources.
    Subclasses must implement abstract methods to handle specific source types.
    """
    
    def __init__(
        self,
        job_manager=None,
        provenance_tracker=None,
    ):
        """
        Initialize import plugin.
        
        Args:
            job_manager: JobManager instance for progress updates
            provenance_tracker: ProvenanceTracker for tracking content sources
        """
        self.job_manager = job_manager
        self.provenance_tracker = provenance_tracker
        self._progress_total_steps = 0
        self._progress_completed_steps = 0
        self._current_job_id: Optional[str] = None
        
    # Abstract methods (must be implemented by subclasses)
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Check if this plugin can handle the given URL.
        
        Args:
            url: URL or identifier of content to import
            
        Returns:
            True if this plugin can handle the URL
        """
        pass
        
    @abstractmethod
    async def download(self, url: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download content from the source.
        
        Args:
            url: URL or identifier of content to download
            parameters: Additional parameters (quality, format, etc.)
            
        Returns:
            Downloaded content metadata (file paths, size, etc.)
            
        Raises:
            ValueError: If download fails
        """
        pass
        
    @abstractmethod
    async def extract_metadata(self, downloaded_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from downloaded content.
        
        Args:
            downloaded_data: Data returned from download()
            
        Returns:
            Extracted metadata (title, author, duration, etc.)
            
        Raises:
            ValueError: If extraction fails
        """
        pass
        
    @abstractmethod
    async def extract_content(self, downloaded_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract main content (text, transcript, etc.) from downloaded data.
        
        Args:
            downloaded_data: Data returned from download()
            
        Returns:
            Extracted content (text, transcript, sections, etc.)
            
        Raises:
            ValueError: If extraction fails
        """
        pass
        
    # Lifecycle hook methods (optional override)
    
    async def on_load(self) -> None:
        """
        Called when plugin is loaded.
        
        Override to perform initialization (load models, connect to APIs, etc.).
        """
        pass
        
    async def before_download(self, url: str, parameters: Dict[str, Any]) -> None:
        """
        Called before downloading content.
        
        Override to perform pre-download validation or setup.
        
        Args:
            url: URL to be downloaded
            parameters: Download parameters
            
        Raises:
            ValueError: If validation fails
        """
        pass
        
    async def after_download(self, url: str, downloaded_data: Dict[str, Any]) -> None:
        """
        Called after downloading content.
        
        Override to perform post-download processing or validation.
        
        Args:
            url: Downloaded URL
            downloaded_data: Downloaded data
        """
        pass
        
    async def before_extract(self, downloaded_data: Dict[str, Any]) -> None:
        """
        Called before extracting metadata and content.
        
        Override to perform pre-extraction setup.
        
        Args:
            downloaded_data: Data to be extracted
        """
        pass
        
    async def after_extract(
        self,
        downloaded_data: Dict[str, Any],
        metadata: Dict[str, Any],
        content: Dict[str, Any],
    ) -> None:
        """
        Called after extraction is complete.
        
        Override to perform post-extraction processing.
        
        Args:
            downloaded_data: Original downloaded data
            metadata: Extracted metadata
            content: Extracted content
        """
        pass
        
    async def on_error(self, error: Exception, stage: str) -> None:
        """
        Called when an error occurs during import.
        
        Override to perform custom error handling or cleanup.
        
        Args:
            error: Exception that occurred
            stage: Import stage where error occurred (download, extract, etc.)
        """
        pass
        
    async def on_complete(self, result: Dict[str, Any]) -> None:
        """
        Called when import completes successfully.
        
        Override to perform cleanup or final processing.
        
        Args:
            result: Complete import result
        """
        pass
        
    # Main import method (orchestrates lifecycle)
    
    async def import_content(
        self,
        url: str,
        parameters: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import content from URL with full lifecycle management.
        
        This is the main entry point that orchestrates the entire import process.
        
        Args:
            url: URL or identifier of content to import
            parameters: Optional parameters for import
            job_id: Optional job ID for progress tracking
            
        Returns:
            Complete import result with metadata, content, and provenance
            
        Raises:
            ValueError: If import fails at any stage
        """
        if parameters is None:
            parameters = {}
            
        self._current_job_id = job_id
        self._progress_total_steps = 5  # download, extract_metadata, extract_content, store, provenance
        self._progress_completed_steps = 0
        
        # Generate content ID
        content_id = str(uuid4())
        
        result = {
            "content_id": content_id,
            "url": url,
            "status": ImportStatus.PENDING.value,
            "started_at": datetime.now().isoformat(),
        }
        
        try:
            # Stage 0: on_load
            await self.on_load()
            
            # Stage 1: Download
            result["status"] = ImportStatus.DOWNLOADING.value
            await self._update_progress(20, "Downloading content")
            await self.before_download(url, parameters)
            
            downloaded_data = await self.download(url, parameters)
            await self.after_download(url, downloaded_data)
            self._progress_completed_steps += 1
            
            # Stage 2: Extract metadata
            result["status"] = ImportStatus.EXTRACTING.value
            await self._update_progress(40, "Extracting metadata")
            await self.before_extract(downloaded_data)
            
            metadata = await self.extract_metadata(downloaded_data)
            self._progress_completed_steps += 1
            
            # Stage 3: Extract content
            await self._update_progress(60, "Extracting content")
            content = await self.extract_content(downloaded_data)
            self._progress_completed_steps += 1
            
            await self.after_extract(downloaded_data, metadata, content)
            
            # Stage 4: Process and store
            result["status"] = ImportStatus.PROCESSING.value
            await self._update_progress(80, "Processing and storing")
            result["metadata"] = metadata
            result["content"] = content
            result["downloaded_data"] = downloaded_data
            self._progress_completed_steps += 1
            
            # Stage 5: Track provenance
            await self._update_progress(90, "Tracking provenance")
            if self.provenance_tracker:
                provenance_id = await self._track_provenance(
                    content_id=content_id,
                    url=url,
                    metadata=metadata,
                    parameters=parameters,
                )
                result["provenance_id"] = provenance_id
            self._progress_completed_steps += 1
            
            # Complete
            result["status"] = ImportStatus.COMPLETED.value
            result["completed_at"] = datetime.now().isoformat()
            await self._update_progress(100, "Import complete")
            
            await self.on_complete(result)
            
            return result
            
        except Exception as e:
            result["status"] = ImportStatus.FAILED.value
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
        content_id: str,
        url: str,
        metadata: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Optional[str]:
        """
        Track content provenance if tracker is available.
        
        Args:
            content_id: Generated content ID
            url: Source URL
            metadata: Extracted metadata
            parameters: Import parameters
            
        Returns:
            Provenance ID if tracked, None otherwise
        """
        if not self.provenance_tracker:
            return None
            
        provenance_data = {
            "content_id": content_id,
            "source_url": url,
            "source_type": self.get_plugin_name(),
            "metadata": metadata,
            "import_parameters": parameters,
            "imported_at": datetime.now().isoformat(),
        }
        
        return await self.provenance_tracker.track_import(provenance_data)
        
    # Plugin metadata methods
    
    @classmethod
    def get_plugin_name(cls) -> str:
        """
        Get the plugin name.
        
        Returns:
            Plugin name (lowercase, e.g., 'youtube', 'pdf', 'webpage')
        """
        return cls.__name__.replace("ImportPlugin", "").lower()
        
    @classmethod
    def get_plugin_version(cls) -> str:
        """
        Get the plugin version.
        
        Returns:
            Version string (e.g., '1.0.0')
        """
        return "1.0.0"
        
    @classmethod
    def get_supported_content_types(cls) -> List[ContentType]:
        """
        Get list of content types this plugin supports.
        
        Returns:
            List of ContentType enums
        """
        return [ContentType.UNKNOWN]
        
    @classmethod
    def get_required_parameters(cls) -> List[str]:
        """
        Get list of required parameters for this plugin.
        
        Returns:
            List of parameter names (e.g., ['url', 'quality'])
        """
        return ["url"]
        
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
        Validate import parameters.
        
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
            f"types={[t.value for t in self.get_supported_content_types()]}>"
        )
