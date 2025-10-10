# Williams Framework AI Librarian

> **Your Personal AI Research Assistant for Maintaining the Williams Framework**

A production-grade, AI-powered knowledge management system that curates, organizes, and maintains a research library focused on AI/ML developments.

## 🎯 Vision

This system acts as your personal librarian, intelligently managing your content library by:
- **Discovering** relevant AI/ML content from multiple sources
- **Screening** content with AI to surface only high-quality, relevant materials
- **Organizing** content into a browsable, semantic knowledge base
- **Maintaining** your library with dead link detection, duplicate management, and updates
- **Answering** questions about your knowledge base with natural language

## 🏗️ Architecture Principles

### SOLID + DRY + TDD
- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed**: Extensible via plugin system
- **Liskov Substitution**: Interface-based design
- **Interface Segregation**: Minimal, focused interfaces
- **Dependency Inversion**: Depend on abstractions
- **Don't Repeat Yourself**: Shared utilities and base classes
- **Test-Driven Development**: Tests written first, 90%+ coverage

### Core Design Patterns
- **Strategy Pattern**: Multiple content extractors (Web, YouTube, PDF)
- **Factory Pattern**: Content processor factory
- **Repository Pattern**: Data access abstraction
- **Observer Pattern**: Event-driven architecture for monitoring
- **Chain of Responsibility**: ETL pipeline stages
- **Builder Pattern**: Prompt construction
- **Adapter Pattern**: External service integration

## 🛠️ Technology Stack

### Core Framework
- **Python 3.11+**: Modern Python with type hints
- **Pydantic 2.x**: Data validation and settings
- **SQLAlchemy 2.x**: Database ORM
- **Asyncio**: Concurrent processing

### UI Layer
- **Streamlit**: Interactive web interface
- **Plotly**: Interactive visualizations
- **PyVis**: Knowledge graph visualization

### AI/ML
- **OpenAI API**: GPT-5 (high), GPT-5-mini (medium), GPT-5-nano (low)
- **LangChain**: LLM orchestration, chains, memory
- **ChromaDB**: Local vector database
- **spaCy**: NER and NLP
- **NetworkX**: Knowledge graph construction

### ETL
- **Trafilatura**: Web content extraction
- **yt-dlp**: YouTube video/transcript download
- **PyPDF**: PDF processing
- **BeautifulSoup4**: HTML parsing
- **HTTPX**: Async HTTP client

### Testing
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **Hypothesis**: Property-based testing

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-service orchestration
- **Redis**: Caching layer
- **PostgreSQL**: Metadata storage
- **Prometheus**: Metrics collection

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────┐
│               PRESENTATION LAYER                     │
│  Streamlit UI: Digest | Library | Search | Chat     │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              APPLICATION LAYER                       │
│  Services: Digest | Curation | Librarian | Search   │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              INTELLIGENCE LAYER                      │
│  LLM Router | LangChain | Prompt Builder | Cost     │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                 ETL PIPELINE                         │
│  Extract | Transform | Load | Knowledge Graph       │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                  DATA LAYER                          │
│  ChromaDB | File System | PostgreSQL | Redis        │
└─────────────────────────────────────────────────────┘
```

## 🎯 Core Features

### Phase 1: Foundation (MVP)
- [x] Project structure and configuration
- [ ] Domain models (Pydantic)
- [ ] Model router with cost optimization
- [ ] ChromaDB repository
- [ ] Basic content extraction (Web)
- [ ] File system organization
- [ ] Simple Streamlit UI

### Phase 2: Intelligence
- [ ] LangChain integration
- [ ] URL screening with GPT-5-nano
- [ ] Content summarization with GPT-5-mini
- [ ] Quality validation
- [ ] Cost tracking and optimization

### Phase 3: Knowledge Graph
- [ ] NER with spaCy
- [ ] Relationship extraction with LLM
- [ ] Graph construction with NetworkX
- [ ] Graph visualization

### Phase 4: Full Experience
- [ ] Daily digest generation
- [ ] Library browser UI
- [ ] Semantic search
- [ ] Chat interface
- [ ] Maintenance worker

## 🔌 Plugin System

The system supports plugins for:
- **Content Extractors**: Add new content sources
- **Transformers**: Add custom processing steps
- **Tools**: Integrate OpenAI tools (web_search, file_search, etc.)
- **Enrichers**: Add metadata enrichment

## 💰 Cost Optimization

### Model Selection Matrix
| Task Complexity | Model | Cost/1M tokens | Use Case |
|----------------|-------|----------------|----------|
| Low | gpt-5-nano | $0.05 input | URL screening, classification |
| Medium | gpt-5-mini | $0.25 input | Summarization, simple analysis |
| High | gpt-5 | $1.25 input | Complex reasoning, validation |

### Cost Control Features
- Prompt caching (7-day TTL)
- Batch processing (10 items/call)
- Token optimization
- Monthly budget tracking
- Feature flags for expensive operations

## 🧪 Testing Strategy

### Test Pyramid
- **70% Unit Tests**: Pure function logic
- **20% Integration Tests**: Service + Repository
- **10% E2E Tests**: Full workflows

### No Mocks in Integration Tests
Real instances of:
- ChromaDB (ephemeral collections)
- PostgreSQL (test database)
- File system (temp directories)
- OpenAI API (actual calls with budget limits)

### TDD Process
1. **Red**: Write failing test
2. **Green**: Minimal implementation
3. **Refactor**: Apply patterns, ensure SOLID

## 📁 Project Structure

See [docs/project-structure.md](docs/project-structure.md) for detailed structure.

## 🚀 Quick Start

```bash
# Clone repository
cd /home/kwilliams/is373/williams-librarian

# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run tests
poetry run pytest

# Start application
poetry run streamlit run app/main.py
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Domain Model](docs/domain-model.md)
- [API Cost Optimization](docs/cost-optimization.md)
- [Testing Guide](docs/testing-guide.md)
- [Plugin Development](docs/plugin-development.md)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

This is a personal research project. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🙏 Acknowledgments

Built on top of:
- OpenAI API (GPT-5 family)
- LangChain
- ChromaDB
- Streamlit
