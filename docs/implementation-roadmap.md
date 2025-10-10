# Implementation Roadmap

## Overview

This document outlines the complete implementation plan for the Williams Framework AI Librarian, following **strict TDD principles** (Red-Green-Refactor cycle).

## TDD Workflow

Every module follows this cycle:

```
1. RED    → Write failing test
2. GREEN  → Write minimum code to pass
3. REFACTOR → Improve code quality
4. REPEAT → Next feature
```

## Implementation Principles

1. **Test First, Always**: No production code without a failing test
2. **Incremental Development**: One small feature at a time
3. **Real Dependencies**: Integration tests use real databases (no mocks)
4. **Continuous Validation**: Run tests after every change
5. **Documentation Alongside**: Update docs as we build

## Phase Overview

```
Phase 0: Project Setup (1-2 days)
    ├── Environment setup
    ├── Dependency management
    └── CI/CD pipeline

Phase 1: Foundation (3-4 days)
    ├── Core types and models
    ├── Configuration system
    └── Logging infrastructure

Phase 2: Data Layer (4-5 days)
    ├── Repository interfaces
    ├── ChromaDB repository
    ├── File system repository
    └── Metadata repository (PostgreSQL)

Phase 3: Intelligence Layer (4-5 days)
    ├── Model router
    ├── Cost optimizer
    ├── LLM client wrapper
    └── Prompt builder

Phase 4: ETL Pipeline (5-7 days)
    ├── Web extractor
    ├── YouTube extractor
    ├── Content transformer
    ├── Loaders (ChromaDB + File)
    └── Knowledge graph builder

Phase 5: Services (4-5 days)
    ├── Curation service
    ├── Digest service
    ├── Search service
    └── Librarian service

Phase 6: Presentation (3-4 days)
    ├── Streamlit UI setup
    ├── Digest page
    ├── Library page
    ├── Search page
    └── Settings page

Phase 7: Workers (2-3 days)
    ├── Digest worker
    ├── Ingestion worker
    └── Maintenance worker

Phase 8: Plugin System (2-3 days)
    ├── Plugin interfaces
    ├── Plugin manager
    └── Example plugins

Phase 9: Production Ready (2-3 days)
    ├── Performance optimization
    ├── Security hardening
    ├── Deployment automation
    └── Monitoring setup
```

**Total Estimated Time**: 30-40 days of focused development

---

## Phase 0: Project Setup

### Objectives
- Create development environment
- Set up dependency management
- Configure testing infrastructure
- Set up CI/CD

### Tasks

#### 0.1 Initialize Project Structure
```bash
# Create directory structure
mkdir -p app/{core,repositories,services,intelligence,pipeline,presentation,workers,plugins}
mkdir -p tests/{unit,integration,e2e,fixtures}
mkdir -p config/{prompts}
mkdir -p scripts
mkdir -p library/{tier-a,tier-b,tier-c,tier-d}
mkdir -p data/{chroma,logs,cache}
```

#### 0.2 Create pyproject.toml
```toml
[tool.poetry]
name = "williams-librarian"
version = "0.1.0"
description = "Personal AI Research Assistant for the Williams Framework"

[tool.poetry.dependencies]
python = "^3.11"
# Core
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
# Database
sqlalchemy = "^2.0.0"
asyncpg = "^0.29.0"
redis = "^5.0.0"
chromadb = "^0.4.0"
# AI/ML
openai = "^1.3.0"
langchain = "^0.1.0"
langchain-openai = "^0.0.2"
spacy = "^3.7.0"
networkx = "^3.2.0"
# ETL
httpx = "^0.27.0"
trafilatura = "^1.6.0"
yt-dlp = "^2024.3.0"
pypdf = "^4.0.0"
beautifulsoup4 = "^4.12.0"
# UI
streamlit = "^1.30.0"
plotly = "^5.18.0"
pyvis = "^0.3.2"
# Utilities
python-dotenv = "^1.0.0"
tenacity = "^8.2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
hypothesis = "^6.92.0"
mypy = "^1.7.0"
ruff = "^0.1.0"
black = "^23.12.0"
pre-commit = "^3.6.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

#### 0.3 Create pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, no I/O)
    integration: Integration tests (real DBs)
    e2e: End-to-end tests (full workflows)
    slow: Tests that take > 5 seconds
    requires_api: Tests that call OpenAI API
    requires_db: Tests that need database

addopts = 
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
    -v
    --tb=short

asyncio_mode = auto
timeout = 300
```

#### 0.4 Create .env.example
```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_ORG_ID=org-...

# Models
SCREENING_MODEL=gpt-5-nano
SUMMARIZATION_MODEL=gpt-5-mini
ANALYSIS_MODEL=gpt-5

# Costs
MONTHLY_API_BUDGET=100.0

# Database
POSTGRES_URL=postgresql://librarian:password@localhost:5432/librarian
REDIS_URL=redis://localhost:6379/0

# Paths
LIBRARY_ROOT=./library
CHROMA_PERSIST_DIR=./data/chroma

# Features
ENABLE_WEB_SEARCH=false
ENABLE_FILE_SEARCH=true
ENABLE_KG_BUILDING=true

# Logging
LOG_LEVEL=INFO
```

#### 0.5 Create docker-compose.yml (Development)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: librarian
      POSTGRES_USER: librarian
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### 0.6 Setup CI/CD
**.github/workflows/ci.yml**:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: librarian_test
          POSTGRES_USER: librarian
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Install dependencies
        run: poetry install
      
      - name: Run unit tests
        run: poetry run pytest -m unit
      
      - name: Run integration tests
        env:
          POSTGRES_URL: postgresql://librarian:password@localhost:5432/librarian_test
          REDIS_URL: redis://localhost:6379/0
        run: poetry run pytest -m integration
      
      - name: Type checking
        run: poetry run mypy app/
      
      - name: Linting
        run: poetry run ruff check app/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Validation Checklist
- [ ] Poetry successfully installs all dependencies
- [ ] Docker Compose starts PostgreSQL and Redis
- [ ] pytest runs without errors (no tests yet)
- [ ] CI pipeline executes successfully
- [ ] Project structure matches specification

---

## Phase 1: Foundation Layer

### Objectives
- Define core domain models with Pydantic
- Implement configuration system
- Set up logging infrastructure
- Create custom exceptions

### Module 1.1: Core Types (Pydantic Models)

**Priority**: HIGHEST (everything depends on this)

#### TDD Cycle 1: ContentSource Model

**RED** - Write test first:
```python
# tests/unit/test_domain_models.py
import pytest
from datetime import datetime
from pydantic import ValidationError
from app.core.types import ContentSource, ContentType

def test_content_source_valid():
    """Valid ContentSource should pass validation"""
    source = ContentSource(
        url="https://example.com/article",
        content_type=ContentType.WEB,
        source_domain="example.com"
    )
    
    assert source.url == "https://example.com/article"
    assert source.content_type == ContentType.WEB
    assert source.source_domain == "example.com"
    assert isinstance(source.discovered_at, datetime)

def test_content_source_invalid_url():
    """Invalid URL should fail validation"""
    with pytest.raises(ValidationError) as exc_info:
        ContentSource(
            url="not-a-url",
            content_type=ContentType.WEB
        )
    assert "url" in str(exc_info.value).lower()
```

**GREEN** - Implement minimum code:
```python
# app/core/types.py
from pydantic import BaseModel, HttpUrl, Field, validator
from datetime import datetime
from enum import Enum
from typing import Optional

class ContentType(str, Enum):
    WEB = "web"
    VIDEO = "video"
    PDF = "pdf"
    SOCIAL_MEDIA = "social_media"
    DOCUMENT = "document"

class ContentSource(BaseModel):
    url: HttpUrl
    content_type: ContentType
    source_domain: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.now)
    
    @validator('source_domain', always=True)
    def extract_domain(cls, v, values):
        if v is None and 'url' in values:
            from urllib.parse import urlparse
            return urlparse(str(values['url'])).netloc
        return v
```

**REFACTOR** - Run tests, ensure they pass, improve code quality

#### TDD Cycle 2-10: Remaining Domain Models

Repeat RED-GREEN-REFACTOR for:
- ScreeningResult
- RawContent
- ProcessedContent
- LibraryFile
- KnowledgeGraphNode
- Relationship
- DigestItem
- MaintenanceTask
- ProcessingRecord

**Test Coverage Goals**:
- Property validation (scores 0-10, required fields)
- Computed properties (should_process, average_score, is_complete)
- Edge cases (empty strings, None values, out-of-range numbers)
- Business logic (quality tier determination, priority calculation)

### Module 1.2: Configuration System

#### TDD Cycle: Settings Class

**RED**:
```python
# tests/unit/test_config.py
import pytest
from pathlib import Path
from app.core.config import Settings

def test_settings_from_env(monkeypatch):
    """Settings should load from environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("MONTHLY_API_BUDGET", "50.0")
    
    settings = Settings()
    
    assert settings.openai_api_key == "sk-test-123"
    assert settings.monthly_api_budget == 50.0

def test_settings_defaults():
    """Settings should have sensible defaults"""
    settings = Settings(openai_api_key="sk-test")
    
    assert settings.screening_model == "gpt-5-nano"
    assert settings.summarization_model == "gpt-5-mini"
    assert settings.enable_web_search is False
    assert settings.enable_file_search is True
```

**GREEN**:
```python
# app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_org_id: Optional[str] = None
    
    # Models
    screening_model: str = "gpt-5-nano"
    summarization_model: str = "gpt-5-mini"
    analysis_model: str = "gpt-5"
    
    # Costs
    monthly_api_budget: float = 100.0
    
    # Database
    postgres_url: str = "postgresql://librarian:password@localhost:5432/librarian"
    redis_url: str = "redis://localhost:6379/0"
    
    # Paths
    library_root: Path = Path("./library")
    chroma_persist_dir: Path = Path("./data/chroma")
    
    # Features
    enable_web_search: bool = False
    enable_file_search: bool = True
    enable_kg_building: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Module 1.3: Exceptions

#### TDD Cycle: Custom Exceptions

**RED**:
```python
# tests/unit/test_exceptions.py
import pytest
from app.core.exceptions import (
    LibrarianException,
    ExtractionError,
    BudgetExceededError
)

def test_extraction_error_inherits_from_base():
    """Custom exceptions should inherit from base"""
    error = ExtractionError("Failed to extract")
    assert isinstance(error, LibrarianException)
    assert str(error) == "Failed to extract"

def test_budget_exceeded_with_context():
    """BudgetExceededError should carry context"""
    error = BudgetExceededError("Budget exceeded", spent=105.0, limit=100.0)
    assert error.spent == 105.0
    assert error.limit == 100.0
```

**GREEN**:
```python
# app/core/exceptions.py
class LibrarianException(Exception):
    """Base exception for all librarian errors"""
    pass

class ExtractionError(LibrarianException):
    """Content extraction failed"""
    pass

class BudgetExceededError(LibrarianException):
    """API budget exceeded"""
    def __init__(self, message: str, spent: float, limit: float):
        super().__init__(message)
        self.spent = spent
        self.limit = limit

class PluginError(LibrarianException):
    """Plugin operation failed"""
    pass

class ValidationError(LibrarianException):
    """Data validation failed"""
    pass
```

### Validation Checklist - Phase 1
- [ ] All 10 domain models implemented with tests
- [ ] Settings class loads from .env correctly
- [ ] All custom exceptions defined
- [ ] Unit test coverage ≥ 95%
- [ ] Type checking passes (mypy)
- [ ] No linting errors (ruff)

---

## Phase 2: Data Layer

### Objectives
- Implement repository pattern
- Create ChromaDB repository with real tests
- Create file system repository
- Create PostgreSQL metadata repository
- Implement caching layer

### Module 2.1: Repository Base Interface

#### TDD Cycle: Base Repository

**RED**:
```python
# tests/unit/test_base_repository.py
import pytest
from abc import ABC
from uuid import UUID
from app.repositories.base import BaseRepository

def test_base_repository_is_abstract():
    """BaseRepository should be abstract"""
    with pytest.raises(TypeError):
        BaseRepository()

def test_repository_interface_methods():
    """Repository should define required methods"""
    assert hasattr(BaseRepository, 'get')
    assert hasattr(BaseRepository, 'save')
    assert hasattr(BaseRepository, 'delete')
```

**GREEN**:
```python
# app/repositories/base.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional
from uuid import UUID

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository interface"""
    
    @abstractmethod
    async def get(self, id: UUID) -> Optional[T]:
        """Retrieve entity by ID"""
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> UUID:
        """Save entity and return ID"""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List all entities with pagination"""
        pass
```

### Module 2.2: ChromaDB Repository

**CRITICAL**: This uses REAL ChromaDB (no mocks)

#### TDD Cycle 1: Initialize ChromaDB

**RED**:
```python
# tests/integration/test_chroma_repository.py
import pytest
import tempfile
import shutil
from pathlib import Path
from app.repositories.chroma_repository import ChromaRepository

@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_chroma_repository_initialization():
    """Should initialize ChromaDB with ephemeral storage"""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        repo = ChromaRepository(persist_directory=temp_dir)
        await repo.initialize()
        
        assert repo.client is not None
        assert repo.collection is not None
    finally:
        shutil.rmtree(temp_dir)
```

**GREEN**:
```python
# app/repositories/chroma_repository.py
import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

class ChromaRepository:
    def __init__(self, persist_directory: Path):
        self.persist_directory = persist_directory
        self.client: Optional[chromadb.Client] = None
        self.collection = None
    
    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.Client(ChromaSettings(
            persist_directory=str(self.persist_directory),
            anonymized_telemetry=False
        ))
        
        self.collection = self.client.get_or_create_collection(
            name="library_content",
            metadata={"description": "Williams Framework library content"}
        )
```

#### TDD Cycle 2: Add Document

**RED**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_document(chroma_repository):
    """Should add document and return ID"""
    doc_id = await chroma_repository.add_document(
        content="Transformers are neural network architectures.",
        metadata={"title": "Attention Is All You Need", "quality": 9.5}
    )
    
    assert doc_id is not None
    assert isinstance(doc_id, str)
```

**GREEN**:
```python
async def add_document(
    self,
    content: str,
    metadata: Dict[str, Any],
    doc_id: Optional[str] = None
) -> str:
    """Add document to ChromaDB"""
    if doc_id is None:
        doc_id = str(uuid4())
    
    self.collection.add(
        documents=[content],
        metadatas=[metadata],
        ids=[doc_id]
    )
    
    return doc_id
```

#### TDD Cycle 3: Semantic Search

**RED**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_semantic_search(chroma_repository):
    """Should search by semantic similarity"""
    # Add test documents
    await chroma_repository.add_document(
        "Transformers use self-attention mechanisms",
        {"topic": "architecture"}
    )
    await chroma_repository.add_document(
        "Python is a programming language",
        {"topic": "programming"}
    )
    
    # Search
    results = await chroma_repository.search(
        query="neural network architecture",
        k=1
    )
    
    assert len(results) == 1
    assert "Transformers" in results[0]["document"]
```

**GREEN**:
```python
async def search(
    self,
    query: str,
    k: int = 10,
    filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Semantic search"""
    results = self.collection.query(
        query_texts=[query],
        n_results=k,
        where=filter
    )
    
    return [
        {
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        }
        for i in range(len(results["ids"][0]))
    ]
```

### Module 2.3: File Repository

#### TDD Cycles: File Operations
- Create directory structure
- Save markdown file
- Read file content
- List files by quality tier
- Move files between tiers

### Module 2.4: Metadata Repository (PostgreSQL)

#### TDD Cycles:
- Define SQLAlchemy models
- Save processing record
- Query by URL
- Update status
- Get cost statistics

### Validation Checklist - Phase 2
- [ ] ChromaDB repository with real tests
- [ ] File repository with actual file I/O
- [ ] PostgreSQL repository with real DB
- [ ] Integration test coverage ≥ 80%
- [ ] All repositories follow base interface
- [ ] No mocks used in integration tests

---

## Phase 3: Intelligence Layer

### Module 3.1: Model Router
- Test complexity → model mapping
- Test cost calculation for each model
- Test model fallback logic

### Module 3.2: Cost Optimizer
- Test cost tracking
- Test budget enforcement
- Test cache hit rate calculation

### Module 3.3: LLM Client
- Test OpenAI API wrapper (with real API, budget controlled)
- Test retry logic
- Test error handling

### Module 3.4: Prompt Builder
- Test template loading
- Test variable substitution
- Test prompt caching strategy

---

## Phase 4: ETL Pipeline

### Module 4.1: Web Extractor
### Module 4.2: YouTube Extractor
### Module 4.3: Content Transformer
### Module 4.4: Loaders
### Module 4.5: Knowledge Graph Builder

---

## Phase 5-9: Services, UI, Workers, Plugins, Production

*(Detailed TDD cycles documented in separate implementation plan)*

---

## Success Metrics

### Test Coverage
- Overall: ≥ 90%
- Unit tests: ≥ 95%
- Integration tests: ≥ 80%
- Critical paths: 100%

### Code Quality
- No type errors (mypy strict mode)
- No linting errors (ruff)
- Cyclomatic complexity < 10
- Function length < 50 lines

### Performance
- URL screening: < 2 seconds
- Content processing: < 30 seconds
- Search queries: < 500ms (p95)

### Cost Efficiency
- Average cost per article: < $0.01
- Monthly baseline: < $1.00
- Cache hit rate: > 40%

---

## Risk Mitigation

### Technical Risks
1. **OpenAI API costs during testing**
   - Mitigation: Budget tracker in test fixtures, mock for unit tests
   
2. **ChromaDB performance with large datasets**
   - Mitigation: Benchmark tests, pagination, collection splitting

3. **Async complexity**
   - Mitigation: Comprehensive async tests, timeout handling

### Process Risks
1. **Scope creep**
   - Mitigation: Strict phase boundaries, MVP-first approach
   
2. **Test maintenance burden**
   - Mitigation: DRY fixtures, test helpers, clear test structure

---

## Next Steps

1. Review and approve this roadmap
2. Create detailed TDD implementation plan for Phase 1
3. Set up development environment (Phase 0)
4. Begin Phase 1, Module 1.1 (ContentSource model)
5. Follow RED-GREEN-REFACTOR religiously

**Remember**: No production code without a failing test first! 🔴 → 🟢 → 🔄
