# Development Checklist

## Purpose

This is your **daily action guide**. Check off items as you complete them. Each item is a concrete, testable task following TDD principles.

---

## Phase 0: Project Setup ⚙️

### Day 1: Environment Setup

- [ ] **0.1** Clone repository and navigate to project
  ```bash
  cd /home/kwilliams/is373/williams-librarian
  ```

- [ ] **0.2** Install Poetry
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  export PATH="$HOME/.local/bin:$PATH"
  ```

- [ ] **0.3** Create `pyproject.toml` (use template from implementation-roadmap.md)
  - [ ] Copy template
  - [ ] Verify all dependencies listed
  - [ ] Run `poetry install`
  - [ ] Verify installation: `poetry run python --version`

- [ ] **0.4** Create directory structure
  ```bash
  mkdir -p app/{core,repositories,services,intelligence,pipeline,presentation,workers,plugins}
  mkdir -p tests/{unit,integration,e2e,fixtures}
  mkdir -p config/prompts
  mkdir -p scripts
  mkdir -p library/{tier-a,tier-b,tier-c,tier-d}
  mkdir -p data/{chroma,logs,cache}
  mkdir -p .github/workflows
  mkdir -p docker
  ```

- [ ] **0.5** Create `__init__.py` files
  ```bash
  find app -type d -exec touch {}/__init__.py \;
  find tests -type d -exec touch {}/__init__.py \;
  ```

- [ ] **0.6** Create `.env.example` (copy from implementation-roadmap.md)
  - [ ] Copy template
  - [ ] Create `.env` from `.env.example`
  - [ ] Add actual `OPENAI_API_KEY`
  - [ ] Test: `cat .env | grep OPENAI_API_KEY`

- [ ] **0.7** Create `pytest.ini` (copy from implementation-roadmap.md)
  - [ ] Copy template
  - [ ] Test: `poetry run pytest --collect-only`

- [ ] **0.8** Create `.gitignore`
  ```gitignore
  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  .pytest_cache/
  .coverage
  htmlcov/
  .mypy_cache/
  
  # Environment
  .env
  .venv/
  venv/
  
  # Data
  library/
  data/
  logs/
  
  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo
  ```

- [ ] **0.9** Create `docker-compose.yml` (copy from implementation-roadmap.md)
  - [ ] Copy template
  - [ ] Start services: `docker-compose up -d`
  - [ ] Verify PostgreSQL: `docker-compose ps postgres`
  - [ ] Verify Redis: `docker-compose ps redis`
  - [ ] Test connection: `docker exec -it williams-librarian-postgres-1 psql -U librarian -d librarian -c "SELECT 1;"`

- [ ] **0.10** Create GitHub Actions CI (`.github/workflows/ci.yml`)
  - [ ] Copy template from implementation-roadmap.md
  - [ ] Commit and push
  - [ ] Verify CI runs on GitHub

- [ ] **0.11** Initialize Git repository
  ```bash
  git init
  git add .
  git commit -m "chore: initial project setup"
  git remote add origin <your-repo-url>
  git push -u origin main
  ```

**Validation**: Run `poetry run pytest --collect-only` → Should show "collected 0 items"

---

## Phase 1: Foundation Layer 🏗️

### Day 2-3: Core Types (Pydantic Models)

#### Module 1.1.1: ContentSource

- [ ] **1.1.1.1** Create test file
  ```bash
  touch tests/unit/test_content_source.py
  ```

- [ ] **1.1.1.2** 🔴 RED: Write first failing test
  ```python
  # tests/unit/test_content_source.py
  import pytest
  from datetime import datetime
  from app.core.types import ContentSource, ContentType
  
  def test_content_source_valid():
      """Valid ContentSource should pass validation"""
      source = ContentSource(
          url="https://arxiv.org/abs/1706.03762",
          content_type=ContentType.WEB
      )
      
      assert source.url == "https://arxiv.org/abs/1706.03762"
      assert source.content_type == ContentType.WEB
      assert source.source_domain == "arxiv.org"
      assert isinstance(source.discovered_at, datetime)
  ```
  - [ ] Run: `poetry run pytest tests/unit/test_content_source.py::test_content_source_valid`
  - [ ] **Expected**: Test FAILS (ImportError)

- [ ] **1.1.1.3** 🟢 GREEN: Implement ContentSource
  ```bash
  touch app/core/types.py
  ```
  - [ ] Add ContentType enum
  - [ ] Add ContentSource model
  - [ ] Add domain validator
  - [ ] Run test again → Should PASS ✅

- [ ] **1.1.1.4** 🔴 RED: Write invalid URL test
  ```python
  def test_content_source_invalid_url():
      with pytest.raises(ValidationError):
          ContentSource(url="not-a-url", content_type=ContentType.WEB)
  ```
  - [ ] Run test → Should PASS (Pydantic handles this)

- [ ] **1.1.1.5** 🔴 RED: Write custom domain test
  - [ ] Write test for custom domain override
  - [ ] Run test → Should PASS

- [ ] **1.1.1.6** 🔴 RED: Write depth tracking test
  - [ ] Write test for depth_from_root
  - [ ] Run test → Should PASS

- [ ] **1.1.1.7** 🔴 RED: Write serialization test
  - [ ] Write test for JSON serialization
  - [ ] Run test → Should PASS

- [ ] **1.1.1.8** Run full test suite
  ```bash
  poetry run pytest tests/unit/test_content_source.py -v --cov=app/core/types
  ```
  - [ ] All tests pass
  - [ ] Coverage: 100% for ContentSource

- [ ] **1.1.1.9** Commit
  ```bash
  git add tests/unit/test_content_source.py app/core/types.py
  git commit -m "feat: add ContentSource model with tests"
  git push
  ```

#### Module 1.1.2: ScreeningResult

- [ ] **1.1.2.1** Create test file: `tests/unit/test_screening_result.py`

- [ ] **1.1.2.2** 🔴 RED: Write valid screening test
  - [ ] Define test with all fields
  - [ ] Run test → Should FAIL

- [ ] **1.1.2.3** 🟢 GREEN: Implement ScreeningResult
  - [ ] Add Priority enum
  - [ ] Add ScreeningResult model with Field validations (ge=0, le=10)
  - [ ] Run test → Should PASS

- [ ] **1.1.2.4** 🔴 RED: Write score validation tests (parametrized)
  - [ ] Test relevance_score > 10 → Should raise ValidationError
  - [ ] Test quality_prediction < 0 → Should raise ValidationError
  - [ ] Test novelty_score > 10 → Should raise ValidationError
  - [ ] Run tests → All should PASS

- [ ] **1.1.2.5** 🔴 RED: Write average_score property test
  - [ ] Test (9.0 + 8.0 + 7.0) / 3 = 8.0
  - [ ] Run test → Should FAIL

- [ ] **1.1.2.6** 🟢 GREEN: Implement average_score property
  ```python
  @property
  def average_score(self) -> float:
      return (self.relevance_score + self.quality_prediction + self.novelty_score) / 3
  ```
  - [ ] Run test → Should PASS

- [ ] **1.1.2.7** 🔴 RED: Write should_process property test (parametrized)
  - [ ] HIGH → True
  - [ ] MEDIUM → True
  - [ ] LOW → True
  - [ ] SKIP → False
  - [ ] Run tests → Should FAIL

- [ ] **1.1.2.8** 🟢 GREEN: Implement should_process property
  ```python
  @property
  def should_process(self) -> bool:
      return self.priority != Priority.SKIP
  ```
  - [ ] Run tests → Should PASS

- [ ] **1.1.2.9** Run full test suite
  ```bash
  poetry run pytest tests/unit/test_screening_result.py -v --cov=app/core/types
  ```
  - [ ] All tests pass
  - [ ] Coverage: 100% for ScreeningResult

- [ ] **1.1.2.10** Commit
  ```bash
  git add tests/unit/test_screening_result.py app/core/types.py
  git commit -m "feat: add ScreeningResult model with score validation"
  git push
  ```

#### Module 1.1.3: RawContent

- [ ] **1.1.3.1** Create test file: `tests/unit/test_raw_content.py`
- [ ] **1.1.3.2** 🔴 RED: Write basic RawContent test
- [ ] **1.1.3.3** 🟢 GREEN: Implement RawContent model
- [ ] **1.1.3.4** 🔴 RED: Write optional fields test
- [ ] **1.1.3.5** Test coverage: 100%
- [ ] **1.1.3.6** Commit

#### Module 1.1.4: ProcessedContent

- [ ] **1.1.4.1** Create test file: `tests/unit/test_processed_content.py`
- [ ] **1.1.4.2** 🔴 RED: Write full processed content test
- [ ] **1.1.4.3** 🟢 GREEN: Implement ProcessedContent model
- [ ] **1.1.4.4** 🔴 RED: Write quality_tier property test (parametrized)
  - [ ] 9.5 → "tier-a"
  - [ ] 8.0 → "tier-b"
  - [ ] 6.5 → "tier-c"
  - [ ] 4.0 → "tier-d"
- [ ] **1.1.4.5** 🟢 GREEN: Implement quality_tier property
- [ ] **1.1.4.6** 🔴 RED: Write reading time test
- [ ] **1.1.4.7** Test coverage: 100%
- [ ] **1.1.4.8** Commit

#### Module 1.1.5: LibraryFile

- [ ] **1.1.5.1** Create test file: `tests/unit/test_library_file.py`
- [ ] **1.1.5.2** 🔴 RED: Write basic LibraryFile test
- [ ] **1.1.5.3** 🟢 GREEN: Implement LibraryFile model
- [ ] **1.1.5.4** 🔴 RED: Write video fields test
- [ ] **1.1.5.5** 🟢 GREEN: Add has_video property
- [ ] **1.1.5.6** 🔴 RED: Write ChromaDB reference test
- [ ] **1.1.5.7** Test coverage: 100%
- [ ] **1.1.5.8** Commit

#### Modules 1.1.6-1.1.10: Remaining Models

- [ ] **1.1.6** KnowledgeGraphNode (with centrality_score)
- [ ] **1.1.7** Relationship (with confidence, evidence)
- [ ] **1.1.8** DigestItem (with relevance_explanation)
- [ ] **1.1.9** MaintenanceTask (with priority)
- [ ] **1.1.10** ProcessingRecord (with status, cost tracking)

**Each follows same pattern**: Test file → RED → GREEN → REFACTOR → Commit

---

### Day 4: Configuration & Exceptions

#### Module 1.2: Configuration System

- [ ] **1.2.1** Create test file: `tests/unit/test_config.py`

- [ ] **1.2.2** 🔴 RED: Write load from env test
  ```python
  def test_settings_from_env(monkeypatch):
      monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
      settings = Settings()
      assert settings.openai_api_key == "sk-test"
  ```
  - [ ] Run test → Should FAIL

- [ ] **1.2.3** 🟢 GREEN: Implement Settings class
  ```bash
  touch app/core/config.py
  ```
  - [ ] Import pydantic_settings.BaseSettings
  - [ ] Define all settings fields
  - [ ] Add Config class with env_file
  - [ ] Run test → Should PASS

- [ ] **1.2.4** 🔴 RED: Write defaults test
- [ ] **1.2.5** 🟢 GREEN: Add default values
- [ ] **1.2.6** 🔴 RED: Write .env file loading test
- [ ] **1.2.7** Test coverage: 100%
- [ ] **1.2.8** Commit

#### Module 1.3: Exceptions

- [ ] **1.3.1** Create test file: `tests/unit/test_exceptions.py`
- [ ] **1.3.2** 🔴 RED: Write base exception test
- [ ] **1.3.3** 🟢 GREEN: Implement LibrarianException
  ```bash
  touch app/core/exceptions.py
  ```
- [ ] **1.3.4** 🔴 RED: Write ExtractionError test
- [ ] **1.3.5** 🟢 GREEN: Implement ExtractionError with url field
- [ ] **1.3.6** 🔴 RED: Write BudgetExceededError test (with context)
- [ ] **1.3.7** 🟢 GREEN: Implement with spent/limit fields
- [ ] **1.3.8** 🔴 RED: Write PluginError test
- [ ] **1.3.9** 🟢 GREEN: Implement with plugin_name field
- [ ] **1.3.10** Test coverage: 100%
- [ ] **1.3.11** Commit

---

### Phase 1 Validation

- [ ] **V1.1** Run all unit tests
  ```bash
  poetry run pytest -m unit -v
  ```
  - [ ] All tests pass
  - [ ] Zero failures

- [ ] **V1.2** Check coverage
  ```bash
  poetry run pytest -m unit --cov=app/core --cov-report=term-missing
  ```
  - [ ] Coverage ≥ 95%

- [ ] **V1.3** Type checking
  ```bash
  poetry run mypy app/core/
  ```
  - [ ] Zero type errors

- [ ] **V1.4** Linting
  ```bash
  poetry run ruff check app/core/
  ```
  - [ ] Zero linting errors

- [ ] **V1.5** Final commit
  ```bash
  git add .
  git commit -m "feat: complete Phase 1 - Foundation layer"
  git push
  ```

---

## Phase 2: Data Layer 💾

### Day 5-6: Repository Interfaces

#### Module 2.1: Base Repository

- [ ] **2.1.1** Create test file: `tests/unit/test_base_repository.py`
- [ ] **2.1.2** 🔴 RED: Write abstract class test
- [ ] **2.1.3** 🟢 GREEN: Implement BaseRepository ABC
  ```bash
  touch app/repositories/base.py
  ```
- [ ] **2.1.4** Define abstract methods (get, save, delete, list_all)
- [ ] **2.1.5** Test coverage: 100%
- [ ] **2.1.6** Commit

#### Module 2.2: ChromaDB Repository

**⚠️ INTEGRATION TESTS - REAL DATABASE**

- [ ] **2.2.1** Start ChromaDB dependency
  ```bash
  docker-compose up -d
  ```

- [ ] **2.2.2** Create test file: `tests/integration/test_chroma_repository.py`

- [ ] **2.2.3** Create fixture for ephemeral ChromaDB
  ```python
  @pytest.fixture
  async def chroma_repo():
      temp_dir = Path(tempfile.mkdtemp(prefix="test_chroma_"))
      repo = ChromaRepository(persist_directory=temp_dir)
      await repo.initialize()
      yield repo
      shutil.rmtree(temp_dir)
  ```

- [ ] **2.2.4** 🔴 RED: Write initialization test
  ```python
  @pytest.mark.integration
  @pytest.mark.requires_db
  @pytest.mark.asyncio
  async def test_chroma_initialize(chroma_repo):
      assert chroma_repo.client is not None
      assert chroma_repo.collection is not None
  ```
  - [ ] Run: `poetry run pytest tests/integration/test_chroma_repository.py::test_chroma_initialize -v`
  - [ ] Should FAIL (no ChromaRepository yet)

- [ ] **2.2.5** 🟢 GREEN: Implement ChromaRepository.__init__ and initialize()
  ```bash
  touch app/repositories/chroma_repository.py
  ```
  - [ ] Import chromadb
  - [ ] Create client in initialize()
  - [ ] Create collection
  - [ ] Run test → Should PASS ✅

- [ ] **2.2.6** 🔴 RED: Write add_document test
  - [ ] Test returns doc_id
  - [ ] Run test → Should FAIL

- [ ] **2.2.7** 🟢 GREEN: Implement add_document()
  - [ ] Use collection.add()
  - [ ] Return document ID
  - [ ] Run test → Should PASS

- [ ] **2.2.8** 🔴 RED: Write get_document test
  - [ ] Add doc, then retrieve by ID
  - [ ] Run test → Should FAIL

- [ ] **2.2.9** 🟢 GREEN: Implement get()
  - [ ] Use collection.get()
  - [ ] Return document data
  - [ ] Run test → Should PASS

- [ ] **2.2.10** 🔴 RED: Write semantic search test
  ```python
  async def test_chroma_semantic_search(chroma_repo):
      await chroma_repo.add_document("Transformers use self-attention", {"topic": "architecture"})
      await chroma_repo.add_document("Python is a programming language", {"topic": "programming"})
      
      results = await chroma_repo.search(query="neural network architecture", k=1)
      
      assert len(results) == 1
      assert "Transformers" in results[0]["document"]
  ```
  - [ ] Run test → Should FAIL

- [ ] **2.2.11** 🟢 GREEN: Implement search()
  - [ ] Use collection.query()
  - [ ] Format results
  - [ ] Run test → Should PASS ✅

- [ ] **2.2.12** 🔴 RED: Write search with filter test
- [ ] **2.2.13** 🟢 GREEN: Add where parameter to search()
- [ ] **2.2.14** 🔴 RED: Write batch_add test
- [ ] **2.2.15** 🟢 GREEN: Implement add_documents_batch()
- [ ] **2.2.16** 🔴 RED: Write update test
- [ ] **2.2.17** 🟢 GREEN: Implement update()
- [ ] **2.2.18** 🔴 RED: Write delete test
- [ ] **2.2.19** 🟢 GREEN: Implement delete()
- [ ] **2.2.20** 🔴 RED: Write count test
- [ ] **2.2.21** 🟢 GREEN: Implement count()

- [ ] **2.2.22** Run full integration test suite
  ```bash
  poetry run pytest tests/integration/test_chroma_repository.py -v
  ```
  - [ ] All tests pass
  - [ ] Uses REAL ChromaDB (not mocked)

- [ ] **2.2.23** Commit
  ```bash
  git add tests/integration/test_chroma_repository.py app/repositories/chroma_repository.py
  git commit -m "feat: add ChromaDB repository with real integration tests"
  git push
  ```

#### Module 2.3: File Repository

- [ ] **2.3.1** Create test file: `tests/integration/test_file_repository.py`
- [ ] **2.3.2** Create fixture for temp library directory
- [ ] **2.3.3** 🔴 RED: Write save markdown test
- [ ] **2.3.4** 🟢 GREEN: Implement save() with YAML frontmatter
- [ ] **2.3.5** 🔴 RED: Write create nested topics test
- [ ] **2.3.6** 🟢 GREEN: Implement directory creation
- [ ] **2.3.7** 🔴 RED: Write list by tier test
- [ ] **2.3.8** 🟢 GREEN: Implement list_by_tier()
- [ ] **2.3.9** 🔴 RED: Write move tier test
- [ ] **2.3.10** 🟢 GREEN: Implement move_to_tier()
- [ ] **2.3.11** 🔴 RED: Write save video test
- [ ] **2.3.12** 🟢 GREEN: Implement save_video()
- [ ] **2.3.13** Run integration tests
- [ ] **2.3.14** Commit

#### Module 2.4: Metadata Repository (PostgreSQL)

**⚠️ INTEGRATION TESTS - REAL DATABASE**

- [ ] **2.4.1** Create SQLAlchemy models: `app/repositories/models.py`
  - [ ] ProcessingRecordModel
  - [ ] Base class

- [ ] **2.4.2** Create test file: `tests/integration/test_metadata_repository.py`

- [ ] **2.4.3** Create fixture for test database
  ```python
  @pytest.fixture(scope="function")
  def test_db():
      engine = create_engine("postgresql://librarian:password@localhost:5432/librarian_test")
      Base.metadata.create_all(engine)
      Session = sessionmaker(bind=engine)
      session = Session()
      yield session
      session.rollback()
      session.close()
      Base.metadata.drop_all(engine)
  ```

- [ ] **2.4.4** 🔴 RED: Write save processing record test
- [ ] **2.4.5** 🟢 GREEN: Implement save_processing_record()
  ```bash
  touch app/repositories/metadata_repository.py
  ```
- [ ] **2.4.6** 🔴 RED: Write get by URL test
- [ ] **2.4.7** 🟢 GREEN: Implement get_by_url()
- [ ] **2.4.8** 🔴 RED: Write cost statistics test
- [ ] **2.4.9** 🟢 GREEN: Implement get_cost_statistics()
- [ ] **2.4.10** 🔴 RED: Write update status test
- [ ] **2.4.11** 🟢 GREEN: Implement update_status()
- [ ] **2.4.12** Run integration tests
- [ ] **2.4.13** Commit

---

### Phase 2 Validation

- [ ] **V2.1** Run all integration tests
  ```bash
  poetry run pytest -m integration -v
  ```
  - [ ] All tests pass
  - [ ] Uses REAL databases (no mocks!)

- [ ] **V2.2** Check integration coverage
  ```bash
  poetry run pytest -m integration --cov=app/repositories --cov-report=term-missing
  ```
  - [ ] Coverage ≥ 80%

- [ ] **V2.3** Type checking
  ```bash
  poetry run mypy app/repositories/
  ```
  - [ ] Zero type errors

- [ ] **V2.4** Final commit
  ```bash
  git add .
  git commit -m "feat: complete Phase 2 - Data layer with real integration tests"
  git push
  ```

---

## Phase 3: Intelligence Layer 🧠

### Day 7-8: LLM Orchestration

#### Module 3.1: Model Router

- [ ] **3.1.1** Create test file: `tests/unit/test_model_router.py`
- [ ] **3.1.2** 🔴 RED: Write complexity → model mapping test
  - [ ] LOW → gpt-5-nano
  - [ ] MEDIUM → gpt-5-mini
  - [ ] HIGH → gpt-5
- [ ] **3.1.3** 🟢 GREEN: Implement ModelRouter.select_model()
  ```bash
  touch app/intelligence/model_router.py
  ```
- [ ] **3.1.4** 🔴 RED: Write cost calculation test
- [ ] **3.1.5** 🟢 GREEN: Implement calculate_cost()
- [ ] **3.1.6** Test coverage: 100%
- [ ] **3.1.7** Commit

#### Module 3.2: Cost Optimizer

- [ ] **3.2.1** Create test file: `tests/unit/test_cost_optimizer.py`
- [ ] **3.2.2** 🔴 RED: Write cost tracking test
- [ ] **3.2.3** 🟢 GREEN: Implement CostOptimizer.track()
- [ ] **3.2.4** 🔴 RED: Write budget enforcement test
- [ ] **3.2.5** 🟢 GREEN: Implement budget checking
- [ ] **3.2.6** 🔴 RED: Write cache hit rate test
- [ ] **3.2.7** 🟢 GREEN: Implement cache statistics
- [ ] **3.2.8** Test coverage: 100%
- [ ] **3.2.9** Commit

#### Module 3.3: LLM Client (OpenAI Wrapper)

**⚠️ INTEGRATION TEST - REAL API (Budget Controlled)**

- [ ] **3.3.1** Create test file: `tests/integration/test_llm_client.py`
- [ ] **3.3.2** Create budget tracker fixture
  ```python
  @pytest.fixture(scope="session")
  def openai_budget():
      class BudgetTracker:
          def __init__(self):
              self.spent = 0.0
              self.max_budget = 1.0  # $1 max for tests
      return BudgetTracker()
  ```
- [ ] **3.3.3** 🔴 RED: Write simple completion test
- [ ] **3.3.4** 🟢 GREEN: Implement LLMClient.create_completion()
  ```bash
  touch app/intelligence/llm_client.py
  ```
- [ ] **3.3.5** 🔴 RED: Write retry logic test
- [ ] **3.3.6** 🟢 GREEN: Add tenacity retry decorator
- [ ] **3.3.7** 🔴 RED: Write error handling test
- [ ] **3.3.8** 🟢 GREEN: Implement error handling
- [ ] **3.3.9** Run integration test (costs real money!)
- [ ] **3.3.10** Commit

#### Module 3.4: Prompt Builder

- [ ] **3.4.1** Create test file: `tests/unit/test_prompt_builder.py`
- [ ] **3.4.2** 🔴 RED: Write template loading test
- [ ] **3.4.3** 🟢 GREEN: Implement PromptBuilder.load_template()
- [ ] **3.4.4** 🔴 RED: Write variable substitution test
- [ ] **3.4.5** 🟢 GREEN: Implement build()
- [ ] **3.4.6** 🔴 RED: Write caching test
- [ ] **3.4.7** 🟢 GREEN: Add caching logic
- [ ] **3.4.8** Test coverage: 100%
- [ ] **3.4.9** Commit

---

## Remaining Phases (Abbreviated)

### Phase 4: ETL Pipeline (Days 9-13)
- Web Extractor → YouTube Extractor → PDF Extractor
- Content Transformer → Summarizer → NER
- ChromaDB Loader → File Loader
- Knowledge Graph Builder

### Phase 5: Services (Days 14-17)
- CurationService (screening)
- DigestService (daily recommendations)
- SearchService (semantic search)
- LibrarianService (maintenance)

### Phase 6: Presentation (Days 18-20)
- Streamlit app setup
- Digest page
- Library browser
- Search interface
- Settings page

### Phase 7: Workers (Days 21-22)
- Digest worker (scheduled)
- Ingestion worker (queue processing)
- Maintenance worker (cleanup)

### Phase 8: Plugin System (Days 23-24)
- Plugin base classes
- Plugin manager
- Example plugins

### Phase 9: Production Ready (Days 25-27)
- Performance optimization
- Security hardening
- Deployment automation
- Monitoring setup

---

## Daily Workflow

### Morning Routine
```bash
# 1. Pull latest
git pull

# 2. Activate environment
cd /home/kwilliams/is373/williams-librarian
poetry shell

# 3. Start services
docker-compose up -d

# 4. Run all tests
poetry run pytest

# 5. Check CI status on GitHub
```

### Development Loop (TDD)
```bash
# RED: Write failing test
nano tests/unit/test_new_feature.py
poetry run pytest tests/unit/test_new_feature.py  # FAILS

# GREEN: Write minimal code
nano app/core/new_feature.py
poetry run pytest tests/unit/test_new_feature.py  # PASSES

# REFACTOR: Improve code
nano app/core/new_feature.py
poetry run pytest tests/unit/test_new_feature.py  # STILL PASSES

# Run full suite
poetry run pytest -m unit

# Commit
git add .
git commit -m "feat: add new_feature"
```

### End of Day
```bash
# 1. Run full test suite
poetry run pytest

# 2. Type check
poetry run mypy app/

# 3. Lint
poetry run ruff check app/

# 4. Commit and push
git add .
git commit -m "feat: daily progress"
git push

# 5. Stop services
docker-compose down
```

---

## Progress Tracking

### Week 1 (Days 1-5)
- [ ] Phase 0: Setup complete
- [ ] Phase 1: Foundation complete
- [ ] Phase 2: Data layer complete

### Week 2 (Days 6-10)
- [ ] Phase 3: Intelligence layer complete
- [ ] Phase 4: ETL pipeline (partial)

### Week 3 (Days 11-15)
- [ ] Phase 4: ETL pipeline complete
- [ ] Phase 5: Services (partial)

### Week 4 (Days 16-20)
- [ ] Phase 5: Services complete
- [ ] Phase 6: Presentation complete

### Week 5 (Days 21-25)
- [ ] Phase 7: Workers complete
- [ ] Phase 8: Plugin system complete

### Week 6 (Days 26-30)
- [ ] Phase 9: Production ready
- [ ] Documentation complete
- [ ] First deployment

---

## Success Criteria

### Phase Completion
- [ ] All tests pass (unit + integration)
- [ ] Coverage ≥ 90% overall
- [ ] Zero type errors (mypy strict)
- [ ] Zero lint errors (ruff)
- [ ] Documentation updated
- [ ] Git committed and pushed
- [ ] CI/CD green

### Project Completion
- [ ] Can screen URLs
- [ ] Can process content
- [ ] Can search library
- [ ] Can generate digest
- [ ] UI functional
- [ ] Docker deployment works
- [ ] Monitoring operational
- [ ] Cost tracking active

---

## Emergency Contacts

### Stuck on Test?
1. Read error message carefully
2. Check `tdd-implementation-plan.md` for examples
3. Run test in isolation: `pytest path/to/test.py::test_name -v`
4. Use `--pdb` flag to debug: `pytest --pdb`

### Database Issues?
```bash
# Reset PostgreSQL
docker-compose down
docker volume rm williams-librarian_postgres_data
docker-compose up -d postgres

# Reset Redis
docker-compose restart redis
```

### Need Help?
- Review `testing-guide.md` for test patterns
- Review `architecture.md` for design decisions
- Check `domain-model.md` for Pydantic examples

---

**Remember**: 🔴 RED → 🟢 GREEN → 🔄 REFACTOR → ✅ COMMIT

Never write production code without a failing test first!
