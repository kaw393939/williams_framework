# Domain Model

## Overview

This document defines all domain entities, value objects, and their relationships using Pydantic models for validation.

## Core Entities

### 1. ContentSource

Represents a URL or source to be processed.

```python
from pydantic import BaseModel, HttpUrl, Field
from enum import Enum
from datetime import datetime
from typing import Optional

class ContentType(str, Enum):
    """Type of content source"""
    WEB = "web"
    YOUTUBE = "youtube"
    PDF = "pdf"
    VIDEO = "video"
    ARXIV = "arxiv"

class ContentSource(BaseModel):
    """Source URL with discovery metadata"""
    
    url: HttpUrl
    content_type: ContentType
    discovered_at: datetime = Field(default_factory=datetime.now)
    source_domain: str
    anchor_text: Optional[str] = None
    depth_from_root: int = Field(default=0, ge=0)
    discovered_from: Optional[HttpUrl] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "url": "https://arxiv.org/abs/2304.12345",
                "content_type": "arxiv",
                "source_domain": "arxiv.org",
                "anchor_text": "Attention Is All You Need",
                "depth_from_root": 1
            }]
        }
    }
```

### 2. ScreeningResult

Result from LLM-based URL screening.

```python
class Priority(str, Enum):
    """Processing priority"""
    SKIP = "skip"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ScreeningResult(BaseModel):
    """LLM screening assessment"""
    
    url: HttpUrl
    relevance_score: float = Field(ge=0, le=10)
    quality_prediction: float = Field(ge=0, le=10)
    novelty_score: float = Field(ge=0, le=10)
    priority: Priority
    reasoning: str = Field(min_length=10)
    
    # Cost estimation
    estimated_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    roi_score: float = Field(ge=0)  # value / cost
    
    # Metadata
    screened_at: datetime = Field(default_factory=datetime.now)
    screened_by_model: str
    
    @property
    def should_process(self) -> bool:
        """Whether this URL should be processed"""
        return self.priority in [Priority.MEDIUM, Priority.HIGH]
    
    @property
    def average_score(self) -> float:
        """Average of all quality scores"""
        return (self.relevance_score + self.quality_prediction + self.novelty_score) / 3
```

### 3. RawContent

Extracted raw content before processing.

```python
class RawContent(BaseModel):
    """Raw extracted content"""
    
    source_url: HttpUrl
    content_type: ContentType
    
    # Content
    raw_text: str = Field(min_length=1)
    raw_html: Optional[str] = None
    
    # Metadata from extraction
    title: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    language: Optional[str] = None
    
    # Extraction metadata
    extracted_at: datetime = Field(default_factory=datetime.now)
    extractor_version: str
    extraction_success: bool = True
    extraction_warnings: list[str] = Field(default_factory=list)
    
    @property
    def word_count(self) -> int:
        return len(self.raw_text.split())
```

### 4. ProcessedContent

Content after transformation and enrichment.

```python
class ProcessedContent(BaseModel):
    """Transformed and enriched content"""
    
    source_url: HttpUrl
    content_type: ContentType
    
    # Core content
    title: str = Field(min_length=1)
    clean_text: str = Field(min_length=1)
    summary: str = Field(min_length=10)
    
    # Extracted information
    key_concepts: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)  # NER results
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    
    # Quality metrics
    quality_score: float = Field(ge=0, le=10)
    readability_score: Optional[float] = None
    
    # Statistics
    word_count: int = Field(ge=0)
    estimated_reading_time: int = Field(ge=0)  # minutes
    
    # Processing metadata
    processed_at: datetime = Field(default_factory=datetime.now)
    processor_version: str
    models_used: dict[str, str] = Field(default_factory=dict)
    
    @property
    def quality_tier(self) -> "QualityTier":
        if self.quality_score >= 9.0:
            return QualityTier.ESSENTIAL
        elif self.quality_score >= 7.0:
            return QualityTier.HIGH
        elif self.quality_score >= 5.0:
            return QualityTier.MEDIUM
        else:
            return QualityTier.LOW
```

### 5. LibraryFile

File stored in organized library.

```python
from pathlib import Path
from uuid import UUID, uuid4

class QualityTier(str, Enum):
    """Quality classification"""
    ESSENTIAL = "essential"  # 9.0+
    HIGH = "high"            # 7.0-8.9
    MEDIUM = "medium"        # 5.0-6.9
    LOW = "low"              # < 5.0

class LibraryFile(BaseModel):
    """File in organized library"""
    
    # Identity
    file_id: UUID = Field(default_factory=uuid4)
    source_url: HttpUrl
    
    # File system
    file_path: Path
    relative_path: str  # From library root
    filename: str
    
    # Organization
    topic_path: str  # e.g., "01_Foundations/Transformers"
    primary_topic: str
    secondary_topics: list[str] = Field(default_factory=list)
    
    # Classification
    content_type: ContentType
    quality_tier: QualityTier
    
    # Metadata
    file_size: int = Field(ge=0)  # bytes
    checksum: str  # SHA256
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    
    # Related files
    video_file: Optional[Path] = None  # For YouTube content
    transcript_file: Optional[Path] = None
    notes_file: Optional[Path] = None
    
    # ChromaDB reference
    chroma_document_id: Optional[str] = None
    
    @property
    def is_video_content(self) -> bool:
        return self.content_type in [ContentType.YOUTUBE, ContentType.VIDEO]
```

### 6. KnowledgeGraphNode

Node in the knowledge graph.

```python
class EntityType(str, Enum):
    """Type of entity"""
    CONCEPT = "concept"
    PERSON = "person"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    PAPER = "paper"
    MODEL = "model"

class KnowledgeGraphNode(BaseModel):
    """Node in knowledge graph"""
    
    # Identity
    node_id: UUID = Field(default_factory=uuid4)
    entity_name: str
    entity_type: EntityType
    
    # Aliases
    aliases: list[str] = Field(default_factory=list)
    
    # References
    mentioned_in: list[UUID] = Field(default_factory=list)  # LibraryFile IDs
    related_nodes: list[UUID] = Field(default_factory=list)  # Node IDs
    
    # Graph metrics
    centrality_score: float = Field(default=0, ge=0, le=1)
    degree: int = Field(default=0, ge=0)  # Number of connections
    
    # Metadata
    description: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
```

### 7. Relationship

Edge in the knowledge graph.

```python
class RelationshipType(str, Enum):
    """Type of relationship"""
    RELATED_TO = "related_to"
    BUILDS_ON = "builds_on"
    CONTRADICTS = "contradicts"
    IMPLEMENTS = "implements"
    CREATED_BY = "created_by"
    PART_OF = "part_of"
    USES = "uses"

class Relationship(BaseModel):
    """Edge in knowledge graph"""
    
    # Identity
    relationship_id: UUID = Field(default_factory=uuid4)
    
    # Nodes
    from_node: UUID  # Source node ID
    to_node: UUID    # Target node ID
    
    # Relationship
    relationship_type: RelationshipType
    confidence: float = Field(ge=0, le=1)
    
    # Evidence
    evidence_files: list[UUID] = Field(default_factory=list)  # LibraryFile IDs
    evidence_text: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    extracted_by_model: Optional[str] = None
```

### 8. DigestItem

Item in daily digest.

```python
class DigestItem(BaseModel):
    """Item recommended in daily digest"""
    
    # Source
    source_url: HttpUrl
    library_file_id: Optional[UUID] = None
    
    # Content
    title: str
    summary: str = Field(max_length=500)
    
    # Recommendation
    relevance_explanation: str
    quality_score: float = Field(ge=0, le=10)
    priority: Priority
    
    # User context
    why_relevant: str  # Why this matters to Williams Framework
    related_concepts: list[str] = Field(default_factory=list)
    
    # Metadata
    estimated_reading_time: int = Field(ge=0)
    discovered_at: datetime
    recommended_at: datetime = Field(default_factory=datetime.now)
```

### 9. MaintenanceTask

Suggested maintenance action.

```python
class TaskType(str, Enum):
    """Type of maintenance task"""
    DEAD_LINK = "dead_link"
    DUPLICATE_CONTENT = "duplicate_content"
    OUTDATED_CONTENT = "outdated_content"
    MISSING_METADATA = "missing_metadata"
    CREATE_COLLECTION = "create_collection"
    REORGANIZE_FILES = "reorganize_files"

class MaintenanceTask(BaseModel):
    """Suggested maintenance action"""
    
    # Identity
    task_id: UUID = Field(default_factory=uuid4)
    task_type: TaskType
    
    # Description
    title: str
    description: str
    reasoning: str
    
    # Affected items
    affected_files: list[UUID] = Field(default_factory=list)
    
    # Recommended action
    recommended_action: str
    automated_fix_available: bool = False
    
    # Priority
    priority: Priority
    estimated_impact: str  # "high" | "medium" | "low"
    
    # Status
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "pending"  # "pending" | "completed" | "dismissed"
```

### 10. ProcessingRecord

Record of content processing.

```python
class ProcessingStatus(str, Enum):
    """Status of processing"""
    PENDING = "pending"
    SCREENING = "screening"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    LOADING = "loading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ProcessingRecord(BaseModel):
    """Record of processing attempt"""
    
    # Identity
    record_id: UUID = Field(default_factory=uuid4)
    source_url: HttpUrl
    
    # Status
    status: ProcessingStatus
    status_message: Optional[str] = None
    
    # Steps completed
    screening_result: Optional[ScreeningResult] = None
    extraction_result: Optional[RawContent] = None
    processing_result: Optional[ProcessedContent] = None
    library_file: Optional[LibraryFile] = None
    
    # Errors
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    
    # Performance
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Cost
    tokens_used: int = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
```

## Value Objects

### TaskComplexity

```python
class TaskComplexity(str, Enum):
    """Complexity level for model selection"""
    LOW = "low"      # gpt-5-nano: screening, classification
    MEDIUM = "medium"  # gpt-5-mini: summarization, analysis
    HIGH = "high"    # gpt-5: complex reasoning, validation
```

### ModelConfig

```python
class ModelConfig(BaseModel):
    """Configuration for LLM model"""
    
    name: str
    cost_per_1m_input: float = Field(gt=0)
    cost_per_1m_output: float = Field(gt=0)
    max_context: int = Field(gt=0)
    supports_streaming: bool = True
    supports_functions: bool = True
    
    # Use cases
    recommended_for: list[str] = Field(default_factory=list)
    
    # Rate limits
    requests_per_minute: Optional[int] = None
    tokens_per_minute: Optional[int] = None
```

### UserPreferences

```python
class UserPreferences(BaseModel):
    """User preferences for content curation"""
    
    # Topics of interest
    primary_topics: list[str] = Field(default_factory=list)
    secondary_topics: list[str] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)
    
    # Quality thresholds
    min_quality_score: float = Field(default=7.0, ge=0, le=10)
    min_relevance_score: float = Field(default=7.0, ge=0, le=10)
    
    # Content preferences
    preferred_content_types: list[ContentType] = Field(default_factory=list)
    max_reading_time: Optional[int] = None  # minutes
    
    # Digest settings
    digest_size: int = Field(default=10, ge=1, le=50)
    digest_frequency: str = "daily"  # "daily" | "weekly"
    
    # Budget
    monthly_api_budget: Optional[float] = None  # dollars
```

## Aggregates

### ContentAggregate

Groups related content entities together.

```python
class ContentAggregate(BaseModel):
    """Aggregate of related content"""
    
    source: ContentSource
    screening: Optional[ScreeningResult] = None
    raw_content: Optional[RawContent] = None
    processed_content: Optional[ProcessedContent] = None
    library_file: Optional[LibraryFile] = None
    
    processing_records: list[ProcessingRecord] = Field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Whether all processing stages are complete"""
        return all([
            self.screening,
            self.raw_content,
            self.processed_content,
            self.library_file
        ])
    
    @property
    def current_status(self) -> ProcessingStatus:
        """Current processing status"""
        if self.library_file:
            return ProcessingStatus.COMPLETED
        elif self.processed_content:
            return ProcessingStatus.LOADING
        elif self.raw_content:
            return ProcessingStatus.TRANSFORMING
        elif self.screening:
            return ProcessingStatus.EXTRACTING
        else:
            return ProcessingStatus.SCREENING
```

## Relationships

### Entity Relationship Diagram

```
ContentSource (1) -----> (1) ScreeningResult
     |
     v
RawContent (1) -----> (1) ProcessedContent
     |
     v
LibraryFile (1) -----> (0..*) KnowledgeGraphNode
     |
     v
KnowledgeGraphNode (0..*) <-----> (0..*) Relationship
     |
     v
DigestItem (0..*)

ProcessingRecord (1) -----> (1) ContentSource
```

## Validation Rules

### Business Rules

1. **URL Screening**
   - Only process URLs with priority >= MEDIUM
   - Skip if screening cost > ROI threshold

2. **Quality Tiers**
   - ESSENTIAL: 9.0-10.0
   - HIGH: 7.0-8.9
   - MEDIUM: 5.0-6.9
   - LOW: < 5.0

3. **File Organization**
   - Files must be in topic-based directories
   - Filenames must be human-readable
   - No duplicate files (by checksum)

4. **Knowledge Graph**
   - Nodes must have at least one mention
   - Relationships must have evidence
   - Confidence >= 0.7 for automatic linking

5. **Cost Control**
   - Track all API calls
   - Alert at 80% of monthly budget
   - Block at 100% of budget

## Next Steps

See [cost-optimization.md](cost-optimization.md) for model selection and cost strategies.
See [testing-guide.md](testing-guide.md) for testing these domain models.
