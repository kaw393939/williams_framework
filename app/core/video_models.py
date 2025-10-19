"""
Video provenance models for tracking generated video content.

These models support complete lineage tracking for AI-generated videos,
including source attribution, scene-level tracking, and AI model usage.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VideoScene(BaseModel):
    """
    Represents a single scene in a generated video.
    
    Tracks which source materials were used for this specific scene.
    """
    scene_num: int = Field(..., description="Scene number in the video")
    text: str = Field(..., description="Scene narration text")
    source_ids: List[str] = Field(default_factory=list, description="Source document IDs used")
    paragraph_ids: List[str] = Field(default_factory=list, description="Specific paragraph IDs referenced")
    figure_ids: List[str] = Field(default_factory=list, description="Figure IDs referenced")
    attribution_text: str = Field(default="", description="Human-readable attribution")
    duration: Optional[float] = Field(None, description="Scene duration in seconds")


class VideoMetadata(BaseModel):
    """Complete metadata for a generated video."""
    video_id: str = Field(..., description="Unique video identifier")
    title: str = Field(..., description="Video title")
    description: str = Field(default="", description="Video description")
    duration: Optional[float] = Field(None, description="Total duration in seconds")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    resolution: Optional[str] = Field(None, description="Video resolution (e.g., '1920x1080')")
    fps: Optional[int] = Field(None, description="Frames per second")
    format: str = Field(default="mp4", description="Video format")
    status: str = Field(default="generating", description="Status: generating, completed, failed")


class AIModelInfo(BaseModel):
    """Information about AI model used for generation."""
    name: str = Field(..., description="Model name (e.g., 'kling', 'veo3')")
    version: str = Field(..., description="Model version")
    provider: Optional[str] = Field(None, description="Provider (e.g., 'Kuaishou', 'Google')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Generation parameters")


class VideoProvenance(BaseModel):
    """
    Complete provenance record for a generated video.
    
    This is the main model that ties everything together:
    - Source materials used
    - Scene-level attributions
    - AI models used
    - Creator information
    - Timestamps
    """
    video_id: str = Field(..., description="Video identifier")
    source_ids: List[str] = Field(..., description="Source document IDs")
    scenes: List[VideoScene] = Field(default_factory=list, description="Scene attributions")
    ai_models: List[AIModelInfo] = Field(default_factory=list, description="AI models used")
    creator_id: Optional[str] = Field(None, description="User who created the video")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    version_of: Optional[str] = Field(None, description="Previous version video_id if this is a revision")
    derived_from: Optional[str] = Field(None, description="Related content ID (e.g., podcast)")
    artifact_id: Optional[str] = Field(None, description="Storage artifact ID")
    metadata: Optional[VideoMetadata] = Field(None, description="Video metadata")


class VideoAttribution(BaseModel):
    """Attribution information for a source document."""
    doc_id: str = Field(..., description="Document identifier")
    citation: str = Field(..., description="Formatted citation text")
    license: Optional[str] = Field(None, description="License type")
    attribution_required: bool = Field(default=True, description="Whether attribution is required")


class VideoGenealogy(BaseModel):
    """
    Complete genealogy of a video showing all provenance relationships.
    
    This is returned by the provenance API to show the full lineage.
    """
    video: VideoMetadata = Field(..., description="Video metadata")
    source_documents: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Papers cited by sources")
    scene_attributions: List[VideoScene] = Field(default_factory=list, description="Scene-level attributions")
    ai_models: List[AIModelInfo] = Field(default_factory=list, description="AI models used")
    creator: Optional[Dict[str, Any]] = Field(None, description="Creator information")
    previous_version: Optional[Dict[str, Any]] = Field(None, description="Previous version")
    next_version: Optional[Dict[str, Any]] = Field(None, description="Next version")
    related_content: List[Dict[str, Any]] = Field(default_factory=list, description="Related content")


class VideoImpact(BaseModel):
    """
    Impact metrics for a generated video.
    
    Tracks how the video has been used and shared.
    """
    video_id: str = Field(..., description="Video identifier")
    view_count: int = Field(default=0, description="Number of views")
    share_count: int = Field(default=0, description="Number of shares")
    derivative_count: int = Field(default=0, description="Number of derivative works")
    citation_count: int = Field(default=0, description="Number of citations")
    derivative_works: List[Dict[str, Any]] = Field(default_factory=list, description="Derivative works")
    citing_videos: List[Dict[str, Any]] = Field(default_factory=list, description="Videos citing this one")
