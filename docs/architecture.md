# System Architecture

## Overview

The Williams Framework AI Librarian is built as a layered, modular system following clean architecture principles.

## Architectural Layers

### 1. Presentation Layer (UI)

**Responsibility**: User interaction and display

**Components**:
- `app/presentation/pages/` - Streamlit pages
- `app/presentation/components/` - Reusable UI components

**Design Patterns**:
- **MVC (Model-View-Controller)**: Separation of UI from business logic
- **Observer**: UI reacts to state changes

**Key Files**:
```
presentation/
├── pages/
│   ├── digest.py          # Daily digest view
│   ├── library.py         # File browser
│   ├── search.py          # Semantic search
│   └── chat.py            # Q&A interface
└── components/
    ├── file_tree.py       # Hierarchical file display
    ├── graph_viz.py       # Knowledge graph visualization
    └── cost_dashboard.py  # Cost tracking display
```

### 2. Application Layer (Services)

**Responsibility**: Business logic orchestration

**Components**:
- `app/services/` - Domain services
- Orchestrates multiple repositories and intelligence layer

**Design Patterns**:
- **Service Layer**: Encapsulates business logic
- **Facade**: Simplifies complex subsystem interactions

**Key Services**:
```python
class DigestService:
    """Generates daily digest of recommended content"""
    async def generate_digest(
        self,
        user_preferences: UserPreferences
    ) -> List[DigestItem]: ...

class CurationService:
    """Screens and processes new content"""
    async def screen_url(self, url: str) -> ScreeningResult: ...
    async def process_content(self, source: ContentSource) -> LibraryFile: ...

class LibrarianService:
    """Organizes and maintains library"""
    async def organize_file(self, file: LibraryFile) -> Path: ...
    async def suggest_maintenance(self) -> List[MaintenanceTask]: ...

class SearchService:
    """Semantic and keyword search"""
    async def semantic_search(self, query: str) -> SearchResult: ...
    async def answer_question(self, question: str) -> Answer: ...
```

### 3. Intelligence Layer (LLM Orchestration)

**Responsibility**: AI model management and cost optimization

**Components**:
- `app/intelligence/` - LLM routing, prompts, cost tracking
- `app/intelligence/langchain_integration.py` - LangChain chains

**Design Patterns**:
- **Strategy**: Different models for different tasks
- **Builder**: Prompt construction
- **Adapter**: External LLM APIs

**Key Components**:
```python
class ModelRouter:
    """Routes tasks to appropriate model based on complexity"""
    def select_model(self, task: TaskComplexity) -> ModelConfig: ...

class PromptBuilder:
    """Builds prompts using templates and context"""
    def build(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str: ...

class CostOptimizer:
    """Tracks and minimizes API costs"""
    async def optimize_prompt(self, prompt: str) -> str: ...
    async def get_monthly_cost(self) -> float: ...

class LangChainOrchestrator:
    """Manages LangChain chains and memory"""
    def create_retrieval_chain(self, vectorstore: VectorStore) -> Chain: ...
```

### 4. ETL Pipeline Layer

**Responsibility**: Extract, Transform, Load content

**Components**:
- `app/pipeline/extractors/` - Content extraction
- `app/pipeline/transformers/` - Content transformation
- `app/pipeline/loaders/` - Data loading
- `app/pipeline/knowledge_graph/` - Graph construction

**Design Patterns**:
- **Chain of Responsibility**: Pipeline stages
- **Factory**: Content processor selection
- **Template Method**: Extraction workflow

**Pipeline Flow**:
```
Extract → Transform → Load → Build Graph
   ↓          ↓         ↓          ↓
  Raw     Processed  Stored    Connected
Content   Content   Content    Content
```

**Key Components**:
```python
class ETLPipeline:
    """Orchestrates full pipeline"""
    async def process(self, source: ContentSource) -> LibraryFile:
        raw = await self.extractor.extract(source)
        processed = await self.transformer.transform(raw)
        file = await self.loader.load(processed)
        await self.kg_builder.build_graph(processed, file)
        return file

class ContentExtractorFactory:
    """Creates appropriate extractor"""
    def create(self, content_type: ContentType) -> ContentExtractor:
        match content_type:
            case ContentType.WEB: return WebExtractor()
            case ContentType.YOUTUBE: return YouTubeExtractor()
            case ContentType.PDF: return PDFExtractor()

class KnowledgeGraphBuilder:
    """Builds knowledge graph using NER + LLM"""
    async def extract_entities(self, content: str) -> List[Entity]: ...
    async def extract_relationships(
        self,
        content: str,
        entities: List[Entity]
    ) -> List[Relationship]: ...
```

### 5. Data Layer (Repositories)

**Responsibility**: Data persistence and retrieval

**Components**:
- `app/repositories/` - Data access objects
- Abstracts database operations

**Design Patterns**:
- **Repository**: Data access abstraction
- **Unit of Work**: Transaction management

**Key Repositories**:
```python
class QdrantRepository:
    """Vector database operations with Qdrant"""
    def add(self, content_id: str, vector: List[float], metadata: Dict) -> None: ...
    def query(self, query_vector: List[float], limit: int = 5) -> List[Dict]: ...
    def delete(self, content_id: str) -> None: ...
    def update_metadata(self, content_id: str, metadata: Dict) -> None: ...

class MinIORepository:
    """S3-compatible object storage operations"""
    async def upload_file(self, bucket: str, key: str, content: bytes) -> str: ...
    async def download_file(self, bucket: str, key: str) -> bytes: ...
    async def delete_file(self, bucket: str, key: str) -> None: ...
    async def list_objects(self, bucket: str, prefix: str) -> List[str]: ...

class GraphRepository:
    """Knowledge graph operations with NetworkX"""
    async def add_node(self, entity: Entity) -> None: ...
    async def add_edge(self, relationship: Relationship) -> None: ...
    async def get_connected_nodes(self, node_id: str) -> List[Node]: ...

class MetadataRepository:
    """PostgreSQL metadata storage"""
    async def save_processing_history(self, record: ProcessingRecord): ...
    async def get_cost_summary(self, period: str) -> CostSummary: ...

class CacheRepository:
    """Redis cache operations"""
    async def get(self, key: str) -> Optional[Any]: ...
    async def set(self, key: str, value: Any, ttl: int) -> None: ...
    async def delete(self, key: str) -> None: ...
```

## Data Flow

### Content Ingestion Flow

```
User submits URL
       ↓
┌──────────────────┐
│ CurationService  │
└──────────────────┘
       ↓
┌──────────────────┐
│ ModelRouter      │ ← Select gpt-5-nano for screening
└──────────────────┘
       ↓
┌──────────────────┐
│ PromptBuilder    │ ← Build screening prompt
└──────────────────┘
       ↓
┌──────────────────┐
│ OpenAI API       │ ← Screen URL
└──────────────────┘
       ↓
   High Priority?
       ↓ YES
┌──────────────────┐
│ ETLPipeline      │
└──────────────────┘
       ↓
┌──────────────────┐
│ Extract Content  │ ← WebExtractor
└──────────────────┘
       ↓
┌──────────────────┐
│ Transform        │ ← Clean, chunk, summarize
└──────────────────┘
       ↓
┌──────────────────┐
│ Load             │ ← Qdrant (vectors) + MinIO (files)
└──────────────────┘
       ↓
┌──────────────────┐
│ Build Graph      │ ← Extract entities/relationships
└──────────────────┘
       ↓
   Library File Created
```

### Search Flow

```
User enters query
       ↓
┌──────────────────┐
│ SearchService    │
└──────────────────┘
       ↓
┌──────────────────┐
│ LangChain        │ ← RetrievalQA chain
└──────────────────┘
       ↓
┌──────────────────┐
│ QdrantRepository │ ← Vector similarity search (Qdrant)
└──────────────────┘
       ↓
┌──────────────────┐
│ OpenAI API       │ ← Generate answer with context
└──────────────────┘
       ↓
   Answer with sources
```

## Plugin System Architecture

### Plugin Interface

```python
class Plugin(ABC):
    """Base plugin interface"""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def version(self) -> str: ...
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None: ...
    
    @abstractmethod
    async def shutdown(self) -> None: ...

class ExtractorPlugin(Plugin):
    """Plugin for custom content extractors"""
    
    @abstractmethod
    async def can_extract(self, url: str) -> bool: ...
    
    @abstractmethod
    async def extract(self, url: str) -> RawContent: ...

class ToolPlugin(Plugin):
    """Plugin for OpenAI tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]: ...
    
    @abstractmethod
    async def execute_tool(self, arguments: Dict[str, Any]) -> Any: ...
```

### Plugin Loading

```python
class PluginManager:
    """Manages plugin lifecycle"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
    
    async def load_plugins(self, plugin_dir: Path):
        """Discover and load plugins from directory"""
        for plugin_path in plugin_dir.glob("*.py"):
            plugin = await self._load_plugin(plugin_path)
            await plugin.initialize({})
            self.plugins[plugin.name] = plugin
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self.plugins.get(name)
```

## OpenAI Tools Integration

### Supported Tools

1. **Web Search** (`web_search`)
   - Cost: $10/1k calls + content tokens
   - Use: Real-time information discovery
   - Configuration: Enable via `enable_web_search` flag

2. **File Search** (`file_search`)
   - Cost: $2.50/1k calls
   - Use: Search uploaded documents
   - Configuration: Vector store IDs

3. **Code Interpreter** (`code_interpreter`)
   - Cost: $0.03/container
   - Use: Execute Python code for analysis
   - Configuration: Enable via `enable_code_interpreter`

4. **Image Generation** (`image_generation`)
   - Cost: Varies by model and resolution
   - Use: Generate diagrams, visualizations
   - Configuration: Model selection (gpt-image-1 vs dall-e-3)

### Tool Configuration

```python
class ToolConfig(BaseModel):
    """Configuration for OpenAI tools"""
    
    # Web Search
    enable_web_search: bool = False
    web_search_domains: Optional[List[str]] = None
    
    # File Search
    enable_file_search: bool = True
    file_search_vector_stores: List[str] = []
    file_search_max_results: int = 10
    
    # Code Interpreter
    enable_code_interpreter: bool = False
    
    # Image Generation
    enable_image_generation: bool = False
    image_generation_model: str = "gpt-image-1-mini"
    image_generation_quality: str = "medium"
```

## Scalability Considerations

### Horizontal Scaling

- **Stateless Services**: All services can be replicated
- **Shared Cache**: Redis for prompt caching
- **Distributed Queue**: For background processing
- **Load Balancer**: Nginx for Streamlit instances

### Vertical Scaling

- **Connection Pooling**: Database connections
- **Async I/O**: Non-blocking operations
- **Batch Processing**: Group API calls
- **Lazy Loading**: On-demand data loading

### Performance Targets

| Metric | Target |
|--------|--------|
| URL Screening | < 2s per URL |
| Content Processing | < 30s per article |
| Semantic Search | < 500ms p95 |
| UI Page Load | < 1s p95 |
| Daily Digest Generation | < 5 min for 100 items |

## Security Architecture

### API Key Management

- Keys stored in environment variables
- Never committed to version control
- Rotation support

### Data Privacy

- No data sent to OpenAI stored by default (store=false option)
- Local Qdrant and MinIO for sensitive content
- Encryption at rest for PostgreSQL and object storage
- MinIO bucket policies for access control

### Rate Limiting

- Respect OpenAI rate limits
- Exponential backoff for retries
- Circuit breaker pattern

## Monitoring & Observability

### Metrics

```python
# Prometheus metrics
api_calls_total = Counter('llm_api_calls_total', ['model', 'operation'])
api_latency_seconds = Histogram('llm_api_latency_seconds', ['model'])
api_cost_dollars = Counter('llm_api_cost_dollars', ['model'])
library_size_total = Gauge('library_files_total')
```

### Logging

```python
# Structured logging
logger.info(
    "Content processed",
    extra={
        "url": source.url,
        "content_type": source.content_type,
        "processing_time": elapsed,
        "tokens_used": tokens,
        "cost": cost
    }
)
```

### Health Checks

- `/health` - Overall system health
- `/health/qdrant` - Qdrant vector database connectivity
- `/health/minio` - MinIO object storage connectivity
- `/health/postgres` - PostgreSQL database connectivity
- `/health/redis` - Redis cache connectivity
- `/health/openai` - OpenAI API key validity

## Next Steps

See [domain-model.md](domain-model.md) for detailed entity definitions.
See [cost-optimization.md](cost-optimization.md) for cost control strategies.
See [testing-guide.md](testing-guide.md) for testing approach.
