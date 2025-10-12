# Testing Guide

## Testing Philosophy

**We do NOT use mocks for integration tests.**  
We use real instances of services to ensure the system works in production conditions.

## Coverage Expectations

- Continuous Integration enforces **90% global coverage** via `pytest --cov=app`.
- When iterating locally on a subset of tests, append `--no-cov` to skip the global gate.
- Before committing or opening a PR, run the full suite with:

    ```bash
    poetry run pytest
    ```

    This command exercises unit + integration suites and refreshes the HTML coverage report under `htmlcov/`.

- Segmented CI lanes can be reproduced locally:

    ```bash
    poetry run pytest -m "unit and not slow"
    poetry run pytest -m "integration and not slow"
    poetry run pytest -m "ui and not slow"
    ```

    Tests inherit their marker automatically from the top-level folder (`tests/unit`, `tests/integration`, `tests/presentation`/`tests/ui`, etc.), so you rarely need to tag them manually.

## Test Pyramid

```
         ┌──────────────┐
         │  E2E Tests   │  10% - Full user workflows
         │   (Real)     │
         └──────────────┘
       ┌────────────────────┐
       │ Integration Tests  │  20% - Services + Real DBs
       │      (Real)        │
       └────────────────────┘
   ┌──────────────────────────┐
   │     Unit Tests           │  70% - Pure logic, isolated
   │   (Isolated, Fast)       │
   └──────────────────────────┘
```

## Test Structure

```
tests/
├── unit/                      # Pure logic tests (no I/O)
│   ├── test_model_router.py
│   ├── test_prompt_builder.py
│   ├── test_domain_models.py
│   └── test_utils.py
│
├── integration/               # Real DB/API tests
│   ├── test_chroma_repository.py
│   ├── test_etl_pipeline.py
│   ├── test_knowledge_graph_builder.py
│   └── test_openai_integration.py
│
├── e2e/                       # Full workflow tests
│   ├── test_content_ingestion.py
│   ├── test_search_flow.py
│   └── test_digest_generation.py
│
├── fixtures/                  # Test data
│   ├── sample_urls.txt
│   ├── sample_content.html
│   └── sample_responses.json
│
└── conftest.py               # Shared fixtures
```

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, no I/O)
    integration: Integration tests (real DBs)
    e2e: End-to-end tests (full workflows)
    ui: Streamlit or UI tests (headless rendering)
    slow: Tests that take > 5 seconds
    requires_api: Tests that call OpenAI API (costs money)
    requires_db: Tests that need database

# Coverage
addopts = 
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
    -v
    --tb=short

# Async support
asyncio_mode = auto

# Timeout
timeout = 300
```

Markers are assigned automatically during collection based on the directory structure (see `tests/conftest.py`), so adding a new test under `tests/unit/` will automatically participate in the unit lane in CI.

### conftest.py (Shared Fixtures)

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4
import chromadb
from chromadb.config import Settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings as AppSettings
from app.core.types import *
from app.repositories.chroma_repository import ChromaRepository
from app.repositories.metadata_repository import MetadataRepository

# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_settings():
    """Test configuration"""
    return AppSettings(
        # OpenAI
        openai_api_key="test-key-will-be-overridden",
        
        # Costs
        monthly_api_budget=10.0,  # Low budget for tests
        
        # Models
        screening_model="gpt-5-nano",
        summarization_model="gpt-5-mini",
        
        # Database
        postgres_url="postgresql://test:test@localhost:5432/librarian_test",
        
        # Paths
        library_root=Path("/tmp/test_library"),
        chroma_persist_dir=Path("/tmp/test_chroma"),
        
        # Features
        enable_web_search=False,  # Too expensive for tests
        enable_kg_building=True,
    )

# ============================================================================
# Database Fixtures (Real Instances)
# ============================================================================

@pytest.fixture(scope="function")
def temp_library_dir():
    """Temporary library directory"""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_library_"))
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
async def chroma_client():
    """Real ChromaDB instance with ephemeral storage"""
    temp_dir = tempfile.mkdtemp(prefix="test_chroma_")
    
    client = chromadb.Client(Settings(
        persist_directory=temp_dir,
        anonymized_telemetry=False
    ))
    
    yield client
    
    # Cleanup
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
async def chroma_repository(chroma_client):
    """Real ChromaRepository"""
    repo = ChromaRepository(client=chroma_client)
    await repo.initialize()
    yield repo

@pytest.fixture(scope="function")
def test_db_engine(test_settings):
    """Real PostgreSQL test database"""
    engine = create_engine(test_settings.postgres_url)
    
    # Create all tables
    from app.repositories.models import Base
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Drop all tables
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Database session for tests"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    
    yield session
    
    session.rollback()
    session.close()

@pytest.fixture(scope="function")
async def metadata_repository(test_db_session):
    """Real MetadataRepository"""
    return MetadataRepository(session=test_db_session)

# ============================================================================
# OpenAI Fixtures (Real API with Budget Control)
# ============================================================================

@pytest.fixture(scope="session")
def openai_test_budget():
    """Budget tracker for OpenAI tests"""
    class BudgetTracker:
        def __init__(self, max_budget: float = 1.0):
            self.max_budget = max_budget
            self.spent = 0.0
            
        def track(self, cost: float):
            self.spent += cost
            if self.spent > self.max_budget:
                raise Exception(f"Test budget exceeded: ${self.spent:.4f} > ${self.max_budget}")
    
    return BudgetTracker()

@pytest.fixture(scope="function")
async def real_openai_client(test_settings, openai_test_budget):
    """Real OpenAI client with budget tracking"""
    from openai import AsyncOpenAI
    
    # This uses REAL API KEY from environment
    client = AsyncOpenAI()
    
    # Wrapper to track costs
    class BudgetedClient:
        def __init__(self, client, tracker):
            self._client = client
            self._tracker = tracker
            
        async def create_completion(self, **kwargs):
            response = await self._client.chat.completions.create(**kwargs)
            
            # Track cost
            cost = self._calculate_cost(response)
            self._tracker.track(cost)
            
            return response
        
        def _calculate_cost(self, response):
            # Calculate actual cost based on usage
            model = response.model
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Cost per 1M tokens (update these values)
            costs = {
                "gpt-5-nano": (0.05, 0.40),
                "gpt-5-mini": (0.25, 2.00),
                "gpt-5": (1.25, 10.00),
            }
            
            input_cost, output_cost = costs.get(model, (0, 0))
            return (input_tokens / 1_000_000 * input_cost + 
                    output_tokens / 1_000_000 * output_cost)
    
    yield BudgetedClient(client, openai_test_budget)

# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_web_url():
    """Sample web URL for testing"""
    return "https://arxiv.org/abs/1706.03762"

@pytest.fixture
def sample_content_source(sample_web_url):
    """Sample ContentSource"""
    return ContentSource(
        url=sample_web_url,
        content_type=ContentType.WEB,
        source_domain="arxiv.org",
        anchor_text="Attention Is All You Need"
    )

@pytest.fixture
def sample_screening_result(sample_web_url):
    """Sample ScreeningResult"""
    return ScreeningResult(
        url=sample_web_url,
        relevance_score=9.5,
        quality_prediction=9.8,
        novelty_score=8.0,
        priority=Priority.HIGH,
        reasoning="Seminal paper on transformer architecture",
        estimated_tokens=5000,
        estimated_cost=0.01,
        roi_score=950.0,
        screened_by_model="gpt-5-nano"
    )

@pytest.fixture
def sample_raw_content(sample_web_url):
    """Sample RawContent"""
    return RawContent(
        source_url=sample_web_url,
        content_type=ContentType.WEB,
        raw_text="The dominant sequence transduction models...",
        title="Attention Is All You Need",
        author="Vaswani et al.",
        extractor_version="1.0.0"
    )

@pytest.fixture
def sample_processed_content(sample_web_url):
    """Sample ProcessedContent"""
    return ProcessedContent(
        source_url=sample_web_url,
        content_type=ContentType.WEB,
        title="Attention Is All You Need",
        clean_text="The dominant sequence transduction models...",
        summary="Introduces the Transformer architecture...",
        key_concepts=["transformer", "attention", "self-attention"],
        entities=["Vaswani", "Google Brain", "Google Research"],
        topics=["deep learning", "nlp", "architecture"],
        quality_score=9.5,
        word_count=8000,
        estimated_reading_time=32,
        processor_version="1.0.0"
    )

# ============================================================================
# Test Helpers
# ============================================================================

class TestHelpers:
    """Helper methods for tests"""
    
    @staticmethod
    async def wait_for_processing(
        record_id: UUID,
        metadata_repo: MetadataRepository,
        timeout: int = 30
    ):
        """Wait for processing to complete"""
        import asyncio
        
        start = asyncio.get_event_loop().time()
        while True:
            record = await metadata_repo.get_processing_record(record_id)
            if record.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                return record
            
            if asyncio.get_event_loop().time() - start > timeout:
                raise TimeoutError("Processing did not complete in time")
            
            await asyncio.sleep(1)
    
    @staticmethod
    def assert_valid_markdown_file(file_path: Path):
        """Assert file is valid markdown"""
        assert file_path.exists(), f"File not found: {file_path}"
        assert file_path.suffix == ".md", f"Not a markdown file: {file_path}"
        
        content = file_path.read_text()
        assert len(content) > 0, "Empty file"
        assert "# " in content, "No heading found"

@pytest.fixture
def test_helpers():
    return TestHelpers()
```

## Unit Tests (Fast, Isolated)

### pipeline/test_pdf_extractor.py

- Validates the async `PDFDocumentExtractor` without real network calls by stubbing `PdfReader` and the HTTP client.
- Confirms metadata normalization, including filename fallbacks when the PDF lacks a title.
- Verifies that extraction fails fast when no text can be recovered from any page.

### pipeline/test_pipeline_cli.py

- Covers CLI utilities, including JSON formatting and the new PDF-aware pipeline selection helper.
- Ensures errors produce URL-scoped log messages, keeping failure output actionable.

### test_model_router.py

```python
import pytest
from app.intelligence.model_router import ModelRouter, TaskComplexity
from app.core.types import ModelConfig

class TestModelRouter:
    """Test model selection logic"""
    
    @pytest.fixture
    def router(self):
        return ModelRouter()
    
    def test_low_complexity_uses_nano(self, router):
        """Low complexity tasks should use gpt-5-nano"""
        model = router.select_model(TaskComplexity.LOW)
        assert model.name == "gpt-5-nano"
        assert model.cost_per_1m_input == 0.05
    
    def test_medium_complexity_uses_mini(self, router):
        """Medium complexity tasks should use gpt-5-mini"""
        model = router.select_model(TaskComplexity.MEDIUM)
        assert model.name == "gpt-5-mini"
        assert model.cost_per_1m_input == 0.25
    
    def test_high_complexity_uses_standard(self, router):
        """High complexity tasks should use gpt-5"""
        model = router.select_model(TaskComplexity.HIGH)
        assert model.name == "gpt-5"
        assert model.cost_per_1m_input == 1.25
    
    @pytest.mark.parametrize("complexity,expected_name,max_cost", [
        (TaskComplexity.LOW, "gpt-5-nano", 0.05),
        (TaskComplexity.MEDIUM, "gpt-5-mini", 0.25),
        (TaskComplexity.HIGH, "gpt-5", 1.25),
    ])
    def test_all_complexities(self, router, complexity, expected_name, max_cost):
        """Test all complexity levels"""
        model = router.select_model(complexity)
        assert model.name == expected_name
        assert model.cost_per_1m_input <= max_cost

class TestCostCalculation:
    """Test cost calculation logic"""
    
    def test_calculate_cost_gpt5_nano(self):
        """Test cost calculation for gpt-5-nano"""
        from app.intelligence.cost_optimizer import CostCalculator
        
        calculator = CostCalculator()
        cost = calculator.calculate(
            model="gpt-5-nano",
            input_tokens=10000,
            output_tokens=1000
        )
        
        # 10k input = 0.01M * $0.05 = $0.0005
        # 1k output = 0.001M * $0.40 = $0.0004
        expected = 0.0005 + 0.0004
        assert abs(cost - expected) < 0.0001
```

### test_domain_models.py

```python
import pytest
from pydantic import ValidationError
from app.core.types import ScreeningResult, Priority

class TestScreeningResult:
    """Test ScreeningResult validation"""
    
    def test_valid_screening_result(self, sample_web_url):
        """Valid screening result should pass validation"""
        result = ScreeningResult(
            url=sample_web_url,
            relevance_score=8.5,
            quality_prediction=9.0,
            novelty_score=7.5,
            priority=Priority.HIGH,
            reasoning="Excellent paper on transformers",
            estimated_tokens=5000,
            estimated_cost=0.01,
            roi_score=850.0,
            screened_by_model="gpt-5-nano"
        )
        
        assert result.should_process is True
        assert result.average_score == 8.333333333333334
    
    def test_score_out_of_range_fails(self, sample_web_url):
        """Score > 10 should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                url=sample_web_url,
                relevance_score=11.0,  # Invalid!
                quality_prediction=9.0,
                novelty_score=7.5,
                priority=Priority.HIGH,
                reasoning="Test",
                estimated_tokens=5000,
                estimated_cost=0.01,
                roi_score=850.0,
                screened_by_model="gpt-5-nano"
            )
        
        assert "relevance_score" in str(exc_info.value)
    
    def test_should_process_logic(self, sample_web_url):
        """Test should_process property"""
        # HIGH priority should process
        result_high = ScreeningResult(
            url=sample_web_url,
            relevance_score=9.0,
            quality_prediction=9.0,
            novelty_score=8.0,
            priority=Priority.HIGH,
            reasoning="Test",
            estimated_tokens=5000,
            estimated_cost=0.01,
            roi_score=900.0,
            screened_by_model="gpt-5-nano"
        )
        assert result_high.should_process is True
        
        # SKIP priority should not process
        result_skip = ScreeningResult(
            url=sample_web_url,
            relevance_score=3.0,
            quality_prediction=2.0,
            novelty_score=1.0,
            priority=Priority.SKIP,
            reasoning="Low quality",
            estimated_tokens=5000,
            estimated_cost=0.01,
            roi_score=20.0,
            screened_by_model="gpt-5-nano"
        )
        assert result_skip.should_process is False
```

## Integration Tests (Real Services)

### pipeline/test_pdf_pipeline.py

- Runs the `ContentPipeline` with the PDF extractor, basic transformer, and a capturing loader to emulate production ingest.
- Asserts the resulting `LibraryFile` preserves extracted text and metadata, giving confidence in real PDF workflows.

### pipeline/test_pdf_cli.py

- Executes the CLI end-to-end for PDF URLs by patching network/storage edges, verifying JSON output and tier assignment.
- Confirms the default pipeline builder routes to the PDF extractor when the URL targets a document.

### test_chroma_repository.py

```python
import pytest
from app.repositories.chroma_repository import ChromaRepository

@pytest.mark.integration
@pytest.mark.requires_db
class TestChromaRepository:
    """Test ChromaDB repository with real database"""
    
    @pytest.mark.asyncio
    async def test_add_and_retrieve_document(
        self,
        chroma_repository,
        sample_processed_content
    ):
        """Should add document and retrieve it"""
        # Add document
        doc_id = await chroma_repository.add_document(
            content=sample_processed_content.clean_text,
            metadata={
                "url": str(sample_processed_content.source_url),
                "title": sample_processed_content.title,
                "quality_score": sample_processed_content.quality_score
            }
        )
        
        assert doc_id is not None
        
        # Retrieve by semantic search
        results = await chroma_repository.search(
            query="transformer architecture",
            k=1
        )
        
        assert len(results) == 1
        assert results[0]["metadata"]["title"] == sample_processed_content.title
    
    @pytest.mark.asyncio
    async def test_semantic_search_ranking(self, chroma_repository):
        """Should rank results by semantic similarity"""
        # Add multiple documents
        docs = [
            ("Transformers are neural network architectures", {"topic": "architecture"}),
            ("Attention mechanisms in deep learning", {"topic": "attention"}),
            ("Python programming basics", {"topic": "programming"}),
        ]
        
        for content, metadata in docs:
            await chroma_repository.add_document(content, metadata)
        
        # Search for transformer-related content
        results = await chroma_repository.search(
            query="transformer neural networks",
            k=3
        )
        
        # Most relevant should be first
        assert "Transformers" in results[0]["document"]
        assert results[0]["metadata"]["topic"] == "architecture"
```

### test_openai_integration.py

```python
import pytest
from app.intelligence.llm_client import LLMClient

@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.slow
class TestOpenAIIntegration:
    """Test real OpenAI API calls with budget control"""
    
    @pytest.mark.asyncio
    async def test_screen_url_with_real_api(
        self,
        real_openai_client,
        sample_web_url,
        test_settings
    ):
        """Should screen URL using real API"""
        from app.services.curation_service import CurationService
        from app.intelligence.model_router import ModelRouter
        
        router = ModelRouter()
        service = CurationService(
            llm_client=real_openai_client,
            model_router=router,
            settings=test_settings
        )
        
        result = await service.screen_url(sample_web_url)
        
        # Verify result structure
        assert result.url == sample_web_url
        assert 0 <= result.relevance_score <= 10
        assert 0 <= result.quality_prediction <= 10
        assert result.priority in [p.value for p in Priority]
        assert len(result.reasoning) > 10
        
        # Verify cost tracking
        assert result.estimated_cost > 0
    
    @pytest.mark.asyncio
    async def test_summarize_content_with_real_api(
        self,
        real_openai_client,
        sample_raw_content
    ):
        """Should summarize content using real API"""
        from app.pipeline.transformers.content_transformer import ContentTransformer
        
        transformer = ContentTransformer(llm_client=real_openai_client)
        
        summary = await transformer.summarize(
            content=sample_raw_content.raw_text[:2000],  # Limit to reduce cost
            max_length=200
        )
        
        assert len(summary) > 0
        assert len(summary) < len(sample_raw_content.raw_text)
        assert isinstance(summary, str)
```

## E2E Tests (Full Workflows)

### test_content_ingestion.py

```python
import pytest
from pathlib import Path

@pytest.mark.e2e
@pytest.mark.requires_api
@pytest.mark.requires_db
@pytest.mark.slow
class TestContentIngestion:
    """Test full content ingestion workflow"""
    
    @pytest.mark.asyncio
    async def test_full_ingestion_workflow(
        self,
        sample_web_url,
        chroma_repository,
        metadata_repository,
        temp_library_dir,
        real_openai_client,
        test_helpers
    ):
        """Test complete flow from URL to library file"""
        from app.services.curation_service import CurationService
        from app.pipeline.etl import ETLPipeline
        from app.intelligence.model_router import ModelRouter
        
        # Setup services
        router = ModelRouter()
        curation_service = CurationService(
            llm_client=real_openai_client,
            model_router=router
        )
        
        etl_pipeline = ETLPipeline(
            chroma_repo=chroma_repository,
            metadata_repo=metadata_repository,
            library_root=temp_library_dir
        )
        
        # 1. Screen URL
        screening = await curation_service.screen_url(sample_web_url)
        assert screening.should_process
        
        # 2. Process content
        source = ContentSource(
            url=sample_web_url,
            content_type=ContentType.WEB,
            source_domain="arxiv.org"
        )
        
        library_file = await etl_pipeline.process(source)
        
        # 3. Verify file created
        assert library_file.file_path.exists()
        test_helpers.assert_valid_markdown_file(library_file.file_path)
        
        # 4. Verify in ChromaDB
        results = await chroma_repository.search(
            query=library_file.title,
            k=1
        )
        assert len(results) > 0
        
        # 5. Verify metadata
        record = await metadata_repository.get_latest_processing_record(sample_web_url)
        assert record.status == ProcessingStatus.COMPLETED
        assert record.cost > 0
```

## Property-Based Testing

```python
from hypothesis import given, strategies as st
import pytest

class TestContentTransformer:
    """Property-based tests for content transformation"""
    
    @given(st.text(min_size=100, max_size=10000))
    def test_summary_always_shorter(self, content):
        """Summary should always be shorter than original"""
        from app.pipeline.transformers.content_transformer import ContentTransformer
        
        transformer = ContentTransformer()
        summary = transformer.extract_summary(content)
        
        assert len(summary) < len(content)
        assert len(summary) > 0
    
    @given(st.text(min_size=1000, max_size=100000))
    def test_chunking_preserves_content(self, content):
        """Chunking should preserve all content"""
        from app.pipeline.transformers.chunker import TextChunker
        
        chunker = TextChunker(chunk_size=500, overlap=50)
        chunks = chunker.chunk(content)
        
        # Reconstruct text from chunks (accounting for overlap)
        reconstructed = chunks[0]
        for chunk in chunks[1:]:
            # Remove overlap
            reconstructed += chunk[50:]
        
        # Should be very similar (accounting for whitespace)
        assert len(reconstructed) >= len(content) * 0.95
```

## Performance Tests

```python
import pytest
import time

@pytest.mark.slow
class TestPerformance:
    """Performance benchmarks"""
    
    @pytest.mark.asyncio
    async def test_screening_latency(self, curation_service, sample_web_url):
        """URL screening should complete in < 5 seconds"""
        start = time.time()
        
        result = await curation_service.screen_url(sample_web_url)
        
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Screening took {elapsed}s (should be < 5s)"
    
    @pytest.mark.asyncio
    async def test_search_latency(self, chroma_repository):
        """Search should complete in < 500ms"""
        # Add some documents first
        for i in range(100):
            await chroma_repository.add_document(
                content=f"Test document {i}",
                metadata={"index": i}
            )
        
        start = time.time()
        results = await chroma_repository.search("test", k=10)
        elapsed = time.time() - start
        
        assert elapsed < 0.5, f"Search took {elapsed}s (should be < 0.5s)"
```

## Running Tests

### Run all tests
```bash
poetry run pytest
```

### Run only unit tests (fast)
```bash
poetry run pytest -m unit
```

### Run integration tests
```bash
poetry run pytest -m integration
```

### Run without API calls (free)
```bash
poetry run pytest -m "not requires_api"
```

### Run with coverage
```bash
poetry run pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
poetry run pytest tests/unit/test_model_router.py -v
```

## Coverage Goals

- **Overall**: ≥ 90%
- **Unit tests**: ≥ 95%
- **Integration tests**: ≥ 80%
- **Critical paths**: 100%

## CI/CD Integration

Tests run automatically on:
- Every pull request
- Every push to main
- Nightly (full suite with API tests)

Budget controls prevent excessive API costs in CI.
