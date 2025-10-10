# TDD Implementation Plan - Detailed

## How to Use This Document

This document provides **specific test scenarios and implementation steps** for each module. Follow the RED-GREEN-REFACTOR cycle for every feature:

```
🔴 RED: Write failing test → Run test (should fail)
🟢 GREEN: Write minimal code → Run test (should pass)
🔄 REFACTOR: Improve code → Run test (still passes)
```

---

## Phase 1: Foundation Layer

### Module 1.1: Core Domain Models

#### 1.1.1 ContentSource Model

**Test File**: `tests/unit/test_content_source.py`

**Test Scenario 1: Valid ContentSource**
```python
def test_content_source_with_valid_data():
    """🔴 RED: Should create ContentSource with valid data"""
    source = ContentSource(
        url="https://arxiv.org/abs/1706.03762",
        content_type=ContentType.WEB
    )
    
    assert source.url == "https://arxiv.org/abs/1706.03762"
    assert source.content_type == ContentType.WEB
    assert source.source_domain == "arxiv.org"
    assert isinstance(source.discovered_at, datetime)
    assert source.depth_from_root == 0
```

**Implementation Steps**:
1. 🔴 Write test above → Run `pytest tests/unit/test_content_source.py::test_content_source_with_valid_data`
   - **Expected**: ImportError or test fails (no ContentSource yet)
2. 🟢 Create `app/core/types.py`:
   ```python
   from pydantic import BaseModel, HttpUrl, Field
   from datetime import datetime
   from enum import Enum
   
   class ContentType(str, Enum):
       WEB = "web"
       VIDEO = "video"
       PDF = "pdf"
   
   class ContentSource(BaseModel):
       url: HttpUrl
       content_type: ContentType
       source_domain: str = ""
       discovered_at: datetime = Field(default_factory=datetime.now)
       depth_from_root: int = 0
   ```
3. Run test → Should fail (source_domain not auto-extracted)
4. 🟢 Add validator:
   ```python
   @validator('source_domain', always=True)
   def extract_domain(cls, v, values):
       if not v and 'url' in values:
           from urllib.parse import urlparse
           return urlparse(str(values['url'])).netloc
       return v
   ```
5. Run test → Should PASS ✅
6. 🔄 REFACTOR: Extract domain logic to utility function if needed

**Test Scenario 2: Invalid URL**
```python
def test_content_source_with_invalid_url():
    """🔴 Should raise ValidationError for invalid URL"""
    with pytest.raises(ValidationError) as exc:
        ContentSource(
            url="not-a-url",
            content_type=ContentType.WEB
        )
    
    errors = exc.value.errors()
    assert any("url" in str(e) for e in errors)
```

**Implementation**: Already handled by Pydantic's HttpUrl validator ✅

**Test Scenario 3: Custom domain override**
```python
def test_content_source_with_custom_domain():
    """🔴 Should allow custom domain override"""
    source = ContentSource(
        url="https://example.com/article",
        content_type=ContentType.WEB,
        source_domain="custom.domain"
    )
    
    assert source.source_domain == "custom.domain"
```

**Test Scenario 4: Depth tracking**
```python
def test_content_source_depth_tracking():
    """🔴 Should track depth from root"""
    source = ContentSource(
        url="https://example.com/nested/deep/article",
        content_type=ContentType.WEB,
        depth_from_root=3
    )
    
    assert source.depth_from_root == 3
```

**Test Scenario 5: JSON serialization**
```python
def test_content_source_serialization():
    """🔴 Should serialize to JSON correctly"""
    source = ContentSource(
        url="https://example.com",
        content_type=ContentType.WEB
    )
    
    json_data = source.model_dump_json()
    loaded = ContentSource.model_validate_json(json_data)
    
    assert loaded.url == source.url
    assert loaded.content_type == source.content_type
```

**Completion Criteria**:
- [ ] All 5 test scenarios pass
- [ ] Coverage: 100% for ContentSource
- [ ] No type errors (`mypy app/core/types.py`)

---

#### 1.1.2 ScreeningResult Model

**Test File**: `tests/unit/test_screening_result.py`

**Test Scenario 1: Valid screening with all scores**
```python
def test_screening_result_valid():
    """🔴 Should create ScreeningResult with valid scores"""
    result = ScreeningResult(
        url="https://example.com",
        relevance_score=9.5,
        quality_prediction=9.0,
        novelty_score=8.5,
        priority=Priority.HIGH,
        reasoning="Excellent paper on transformers",
        estimated_tokens=5000,
        estimated_cost=0.01,
        roi_score=950.0,
        screened_by_model="gpt-5-nano"
    )
    
    assert result.relevance_score == 9.5
    assert result.priority == Priority.HIGH
```

**Test Scenario 2: Score validation (0-10 range)**
```python
@pytest.mark.parametrize("score_field,invalid_value", [
    ("relevance_score", 11.0),
    ("quality_prediction", -1.0),
    ("novelty_score", 15.5),
])
def test_screening_result_score_validation(score_field, invalid_value):
    """🔴 Scores must be 0-10"""
    with pytest.raises(ValidationError) as exc:
        ScreeningResult(
            url="https://example.com",
            relevance_score=5.0,
            quality_prediction=5.0,
            novelty_score=5.0,
            priority=Priority.MEDIUM,
            **{score_field: invalid_value}
        )
    
    assert score_field in str(exc.value)
```

**Implementation**:
```python
class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"

class ScreeningResult(BaseModel):
    url: HttpUrl
    relevance_score: float = Field(..., ge=0.0, le=10.0)
    quality_prediction: float = Field(..., ge=0.0, le=10.0)
    novelty_score: float = Field(..., ge=0.0, le=10.0)
    priority: Priority
    reasoning: str
    estimated_tokens: int = Field(..., gt=0)
    estimated_cost: float = Field(..., ge=0.0)
    roi_score: float
    screened_by_model: str
    screened_at: datetime = Field(default_factory=datetime.now)
```

**Test Scenario 3: Computed property - average_score**
```python
def test_screening_result_average_score():
    """🔴 Should compute average of three scores"""
    result = ScreeningResult(
        url="https://example.com",
        relevance_score=9.0,
        quality_prediction=8.0,
        novelty_score=7.0,
        priority=Priority.HIGH,
        reasoning="Test",
        estimated_tokens=1000,
        estimated_cost=0.001,
        roi_score=800.0,
        screened_by_model="gpt-5-nano"
    )
    
    assert result.average_score == 8.0
```

**Implementation**:
```python
@property
def average_score(self) -> float:
    """Average of relevance, quality, and novelty"""
    return (self.relevance_score + self.quality_prediction + self.novelty_score) / 3
```

**Test Scenario 4: Computed property - should_process**
```python
@pytest.mark.parametrize("priority,expected", [
    (Priority.HIGH, True),
    (Priority.MEDIUM, True),
    (Priority.LOW, True),
    (Priority.SKIP, False),
])
def test_screening_result_should_process(priority, expected):
    """🔴 Should process if priority is not SKIP"""
    result = ScreeningResult(
        url="https://example.com",
        relevance_score=5.0,
        quality_prediction=5.0,
        novelty_score=5.0,
        priority=priority,
        reasoning="Test",
        estimated_tokens=1000,
        estimated_cost=0.001,
        roi_score=500.0,
        screened_by_model="gpt-5-nano"
    )
    
    assert result.should_process == expected
```

**Implementation**:
```python
@property
def should_process(self) -> bool:
    """Whether content should be processed"""
    return self.priority != Priority.SKIP
```

**Completion Criteria**:
- [ ] All test scenarios pass
- [ ] Parametrized tests for all three score fields
- [ ] Both computed properties working
- [ ] Coverage: 100%

---

#### 1.1.3 ProcessedContent Model

**Test File**: `tests/unit/test_processed_content.py`

**Test Scenario 1: Full processed content**
```python
def test_processed_content_full():
    """🔴 Should create ProcessedContent with all fields"""
    content = ProcessedContent(
        source_url="https://example.com",
        content_type=ContentType.WEB,
        title="Attention Is All You Need",
        clean_text="The dominant sequence transduction models...",
        summary="Introduces the Transformer architecture.",
        key_concepts=["transformer", "attention", "neural networks"],
        entities=["Vaswani", "Google Brain"],
        topics=["deep learning", "nlp"],
        quality_score=9.5,
        word_count=8000,
        estimated_reading_time=32,
        processor_version="1.0.0"
    )
    
    assert content.title == "Attention Is All You Need"
    assert len(content.key_concepts) == 3
    assert content.quality_score == 9.5
```

**Test Scenario 2: Quality tier determination**
```python
@pytest.mark.parametrize("quality_score,expected_tier", [
    (9.5, "tier-a"),
    (8.0, "tier-b"),
    (6.5, "tier-c"),
    (4.0, "tier-d"),
])
def test_processed_content_quality_tier(quality_score, expected_tier):
    """🔴 Should determine quality tier from score"""
    content = ProcessedContent(
        source_url="https://example.com",
        content_type=ContentType.WEB,
        title="Test",
        clean_text="Test content",
        summary="Test summary",
        quality_score=quality_score,
        word_count=1000,
        processor_version="1.0.0"
    )
    
    assert content.quality_tier == expected_tier
```

**Implementation**:
```python
@property
def quality_tier(self) -> str:
    """Determine quality tier from score"""
    if self.quality_score >= 9.0:
        return "tier-a"
    elif self.quality_score >= 7.0:
        return "tier-b"
    elif self.quality_score >= 5.0:
        return "tier-c"
    else:
        return "tier-d"
```

**Test Scenario 3: Reading time calculation**
```python
def test_processed_content_reading_time_calculation():
    """🔴 Should calculate reading time from word count"""
    content = ProcessedContent(
        source_url="https://example.com",
        content_type=ContentType.WEB,
        title="Test",
        clean_text="Test content",
        summary="Test",
        word_count=1000,  # ~4 minutes at 250 wpm
        processor_version="1.0.0"
    )
    
    # If estimated_reading_time not provided, calculate it
    if content.estimated_reading_time is None:
        assert content.calculated_reading_time == 4
```

**Test Scenario 4: Empty lists default to empty**
```python
def test_processed_content_empty_lists():
    """🔴 Should handle empty optional lists"""
    content = ProcessedContent(
        source_url="https://example.com",
        content_type=ContentType.WEB,
        title="Test",
        clean_text="Test",
        summary="Test",
        word_count=100,
        processor_version="1.0.0"
    )
    
    assert content.key_concepts == []
    assert content.entities == []
    assert content.topics == []
```

**Completion Criteria**:
- [ ] All scenarios pass
- [ ] Quality tier logic correct
- [ ] Optional fields handled properly
- [ ] Coverage: 100%

---

#### 1.1.4 LibraryFile Model

**Test File**: `tests/unit/test_library_file.py`

**Test Scenario 1: Basic library file**
```python
def test_library_file_creation():
    """🔴 Should create LibraryFile with required fields"""
    file = LibraryFile(
        file_id=uuid4(),
        source_url="https://example.com",
        file_path=Path("library/tier-a/ai-ml/attention.md"),
        title="Attention Is All You Need",
        quality_tier="tier-a",
        topic_path="ai-ml",
        word_count=8000
    )
    
    assert file.file_path.exists() is False  # Not created yet
    assert file.quality_tier == "tier-a"
    assert file.topic_path == "ai-ml"
```

**Test Scenario 2: Video with transcript**
```python
def test_library_file_with_video():
    """🔴 Should handle video files with transcripts"""
    file = LibraryFile(
        file_id=uuid4(),
        source_url="https://youtube.com/watch?v=abc123",
        file_path=Path("library/tier-a/lectures/video.md"),
        title="Neural Networks Explained",
        quality_tier="tier-a",
        topic_path="lectures",
        word_count=5000,
        video_file=Path("library/tier-a/lectures/video.mp4"),
        transcript_file=Path("library/tier-a/lectures/video.txt")
    )
    
    assert file.video_file is not None
    assert file.transcript_file is not None
    assert file.has_video is True
```

**Implementation**:
```python
class LibraryFile(BaseModel):
    file_id: UUID
    source_url: HttpUrl
    file_path: Path
    title: str
    quality_tier: str
    topic_path: str
    word_count: int
    
    # Optional video fields
    video_file: Optional[Path] = None
    transcript_file: Optional[Path] = None
    
    # ChromaDB reference
    chroma_document_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    @property
    def has_video(self) -> bool:
        return self.video_file is not None
    
    class Config:
        arbitrary_types_allowed = True  # For Path
```

**Test Scenario 3: ChromaDB linking**
```python
def test_library_file_chroma_reference():
    """🔴 Should store ChromaDB document reference"""
    file = LibraryFile(
        file_id=uuid4(),
        source_url="https://example.com",
        file_path=Path("library/tier-a/test.md"),
        title="Test",
        quality_tier="tier-a",
        topic_path="test",
        word_count=1000,
        chroma_document_id="chroma-doc-123"
    )
    
    assert file.chroma_document_id == "chroma-doc-123"
```

**Completion Criteria**:
- [ ] All scenarios pass
- [ ] Path handling works correctly
- [ ] Video fields optional
- [ ] Coverage: 100%

---

#### 1.1.5-1.1.10: Remaining Models

**Similar TDD cycles for**:
- KnowledgeGraphNode (with centrality score)
- Relationship (with confidence levels)
- DigestItem (with relevance explanation)
- MaintenanceTask (with priority)
- ProcessingRecord (with status tracking)
- Value Objects (TaskComplexity, ModelConfig, UserPreferences)

**Test Patterns**:
- ✅ Valid creation
- ✅ Field validation
- ✅ Computed properties
- ✅ Edge cases
- ✅ Serialization/deserialization

---

### Module 1.2: Configuration System

**Test File**: `tests/unit/test_config.py`

**Test Scenario 1: Load from environment**
```python
def test_settings_load_from_env(monkeypatch):
    """🔴 Should load from environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("MONTHLY_API_BUDGET", "50.0")
    monkeypatch.setenv("SCREENING_MODEL", "gpt-5-nano")
    
    settings = Settings()
    
    assert settings.openai_api_key == "sk-test-key"
    assert settings.monthly_api_budget == 50.0
    assert settings.screening_model == "gpt-5-nano"
```

**Test Scenario 2: Default values**
```python
def test_settings_defaults():
    """🔴 Should have sensible defaults"""
    settings = Settings(openai_api_key="sk-test")
    
    assert settings.screening_model == "gpt-5-nano"
    assert settings.summarization_model == "gpt-5-mini"
    assert settings.monthly_api_budget == 100.0
    assert settings.enable_web_search is False
    assert settings.enable_file_search is True
```

**Test Scenario 3: Load from .env file**
```python
def test_settings_load_from_file(tmp_path):
    """🔴 Should load from .env file"""
    env_file = tmp_path / ".env"
    env_file.write_text("""
OPENAI_API_KEY=sk-file-key
MONTHLY_API_BUDGET=75.0
""")
    
    settings = Settings(_env_file=env_file)
    
    assert settings.openai_api_key == "sk-file-key"
    assert settings.monthly_api_budget == 75.0
```

**Test Scenario 4: Path validation**
```python
def test_settings_path_creation():
    """🔴 Should create paths if they don't exist"""
    settings = Settings(
        openai_api_key="sk-test",
        library_root=Path("./test_library"),
        chroma_persist_dir=Path("./test_chroma")
    )
    
    # Paths should be created when needed
    settings.library_root.mkdir(parents=True, exist_ok=True)
    assert settings.library_root.exists()
```

**Completion Criteria**:
- [ ] Loads from environment
- [ ] Loads from .env file
- [ ] Has sensible defaults
- [ ] Type validation works
- [ ] Coverage: 100%

---

### Module 1.3: Custom Exceptions

**Test File**: `tests/unit/test_exceptions.py`

**Test Scenarios**:
```python
def test_base_exception():
    """🔴 LibrarianException is base for all"""
    error = LibrarianException("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)

def test_extraction_error():
    """🔴 ExtractionError inherits from base"""
    error = ExtractionError("Failed to extract", url="https://example.com")
    assert isinstance(error, LibrarianException)
    assert error.url == "https://example.com"

def test_budget_exceeded_with_context():
    """🔴 BudgetExceededError carries financial context"""
    error = BudgetExceededError(
        "Budget exceeded",
        spent=105.50,
        limit=100.0,
        operation="screening"
    )
    
    assert error.spent == 105.50
    assert error.limit == 100.0
    assert error.operation == "screening"
    assert "105.50" in str(error)

def test_plugin_error():
    """🔴 PluginError for plugin failures"""
    error = PluginError("Plugin failed", plugin_name="twitter-extractor")
    assert error.plugin_name == "twitter-extractor"
```

**Implementation** (`app/core/exceptions.py`):
```python
class LibrarianException(Exception):
    """Base exception"""
    pass

class ExtractionError(LibrarianException):
    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(message)
        self.url = url

class BudgetExceededError(LibrarianException):
    def __init__(self, message: str, spent: float, limit: float, operation: str):
        super().__init__(f"{message}: spent ${spent:.2f}, limit ${limit:.2f}")
        self.spent = spent
        self.limit = limit
        self.operation = operation

class PluginError(LibrarianException):
    def __init__(self, message: str, plugin_name: str):
        super().__init__(f"Plugin '{plugin_name}': {message}")
        self.plugin_name = plugin_name

class ValidationError(LibrarianException):
    pass
```

**Completion Criteria**:
- [ ] All exception types defined
- [ ] Proper inheritance hierarchy
- [ ] Context data preserved
- [ ] Coverage: 100%

---

## Phase 2: Data Layer

### Module 2.1: ChromaDB Repository

**Test File**: `tests/integration/test_chroma_repository.py`

**⚠️ CRITICAL**: Use REAL ChromaDB (no mocks)

**Setup Fixture**:
```python
import pytest
import tempfile
import shutil
from pathlib import Path
from app.repositories.chroma_repository import ChromaRepository

@pytest.fixture
async def chroma_repo():
    """Real ChromaDB instance with ephemeral storage"""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_chroma_"))
    
    repo = ChromaRepository(persist_directory=temp_dir)
    await repo.initialize()
    
    yield repo
    
    # Cleanup
    shutil.rmtree(temp_dir)
```

**Test Scenario 1: Initialize collection**
```python
@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_chroma_initialize(chroma_repo):
    """🔴 Should initialize ChromaDB with collection"""
    assert chroma_repo.client is not None
    assert chroma_repo.collection is not None
    assert chroma_repo.collection.name == "library_content"
```

**Test Scenario 2: Add single document**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_add_document(chroma_repo):
    """🔴 Should add document and return ID"""
    doc_id = await chroma_repo.add_document(
        content="Transformers are neural network architectures.",
        metadata={"title": "Test Article", "quality": 9.5}
    )
    
    assert doc_id is not None
    assert len(doc_id) > 0
```

**Test Scenario 3: Retrieve document**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_get_document(chroma_repo):
    """🔴 Should retrieve document by ID"""
    # Add document
    doc_id = await chroma_repo.add_document(
        content="Test content",
        metadata={"title": "Test"}
    )
    
    # Retrieve
    doc = await chroma_repo.get(doc_id)
    
    assert doc is not None
    assert doc["content"] == "Test content"
    assert doc["metadata"]["title"] == "Test"
```

**Test Scenario 4: Semantic search**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_semantic_search(chroma_repo):
    """🔴 Should search by semantic similarity"""
    # Add multiple documents
    await chroma_repo.add_document(
        "Transformers use self-attention mechanisms for sequence modeling",
        {"topic": "architecture"}
    )
    await chroma_repo.add_document(
        "Python is a high-level programming language",
        {"topic": "programming"}
    )
    await chroma_repo.add_document(
        "Neural networks are inspired by biological neurons",
        {"topic": "ml-basics"}
    )
    
    # Search for transformer-related content
    results = await chroma_repo.search(
        query="neural network architecture for NLP",
        k=2
    )
    
    assert len(results) <= 2
    # Most relevant should be about transformers
    assert "Transformers" in results[0]["document"] or "Neural" in results[0]["document"]
```

**Test Scenario 5: Search with metadata filter**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_search_with_filter(chroma_repo):
    """🔴 Should filter results by metadata"""
    await chroma_repo.add_document(
        "Content A",
        {"quality": 9.5, "tier": "tier-a"}
    )
    await chroma_repo.add_document(
        "Content B",
        {"quality": 7.5, "tier": "tier-b"}
    )
    
    # Search only tier-a
    results = await chroma_repo.search(
        query="Content",
        k=10,
        filter={"tier": "tier-a"}
    )
    
    assert len(results) == 1
    assert results[0]["metadata"]["tier"] == "tier-a"
```

**Test Scenario 6: Batch add documents**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_batch_add(chroma_repo):
    """🔴 Should add multiple documents efficiently"""
    documents = [
        ("Document 1", {"index": 1}),
        ("Document 2", {"index": 2}),
        ("Document 3", {"index": 3}),
    ]
    
    doc_ids = await chroma_repo.add_documents_batch(documents)
    
    assert len(doc_ids) == 3
    
    # Verify all added
    for doc_id in doc_ids:
        doc = await chroma_repo.get(doc_id)
        assert doc is not None
```

**Test Scenario 7: Update document**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_update_document(chroma_repo):
    """🔴 Should update existing document"""
    # Add document
    doc_id = await chroma_repo.add_document(
        "Original content",
        {"version": 1}
    )
    
    # Update
    await chroma_repo.update(
        doc_id,
        content="Updated content",
        metadata={"version": 2}
    )
    
    # Verify
    doc = await chroma_repo.get(doc_id)
    assert doc["content"] == "Updated content"
    assert doc["metadata"]["version"] == 2
```

**Test Scenario 8: Delete document**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_delete_document(chroma_repo):
    """🔴 Should delete document"""
    doc_id = await chroma_repo.add_document("Test", {})
    
    deleted = await chroma_repo.delete(doc_id)
    assert deleted is True
    
    doc = await chroma_repo.get(doc_id)
    assert doc is None
```

**Test Scenario 9: Count documents**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chroma_count(chroma_repo):
    """🔴 Should count total documents"""
    assert await chroma_repo.count() == 0
    
    await chroma_repo.add_document("Doc 1", {})
    await chroma_repo.add_document("Doc 2", {})
    
    assert await chroma_repo.count() == 2
```

**Implementation Checklist**:
- [ ] All 9 test scenarios pass
- [ ] Uses REAL ChromaDB (not mocked)
- [ ] Proper async/await
- [ ] Error handling for edge cases
- [ ] Integration test coverage ≥ 80%

---

### Module 2.2: File Repository

**Test File**: `tests/integration/test_file_repository.py`

**Setup Fixture**:
```python
@pytest.fixture
def temp_library(tmp_path):
    """Temporary library directory"""
    library_root = tmp_path / "library"
    library_root.mkdir()
    
    # Create tier directories
    for tier in ["tier-a", "tier-b", "tier-c", "tier-d"]:
        (library_root / tier).mkdir()
    
    return library_root

@pytest.fixture
def file_repo(temp_library):
    """File repository instance"""
    from app.repositories.file_repository import FileRepository
    return FileRepository(library_root=temp_library)
```

**Test Scenario 1: Save markdown file**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_repo_save_markdown(file_repo, temp_library):
    """🔴 Should save markdown file with frontmatter"""
    content = ProcessedContent(
        source_url="https://example.com/article",
        content_type=ContentType.WEB,
        title="Test Article",
        clean_text="This is the article content.",
        summary="A test article",
        quality_score=9.5,
        word_count=5,
        processor_version="1.0.0"
    )
    
    file_path = await file_repo.save(content, topic="ai-ml")
    
    # Verify file exists
    assert file_path.exists()
    assert file_path.parent.name == "ai-ml"
    assert file_path.parent.parent.name == "tier-a"
    
    # Verify content
    text = file_path.read_text()
    assert "title: Test Article" in text
    assert "quality_score: 9.5" in text
    assert "This is the article content." in text
```

**Test Scenario 2: Create topic directory structure**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_repo_create_nested_topics(file_repo):
    """🔴 Should create nested topic directories"""
    content = ProcessedContent(
        source_url="https://example.com",
        title="Test",
        clean_text="Content",
        quality_score=8.0,
        word_count=1,
        processor_version="1.0.0"
    )
    
    file_path = await file_repo.save(content, topic="ai/ml/transformers")
    
    assert file_path.exists()
    assert "ai" in str(file_path)
    assert "ml" in str(file_path)
    assert "transformers" in str(file_path)
```

**Test Scenario 3: List files by tier**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_repo_list_by_tier(file_repo):
    """🔴 Should list all files in a tier"""
    # Add files to tier-a
    for i in range(3):
        content = ProcessedContent(
            source_url=f"https://example.com/{i}",
            title=f"Article {i}",
            clean_text="Content",
            quality_score=9.0,
            word_count=1,
            processor_version="1.0.0"
        )
        await file_repo.save(content, topic="test")
    
    # List tier-a files
    files = await file_repo.list_by_tier("tier-a")
    
    assert len(files) == 3
    assert all(f.quality_tier == "tier-a" for f in files)
```

**Test Scenario 4: Move file between tiers**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_repo_move_tier(file_repo):
    """🔴 Should move file to different quality tier"""
    content = ProcessedContent(
        source_url="https://example.com",
        title="Test",
        clean_text="Content",
        quality_score=9.0,  # tier-a
        word_count=1,
        processor_version="1.0.0"
    )
    
    file_path = await file_repo.save(content, topic="test")
    assert "tier-a" in str(file_path)
    
    # Move to tier-b
    new_path = await file_repo.move_to_tier(file_path, "tier-b")
    
    assert "tier-b" in str(new_path)
    assert not file_path.exists()
    assert new_path.exists()
```

**Test Scenario 5: Save video with transcript**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_repo_save_video(file_repo):
    """🔴 Should save video file and transcript separately"""
    content = ProcessedContent(
        source_url="https://youtube.com/watch?v=abc",
        content_type=ContentType.VIDEO,
        title="Video Lecture",
        clean_text="Transcript text here",
        quality_score=9.0,
        word_count=100,
        processor_version="1.0.0"
    )
    
    video_data = b"fake video bytes"
    
    file_path = await file_repo.save_video(
        content=content,
        topic="lectures",
        video_bytes=video_data
    )
    
    # Should create .md, .mp4, and .txt files
    assert file_path.exists()
    video_file = file_path.with_suffix(".mp4")
    transcript_file = file_path.with_suffix(".txt")
    
    assert video_file.exists()
    assert transcript_file.exists()
    assert transcript_file.read_text() == "Transcript text here"
```

**Implementation Checklist**:
- [ ] Saves markdown with YAML frontmatter
- [ ] Creates nested directory structure
- [ ] Lists files by tier
- [ ] Moves files between tiers
- [ ] Handles video + transcript
- [ ] Integration test coverage ≥ 80%

---

### Module 2.3: Metadata Repository (PostgreSQL)

**Test File**: `tests/integration/test_metadata_repository.py`

**Setup Fixture**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.repositories.models import Base
from app.repositories.metadata_repository import MetadataRepository

@pytest.fixture(scope="function")
def test_db():
    """Test database with clean schema"""
    engine = create_engine("postgresql://librarian:password@localhost:5432/librarian_test")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # Cleanup
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def metadata_repo(test_db):
    return MetadataRepository(session=test_db)
```

**Test Scenario 1: Save processing record**
```python
@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_metadata_save_processing_record(metadata_repo):
    """🔴 Should save processing record to PostgreSQL"""
    record = ProcessingRecord(
        record_id=uuid4(),
        url="https://example.com",
        status=ProcessingStatus.COMPLETED,
        content_type=ContentType.WEB,
        tokens_used=5000,
        cost=0.01,
        processing_duration=25.5
    )
    
    saved_id = await metadata_repo.save_processing_record(record)
    
    assert saved_id == record.record_id
```

**Test Scenario 2: Query by URL**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_get_by_url(metadata_repo):
    """🔴 Should retrieve processing record by URL"""
    record = ProcessingRecord(
        record_id=uuid4(),
        url="https://example.com/article",
        status=ProcessingStatus.COMPLETED,
        tokens_used=1000,
        cost=0.001
    )
    
    await metadata_repo.save_processing_record(record)
    
    retrieved = await metadata_repo.get_by_url("https://example.com/article")
    
    assert retrieved is not None
    assert retrieved.url == record.url
```

**Test Scenario 3: Get cost statistics**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_cost_statistics(metadata_repo):
    """🔴 Should calculate cost statistics"""
    # Add multiple records
    for i in range(10):
        record = ProcessingRecord(
            record_id=uuid4(),
            url=f"https://example.com/{i}",
            status=ProcessingStatus.COMPLETED,
            tokens_used=1000 * (i + 1),
            cost=0.001 * (i + 1)
        )
        await metadata_repo.save_processing_record(record)
    
    stats = await metadata_repo.get_cost_statistics(days=30)
    
    assert stats["total_cost"] == 0.055  # Sum of 0.001 to 0.010
    assert stats["total_items"] == 10
    assert stats["avg_cost_per_item"] == 0.0055
```

**Test Scenario 4: Update status**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_update_status(metadata_repo):
    """🔴 Should update processing status"""
    record = ProcessingRecord(
        record_id=uuid4(),
        url="https://example.com",
        status=ProcessingStatus.PENDING
    )
    
    await metadata_repo.save_processing_record(record)
    
    # Update to processing
    await metadata_repo.update_status(
        record.record_id,
        ProcessingStatus.PROCESSING
    )
    
    updated = await metadata_repo.get(record.record_id)
    assert updated.status == ProcessingStatus.PROCESSING
```

**SQLAlchemy Models** (`app/repositories/models.py`):
```python
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class ProcessingStatusEnum(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingRecordModel(Base):
    __tablename__ = "processing_records"
    
    record_id = Column(UUID(as_uuid=True), primary_key=True)
    url = Column(String, nullable=False, index=True)
    status = Column(Enum(ProcessingStatusEnum), nullable=False)
    content_type = Column(String)
    tokens_used = Column(Integer)
    cost = Column(Float)
    processing_duration = Column(Float)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**Implementation Checklist**:
- [ ] SQLAlchemy models defined
- [ ] Save/retrieve records
- [ ] Query by URL
- [ ] Cost statistics
- [ ] Status updates
- [ ] Uses REAL PostgreSQL
- [ ] Integration test coverage ≥ 80%

---

## Running Tests

### Unit Tests (Fast)
```bash
# All unit tests
poetry run pytest -m unit

# Specific module
poetry run pytest tests/unit/test_content_source.py -v

# With coverage
poetry run pytest -m unit --cov=app/core
```

### Integration Tests (Real DBs)
```bash
# Start dependencies
docker-compose up -d

# Run integration tests
poetry run pytest -m integration

# Specific repository
poetry run pytest tests/integration/test_chroma_repository.py -v
```

### Watch Mode (TDD)
```bash
# Install pytest-watch
poetry add --dev pytest-watch

# Watch for changes
poetry run ptw -- -m unit
```

---

## Daily TDD Workflow

```bash
# Morning: Pull latest, run all tests
git pull
poetry run pytest

# Development cycle (repeat):
# 1. Write failing test (RED)
nano tests/unit/test_new_feature.py
poetry run pytest tests/unit/test_new_feature.py  # Should FAIL

# 2. Write minimum code (GREEN)
nano app/core/new_feature.py
poetry run pytest tests/unit/test_new_feature.py  # Should PASS

# 3. Refactor (REFACTOR)
nano app/core/new_feature.py  # Improve
poetry run pytest tests/unit/test_new_feature.py  # Still PASS

# 4. Run full test suite
poetry run pytest -m unit

# 5. Commit
git add .
git commit -m "feat: add new_feature with tests"

# End of day: Run all tests including integration
poetry run pytest
git push
```

---

## Continuation

This document covers **Phase 1 and Phase 2 in detail**. 

**Next documents to create**:
1. `tdd-phase3-intelligence.md` - Intelligence layer (ModelRouter, CostOptimizer, LLM Client)
2. `tdd-phase4-pipeline.md` - ETL pipeline (Extractors, Transformers, Loaders)
3. `tdd-phase5-services.md` - Business services
4. `tdd-phase6-ui.md` - Streamlit presentation layer

Each phase follows the same RED-GREEN-REFACTOR cycle with specific test scenarios! 🔴🟢🔄
