# Neo4j Provenance-First Architecture - Analysis & Adaptation

**Date**: October 12, 2025  
**Status**: Strategic Architecture Decision  
**Impact**: HIGH - Affects entire ingestion pipeline and data model

---

## 🎯 Executive Summary

**Recommendation**: Implement Neo4j knowledge graph architecture **BEFORE** FastAPI real-time streaming.

**Why**: This is a **foundational architecture change** that transforms how we ingest, store, and query content. The FastAPI streaming should stream progress for the NEW pipeline, not the old one. Doing FastAPI first would mean rebuilding it immediately after.

**Approach**: Hybrid Neo4j + Qdrant strategy, phased implementation over 3 sprints.

---

## 📊 Current vs. Proposed Architecture

### Current State (Sprints 1-4)

```
URL → Extract → Transform → Load
                    ↓
              Basic metadata
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
    Qdrant vectors      MinIO files
    (embeddings)        (markdown)
         ↓                     ↓
    Vector search       File storage
```

**Capabilities**:
- ✅ Basic extraction (HTML, PDF, YouTube)
- ✅ Simple transformation (summary, tags)
- ✅ Vector embeddings (Qdrant)
- ✅ File storage (MinIO)
- ✅ Simple search

**Missing**:
- ❌ No entity recognition (NER)
- ❌ No entity linking
- ❌ No relation extraction
- ❌ No knowledge graph
- ❌ No provenance tracking
- ❌ No coreference resolution
- ❌ No clickable citations with offsets
- ❌ No page mapping (PDFs)
- ❌ No "explain this answer" subgraphs

---

### Proposed State (Neo4j + Enhanced Pipeline)

```
URL → Fetch → Chunk → Coref → NER → Link → Relations → Embed → Index
         ↓      ↓       ↓      ↓      ↓       ↓         ↓        ↓
      MinIO  MinIO   MinIO  MinIO  MinIO   MinIO    MinIO   Neo4j + Qdrant
      raw/   derived/ coref  mentions links  relations embeddings  (dual index)
                ↓                                                    ↓
                └────────────────────────────────────────────> Knowledge Graph
                                                                     ↓
                                                              ┌──────┴──────┐
                                                              ↓             ↓
                                                         RAG with      Graph Viz
                                                         Citations     & Export
```

**New Capabilities**:
- ✅ Full provenance (doc → chunk → mention → entity → relation)
- ✅ Knowledge graph (entities and relationships)
- ✅ Clickable citations (byte offsets, page maps)
- ✅ Entity linking (canonical entity IDs)
- ✅ Coreference resolution (he/she/it → actual entity)
- ✅ Relation extraction (EMPLOYED_BY, FOUNDED, CITES)
- ✅ Graph-guided retrieval (filter by entities, dates, relationships)
- ✅ "Explain this answer" subgraph exports
- ✅ Deterministic IDs (idempotent re-ingestion)

---

## 🤔 Key Architectural Decisions

### Decision 1: Neo4j vs. Qdrant for Vectors?

**Option A: Neo4j Only (Recommended for MVP)**
- ✅ Simpler architecture (one database)
- ✅ Neo4j 5+ has native vector indexes
- ✅ Graph-guided retrieval in single query
- ✅ Lower operational complexity
- ✅ Good for single-user local setup
- ⚠️ Vector performance less mature than Qdrant
- ⚠️ May need Qdrant for scale later

**Option B: Hybrid Neo4j + Qdrant (Future)**
- ✅ Best of both: graph + specialized vector DB
- ✅ Graph prefilter → Qdrant search (outlined in spec)
- ✅ Proven vector performance at scale
- ❌ More complexity (two DBs to manage)
- ❌ More expensive (cloud costs)
- ❌ Overkill for single-user

**Decision**: Start with **Neo4j-only** (Option A), add Qdrant as optional optimization in future sprint.

**Implementation**: Keep Qdrant code dormant, make vector store configurable.

---

### Decision 2: When to Implement This?

**Option A: Before FastAPI Sprint (Recommended)**
- ✅ FastAPI streams progress for NEW pipeline
- ✅ Don't build real-time streaming twice
- ✅ Foundation correct from start
- ❌ Delays visible progress (no UI updates yet)
- ❌ Larger scope before user-facing features

**Option B: After FastAPI Sprint**
- ✅ Get UI working faster
- ✅ Show incremental progress
- ❌ Have to rebuild FastAPI streaming for new pipeline
- ❌ Throw away current simple pipeline
- ❌ More total work

**Decision**: **Before FastAPI** (Option A). This is foundational.

---

### Decision 3: Migration Strategy?

**Option A: Big Bang (Replace Everything)**
- Rewrite entire pipeline at once
- High risk, long feedback cycle
- ❌ Not recommended

**Option B: Phased (3 Sprints)**
- Sprint 5: Neo4j + Basic NER/Linking
- Sprint 6: Relations + Provenance
- Sprint 7: FastAPI + Real-time Streaming
- ✅ Recommended approach

**Decision**: **Phased** (Option B) with clear milestones.

---

## 📋 Adaptation to Williams Framework

### What to Keep from Spec

✅ **Core Concepts**:
- Deterministic IDs (sha256-based `doc_id`)
- Provenance chains (doc → chunk → mention → entity)
- MinIO structured layout (raw/ + derived/)
- Neo4j graph model (Document, Chunk, Entity, Relations)
- Clickable citations with offsets
- Idempotent re-ingestion
- Cost controls and privacy-first

✅ **Pipeline Stages**:
1. Fetch/Normalize
2. Chunker (deterministic offsets)
3. Coreference (local model)
4. NER (spaCy)
5. Entity Linking (local alias table first)
6. Relation Extraction (precision-first)
7. Embeddings (per chunk + optional per entity)
8. Indexing (Neo4j with vector indexes)

✅ **RAG Enhancements**:
- `/v1/rag/query` with citations
- `/v1/rag/explain` for subgraphs
- Graph export (GraphML, JSON)

---

### What to Adapt for Williams Framework

#### 1. Tier System Integration

**Spec**: No tier concept  
**Williams**: Keep tier-a/b/c/d quality scoring

**Adaptation**:
```python
# Add to Document node
:Document {
    doc_id: str,
    tier: str,           # NEW: tier-a through tier-d
    quality_score: float, # NEW: 0-10 screening score
    # ... existing fields
}

# MinIO layout becomes:
raw/{tier}/{doc_id}/source.ext
derived/{tier}/{doc_id}/manifest.json
# ... etc
```

**Benefit**: Maintain quality-first curation while adding provenance.

---

#### 2. Model Router Integration

**Spec**: Fixed model choices  
**Williams**: Dynamic model routing (nano/mini/standard)

**Adaptation**:
```python
class PipelineConfig:
    ner_model: ModelComplexity = ModelComplexity.MINI
    linking_model: ModelComplexity = ModelComplexity.STANDARD
    relation_model: ModelComplexity = ModelComplexity.STANDARD
    embedding_model: str = "bge-m3"
    
    # Cost tracking per stage
    cost_caps: dict[str, float] = {
        "ner": 0.10,      # per doc
        "linking": 0.50,  # per doc
        "relations": 1.00 # per doc
    }
```

**Benefit**: Preserve cost optimization strategy.

---

#### 3. Plugin Architecture

**Spec**: Hardcoded extractors  
**Williams**: Plugin registry for extensibility

**Adaptation**:
```python
# Keep existing plugin system
class NERPlugin(Plugin):
    async def extract_entities(
        self, 
        chunk: Chunk, 
        context: dict
    ) -> list[Mention]:
        """Plugin hook for custom NER models"""
        
class LinkingPlugin(Plugin):
    async def link_entity(
        self,
        mention: Mention,
        candidates: list[Entity],
        context: dict
    ) -> Link:
        """Plugin hook for custom entity linking"""
```

**Benefit**: Allow domain-specific NER/linking (legal, medical, technical).

---

#### 4. Existing Services Integration

**Spec**: New endpoints  
**Williams**: Extend existing services

**Adaptation**:
```python
# Enhance existing SearchService
class SearchService:
    async def semantic_search(
        self, 
        query: str,
        filters: SearchFilters  # NEW: entity, date, relation filters
    ) -> SearchResult:
        # Use Neo4j graph-guided retrieval
        
    async def explain_answer(
        self,
        chunk_ids: list[str]
    ) -> SubGraph:
        # NEW: Return provenance subgraph

# Enhance existing ContentService  
class ContentService:
    async def screen_url(self, url: str) -> ScreeningResult:
        # Keep existing screening logic
        
    async def process_content_advanced(
        self,
        source: ContentSource
    ) -> EnhancedPipelineResult:
        # NEW: Full NER/linking/relations pipeline
```

**Benefit**: Preserve existing functionality, add enhanced mode.

---

#### 5. Testing Patterns

**Spec**: Generic test approach  
**Williams**: TDD with real services (no mocks)

**Adaptation**:
```python
# tests/integration/pipeline/test_ner_real_neo4j.py

@pytest.fixture
async def neo4j_driver():
    """REAL Neo4j instance in Docker (no mocks)"""
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    yield driver
    # Cleanup test data
    await cleanup_test_documents(driver)

@pytest.mark.asyncio
async def test_ner_pipeline_stores_entities_in_real_neo4j(neo4j_driver):
    """Should extract entities and store in REAL Neo4j"""
    # Ingest test document
    result = await pipeline.process_content_advanced(test_source)
    
    # Verify in REAL Neo4j
    entities = await neo4j_driver.execute_query(
        "MATCH (e:Entity)-[:MENTIONS]-(c:Chunk {chunk_id: $chunk_id}) RETURN e",
        chunk_id=result.chunks[0].chunk_id
    )
    
    assert len(entities) > 0
    assert entities[0]["type"] in ["PERSON", "ORG", "GPE"]
```

**Benefit**: Maintain 90%+ coverage with real integration tests.

---

## 🗺️ Phased Implementation Roadmap

### Sprint 5: Neo4j Foundation + Basic NER

**Duration**: 2 weeks  
**Goal**: Neo4j graph database with basic entity extraction

**Stories**:
1. **S5-501**: Neo4j Integration & Schema
   - Set up Neo4j container in docker-compose
   - Create node/relationship schema
   - Vector index creation
   - Connection pooling
   - **Tests**: 12 integration tests with real Neo4j

2. **S5-502**: Deterministic ID System
   - SHA256-based `doc_id`
   - Offset-based `chunk_id`
   - Mention/relation ID generators
   - **Tests**: 8 unit tests for ID determinism

3. **S5-503**: Enhanced Chunker with Provenance
   - Deterministic byte offsets
   - Heading path capture
   - Page map for PDFs (char → page/bbox)
   - **Tests**: 10 tests (unit + integration with real PDFs)

4. **S5-504**: NER Pipeline (SpaCy)
   - Entity extraction (PERSON, ORG, GPE, etc.)
   - Confidence scoring
   - Model versioning
   - Store to Neo4j
   - **Tests**: 15 tests with real SpaCy model

**Deliverables**:
- ✅ Neo4j running in docker-compose
- ✅ Documents, Chunks, Entities in graph
- ✅ Basic NER working with confidence scores
- ✅ Provenance chain: doc → chunk → entity
- ✅ 45+ tests, 90%+ coverage

**Acceptance**: Ingest a test article → see entities in Neo4j → query by Cypher.

---

### Sprint 6: Entity Linking + Relations

**Duration**: 2 weeks  
**Goal**: Canonical entities and relationship extraction

**Stories**:
1. **S6-601**: Coreference Resolution
   - Integrate local coref model
   - Chain tracking per chunk
   - Store coref_chain_id in mentions
   - **Tests**: 10 tests with real coref examples

2. **S6-602**: Entity Linking System
   - Local alias table (CSV seed)
   - Candidate generation
   - Optional LLM reranking (budget-controlled)
   - Canonical entity IDs (eid)
   - **Tests**: 12 tests with real alias lookups

3. **S6-603**: Relation Extraction
   - Pattern-based extraction (EMPLOYED_BY, FOUNDED, CITES)
   - LLM verifier (precision-first)
   - Provenance storage (chunk_id, span, quote)
   - **Tests**: 15 tests with real text examples

4. **S6-604**: RAG with Citations
   - Enhance search to return citations
   - Include byte offsets and quotes
   - Page map integration for PDFs
   - **Tests**: 12 tests for citation accuracy

**Deliverables**:
- ✅ Coref chains in graph
- ✅ Canonical entities linked
- ✅ Relations extracted and stored
- ✅ RAG returns clickable citations
- ✅ 49+ tests, 90%+ coverage

**Acceptance**: Ask "Who founded OpenAI?" → get answer with citation showing exact quote and page number.

---

### Sprint 7: FastAPI Real-time + Graph Viz

**Duration**: 2 weeks  
**Goal**: Real-time streaming UI + graph export

**Stories**:
1. **S7-701**: FastAPI Progress Streaming (adapted from previous plan)
   - Stream NEW pipeline stages: fetch, chunk, coref, ner, link, relations, embed, index
   - SSE events for each stage
   - **Tests**: 15 tests with real SSE

2. **S7-702**: Streamlit Ingestion UI
   - Submit URLs
   - Real-time progress display
   - Show entities extracted
   - **Tests**: 8 UI tests

3. **S7-703**: Graph Export APIs
   - `/v1/graph/export/json` (D3-ready)
   - `/v1/graph/export/graphml` (Cypher → GraphML)
   - `/v1/rag/explain` (subgraph for answer)
   - **Tests**: 10 tests

4. **S7-704**: Graph Visualization Page
   - Streamlit page with D3.js or Plotly
   - Show entities and relations
   - Click nodes → see provenance
   - **Tests**: 6 integration tests

**Deliverables**:
- ✅ FastAPI streaming for NEW pipeline
- ✅ Streamlit shows real-time NER progress
- ✅ Graph visualization working
- ✅ Export subgraphs as JSON/GraphML
- ✅ 39+ tests, 90%+ coverage

**Acceptance**: Ingest → watch entities appear in real-time → visualize knowledge graph → export.

---

## 💰 Cost & Effort Analysis

### Comparison

| Approach | Sprints | Tests | Lines of Code | Risk |
|----------|---------|-------|---------------|------|
| **Original Plan** (FastAPI only) | 1 | 40 | ~2,000 | Low |
| **Neo4j First** (Recommended) | 3 | 133+ | ~8,000 | Medium |
| **Neo4j After** (Not recommended) | 4 | 173+ | ~10,000 | High (rework) |

### Why Neo4j First is Less Work

**If we do FastAPI first, then Neo4j**:
1. Sprint 5: Build FastAPI streaming for OLD pipeline (40 tests, 2k LOC)
2. Sprint 6-7: Build Neo4j pipeline (93 tests, 6k LOC)
3. Sprint 8: **REBUILD** FastAPI to stream NEW pipeline (40 tests, 2k LOC - WASTED)

**Total**: 173 tests, ~10k LOC, **HIGH REWORK**

**If we do Neo4j first, then FastAPI**:
1. Sprint 5-6: Build Neo4j pipeline (94 tests, 6k LOC)
2. Sprint 7: Build FastAPI streaming for NEW pipeline (39 tests, 2k LOC)

**Total**: 133 tests, ~8k LOC, **NO REWORK**

**Savings**: 40 tests, ~2k LOC, **avoid complete FastAPI rebuild**

---

## 🎯 Recommended Path Forward

### Immediate Actions (This Week)

1. **Review & Approve** this analysis
2. **Update business plan** to reflect knowledge graph capabilities
3. **Add Neo4j to docker-compose.yml**
4. **Create Sprint 5 detailed TDD plan** (Neo4j Foundation)
5. **Postpone** FastAPI streaming to Sprint 7

### Updated Sprint Sequence

```
✅ Sprint 1-4: Foundation (COMPLETE)
⏳ Sprint 5: Neo4j + NER (2 weeks) - START HERE
⏳ Sprint 6: Linking + Relations (2 weeks)
⏳ Sprint 7: FastAPI + Viz (2 weeks)
⏳ Sprint 8: Polish + Demo (1 week)
```

**Total**: 7 weeks to complete advanced pipeline with real-time UI

---

## ❓ Discussion Questions

### Technical
1. **Neo4j Edition**: Use Community (free) or Enterprise (paid)? Community sufficient for single-user.
2. **Vector Dimensions**: Stick with current embedding model or switch? (spec suggests bge-m3, 1024-dim)
3. **NER Model**: SpaCy transformer (accurate, slower) or statistical (fast, less accurate)?
4. **Coref Model**: Which local model? (AllenNLP, Hugging Face, SpanBERT?)

### Strategic
1. **Should we keep Qdrant dormant** or remove completely? Recommend: Keep config flag, dormant code.
2. **Entity linking web lookups**: Off by default per spec, but do we want Wikidata integration later? Recommend: Yes, post-MVP.
3. **Relation types**: Start with which set? Recommend: EMPLOYED_BY, FOUNDED, CITES, AUTHORED.

### Product
1. **Priority**: Graph viz vs. real-time progress? Both important, graph viz wins (more differentiation).
2. **Demo dataset**: What to showcase? Recommend: AI research papers (transformers, GPT, etc.) - aligns with business plan.

---

## 📊 Impact on Business Plan

### Enhanced Value Propositions

**Before** (Current):
> "Williams AI curates content, generates podcasts, and provides voice conversations with your knowledge base."

**After** (Neo4j + Provenance):
> "Williams AI builds a **provenance-tracked knowledge graph** from your research, enabling **AI answers with clickable citations**, **relationship discovery**, and **explainable reasoning paths**."

### New Competitive Advantages

| Competitor | Citations | Provenance | Knowledge Graph | Our Advantage |
|------------|-----------|------------|-----------------|---------------|
| ChatGPT | ❌ | ❌ | ❌ | **Full provenance + explainable answers** |
| Perplexity | ⚡ Basic | ❌ | ❌ | **Byte-level offsets + graph relationships** |
| Notion AI | ❌ | ❌ | ❌ | **Knowledge graph + entity linking** |
| **Williams AI** | ✅ | ✅ | ✅ | **Only integrated solution** |

### Investor Pitch Enhancement

**New slides**:
- "Provenance-First Architecture" - Every answer traceable to source
- "Knowledge Graph" - Entities and relationships, not just keywords
- "Explainable AI" - Show reasoning paths, not black boxes
- "Graph Visualization" - See how concepts connect

**Strengthens**:
- IP/defensibility (complex pipeline)
- Product differentiation (unique capabilities)
- Enterprise value (audit trails, compliance)
- Trust & transparency (verify every claim)

---

## ✅ Acceptance Criteria for This Decision

We proceed with Neo4j-first approach if:
- ✅ Team agrees this is foundational (not premature optimization)
- ✅ Effort estimate acceptable (3 sprints = 6 weeks)
- ✅ Business value clear (citations + graph > real-time streaming alone)
- ✅ Risk manageable (phased approach with tests)
- ✅ Docker setup straightforward (Neo4j container works)

---

## 🚀 Next Steps

**If Approved**:
1. Add Neo4j to `docker-compose.yml` (5.x with vector support)
2. Create `docs/SPRINT-5-NEO4J-TDD-PLAN.md` (detailed day-by-day)
3. Seed alias table CSV with test entities
4. Download SpaCy model: `python -m spacy download en_core_web_trf`
5. Start S5-501: Neo4j integration tests (RED phase)

**First Command**:
```bash
# Add Neo4j to docker-compose
# Then verify
sudo docker-compose up -d neo4j
sudo docker-compose logs neo4j
```

---

**Your call**: Should we proceed with Neo4j-first approach? Any concerns or modifications?
