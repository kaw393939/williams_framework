"""Core Pydantic domain models for the Williams Librarian.

This module contains the primary domain models that represent business entities.
All models use Pydantic for validation and serialization.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.core.types import ContentSource


class ScreeningResult(BaseModel):
    """Result of content screening by the AI screener.

    This model captures the LLM's assessment of whether content should be
    accepted into the library, along with quality estimates and reasoning.

    Attributes:
        screening_score: Overall screening score (0-10)
        decision: Accept, reject, or maybe (needs human review)
        reasoning: LLM's explanation for the decision
        estimated_quality: Predicted quality score if accepted (0-10)
    """

    model_config = {"frozen": True}  # Make immutable

    screening_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Overall screening score from 0 (lowest) to 10 (highest)"
    )

    decision: Literal["ACCEPT", "REJECT", "MAYBE"] = Field(
        ...,
        description="Screening decision: ACCEPT (add to library), REJECT (discard), MAYBE (human review)"
    )

    reasoning: str = Field(
        ...,
        min_length=1,
        description="LLM's explanation for the screening decision"
    )

    estimated_quality: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Estimated quality score if content is accepted (0-10)"
    )

    @field_validator("reasoning")
    @classmethod
    def reasoning_not_empty(cls, v: str) -> str:
        """Validate that reasoning is not empty or whitespace."""
        if not v.strip():
            raise ValueError("reasoning cannot be empty or whitespace")
        return v


class RawContent(BaseModel):
    """Raw extracted content before processing.

    This model represents content immediately after extraction from its source,
    before any AI processing or transformation has occurred.

    Attributes:
        url: Source URL of the content
        source_type: Type of source (web, youtube, pdf, text)
        raw_text: Raw extracted text content
        metadata: Additional metadata from extraction (flexible dict)
        extracted_at: Timestamp when content was extracted
    """

    url: HttpUrl = Field(
        ...,
        description="Source URL of the content"
    )

    source_type: ContentSource = Field(
        ...,
        description="Type of content source"
    )

    raw_text: str = Field(
        ...,
        min_length=1,
        description="Raw extracted text content"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from extraction process"
    )

    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when content was extracted"
    )

    @field_validator("raw_text")
    @classmethod
    def raw_text_not_empty(cls, v: str) -> str:
        """Validate that raw_text is not empty or whitespace."""
        if not v.strip():
            raise ValueError("raw_text cannot be empty or whitespace")
        return v


class ProcessedContent(BaseModel):
    """Content after AI processing and screening.

    This model represents content that has been analyzed by the LLM,
    with extracted title, summary, key points, tags, and screening decision.

    Attributes:
        url: Source URL of the content
        source_type: Type of source (web, youtube, pdf, text)
        title: Extracted or generated title
        summary: AI-generated summary
        key_points: List of key takeaways
        tags: List of relevant tags/topics
        screening_result: AI screening decision and scores
        processed_at: Timestamp when processing completed
    """

    url: HttpUrl = Field(
        ...,
        description="Source URL of the content"
    )

    source_type: ContentSource = Field(
        ...,
        description="Type of content source"
    )

    title: str = Field(
        ...,
        min_length=1,
        description="Extracted or generated title"
    )

    summary: str = Field(
        ...,
        min_length=1,
        description="AI-generated summary of content"
    )

    key_points: list[str] = Field(
        default_factory=list,
        description="List of key takeaways from the content"
    )

    tags: list[str] = Field(
        default_factory=list,
        description="List of relevant tags/topics"
    )

    screening_result: ScreeningResult = Field(
        ...,
        description="AI screening decision and quality assessment"
    )

    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when processing completed"
    )

    @field_validator("title", "summary")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate that text fields are not empty or whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v


class LibraryFile(BaseModel):
    """File stored in the quality-tiered library.

    This model represents a markdown file saved in one of the quality tiers
    (tier-a through tier-d) of the content library.

    Attributes:
        file_path: Path to the file in the library
        url: Original source URL
        source_type: Type of source (web, youtube, pdf, text)
        tier: Quality tier (tier-a, tier-b, tier-c, tier-d)
        quality_score: Quality score (0-10)
        title: Content title
        tags: List of tags
        created_at: Timestamp when file was created
    """

    file_path: Path = Field(
        ...,
        description="Path to the file in the library"
    )

    url: HttpUrl = Field(
        ...,
        description="Original source URL"
    )

    source_type: ContentSource = Field(
        ...,
        description="Type of content source"
    )

    tier: Literal["tier-a", "tier-b", "tier-c", "tier-d"] = Field(
        ...,
        description="Quality tier: tier-a (9.0+), tier-b (7.0-8.9), tier-c (5.0-6.9), tier-d (<5.0)"
    )

    quality_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Quality score (0-10)"
    )

    title: str = Field(
        ...,
        min_length=1,
        description="Content title"
    )

    tags: list[str] = Field(
        default_factory=list,
        description="List of relevant tags"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when file was created"
    )


class KnowledgeGraphNode(BaseModel):
    """Node in the knowledge graph.

    Represents entities, concepts, topics, people, or organizations
    extracted from content and connected in the knowledge graph.

    Attributes:
        node_id: Unique identifier for the node
        label: Human-readable label
        node_type: Type of entity (concept, topic, person, organization, technology)
        properties: Flexible dict for additional attributes
        created_at: Timestamp when node was created
    """

    node_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the node"
    )

    label: str = Field(
        ...,
        min_length=1,
        description="Human-readable label for the node"
    )

    node_type: Literal["concept", "topic", "person", "organization", "technology"] = Field(
        ...,
        description="Type of entity this node represents"
    )

    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible properties for the node"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when node was created"
    )


class Relationship(BaseModel):
    """Relationship between two nodes in the knowledge graph.

    Represents connections between entities with a type and weight.

    Attributes:
        source_id: ID of the source node
        target_id: ID of the target node
        relationship_type: Type of relationship
        weight: Strength of relationship (0-1)
        created_at: Timestamp when relationship was created
    """

    source_id: str = Field(
        ...,
        min_length=1,
        description="ID of the source node"
    )

    target_id: str = Field(
        ...,
        min_length=1,
        description="ID of the target node"
    )

    relationship_type: Literal["related_to", "mentions", "references", "derived_from", "similar_to"] = Field(
        ...,
        description="Type of relationship between nodes"
    )

    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Strength of the relationship (0-1)"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when relationship was created"
    )


class DigestItem(BaseModel):
    """Item to include in a digest email.

    Represents a single piece of content selected for the daily digest,
    with relevant metadata for presentation in the email.

    Attributes:
        url: Source URL
        title: Content title
        summary: Brief summary
        quality_score: Quality score (0-10)
        tier: Quality tier
        tags: Content tags
        added_date: When added to library
    """

    url: HttpUrl = Field(
        ...,
        description="Source URL"
    )

    title: str = Field(
        ...,
        min_length=1,
        description="Content title"
    )

    summary: str = Field(
        ...,
        description="Brief content summary"
    )

    quality_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Quality score"
    )

    tier: Literal["tier-a", "tier-b", "tier-c", "tier-d"] = Field(
        ...,
        description="Quality tier"
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Content tags"
    )

    added_date: datetime = Field(
        ...,
        description="Date added to library"
    )


class MaintenanceTask(BaseModel):
    """Scheduled maintenance task for library management.

    Represents automated maintenance operations like re-screening,
    quality updates, or cleanup tasks.

    Attributes:
        task_id: Unique task identifier
        task_type: Type of maintenance task
        status: Current status
        scheduled_for: When task should run
        completed_at: When task completed (if done)
        details: Additional task details
    """

    task_id: str = Field(
        ...,
        min_length=1,
        description="Unique task identifier"
    )

    task_type: Literal["rescreen", "quality_update", "cleanup", "digest", "backup"] = Field(
        ...,
        description="Type of maintenance task"
    )

    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending",
        description="Current task status"
    )

    scheduled_for: datetime = Field(
        ...,
        description="When the task should run"
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When the task completed (if done)"
    )

    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task-specific details"
    )


class ProcessingRecord(BaseModel):
    """Record of content processing operations.

    Tracks the processing history for audit and debugging purposes.

    Attributes:
        record_id: Unique record identifier
        content_url: URL of processed content
        operation: Type of operation performed
        status: Operation status
        started_at: When processing started
        completed_at: When processing completed
        error_message: Error details if failed
        metadata: Additional processing metadata
    """

    record_id: str = Field(
        ...,
        min_length=1,
        description="Unique record identifier"
    )

    content_url: HttpUrl = Field(
        ...,
        description="URL of the processed content"
    )

    operation: Literal["extract", "screen", "process", "store", "index"] = Field(
        ...,
        description="Type of operation performed"
    )

    status: Literal["started", "completed", "failed"] = Field(
        ...,
        description="Operation status"
    )

    started_at: datetime = Field(
        default_factory=datetime.now,
        description="When processing started"
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When processing completed (if done)"
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if operation failed"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing metadata"
    )


class SearchResult(BaseModel):
    """Result from semantic search of the library.

    Attributes:
        file_path: Path to the file in the library
        url: Original source URL
        title: Content title
        summary: Content summary
        tags: List of tags
        tier: Quality tier
        quality_score: Quality score
        relevance_score: Search relevance score (0-1)
        matched_content: Snippet of matched content
    """

    file_path: str = Field(
        ...,
        description="Path to the file in the library"
    )

    url: str = Field(
        ...,
        description="Original source URL"
    )

    title: str = Field(
        ...,
        description="Content title"
    )

    summary: str = Field(
        ...,
        description="Content summary"
    )

    tags: list[str] = Field(
        default_factory=list,
        description="List of tags"
    )

    tier: str = Field(
        ...,
        description="Quality tier (a, b, c, d)"
    )

    quality_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Quality score"
    )

    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Search relevance score"
    )

    matched_content: str | None = Field(
        default=None,
        description="Snippet of matched content"
    )

    # Optional fields for chunk-based results
    content_id: str | None = Field(
        default=None,
        description="Content ID for chunk-based results"
    )

    chunk_index: int | None = Field(
        default=None,
        description="Chunk index within content"
    )

    # Optional YouTube-specific fields
    video_id: str | None = Field(
        default=None,
        description="YouTube video ID"
    )

    channel: str | None = Field(
        default=None,
        description="YouTube channel name"
    )

    timestamp: str | None = Field(
        default=None,
        description="Timestamp in video (for YouTube)"
    )


class LibraryStats(BaseModel):
    """Statistics about the library contents.

    Attributes:
        total_files: Total number of files in library
        files_by_tier: Count of files in each tier
        average_quality: Average quality score
        total_tags: Total number of unique tags
        recent_additions: Number of files added recently
        storage_size_mb: Total storage size in MB
    """

    total_files: int = Field(
        ...,
        ge=0,
        description="Total number of files in library"
    )

    files_by_tier: dict[str, int] = Field(
        default_factory=dict,
        description="Count of files in each tier"
    )

    average_quality: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Average quality score across all files"
    )

    total_tags: int = Field(
        ...,
        ge=0,
        description="Total number of unique tags"
    )

    recent_additions: int = Field(
        default=0,
        ge=0,
        description="Number of files added in last 7 days"
    )

    storage_size_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="Total storage size in MB"
    )


# DigestItem class already defined above (line 326)
# This duplicate definition has been removed to fix F811 lint error


class Digest(BaseModel):
    """Email digest of curated content.

    Represents a daily digest email containing selected high-quality content
    from the library. Tracks what was sent, when, and to whom.

    Attributes:
        digest_id: Unique digest identifier
        date: Digest date
        subject: Email subject line
        items: Content items in digest
        html_content: HTML email body
        text_content: Plain text email body
        recipients: Email recipients
        sent_at: When digest was sent (None if not sent)
        created_at: When digest was created
    """

    digest_id: str = Field(
        ...,
        min_length=1,
        description="Unique digest identifier"
    )

    date: datetime = Field(
        ...,
        description="Digest date"
    )

    subject: str = Field(
        ...,
        min_length=1,
        description="Email subject line"
    )

    items: list[DigestItem] = Field(
        default_factory=list,
        description="Content items in digest"
    )

    html_content: str | None = Field(
        default=None,
        description="HTML email body"
    )

    text_content: str | None = Field(
        default=None,
        description="Plain text email body"
    )

    recipients: list[str] = Field(
        default_factory=list,
        description="Email recipients"
    )

    sent_at: datetime | None = Field(
        default=None,
        description="When digest was sent"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When digest was created"
    )
