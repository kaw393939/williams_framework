# Project Structure

## Directory Overview

```
williams-librarian/
├── app/                           # Main application code
│   ├── __init__.py
│   ├── core/                      # Core utilities and configuration
│   │   ├── __init__.py
│   │   ├── config.py              # Settings and configuration
│   │   ├── types.py               # Domain models (Pydantic)
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── logging.py             # Logging configuration
│   │   └── utils.py               # Utility functions
│   │
│   ├── repositories/              # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py                # Base repository interface
│   │   ├── chroma_repository.py   # ChromaDB operations
│   │   ├── file_repository.py     # File system operations
│   │   ├── metadata_repository.py # PostgreSQL metadata
│   │   ├── cache_repository.py    # Redis cache
│   │   └── models.py              # SQLAlchemy models
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── digest_service.py      # Daily digest generation
│   │   ├── curation_service.py    # Content screening/curation
│   │   ├── librarian_service.py   # Library maintenance
│   │   └── search_service.py      # Search and retrieval
│   │
│   ├── intelligence/              # LLM orchestration layer
│   │   ├── __init__.py
│   │   ├── model_router.py        # Task → Model mapping
│   │   ├── prompt_builder.py      # Prompt templates
│   │   ├── cost_optimizer.py      # Cost tracking/optimization
│   │   ├── llm_client.py          # OpenAI client wrapper
│   │   └── langchain_integration.py # LangChain setup
│   │
│   ├── pipeline/                  # ETL pipeline
│   │   ├── __init__.py
│   │   ├── cli.py                 # Command-line entry point
│   │   ├── etl.py                 # Pipeline orchestrator
│   │   ├── extractors/            # Content extractors
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── html.py            # HTML web extractor
│   │   ├── transformers/          # Content transformers
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── basic.py           # Heuristic summariser/tagger
│   │   └── loaders/               # Data loaders
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── library.py         # Persist to library + vector store
│   │
│   ├── presentation/              # UI layer (Streamlit)
│   │   ├── __init__.py
│   │   ├── app.py                 # Main Streamlit app
│   │   ├── pages/                 # Streamlit pages
│   │   │   ├── __init__.py
│   │   │   ├── 1_digest.py        # Daily digest view
│   │   │   ├── 2_library.py       # Browse library
│   │   │   ├── 3_search.py        # Search interface
│   │   │   ├── 4_add_content.py   # Add new content
│   │   │   ├── 5_knowledge_graph.py # Graph visualization
│   │   │   └── 6_settings.py      # Configuration
│   │   ├── components/            # Reusable UI components
│   │   │   ├── __init__.py
│   │   │   ├── content_card.py
│   │   │   ├── quality_badge.py
│   │   │   └── cost_meter.py
│   │   └── utils.py               # UI utilities
│   │
│   ├── workers/                   # Background jobs
│   │   ├── __init__.py
│   │   ├── digest_worker.py       # Generate daily digest
│   │   ├── maintenance_worker.py  # Library maintenance
│   │   └── ingestion_worker.py    # Process content queue
│   │
│   └── plugins/                   # Plugin system
│       ├── __init__.py
│       ├── base.py                # Plugin interfaces
│       ├── manager.py             # Plugin manager
│       └── registry.py            # Plugin registry
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── fixtures/                  # Test data
│   │   ├── sample_urls.txt
│   │   ├── sample_content.html
│   │   └── sample_responses.json
│   ├── unit/                      # Unit tests
│   │   ├── __init__.py
│   │   ├── test_model_router.py
│   │   ├── test_prompt_builder.py
│   │   ├── test_domain_models.py
│   │   └── test_cost_optimizer.py
│   ├── integration/               # Integration tests
│   │   ├── __init__.py
│   │   ├── test_chroma_repository.py
│   │   ├── test_etl_pipeline.py
│   │   └── test_openai_integration.py
│   └── e2e/                       # End-to-end tests
│       ├── __init__.py
│       ├── test_content_ingestion.py
│       └── test_search_flow.py
│
├── docs/                          # Documentation
│   ├── architecture.md
│   ├── domain-model.md
│   ├── cost-optimization.md
│   ├── testing-guide.md
│   ├── plugin-development.md
│   ├── project-structure.md       # This file
│   └── deployment.md
│
├── config/                        # Configuration files
│   ├── settings.yaml              # Default settings
│   ├── plugins.yaml               # Plugin configuration
│   └── prompts/                   # Prompt templates
│       ├── screening.txt
│       ├── summarization.txt
│       └── digest.txt
│
├── scripts/                       # Utility scripts
│   ├── init_db.py                 # Initialize databases
│   ├── import_bookmarks.py        # Import browser bookmarks
│   ├── export_library.py          # Export library data
│   └── run_maintenance.py         # Manual maintenance tasks
│
├── library/                       # Content storage (gitignored)
│   ├── tier-a/                    # Quality tier A (9.0+)
│   ├── tier-b/                    # Quality tier B (7.0-8.9)
│   ├── tier-c/                    # Quality tier C (5.0-6.9)
│   └── tier-d/                    # Quality tier D (<5.0)
│
├── data/                          # Runtime data (gitignored)
│   ├── chroma/                    # ChromaDB persistence
│   ├── cache/                     # File cache
│   └── logs/                      # Application logs
│
├── .github/                       # GitHub configuration
│   └── workflows/
│       ├── ci.yml                 # CI pipeline
│       └── release.yml            # Release automation
│
├── docker/                        # Docker configurations
│   ├── Dockerfile                 # Production image
│   ├── Dockerfile.dev             # Development image
│   └── docker-compose.yml         # Multi-container setup
│
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── pyproject.toml                 # Poetry configuration
├── poetry.lock                    # Locked dependencies
├── pytest.ini                     # Pytest configuration
├── mypy.ini                       # Type checking configuration
├── .pre-commit-config.yaml        # Pre-commit hooks
└── README.md                      # Project overview
```

## Module Details

### `app/core/`

**Purpose**: Core utilities, configuration, and domain models

#### `config.py`
```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
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
```

#### `types.py`
Contains all Pydantic domain models (see `domain-model.md`)

#### `exceptions.py`
```python
class LibrarianException(Exception):
    """Base exception"""
    pass

class ExtractionError(LibrarianException):
    """Content extraction failed"""
    pass

class BudgetExceededError(LibrarianException):
    """API budget exceeded"""
    pass

class PluginError(LibrarianException):
    """Plugin operation failed"""
    pass
```

### `app/repositories/`

**Purpose**: Data access abstraction

Each repository follows the Repository pattern:
```python
class BaseRepository(ABC):
    @abstractmethod
    async def get(self, id: UUID) -> Optional[T]:
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> UUID:
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass
```

### `app/services/`

**Purpose**: Business logic and use cases

Each service encapsulates a specific business capability:

- **DigestService**: Generate personalized daily digests
- **CurationService**: Screen and curate content
- **LibrarianService**: Maintain library organization
- **SearchService**: Semantic search and retrieval

### `app/intelligence/`

**Purpose**: LLM orchestration and optimization

Key components:

- **ModelRouter**: Select appropriate model based on task complexity
- **PromptBuilder**: Construct prompts from templates
- **CostOptimizer**: Track and optimize API costs
- **LLMClient**: Unified OpenAI API client

### `app/pipeline/`

**Purpose**: ETL pipeline for content processing

Flow: `Extract → Transform → Load`

Key components shipped today:

- **CLI (`cli.py`)** – lightweight command-line runner with file-system friendly defaults.
- **`HTMLWebExtractor`** – async HTML retrieval with trafilatura enrichment.
- **`BasicContentTransformer`** – deterministic heuristics for summaries, key points, and tags.
- **`LibraryContentLoader`** – writes Markdown snapshots, seeds the vector store, and caches processed payloads.

The pipeline orchestrator (`etl.py`) wires these strategies and returns a `PipelineResult` with raw, processed, and stored artifacts.

### `app/presentation/`

**Purpose**: User interface (Streamlit)

Multi-page Streamlit app:
1. **Digest**: Daily recommendations
2. **Library**: Browse organized content
3. **Search**: Semantic search interface
4. **Add Content**: Submit new URLs
5. **Knowledge Graph**: Interactive graph visualization
6. **Settings**: Configuration and preferences

### `app/workers/`

**Purpose**: Background job processing

Workers run independently:
- **digest_worker**: Generate digest at scheduled time
- **maintenance_worker**: Perform library cleanup
- **ingestion_worker**: Process content queue

Can be run as:
- Scheduled cron jobs
- Long-running daemons
- One-off tasks

### `app/plugins/`

**Purpose**: Plugin system for extensibility

See `plugin-development.md` for details.

### `tests/`

**Purpose**: Comprehensive test suite

Test pyramid:
- 70% Unit tests (fast, isolated)
- 20% Integration tests (real DBs)
- 10% E2E tests (full workflows)

See `testing-guide.md` for details.

## Configuration Files

### `.env`

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# Database
POSTGRES_URL=postgresql://user:pass@localhost:5432/librarian
REDIS_URL=redis://localhost:6379/0

# Features
ENABLE_WEB_SEARCH=false
ENABLE_FILE_SEARCH=true

# Costs
MONTHLY_API_BUDGET=100.0
```

### `config/settings.yaml`

```yaml
screening:
  model: gpt-5-nano
  max_tokens: 200
  temperature: 0.3

summarization:
  model: gpt-5-mini
  max_tokens: 500
  temperature: 0.5

quality_tiers:
  tier_a: 9.0
  tier_b: 7.0
  tier_c: 5.0
```

### `config/prompts/screening.txt`

```
You are an AI research librarian for the Williams Framework...
[Prompt template with variables]
```

## Data Storage

### `library/` (Content Files)

```
library/
├── tier-a/
│   ├── ai-ml/
│   │   └── attention-is-all-you-need.md
│   └── software-engineering/
│       └── clean-architecture.md
├── tier-b/
│   └── web-development/
│       └── react-best-practices.md
└── ...
```

Each `.md` file contains:
- Original content (cleaned)
- Metadata (YAML frontmatter)
- Extracted entities
- Links to related content

### `data/chroma/` (Vector Database)

ChromaDB persistence directory (managed by ChromaDB)

### `data/logs/` (Application Logs)

```
logs/
├── app.log              # Main application log
├── costs.log            # API cost tracking
├── errors.log           # Error log
└── access.log           # HTTP access log
```

## Entry Points

### Streamlit UI

```bash
poetry run streamlit run app/presentation/app.py
```

### CLI

```bash
poetry run librarian digest generate
poetry run librarian search "transformer architecture"
poetry run librarian add-url https://arxiv.org/abs/1706.03762
poetry run librarian maintenance run
```

### Workers

```bash
poetry run python -m app.workers.digest_worker
poetry run python -m app.workers.maintenance_worker
poetry run python -m app.workers.ingestion_worker
```

### API Server (Optional)

```bash
poetry run uvicorn app.api:app --reload
```

## Development Workflow

### 1. Setup

```bash
# Clone repository
git clone https://github.com/kevinwilliams/williams-librarian.git
cd williams-librarian

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Initialize databases
poetry run python scripts/init_db.py
```

### 2. Run Tests

```bash
# Unit tests (fast)
poetry run pytest -m unit

# Integration tests
poetry run pytest -m integration

# All tests with coverage
poetry run pytest --cov
```

### 3. Run Application

```bash
# Start services (PostgreSQL, Redis, ChromaDB)
docker-compose up -d

# Start Streamlit UI
poetry run streamlit run app/presentation/app.py

# Start workers (separate terminals)
poetry run python -m app.workers.digest_worker
```

### 4. Development Tools

```bash
# Type checking
poetry run mypy app/

# Linting
poetry run ruff check app/

# Formatting
poetry run black app/

# Pre-commit hooks
poetry run pre-commit run --all-files
```

## Production Deployment

See `deployment.md` for:
- Docker deployment
- Kubernetes setup
- Monitoring configuration
- Backup strategies
