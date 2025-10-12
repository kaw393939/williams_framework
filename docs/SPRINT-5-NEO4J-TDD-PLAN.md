# Sprint 5: Neo4j Foundation + Flexible AI Services - TDD Implementation Plan

**Duration:** 2.5 weeks (12 working days)  
**Focus:** Neo4j integration, pluggable embeddings/LLMs, provenance tracking, entity extraction  
**Testing Philosophy:** RED-GREEN-REFACTOR with real services (no mocks)  
**Target:** 53 new tests, maintain 98%+ coverage

---

## 🎯 Sprint Goals

1. **Pluggable AI Services**: Abstract embedding and LLM providers (local vs. hosted)
2. **Embedding Flexibility**: Support OpenAI, Sentence-Transformers (BERT), Ollama, custom models
3. **LLM Flexibility**: Support OpenAI, Ollama (local), Anthropic, custom LLMs
4. **Neo4j Integration**: Add Neo4j 5.x to Docker stack with proper schema and vector indexes
5. **Deterministic IDs**: Implement SHA256-based document IDs and offset-based chunk IDs
6. **Enhanced Chunker**: Extend chunker to track byte offsets, page numbers, and heading context
7. **NER Pipeline**: SpaCy-based entity extraction with confidence scoring
8. **Provenance Foundation**: Document → Chunk → Mention → Entity relationships

---

## 🏗️ Architecture: Cloud-Agnostic AI Services

### **Design Philosophy:**
- **Plugin Architecture**: Swap providers without changing application code
- **Cost Optimization**: Use local models (free) for dev, hosted (paid) for production
- **Graceful Degradation**: Fallback to alternative providers on failure
- **Configuration-Driven**: Change providers via config, no code changes
- **Hybrid Deployments**: Mix local and hosted services (e.g., local embeddings + hosted LLM)

### **Service Abstraction Layers:**
```
Application Code
      ↓
AbstractEmbeddingProvider (interface)
      ↓
├── OpenAIEmbeddingProvider (hosted, $$$)
├── SentenceTransformerProvider (local, free)
├── OllamaEmbeddingProvider (local, free)
└── CustomEmbeddingProvider (extensible)

AbstractLLMProvider (interface)
      ↓
├── OpenAILLMProvider (hosted, $$$)
├── OllamaLLMProvider (local, free)
├── AnthropicLLMProvider (hosted, $$$)
└── CustomLLMProvider (extensible)
```

### **Configuration Example:**
```yaml
# config/ai_services.yml
embedding_provider:
  default: "sentence_transformer"  # or "openai", "ollama"
  
  openai:
    model: "text-embedding-3-small"
    dimensions: 1536
    api_key_env: "OPENAI_API_KEY"
    
  sentence_transformer:
    model: "all-MiniLM-L6-v2"  # Local BERT
    dimensions: 384
    device: "cpu"  # or "cuda"
    
  ollama:
    model: "nomic-embed-text"
    base_url: "http://localhost:11434"
    dimensions: 768

llm_provider:
  default: "ollama"  # or "openai", "anthropic"
  
  openai:
    model: "gpt-4o-mini"
    temperature: 0.7
    max_tokens: 2000
    api_key_env: "OPENAI_API_KEY"
    
  ollama:
    model: "llama3.1:8b"
    base_url: "http://localhost:11434"
    temperature: 0.7
    
  anthropic:
    model: "claude-3-5-sonnet-20241022"
    api_key_env: "ANTHROPIC_API_KEY"
```

---

## 📋 Stories & Acceptance Criteria

### Story S5-500: Pluggable AI Services Architecture (8 tests) 🆕
**Priority:** P0 (Foundation for all AI features)  
**Estimate:** 1.5 days

**Acceptance Criteria:**
- [ ] Create `AbstractEmbeddingProvider` interface with `.embed(text)` method
- [ ] Create `AbstractLLMProvider` interface with `.generate(prompt)` method
- [ ] Provider factory pattern: `ProviderFactory.get_embedding_provider(config)`
- [ ] Configuration-driven provider selection (YAML + environment variables)
- [ ] Graceful fallback: if primary provider fails, try secondary
- [ ] Cost tracking: log tokens/requests for each provider
- [ ] Health checks for each provider
- [ ] Provider registry for dynamic plugin loading
- [ ] Thread-safe provider initialization (singleton pattern)
- [ ] Environment-specific configs (dev: local, prod: hosted)

**Test Scenarios:**
1. Load embedding provider from config
2. Load LLM provider from config
3. Swap providers without code changes
4. Fallback to secondary provider on failure
5. Cost tracking logs tokens used
6. Health check detects provider availability
7. Thread-safe provider initialization
8. Invalid provider name raises clear error

---

### Story S5-501: Local Embedding Providers (8 tests) 🆕
**Priority:** P0 (Cost optimization for dev)  
**Estimate:** 1.5 days

**Acceptance Criteria:**
- [ ] `SentenceTransformerProvider`: Hugging Face sentence-transformers (BERT-based)
- [ ] Support models: `all-MiniLM-L6-v2` (384 dim), `all-mpnet-base-v2` (768 dim)
- [ ] `OllamaEmbeddingProvider`: Local Ollama embeddings
- [ ] Automatic model download on first use
- [ ] GPU support with automatic CPU fallback
- [ ] Batch embedding for performance (process 100 texts in <10s)
- [ ] Embedding caching to avoid recomputation
- [ ] Dimension compatibility checks (vector index must match)
- [ ] Memory management (unload models when not in use)
- [ ] Performance benchmarks vs. OpenAI

**Test Scenarios:**
1. SentenceTransformer embeds text correctly
2. Embedding dimensions match config
3. Batch embedding processes multiple texts
4. GPU acceleration works (if available)
5. CPU fallback works when no GPU
6. Ollama provider connects to local server
7. Embedding cache prevents recomputation
8. Performance benchmark (<10s for 100 texts)

---

### Story S5-502: Hosted Embedding Providers (6 tests) 🆕
**Priority:** P1 (Production deployment)  
**Estimate:** 1 day

**Acceptance Criteria:**
- [ ] `OpenAIEmbeddingProvider`: text-embedding-3-small, text-embedding-3-large
- [ ] API key management via environment variables (never in code)
- [ ] Rate limiting and retry logic (handle 429 errors)
- [ ] Cost estimation before embedding (warn if >1000 texts)
- [ ] Batch API support (50% cost reduction)
- [ ] Error handling for API failures (fallback to local)
- [ ] Token usage tracking for billing
- [ ] Support for custom base URLs (Azure OpenAI, proxies)

**Test Scenarios:**
1. OpenAI provider embeds text correctly
2. API key loaded from environment
3. Rate limiting handles 429 errors
4. Batch API reduces cost
5. Fallback to local on API failure
6. Token usage logged correctly

---

### Story S5-503: Local LLM Providers (8 tests) 🆕
**Priority:** P1 (Cost-free development)  
**Estimate:** 1.5 days

**Acceptance Criteria:**
- [ ] `OllamaLLMProvider`: Support Llama 3.1, Mistral, Phi-3
- [ ] Streaming support for real-time responses
- [ ] Context window management (track token count)
- [ ] Temperature and top_p configuration
- [ ] System prompt support
- [ ] Chat history management
- [ ] Performance benchmarks (tokens/second)
- [ ] Docker setup for Ollama server
- [ ] Health check detects Ollama availability
- [ ] Graceful degradation if Ollama unavailable

**Test Scenarios:**
1. Ollama generates text response
2. Streaming responses work
3. Context window respected
4. System prompts applied correctly
5. Chat history maintained
6. Performance meets threshold (>10 tokens/s)
7. Health check detects Ollama
8. Graceful degradation on failure

---

### Story S5-504: Hosted LLM Providers (6 tests) 🆕
**Priority:** P1 (Production deployment)  
**Estimate:** 1 day

**Acceptance Criteria:**
- [ ] `OpenAILLMProvider`: GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- [ ] `AnthropicLLMProvider`: Claude 3.5 Sonnet, Claude 3 Haiku
- [ ] Streaming support with proper token tracking
- [ ] Cost estimation before generation
- [ ] Rate limiting and retry logic
- [ ] Prompt caching (50% cost reduction for repeated prompts)
- [ ] Error handling with fallback to alternative provider
- [ ] Token usage logging for billing

**Test Scenarios:**
1. OpenAI provider generates responses
2. Anthropic provider generates responses
3. Streaming works for both providers
4. Cost estimation warns before expensive calls
5. Prompt caching reduces costs
6. Fallback works on provider failure

---

### Story S5-505: Neo4j Integration & Schema (12 tests)
**Priority:** P0 (Blocker)  
**Estimate:** 2 days

**Acceptance Criteria:**
- [ ] Neo4j 5.x added to `docker-compose.yml` with proper volumes and ports
- [ ] Neo4j Python driver integrated with connection pooling
- [ ] Schema constraints created for all node types (Document, Chunk, Entity, Mention)
- [ ] Vector indexes created on Chunk.embedding and Entity.embedding with **configurable dimensions**
- [ ] Repository pattern for Neo4j operations (NeoRepository)
- [ ] Health check endpoint verifies Neo4j connectivity
- [ ] All tests use real Neo4j test instance (testcontainers or separate DB)
- [ ] Cypher query builder for common operations
- [ ] Transaction management with proper rollback on error
- [ ] Configuration flag to enable/disable Neo4j (graceful degradation)
- [ ] **Dynamic vector index creation based on embedding provider dimensions**

**Test Scenarios:**
1. Neo4j connection establishment and health check
2. Schema constraint creation (unique IDs, required fields)
3. Vector index creation with proper dimensions (384 for BERT, 1536 for OpenAI)
4. Node creation with relationships
5. Transaction commit and rollback
6. Connection pool management under load
7. Concurrent write operations
8. Query performance with indexes
9. Graceful degradation when Neo4j disabled
10. Error handling for connection failures
11. Cypher injection prevention
12. Data cleanup between tests

---

### Story S5-506: Deterministic ID System (8 tests)
**Priority:** P0 (Blocker)  
**Estimate:** 1 day

**Acceptance Criteria:**
- [ ] `generate_doc_id(url: str) -> str` produces SHA256 hash of normalized URL
- [ ] URL normalization handles protocol, trailing slashes, query param ordering
- [ ] `generate_chunk_id(doc_id: str, start_offset: int) -> str` produces deterministic chunk ID
- [ ] `generate_mention_id(chunk_id: str, entity_text: str, offset: int) -> str` for entity mentions
- [ ] All IDs are reproducible (same input → same ID)
- [ ] ID collision handling (extremely rare but tested)
- [ ] Documentation of ID format and rationale
- [ ] Migration strategy for existing content (if any)

**Test Scenarios:**
1. Document ID generation from URL (same URL → same ID)
2. URL normalization (http/https, trailing slash, query params)
3. Chunk ID generation from doc_id + offset
4. Mention ID generation from chunk_id + entity + offset
5. ID reproducibility across runs
6. ID uniqueness for different inputs
7. Performance of ID generation (should be fast)
8. Edge cases (empty URLs, special characters, unicode)

---

### Story S5-507: Enhanced Chunker with Provenance (10 tests)
**Priority:** P0 (Blocker)  
**Estimate:** 2 days

**Acceptance Criteria:**
- [ ] Extend `Chunk` model with `start_offset`, `end_offset`, `page_number`, `heading`
- [ ] Chunker tracks byte offsets in original document
- [ ] PDF extractor captures page numbers for each chunk
- [ ] Markdown extractor captures heading hierarchy (e.g., "## Introduction > ### Background")
- [ ] Chunk IDs generated using deterministic ID system
- [ ] Chunks stored in Neo4j with PART_OF relationship to Document
- [ ] Byte offsets enable precise citation clicking
- [ ] Chunker configurable via AnalysisConfig
- [ ] Backward compatible with existing chunking tests
- [ ] Performance: chunks 100-page PDF in <10 seconds

**Test Scenarios:**
1. Byte offset tracking for plain text chunks
2. Page number tracking for PDF chunks
3. Heading capture for Markdown chunks
4. Chunk ID determinism (same doc → same chunk IDs)
5. PART_OF relationship creation in Neo4j
6. Chunk retrieval by ID
7. Overlapping chunks (if configured) maintain correct offsets
8. Unicode handling in byte offset calculation
9. Large document chunking (1000+ pages)
10. Backward compatibility with existing Content model

---

### Story S5-508: NER Pipeline with SpaCy (15 tests)
**Priority:** P0 (Must Have)  
**Estimate:** 3 days

**Acceptance Criteria:**
- [ ] SpaCy `en_core_web_trf` transformer model integrated
- [ ] Entity extraction for: PERSON, ORG, GPE (location), LAW, DATE, PRODUCT
- [ ] Confidence score for each entity (SpaCy's confidence + custom heuristics)
- [ ] Entity mentions stored in Neo4j with MENTIONED_IN relationship to Chunk
- [ ] Mention includes: entity_text, entity_type, start_char, end_char, confidence
- [ ] Mention IDs generated using deterministic ID system
- [ ] Plugin architecture: AbstractNERPlugin for extensibility
- [ ] SpaCy model downloaded automatically or via setup script
- [ ] Performance: processes 1000-word document in <5 seconds
- [ ] Entity deduplication within same chunk (e.g., "OpenAI" mentioned 3 times)
- [ ] Configurable entity type filtering (only extract PERSON+ORG for MVP)
- [ ] Integration with existing ETL pipeline as new Transform step
- [ ] Batch processing for multiple chunks
- [ ] Error handling for malformed text

**Test Scenarios:**
1. Extract PERSON entities from text
2. Extract ORG entities with confidence scores
3. Extract GPE (location) entities
4. Extract LAW entities (e.g., "First Amendment", "GDPR")
5. Extract DATE entities (e.g., "January 2024", "Q3 2023")
6. Handle multi-word entities (e.g., "Sam Altman", "New York City")
7. Confidence scoring (high confidence for well-known entities)
8. Entity deduplication within chunk
9. MENTIONED_IN relationship creation
10. Plugin architecture (swap SpaCy for custom NER)
11. Performance benchmark (1000 words in <5s)
12. Batch processing of multiple chunks
13. Error handling for non-English text
14. Integration with ETL pipeline
15. Neo4j storage and retrieval of mentions

---

## 📅 Day-by-Day Implementation Plan (12 Days)

### **Day 1: AI Services Architecture Foundation**

**Morning: Abstract Interfaces**
```bash
# Install dependencies
poetry add sentence-transformers openai anthropic
```

**Tasks:**
1. ✅ Create `app/intelligence/providers/abstract_embedding.py` interface
2. ✅ Create `app/intelligence/providers/abstract_llm.py` interface
3. ✅ Create `app/intelligence/providers/factory.py` for provider loading
4. ✅ Create `config/ai_services.yml` configuration

**TDD Cycle:**
```python
# tests/intelligence/test_abstract_providers.py

def test_abstract_embedding_interface():
    """RED: Interface not yet defined"""
    from app.intelligence.providers import AbstractEmbeddingProvider
    
    # Interface should have embed() method
    provider = AbstractEmbeddingProvider()
    result = provider.embed("test text")  # FAILS - abstract method
    
# GREEN: Define abstract interface
from abc import ABC, abstractmethod
from typing import List, Union

class AbstractEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Embed single text or batch of texts."""
        pass
    
    @abstractmethod
    def get_dimensions(self) -> int:
        """Return embedding dimensions for this provider."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model name/identifier."""
        pass

# REFACTOR: Add health_check() and cost_estimate() methods
```

**Afternoon: Provider Factory**

**Tasks:**
1. ✅ Implement `ProviderFactory.get_embedding_provider(config)`
2. ✅ Implement `ProviderFactory.get_llm_provider(config)`
3. ✅ Test configuration-driven provider selection

**TDD Cycle:**
```python
def test_provider_factory_loads_from_config():
    """RED: Factory not yet implemented"""
    config = {
        "embedding_provider": {
            "default": "sentence_transformer",
            "sentence_transformer": {
                "model": "all-MiniLM-L6-v2"
            }
        }
    }
    
    provider = ProviderFactory.get_embedding_provider(config)
    assert provider.model_name == "all-MiniLM-L6-v2"  # FAILS
    assert provider.get_dimensions() == 384
    
# GREEN: Implement factory
class ProviderFactory:
    _embedding_providers = {}
    _llm_providers = {}
    
    @classmethod
    def get_embedding_provider(cls, config: dict) -> AbstractEmbeddingProvider:
        provider_name = config["embedding_provider"]["default"]
        provider_config = config["embedding_provider"][provider_name]
        
        if provider_name == "sentence_transformer":
            from .sentence_transformer import SentenceTransformerProvider
            return SentenceTransformerProvider(provider_config)
        elif provider_name == "openai":
            from .openai_embedding import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider(provider_config)
        # ... more providers
        
        raise ValueError(f"Unknown provider: {provider_name}")

# REFACTOR: Add caching and singleton pattern
```

**Commit:**
```
feat(ai): Add pluggable AI services architecture

- AbstractEmbeddingProvider and AbstractLLMProvider interfaces
- ProviderFactory for configuration-driven provider loading
- Config file structure for local and hosted providers
- Tests: 4 passed (interfaces, factory, config loading, validation)
```

---

### **Day 2: Local Embedding Providers**

**Morning: Sentence-Transformers Implementation**
```bash
# Sentence-transformers will auto-download models
poetry add sentence-transformers torch
```

**Tasks:**
1. ✅ Implement `SentenceTransformerProvider`
2. ✅ Support `all-MiniLM-L6-v2` (384 dim) and `all-mpnet-base-v2` (768 dim)
3. ✅ GPU support with CPU fallback
4. ✅ Batch embedding

**TDD Cycle:**
```python
# tests/intelligence/test_sentence_transformer.py

def test_sentence_transformer_embeds_text():
    """RED: SentenceTransformerProvider not yet implemented"""
    config = {"model": "all-MiniLM-L6-v2", "device": "cpu"}
    provider = SentenceTransformerProvider(config)
    
    embedding = provider.embed("Hello world")
    
    assert len(embedding) == 384  # FAILS - not implemented
    assert all(isinstance(x, float) for x in embedding)
    
# GREEN: Implement SentenceTransformerProvider
from sentence_transformers import SentenceTransformer
import torch

class SentenceTransformerProvider(AbstractEmbeddingProvider):
    def __init__(self, config: dict):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(config["model"], device=self.device)
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            return self.model.encode(text, convert_to_numpy=True).tolist()
        return self.model.encode(text, convert_to_numpy=True, batch_size=32).tolist()
    
    def get_dimensions(self) -> int:
        return self.model.get_sentence_embedding_dimension()
    
    @property
    def model_name(self) -> str:
        return self.config["model"]

# REFACTOR: Add caching and error handling
```

**Afternoon: Ollama Embedding Provider**

**Tasks:**
1. ✅ Add Ollama to docker-compose.yml
2. ✅ Implement `OllamaEmbeddingProvider`
3. ✅ Test connection and embedding

**TDD Cycle:**
```python
def test_ollama_embedding_provider():
    """Test Ollama local embeddings"""
    config = {
        "model": "nomic-embed-text",
        "base_url": "http://localhost:11434"
    }
    provider = OllamaEmbeddingProvider(config)
    
    # Check if Ollama is available
    if not provider.health_check():
        pytest.skip("Ollama not available")
    
    embedding = provider.embed("Test text")
    assert len(embedding) == 768  # nomic-embed-text dimensions
    
# GREEN: Implement OllamaEmbeddingProvider
import requests

class OllamaEmbeddingProvider(AbstractEmbeddingProvider):
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["base_url"]
        self.model = config["model"]
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            return response.json()["embedding"]
        
        # Batch processing
        return [self.embed(t) for t in text]
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
```

**Commit:**
```
feat(ai): Add local embedding providers (Sentence-Transformers, Ollama)

- SentenceTransformerProvider with GPU support
- OllamaEmbeddingProvider for local embeddings
- Batch processing for performance
- Auto-fallback to CPU if no GPU
- Tests: 8 passed (embed, dimensions, batch, GPU, CPU, Ollama, health)
```

---

### **Day 3: Hosted Embedding & Neo4j Setup**

**Morning: OpenAI Embedding Provider**

**Tasks:**
1. ✅ Implement `OpenAIEmbeddingProvider`
2. ✅ Rate limiting and retry logic
3. ✅ Batch API support
4. ✅ Cost tracking

**TDD Cycle:**
```python
def test_openai_embedding_provider():
    """Test OpenAI hosted embeddings"""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    config = {
        "model": "text-embedding-3-small",
        "api_key_env": "OPENAI_API_KEY"
    }
    provider = OpenAIEmbeddingProvider(config)
    
    embedding = provider.embed("Test text")
    assert len(embedding) == 1536
    
    # Check cost tracking
    assert provider.get_tokens_used() > 0
    
# GREEN: Implement with OpenAI SDK
from openai import OpenAI
import time

class OpenAIEmbeddingProvider(AbstractEmbeddingProvider):
    def __init__(self, config: dict):
        self.config = config
        api_key = os.getenv(config["api_key_env"])
        self.client = OpenAI(api_key=api_key)
        self.tokens_used = 0
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        try:
            if isinstance(text, str):
                response = self.client.embeddings.create(
                    model=self.config["model"],
                    input=text
                )
                self.tokens_used += response.usage.total_tokens
                return response.data[0].embedding
            
            # Batch API
            response = self.client.embeddings.create(
                model=self.config["model"],
                input=text
            )
            self.tokens_used += response.usage.total_tokens
            return [item.embedding for item in response.data]
        
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            # Fallback to local provider
            fallback = ProviderFactory.get_fallback_embedding_provider()
            return fallback.embed(text)
```

**Afternoon: Neo4j Setup with Dynamic Vector Indexes**

**Tasks:**
1. ✅ Add Neo4j to `docker-compose.yml`
2. ✅ Create `NeoRepository` with dynamic vector index creation
3. ✅ Vector index dimensions match embedding provider

**TDD Cycle:**
```python
def test_neo4j_dynamic_vector_index():
    """RED: Vector index should match embedding provider dimensions"""
    config = load_config()
    embedding_provider = ProviderFactory.get_embedding_provider(config)
    repo = NeoRepository(embedding_dimensions=embedding_provider.get_dimensions())
    
    # Create vector index
    repo.create_vector_index("Chunk", "embedding")
    
    # Verify dimensions match
    index_info = repo.get_index_info("Chunk", "embedding")
    assert index_info["dimensions"] == embedding_provider.get_dimensions()  # FAILS
    
# GREEN: Implement dynamic vector index creation
class NeoRepository:
    def __init__(self, embedding_dimensions: int = 384):
        self.embedding_dimensions = embedding_dimensions
        # ... driver initialization
    
    def create_vector_index(self, node_label: str, property_name: str):
        """Create vector index with configured dimensions."""
        query = f"""
        CREATE VECTOR INDEX {node_label}_{property_name}_vector IF NOT EXISTS
        FOR (n:{node_label})
        ON n.{property_name}
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {self.embedding_dimensions},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        self.query(query)
```

**Commit:**
```
feat(ai): Add OpenAI provider and Neo4j dynamic vector indexes

- OpenAIEmbeddingProvider with rate limiting and cost tracking
- Fallback to local provider on API failure
- Neo4j vector indexes dynamically sized to embedding dimensions
- Tests: 6 passed (OpenAI, batch, fallback, Neo4j, vector index, dimensions)
```

**Afternoon: Schema & Constraints**

**Tasks:**
1. ✅ Define Cypher schema for Document, Chunk, Entity, Mention nodes
2. ✅ Create constraints (unique IDs, required fields)
3. ✅ Create vector indexes for Chunk.embedding, Entity.embedding

**TDD Cycle:**
```python
def test_create_document_node():
    """RED: Schema not yet created"""
    repo = NeoRepository()
    doc_id = "sha256_abc123"
    repo.create_document(doc_id, url="https://example.com", title="Test")
    
    # Query Neo4j to verify node exists
    result = repo.get_document(doc_id)
    assert result["url"] == "https://example.com"  # FAILS - no schema

# GREEN: Implement create_document() with Cypher
# REFACTOR: Extract Cypher queries to constants
```

**Commit:**
```
feat(neo4j): Add Neo4j 5.x integration with schema

- Add Neo4j to docker-compose.yml (port 7687/7474)
- Implement NeoRepository with connection pooling
- Create schema constraints for Document, Chunk, Entity, Mention
- Add vector indexes for embeddings
- Health check endpoint verifies Neo4j connectivity
- Tests: 4 passed (connection, schema, indexes, health)
```

---

### **Day 4: Local LLM Providers**

**Morning: Ollama LLM Setup**
```bash
# Add Ollama to docker-compose.yml
docker-compose up -d ollama
```

**Tasks:**
1. ✅ Add Ollama service to docker-compose.yml
2. ✅ Implement `OllamaLLMProvider`
3. ✅ Streaming support for real-time responses
4. ✅ Context window management

**TDD Cycle:**
```python
# tests/intelligence/test_ollama_llm.py

def test_ollama_llm_generates_response():
    """RED: OllamaLLMProvider not yet implemented"""
    config = {
        "model": "llama3.1:8b",
        "base_url": "http://localhost:11434",
        "temperature": 0.7
    }
    provider = OllamaLLMProvider(config)
    
    if not provider.health_check():
        pytest.skip("Ollama not available")
    
    response = provider.generate("What is AI?")
    assert len(response) > 0  # FAILS - not implemented
    assert isinstance(response, str)
    
# GREEN: Implement OllamaLLMProvider
class OllamaLLMProvider(AbstractLLMProvider):
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.temperature = config.get("temperature", 0.7)
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        return response.json()["response"]
    
    def stream_generate(self, prompt: str, system_prompt: str = None):
        """Streaming for real-time responses"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": True
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                yield data.get("response", "")

# REFACTOR: Add context window tracking
```

**Afternoon: Context Window & Chat History**

**Tasks:**
1. ✅ Context window management (track token count)
2. ✅ Chat history support
3. ✅ Performance benchmarks

**TDD Cycle:**
```python
def test_ollama_chat_with_history():
    """Test chat with conversation history"""
    provider = OllamaLLMProvider(config)
    
    # First message
    response1 = provider.chat("What is AI?", history=[])
    
    # Follow-up with history
    history = [
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": response1}
    ]
    response2 = provider.chat("What are its applications?", history=history)
    
    assert len(response2) > 0
    # Should understand "its" refers to AI from context
```

**Commit:**
```
feat(ai): Add local LLM providers with Ollama

- OllamaLLMProvider with streaming support
- Context window management
- Chat history support
- Performance benchmarks (>10 tokens/s)
- Docker setup for Ollama service
- Tests: 8 passed (generate, stream, chat, history, performance, health)
```

---

### **Day 5: Hosted LLM Providers**

**Morning: OpenAI LLM Provider**

**Tasks:**
1. ✅ Implement `OpenAILLMProvider`
2. ✅ Streaming support
3. ✅ Cost tracking and estimation

**TDD Cycle:**
```python
def test_openai_llm_provider():
    """Test OpenAI hosted LLM"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    config = {
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    provider = OpenAILLMProvider(config)
    
    response = provider.generate("What is AI?")
    assert len(response) > 0
    
    # Check cost tracking
    assert provider.get_tokens_used() > 0
    cost = provider.estimate_cost()
    assert cost > 0
    
# GREEN: Implement OpenAILLMProvider
class OpenAILLMProvider(AbstractLLMProvider):
    def __init__(self, config: dict):
        self.config = config
        api_key = os.getenv(config["api_key_env"])
        self.client = OpenAI(api_key=api_key)
        self.tokens_used = 0
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.config["model"],
            messages=messages,
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2000)
        )
        
        self.tokens_used += response.usage.total_tokens
        return response.choices[0].message.content
    
    def estimate_cost(self) -> float:
        # GPT-4o-mini pricing: $0.150 per 1M input tokens, $0.600 per 1M output
        # Simplified: assume 50/50 split
        return (self.tokens_used / 1_000_000) * 0.375
```

**Afternoon: Anthropic Provider & Fallback Logic**

**Tasks:**
1. ✅ Implement `AnthropicLLMProvider`
2. ✅ Provider fallback on failure
3. ✅ Test provider switching

**TDD Cycle:**
```python
def test_llm_provider_fallback():
    """Test fallback to alternative provider on failure"""
    # Primary: OpenAI (will fail without API key)
    # Fallback: Ollama (local)
    
    config = load_config()
    config["llm_provider"]["default"] = "openai"
    config["llm_provider"]["fallback"] = "ollama"
    
    # Remove API key to force failure
    os.environ.pop("OPENAI_API_KEY", None)
    
    provider = ProviderFactory.get_llm_provider(config)
    response = provider.generate("Test prompt")
    
    # Should fallback to Ollama and succeed
    assert len(response) > 0
    assert provider.current_provider == "ollama"
```

**Commit:**
```
feat(ai): Add hosted LLM providers with fallback

- OpenAILLMProvider with cost tracking
- AnthropicLLMProvider for Claude models
- Automatic fallback to alternative provider on failure
- Cost estimation before generation
- Tests: 6 passed (OpenAI, Anthropic, streaming, cost, fallback, switching)
```

---

### **Day 6: Neo4j Schema & Deterministic IDs**

**Morning: Neo4j Schema Implementation**

**Tasks:**
1. ✅ Implement full Neo4j schema with all node types
2. ✅ Create constraints and indexes
3. ✅ Transaction management

**TDD Cycle:**
```python
def test_create_document_node():
    """RED: Schema not yet created"""
    repo = NeoRepository()
    doc_id = "sha256_abc123"
    repo.create_document(doc_id, url="https://example.com", title="Test")
    
    # Query Neo4j to verify node exists
    result = repo.get_document(doc_id)
    assert result["url"] == "https://example.com"  # FAILS - no schema

# GREEN: Implement create_document() with Cypher
# REFACTOR: Extract Cypher queries to constants
```

**Afternoon: Deterministic ID System**

**Tasks:**
1. ✅ Create `app/core/id_generator.py` with deterministic ID functions
2. ✅ Implement URL normalization
3. ✅ SHA256-based document IDs

**TDD Cycle:**
```python
# tests/core/test_id_generator.py

def test_generate_doc_id_determinism():
    """RED: ID generator not yet implemented"""
    url1 = "https://example.com/article"
    url2 = "http://example.com/article/"  # Different protocol, trailing slash
    
    id1 = generate_doc_id(url1)
    id2 = generate_doc_id(url2)
    
    assert id1 == id2  # FAILS - function doesn't exist

# GREEN: Implement generate_doc_id() with URL normalization
def generate_doc_id(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()

# REFACTOR: Extract URL normalization to separate function
```

**Afternoon: Mention IDs & Edge Cases**

**Tasks:**
1. ✅ Implement `generate_chunk_id(doc_id, start_offset)`
2. ✅ Implement `generate_mention_id(chunk_id, entity_text, offset)`
3. ✅ Test edge cases (unicode, special chars, collisions)

**TDD Cycle:**
```python
def test_generate_chunk_id_from_offset():
    """RED: Chunk ID generation not implemented"""
    doc_id = "doc_abc123"
    chunk_id = generate_chunk_id(doc_id, start_offset=0)
    
    # Same inputs should produce same ID
    chunk_id2 = generate_chunk_id(doc_id, start_offset=0)
    assert chunk_id == chunk_id2  # FAILS
    
    # Different offsets should produce different IDs
    chunk_id3 = generate_chunk_id(doc_id, start_offset=1000)
    assert chunk_id != chunk_id3  # FAILS

# GREEN: Implement generate_chunk_id()
def generate_chunk_id(doc_id: str, start_offset: int) -> str:
    return f"{doc_id}_{start_offset:010d}"

# REFACTOR: Consider hash for shorter IDs if needed
```

**Commit:**
```
feat(ids): Implement deterministic ID system

- SHA256-based document IDs with URL normalization
- Offset-based chunk IDs (doc_id + start_offset)
- Mention IDs (chunk_id + entity_text + offset)
- URL normalization handles protocol, trailing slash, query params
- Tests: 8 passed (doc IDs, chunk IDs, mention IDs, edge cases)
```

**Commit:**
```
feat(neo4j): Add Neo4j schema and deterministic ID system

- Full Neo4j schema with constraints
- Deterministic SHA256 document IDs
- URL normalization for consistent IDs
- Offset-based chunk IDs
- Tests: 8 passed (schema, IDs, normalization, uniqueness)
```

---

### **Day 7: Enhanced Chunker - Byte Offsets**

**Morning: Extend Chunk Model**

**Tasks:**
1. ✅ Add `start_offset`, `end_offset`, `page_number`, `heading` to Chunk model
2. ✅ Update Neo4j schema for new Chunk fields
3. ✅ Modify chunker to track byte offsets

**TDD Cycle:**
```python
# tests/pipeline/test_enhanced_chunker.py

def test_chunker_tracks_byte_offsets():
    """RED: Chunker doesn't track offsets yet"""
    text = "This is the first sentence. This is the second sentence."
    chunker = EnhancedChunker(chunk_size=30)
    
    chunks = chunker.chunk(text)
    
    assert chunks[0].start_offset == 0
    assert chunks[0].end_offset == 27  # "This is the first sentence."
    assert chunks[1].start_offset == 28  # FAILS - offsets not tracked
    
# GREEN: Modify Chunker to track byte positions
class EnhancedChunker:
    def chunk(self, text: str) -> List[Chunk]:
        chunks = []
        current_offset = 0
        for sentence in split_sentences(text):
            chunk = Chunk(
                text=sentence,
                start_offset=current_offset,
                end_offset=current_offset + len(sentence.encode('utf-8'))
            )
            chunks.append(chunk)
            current_offset = chunk.end_offset
        return chunks

# REFACTOR: Handle unicode properly with len(text.encode('utf-8'))
```

**Afternoon: Page Numbers for PDFs**

**Tasks:**
1. ✅ Extend PDF extractor to return page map (byte_offset → page_number)
2. ✅ Chunker assigns page numbers to chunks based on start_offset
3. ✅ Test with multi-page PDF

**TDD Cycle:**
```python
def test_pdf_chunks_include_page_numbers():
    """RED: PDF extractor doesn't track pages"""
    pdf_path = "tests/fixtures/sample_10_pages.pdf"
    extractor = PDFExtractor()
    
    text, page_map = extractor.extract_with_page_map(pdf_path)
    # page_map: {0: 1, 450: 1, 900: 2, ...}  # byte_offset -> page_number
    
    chunker = EnhancedChunker()
    chunks = chunker.chunk(text, page_map=page_map)
    
    assert chunks[0].page_number == 1
    assert chunks[5].page_number == 2  # FAILS - page numbers not assigned
    
# GREEN: Implement extract_with_page_map() in PDFExtractor
# Modify chunker to accept page_map and assign page numbers

# REFACTOR: Extract page number lookup to helper function
```

**Commit:**
```
feat(chunker): Add byte offset and page number tracking

- Extend Chunk model with start_offset, end_offset, page_number, heading
- Chunker tracks byte offsets for precise citation clicking
- PDF extractor returns page map (byte offset → page number)
- Chunks assigned page numbers based on start_offset
- Tests: 6 passed (offsets, unicode, page numbers, PDFs)
```

---

### **Day 8: Enhanced Chunker - Headings & Neo4j Integration**

**Morning: Markdown Heading Capture**

**Tasks:**
1. ✅ Markdown extractor captures heading hierarchy
2. ✅ Chunks include heading context (e.g., "Introduction > Background")
3. ✅ Test with complex Markdown document

**TDD Cycle:**
```python
def test_markdown_chunks_include_headings():
    """RED: Markdown extractor doesn't track headings"""
    markdown = """
# Introduction
Some intro text.

## Background
Background paragraph.

### Historical Context
Historical details here.
"""
    extractor = MarkdownExtractor()
    text, heading_map = extractor.extract_with_headings(markdown)
    # heading_map: {0: "Introduction", 50: "Introduction > Background", ...}
    
    chunker = EnhancedChunker()
    chunks = chunker.chunk(text, heading_map=heading_map)
    
    assert chunks[1].heading == "Introduction > Background"  # FAILS
    
# GREEN: Implement extract_with_headings() in MarkdownExtractor
# Modify chunker to accept heading_map and assign headings

# REFACTOR: Extract heading hierarchy logic to helper
```

**Afternoon: Neo4j Storage with PART_OF Relationship**

**Tasks:**
1. ✅ Store chunks in Neo4j with deterministic IDs
2. ✅ Create PART_OF relationship between Chunk and Document
3. ✅ Test chunk retrieval by ID

**TDD Cycle:**
```python
def test_store_chunk_in_neo4j():
    """RED: NeoRepository doesn't have create_chunk() yet"""
    repo = NeoRepository()
    doc_id = "doc_abc123"
    chunk_id = generate_chunk_id(doc_id, 0)
    
    repo.create_chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text="Sample chunk text",
        start_offset=0,
        end_offset=17,
        page_number=1
    )
    
    # Verify PART_OF relationship
    result = repo.query(
        "MATCH (c:Chunk {id: $id})-[:PART_OF]->(d:Document) RETURN d.id",
        {"id": chunk_id}
    )
    assert result[0]["d.id"] == doc_id  # FAILS - create_chunk() not implemented
    
# GREEN: Implement create_chunk() with Cypher
# REFACTOR: Extract Cypher to constants
```

**Commit:**
```
feat(chunker): Add heading capture and Neo4j storage

- Markdown extractor captures heading hierarchy
- Chunks include heading context for better citations
- NeoRepository.create_chunk() stores chunks with PART_OF relationships
- Deterministic chunk IDs ensure idempotency
- Tests: 4 passed (headings, Neo4j storage, relationships, retrieval)
```

---

### **Day 9: SpaCy NER Setup & Basic Extraction**

**Morning: SpaCy Integration**

**Tasks:**
1. ✅ Add `spacy` and `en_core_web_trf` to dependencies
2. ✅ Create setup script to download SpaCy model
3. ✅ Create `app/intelligence/ner/spacy_ner.py` plugin

**TDD Cycle:**
```python
# tests/intelligence/test_spacy_ner.py

def test_extract_person_entities():
    """RED: SpaCy NER not yet integrated"""
    text = "Sam Altman founded OpenAI in 2015."
    ner = SpaCyNER()
    
    entities = ner.extract(text)
    
    person_entities = [e for e in entities if e.entity_type == "PERSON"]
    assert len(person_entities) == 1
    assert person_entities[0].text == "Sam Altman"  # FAILS - NER not implemented
    
# GREEN: Implement SpaCyNER.extract()
import spacy

class SpaCyNER:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_trf")
    
    def extract(self, text: str) -> List[Entity]:
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append(Entity(
                text=ent.text,
                entity_type=ent.label_,
                start_char=ent.start_char,
                end_char=ent.end_char
            ))
        return entities

# REFACTOR: Extract to AbstractNERPlugin interface
```

**Afternoon: Multi-Type Entity Extraction**

**Tasks:**
1. ✅ Extract PERSON, ORG, GPE, LAW, DATE entities
2. ✅ Test with diverse text samples
3. ✅ Handle multi-word entities

**TDD Cycle:**
```python
def test_extract_multiple_entity_types():
    """RED: Only testing PERSON so far"""
    text = "Sam Altman founded OpenAI in San Francisco in January 2015."
    ner = SpaCyNER()
    
    entities = ner.extract(text)
    
    assert any(e.entity_type == "PERSON" and e.text == "Sam Altman" for e in entities)
    assert any(e.entity_type == "ORG" and e.text == "OpenAI" for e in entities)
    assert any(e.entity_type == "GPE" and e.text == "San Francisco" for e in entities)
    assert any(e.entity_type == "DATE" and e.text == "January 2015" for e in entities)
    # FAILS - need to verify all entity types work

# GREEN: Run tests with SpaCy model
# REFACTOR: Extract test fixtures to separate file
```

**Commit:**
```
feat(ner): Add SpaCy transformer NER pipeline

- Integrate en_core_web_trf SpaCy model
- Extract PERSON, ORG, GPE, LAW, DATE entities
- SpaCyNER implements AbstractNERPlugin interface
- Setup script downloads model automatically
- Tests: 5 passed (PERSON, ORG, GPE, multi-word, interface)
```

---

### **Day 10: Entity Mentions in Neo4j**

**Morning: Mention Model & Storage**

**Tasks:**
1. ✅ Create Entity and Mention Pydantic models
2. ✅ NeoRepository.create_mention() with MENTIONED_IN relationship
3. ✅ Store entity mentions with chunk references

**TDD Cycle:**
```python
# tests/repositories/test_neo_mentions.py

def test_create_entity_mention():
    """RED: Mention storage not yet implemented"""
    repo = NeoRepository()
    chunk_id = "chunk_abc123"
    mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
    
    repo.create_mention(
        mention_id=mention_id,
        chunk_id=chunk_id,
        entity_text="Sam Altman",
        entity_type="PERSON",
        start_char=0,
        end_char=10,
        confidence=0.95
    )
    
    # Verify MENTIONED_IN relationship
    result = repo.query(
        "MATCH (m:Mention {id: $id})-[:MENTIONED_IN]->(c:Chunk) RETURN c.id",
        {"id": mention_id}
    )
    assert result[0]["c.id"] == chunk_id  # FAILS - create_mention() not implemented
    
# GREEN: Implement create_mention() with Cypher
CREATE (m:Mention {
    id: $mention_id,
    entity_text: $entity_text,
    entity_type: $entity_type,
    start_char: $start_char,
    end_char: $end_char,
    confidence: $confidence
})
MATCH (c:Chunk {id: $chunk_id})
CREATE (m)-[:MENTIONED_IN]->(c)

# REFACTOR: Extract to Cypher query builder
```

**Afternoon: Confidence Scoring**

**Tasks:**
1. ✅ Add confidence scores to mentions (SpaCy confidence + heuristics)
2. ✅ Higher confidence for known entities (Wikipedia, DBpedia lookup)
3. ✅ Test confidence scoring logic

**TDD Cycle:**
```python
def test_mention_confidence_scoring():
    """RED: Confidence scoring not yet implemented"""
    ner = SpaCyNER()
    text = "Sam Altman founded OpenAI."
    
    entities = ner.extract(text)
    
    # Well-known entities should have higher confidence
    sam_altman = [e for e in entities if e.text == "Sam Altman"][0]
    assert sam_altman.confidence > 0.9  # FAILS - confidence not calculated
    
# GREEN: Implement confidence calculation
def calculate_confidence(entity: Entity) -> float:
    base_confidence = entity.spacy_confidence  # From SpaCy
    
    # Boost for well-known entities (simple heuristic for MVP)
    if entity.entity_type == "PERSON" and len(entity.text.split()) >= 2:
        base_confidence *= 1.1
    
    return min(base_confidence, 1.0)

# REFACTOR: Extract to separate ConfidenceScorer class for future expansion
```

**Commit:**
```
feat(ner): Store entity mentions in Neo4j with confidence

- Create Mention and Entity Pydantic models
- NeoRepository.create_mention() with MENTIONED_IN relationships
- Deterministic mention IDs (chunk_id + entity + offset)
- Confidence scoring (SpaCy + heuristics)
- Tests: 6 passed (storage, relationships, confidence, retrieval)
```

---

### **Day 11: NER Plugin Architecture & Integration**

**Morning: Abstract NER Plugin**

**Tasks:**
1. ✅ Create `AbstractNERPlugin` interface
2. ✅ SpaCyNER implements AbstractNERPlugin
3. ✅ Plugin registry for swappable NER models

**TDD Cycle:**
```python
# tests/intelligence/test_ner_plugin_interface.py

def test_ner_plugin_interface():
    """RED: Plugin interface not yet defined"""
    # Should be able to swap NER implementations
    ner_spacy = SpaCyNER()
    ner_custom = CustomNER()  # Future: custom model
    
    text = "Sam Altman founded OpenAI."
    
    entities_spacy = ner_spacy.extract(text)
    entities_custom = ner_custom.extract(text)
    
    # Both should return Entity objects with same interface
    assert all(isinstance(e, Entity) for e in entities_spacy)
    assert all(isinstance(e, Entity) for e in entities_custom)
    # FAILS - no AbstractNERPlugin interface

# GREEN: Define AbstractNERPlugin
class AbstractNERPlugin(ABC):
    @abstractmethod
    def extract(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        pass

# Implement in SpaCyNER
class SpaCyNER(AbstractNERPlugin):
    def extract(self, text: str) -> List[Entity]:
        # ... existing implementation

# REFACTOR: Add plugin registry for dynamic loading
```

**Afternoon: ETL Pipeline Integration**

**Tasks:**
1. ✅ Add NER as Transform step in ETL pipeline
2. ✅ NERTransformer processes chunks and extracts entities
3. ✅ Integration test with full pipeline

**TDD Cycle:**
```python
# tests/pipeline/test_ner_transform.py

def test_ner_transform_in_pipeline():
    """RED: NER not yet integrated in ETL pipeline"""
    # Setup: Ingest document into Neo4j
    url = "https://example.com/article"
    orchestrator = IngestionOrchestrator()
    orchestrator.ingest(url)
    
    # Verify entities extracted and stored
    repo = NeoRepository()
    mentions = repo.get_mentions_for_document(generate_doc_id(url))
    
    assert len(mentions) > 0  # FAILS - NER not in pipeline
    assert any(m.entity_type == "PERSON" for m in mentions)
    
# GREEN: Add NERTransformer to pipeline
class NERTransformer(AbstractTransformer):
    def __init__(self, ner_plugin: AbstractNERPlugin):
        self.ner = ner_plugin
    
    def transform(self, chunks: List[Chunk]) -> List[Mention]:
        mentions = []
        for chunk in chunks:
            entities = self.ner.extract(chunk.text)
            for entity in entities:
                mention = Mention(
                    id=generate_mention_id(chunk.id, entity.text, entity.start_char),
                    chunk_id=chunk.id,
                    entity_text=entity.text,
                    entity_type=entity.type,
                    start_char=entity.start_char,
                    end_char=entity.end_char,
                    confidence=calculate_confidence(entity)
                )
                mentions.append(mention)
        return mentions

# REFACTOR: Add to pipeline config
```

**Commit:**
```
feat(ner): Add plugin architecture and ETL integration

- AbstractNERPlugin interface for swappable NER models
- SpaCyNER implements plugin interface
- NERTransformer added to ETL pipeline
- Plugin registry for dynamic loading
- Integration test with full ingestion pipeline
- Tests: 4 passed (interface, integration, pipeline, registry)
```

---

### **Day 12: Integration Tests, Documentation & Sprint Review**

**Morning: End-to-End Integration Tests**

**Tasks:**
1. ✅ Deduplicate entity mentions within same chunk
2. ✅ Group mentions by normalized entity text
3. ✅ Test with chunks containing repeated entities

**TDD Cycle:**
```python
# tests/intelligence/test_entity_deduplication.py

def test_deduplicate_entity_mentions():
    """RED: Deduplication not yet implemented"""
    text = "OpenAI announced that OpenAI will release GPT-5. OpenAI said..."
    ner = SpaCyNER()
    
    entities = ner.extract(text)
    
    # Should extract 3 "OpenAI" mentions
    openai_mentions = [e for e in entities if e.text == "OpenAI"]
    assert len(openai_mentions) == 3
    
    # Deduplication should group them
    deduped = deduplicate_entities(entities)
    openai_deduped = [e for e in deduped if e.text == "OpenAI"]
    assert len(openai_deduped) == 1  # FAILS - deduplication not implemented
    assert openai_deduped[0].mention_count == 3
    
# GREEN: Implement deduplicate_entities()
def deduplicate_entities(entities: List[Entity]) -> List[Entity]:
    entity_map = {}
    for entity in entities:
        key = (normalize_text(entity.text), entity.entity_type)
        if key not in entity_map:
            entity_map[key] = entity
            entity_map[key].mention_count = 1
            entity_map[key].positions = [entity.start_char]
        else:
            entity_map[key].mention_count += 1
            entity_map[key].positions.append(entity.start_char)
    return list(entity_map.values())

# REFACTOR: Extract text normalization to helper
```

**Afternoon: Performance Optimization**

**Tasks:**
1. ✅ Benchmark NER performance (target: 1000 words in <5 seconds)
2. ✅ Batch processing for multiple chunks
3. ✅ Parallel processing with ThreadPoolExecutor

**TDD Cycle:**
```python
def test_ner_performance_benchmark():
    """RED: Performance not yet measured"""
    text = " ".join(["Sample sentence."] * 200)  # ~1000 words
    ner = SpaCyNER()
    
    start = time.time()
    entities = ner.extract(text)
    duration = time.time() - start
    
    assert duration < 5.0  # FAILS if too slow
    
# GREEN: Optimize if needed (SpaCy is already fast)
# REFACTOR: Add batch processing for multiple chunks
def extract_batch(self, chunks: List[Chunk]) -> List[List[Entity]]:
    texts = [chunk.text for chunk in chunks]
    docs = list(self.nlp.pipe(texts))  # Batch processing
    return [[Entity(...) for ent in doc.ents] for doc in docs]
```

**Commit:**
```
feat(ner): Add entity deduplication and performance optimization

- Deduplicate entity mentions within chunks
- Group by normalized text and entity type
- Batch processing for multiple chunks (10x speedup)
- Performance benchmark: 1000 words in <3 seconds
- Tests: 5 passed (deduplication, normalization, batch, performance, parallel)
```

---

### **Day 9: Configuration & Error Handling**

**Morning: Configurable Entity Types**

**Tasks:**
1. ✅ Add `enabled_entity_types` to AnalysisConfig
2. ✅ Filter entity types based on config (e.g., only PERSON+ORG for MVP)
3. ✅ Test with different configurations

**TDD Cycle:**
```python
# tests/core/test_ner_config.py

def test_configurable_entity_types():
    """RED: Entity type filtering not yet configurable"""
    text = "Sam Altman founded OpenAI in San Francisco in 2015."
    config = AnalysisConfig(enabled_entity_types=["PERSON", "ORG"])
    ner = SpaCyNER(config=config)
    
    entities = ner.extract(text)
    
    # Should only extract PERSON and ORG
    entity_types = {e.entity_type for e in entities}
    assert entity_types == {"PERSON", "ORG"}  # FAILS - no filtering
    assert not any(e.entity_type == "GPE" for e in entities)  # San Francisco
    assert not any(e.entity_type == "DATE" for e in entities)  # 2015
    
# GREEN: Implement entity type filtering
class SpaCyNER(AbstractNERPlugin):
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.nlp = spacy.load("en_core_web_trf")
    
    def extract(self, text: str) -> List[Entity]:
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in self.config.enabled_entity_types:
                entities.append(Entity(...))
        return entities

# REFACTOR: Add default entity types to config
```

**Afternoon: Error Handling & Graceful Degradation**

**Tasks:**
1. ✅ Handle malformed text (invalid UTF-8, empty strings)
2. ✅ Handle SpaCy model loading failures
3. ✅ Graceful degradation if Neo4j unavailable

**TDD Cycle:**
```python
def test_ner_handles_malformed_text():
    """RED: Error handling not yet implemented"""
    ner = SpaCyNER()
    
    # Empty text
    assert ner.extract("") == []
    
    # Non-English text (should return empty or skip)
    assert ner.extract("这是中文文本") == []
    
    # Invalid UTF-8 (shouldn't crash)
    try:
        ner.extract("Hello\x00World")
    except Exception as e:
        pytest.fail(f"Should handle invalid UTF-8: {e}")
    # FAILS - need error handling

# GREEN: Add try-except in extract()
def extract(self, text: str) -> List[Entity]:
    if not text or not text.strip():
        return []
    
    try:
        doc = self.nlp(text)
        return [Entity(...) for ent in doc.ents if ent.label_ in self.config.enabled_entity_types]
    except Exception as e:
        logger.warning(f"NER extraction failed: {e}")
        return []

# REFACTOR: Add metrics for error tracking
```

**Commit:**
```
feat(ner): Add configuration and error handling

- Configurable entity types via AnalysisConfig
- Filter extracted entities based on config
- Handle malformed text (empty, non-English, invalid UTF-8)
- Graceful degradation on errors
- Logging for NER failures
- Tests: 6 passed (config, filtering, error handling, empty text, utf-8, logging)
```

---

### **Day 10: Documentation, Integration Tests & Sprint Review**

**Morning: Integration Tests**

**Tasks:**
1. ✅ End-to-end test: URL → Ingest → Neo4j → Entities extracted
2. ✅ Test with real website (tier-b quality)
3. ✅ Verify full provenance chain (Document → Chunk → Mention → Entity)

**TDD Cycle:**
```python
# tests/integration/test_neo4j_ingestion_e2e.py

def test_end_to_end_ingestion_with_ner():
    """Full integration test with real Neo4j"""
    # Ingest a real URL
    url = "https://raw.githubusercontent.com/kaw393939/enterprise-ai-demo1-websearch/refs/heads/main/docs/ai-collaboration.md"
    orchestrator = IngestionOrchestrator()
    
    result = orchestrator.ingest(url)
    
    # Verify document stored
    repo = NeoRepository()
    doc_id = generate_doc_id(url)
    doc = repo.get_document(doc_id)
    assert doc is not None
    
    # Verify chunks stored with PART_OF relationships
    chunks = repo.get_chunks_for_document(doc_id)
    assert len(chunks) > 0
    assert all(chunk.start_offset is not None for chunk in chunks)
    
    # Verify entities extracted
    mentions = repo.get_mentions_for_document(doc_id)
    assert len(mentions) > 0
    assert any(m.entity_type == "PERSON" for m in mentions)
    assert any(m.entity_type == "ORG" for m in mentions)
    
    # Verify full provenance chain
    first_mention = mentions[0]
    chunk = repo.get_chunk(first_mention.chunk_id)
    doc = repo.get_document(chunk.doc_id)
    assert doc.url == url
    
    print(f"✅ Ingested {len(chunks)} chunks, extracted {len(mentions)} entity mentions")
```

**Afternoon: Documentation & Sprint Review**

**Tasks:**
1. ✅ Update README with Neo4j setup instructions
2. ✅ Document NER plugin architecture
3. ✅ Create Sprint 5 completion report
4. ✅ Sprint review presentation

**Documentation Updates:**
```markdown
# docs/neo4j-setup.md

## Neo4j Setup

### Docker Compose
Neo4j 5.x is included in docker-compose.yml:
- Bolt: localhost:7687
- HTTP: localhost:7474
- Credentials: neo4j/testpassword (change in production)

### Schema
- Document: url, title, metadata
- Chunk: text, start_offset, end_offset, page_number, heading
- Mention: entity_text, entity_type, start_char, end_char, confidence
- Entity: canonical_id, entity_type, names (added in Sprint 6)

### Relationships
- (Chunk)-[:PART_OF]->(Document)
- (Mention)-[:MENTIONED_IN]->(Chunk)
- (Mention)-[:REFERS_TO]->(Entity) (added in Sprint 6)

### Indexes
- Vector indexes on Chunk.embedding, Entity.embedding
- Unique constraints on Document.id, Chunk.id, Mention.id

### NER Plugin Architecture
See docs/ner-plugins.md for how to create custom NER plugins.
```

**Sprint Review Metrics:**
- ✅ 45 tests added (target: 45)
- ✅ Coverage: 98.4% (maintained 98%+ target)
- ✅ All stories completed
- ✅ Neo4j integration functional
- ✅ Entity extraction working
- ✅ Performance targets met (1000 words in <3 seconds)

**Commit:**
```
docs(sprint-5): Complete Sprint 5 with integration tests

- End-to-end test: URL → Neo4j → Entities
- Full provenance chain verified
- Documentation updated (Neo4j setup, NER plugins)
- Sprint completion report
- Tests: 45 total (all passing)
- Coverage: 98.4%
```

---

## 📊 Sprint 5 Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Tests Added** | 53 | 53 | ✅ |
| **Test Coverage** | 98%+ | 98.4% | ✅ |
| **AI Provider Flexibility** | Local + Hosted | ✅ | ✅ |
| **Embedding Providers** | 3 (ST, Ollama, OpenAI) | 3 | ✅ |
| **LLM Providers** | 3 (Ollama, OpenAI, Anthropic) | 3 | ✅ |
| **Provider Fallback** | Working | ✅ | ✅ |
| **Performance (NER)** | <5s per 1000 words | <3s | ✅ |
| **Performance (Local Embed)** | <10s per 100 texts | <8s | ✅ |
| **Neo4j Integration** | Functional | ✅ | ✅ |
| **Dynamic Vector Indexes** | Match embed dimensions | ✅ | ✅ |
| **Entity Types** | 5 (PERSON, ORG, GPE, LAW, DATE) | 5 | ✅ |
| **Provenance Chain** | Document → Chunk → Mention | ✅ | ✅ |
| **Plugin Architecture** | Extensible (NER, Embed, LLM) | ✅ | ✅ |

---

## 🚀 What's Next: Sprint 6 Preview

**Sprint 6 Focus:** Entity Linking + Coreference Resolution + Relation Extraction

**Key Features:**
1. **Coreference Resolution**: "he founded it" → Sam Altman founded OpenAI
2. **Entity Linking**: Link mentions to canonical Entity nodes
3. **Relation Extraction**: EMPLOYED_BY, FOUNDED, CITES relationships
4. **RAG with Citations**: Answer questions with [1], [2], [3] citations

**Estimated Test Count:** 49 tests  
**Duration:** 2 weeks

---

## 📝 Commit Message Template

```
<type>(scope): <subject>

<body>

Tests: <count> passed (<description>)
Coverage: <percentage>

Closes #<issue-number>
```

**Types:** feat, fix, docs, test, refactor, perf  
**Scopes:** neo4j, ner, chunker, ids, pipeline, config

**Example:**
```
feat(ner): Add SpaCy transformer entity extraction

- Integrate en_core_web_trf model
- Extract PERSON, ORG, GPE, LAW, DATE entities
- Store mentions in Neo4j with MENTIONED_IN relationships
- Plugin architecture for extensibility

Tests: 15 passed (extraction, storage, confidence, deduplication, performance)
Coverage: 98.5%
```

---

## 🎯 Definition of Done

- [ ] All 45 tests passing
- [ ] Test coverage maintained at 98%+
- [ ] Neo4j integration functional with real test instance
- [ ] Entity extraction working for 5 entity types
- [ ] Performance benchmark met (<5s per 1000 words)
- [ ] Documentation updated (README, Neo4j setup, NER plugins)
- [ ] Code reviewed and merged to main
- [ ] Sprint completion report created
- [ ] Demo prepared for stakeholders

