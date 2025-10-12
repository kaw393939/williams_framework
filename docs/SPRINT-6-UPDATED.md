# Sprint 6: Entity Linking + Relations + RAG Citations - UPDATED TDD Plan

**Duration:** 2 weeks (10 working days)  
**Focus:** Build on Sprint 5 entity extraction with coreference, linking, relations, and RAG citations  
**Testing Philosophy:** RED-GREEN-REFACTOR with real services (NO MOCKS)  
**Target:** 45 new tests, maintain 85%+ coverage  
**Updated:** October 12, 2025 (Post-Sprint 5 Completion)

---

## 🎯 Sprint Goals (Updated from Sprint 5 Foundation)

**Building on Sprint 5 Achievements:**
- ✅ Entity extraction with spaCy + LLM fallback (Sprint 5)
- ✅ Neo4j knowledge graph with provenance tracking (Sprint 5)
- ✅ Deterministic ID system for entities, mentions, chunks (Sprint 5)
- ✅ Multi-provider AI architecture (Sprint 5)
- ✅ 85%+ test coverage with NO MOCKS policy (Sprint 5)

**Sprint 6 Enhancements:**
1. **Coreference Resolution**: Link pronouns to entities using existing entity extraction
2. **Entity Linking**: Create canonical entities and link mentions across documents
3. **Relation Extraction**: Discover relationships between entities (EMPLOYED_BY, FOUNDED, CITES, etc.)
4. **RAG with Citations**: Answer questions with [1], [2], [3] citations to source chunks
5. **Graph Reasoning**: Query entity relationships and explain RAG answers

---

## 📦 Sprint 5 Foundation (What We Built)

### Existing Infrastructure
```
app/intelligence/
├── providers/
│   ├── abstract_llm.py                    # Base LLM interface
│   ├── anthropic_llm_provider.py          # Claude 3.7 integration
│   ├── openai_llm_provider.py             # GPT integration
│   ├── ollama_llm_provider.py             # Local model support
│   ├── abstract_embedding.py              # Base embedding interface
│   ├── sentence_transformers_provider.py  # Local embeddings
│   └── factory.py                         # Provider factory with fallbacks

app/pipeline/transformers/
├── enhanced_chunker.py                    # Semantic chunking (94% coverage)
└── entity_extractor.py                    # spaCy + LLM NER (94% coverage)

app/repositories/
└── neo_repository.py                      # Full Neo4j implementation (100% coverage)
```

### Existing Data Model (Sprint 5)
```cypher
// Document hierarchy with provenance
(:Document {doc_id, url, title})
  -[:HAS_CHUNK]->(:Chunk {chunk_id, text, byte_offset, tokens})
    -[:CONTAINS_MENTION]->(:Mention {mention_id, text, entity_type, start, end})

// Entity extraction (Sprint 5)
(:Mention)-[:REFERS_TO]->(:Entity {entity_id, canonical_text, entity_type})

// Vector search (Sprint 5)
(:Chunk {embedding: VECTOR})  // 384-dim sentence-transformer embeddings
```

---

## 📋 Stories & Acceptance Criteria (Updated)

### Story S6-601: Coreference Resolution Integration (8 tests)
**Priority:** P0 (Foundation for entity linking)  
**Estimate:** 2 days

**Context:** Extend Sprint 5 entity extraction to resolve pronouns to their referents.

**Acceptance Criteria:**
- [ ] Integrate spaCy's coreference module or neuralcoref
- [ ] Process coreference AFTER entity extraction in pipeline
- [ ] Create (:Mention)-[:COREF_WITH]->(:Mention) relationships
- [ ] Store coreference clusters in Neo4j
- [ ] Configuration in `config/ai_services.yml` to enable/disable
- [ ] Reuse existing `EntityExtractor` from Sprint 5
- [ ] Add `CorefResolver` transformer after entity extraction
- [ ] Performance: process 1000-word document in <5 seconds (Sprint 5: entity extraction in <10s)
- [ ] Integration test with full pipeline (extract → chunk → NER → coref)

**Test Scenarios:**
1. Resolve "he" pronoun to PERSON entity mention
2. Resolve "it" pronoun to ORG entity mention
3. Create COREF_WITH relationships in Neo4j
4. Retrieve coreference chains for document
5. Integration with EntityExtractor from Sprint 5
6. Configuration via ai_services.yml
7. Performance benchmark (1000 words <5s)
8. Pipeline integration test (full ETL)

**Implementation Notes:**
- Reuse `app/pipeline/transformers/entity_extractor.py` output
- Add new `app/pipeline/transformers/coref_resolver.py`
- Extend `app/repositories/neo_repository.py` with `create_coref_relationships()`
- Use existing `mention_id` generation from Sprint 5

---

### Story S6-602: Canonical Entity Linking (10 tests)
**Priority:** P0 (Core graph capability)  
**Estimate:** 3 days

**Context:** Consolidate entity mentions across documents into canonical entities.

**Acceptance Criteria:**
- [ ] Entity linking algorithm: fuzzy match on normalized text + entity type
- [ ] Create canonical (:Entity) nodes separate from (:Mention)
- [ ] Link mentions: (:Mention)-[:LINKED_TO {confidence: float}]->(:Entity)
- [ ] Entity deduplication: "OpenAI" in doc1 + "OpenAI Inc." in doc2 → same Entity
- [ ] Confidence scoring: exact match (1.0), fuzzy match (0.8-0.99), context similarity (0.6-0.79)
- [ ] Entity attributes: `canonical_name`, `aliases: []`, `entity_type`, `mention_count`
- [ ] Use existing `entity_id` generation from Sprint 5 for canonical IDs
- [ ] Batch linking for performance (process 100 mentions in <10s)
- [ ] Neo4j transaction safety (rollback on linking failure)
- [ ] Integration with existing `NeoRepository` from Sprint 5

**Test Scenarios:**
1. Link single mention to new canonical Entity
2. Link multiple mentions to same Entity (same document)
3. Entity deduplication across documents
4. Fuzzy matching ("Open AI" → "OpenAI")
5. Confidence scoring (exact/fuzzy/context)
6. Create LINKED_TO relationships with confidence
7. Entity attributes stored correctly
8. Batch linking performance (100 mentions <10s)
9. Transaction rollback on error
10. Integration with Sprint 5 NeoRepository

**Implementation Notes:**
- Add `app/services/entity_linking_service.py`
- Extend `neo_repository.py` with `link_mention_to_entity(mention_id, entity_id, confidence)`
- Reuse existing `generate_entity_id()` from Sprint 5
- Use sentence-transformer embeddings for context similarity

---

### Story S6-603: Relation Extraction with Dependency Parsing (12 tests)
**Priority:** P0 (Knowledge graph connections)  
**Estimate:** 3 days

**Context:** Discover relationships between entities using pattern matching + dependency parsing.

**Acceptance Criteria:**
- [ ] Pattern-based relation extraction using spaCy dependency parsing
- [ ] Relation types: EMPLOYED_BY, FOUNDED, CITES, LOCATED_IN, PART_OF
- [ ] Store as edges: (:Entity)-[:EMPLOYED_BY {confidence, evidence_chunk_id}]->(:Entity)
- [ ] Relationship attributes: `confidence`, `source_chunk_id`, `evidence_text`, `extracted_at`
- [ ] Rule patterns:
  - EMPLOYED_BY: "X works at Y", "X joined Y", "X is CEO of Y"
  - FOUNDED: "X founded Y", "X started Y", "X co-founded Y"
  - CITES: "X referenced Y", "according to Y", "Y stated"
  - LOCATED_IN: "X in Y", "X based in Y"
- [ ] Bidirectional when appropriate (X-[PART_OF]->Y, Y-[HAS_PART]->X)
- [ ] Relation deduplication (same relation from multiple chunks)
- [ ] Configuration in `config/ai_services.yml` for relation types
- [ ] Integration with existing entity extraction pipeline
- [ ] Performance: extract relations from 50 chunks in <15 seconds
- [ ] Use existing provider architecture from Sprint 5 (optional LLM for complex patterns)

**Test Scenarios:**
1. Extract EMPLOYED_BY ("X works at Y")
2. Extract FOUNDED ("X founded Y")
3. Extract CITES ("according to X")
4. Extract LOCATED_IN ("X based in Y")
5. Store relationship edges in Neo4j
6. Relationship confidence scoring
7. Temporal relations ("founded in 2015")
8. Bidirectional relationships
9. Relation deduplication
10. Dependency parsing patterns
11. Performance (50 chunks <15s)
12. Integration with entity linking

**Implementation Notes:**
- Add `app/pipeline/transformers/relation_extractor.py`
- Use spaCy dependency parsing (already available from Sprint 5)
- Extend `neo_repository.py` with `create_relationship(source_entity_id, target_entity_id, rel_type, **attrs)`
- Reuse LLM providers from Sprint 5 for ambiguous cases

---

### Story S6-604: RAG with Citations (10 tests)
**Priority:** P0 (User-facing value)  
**Estimate:** 2 days

**Context:** Answer questions with citations linking to source chunks using Neo4j graph.

**Acceptance Criteria:**
- [ ] Enhance `SearchService` to return citations with vector search results
- [ ] Citation format: `[1]`, `[2]`, `[3]` with metadata
- [ ] Citation metadata: `doc_url`, `chunk_id`, `page_number`, `byte_offset`, `quote_text`
- [ ] RAG pipeline:
  1. Embed query using sentence-transformer (from Sprint 5)
  2. Vector search in Neo4j (existing `neo_repository.vector_search()`)
  3. Retrieve chunks with provenance (Document, Chunk, Entities)
  4. Generate answer with LLM (existing provider architecture)
  5. Insert inline citations
- [ ] LLM prompt: "Answer using provided sources. Cite sources as [1], [2], [3]."
- [ ] Citation resolver: map `[1]` → full metadata
- [ ] Graph traversal for "Explain this answer" (entity relationships used in answer)
- [ ] Integration with existing `SearchService` from Sprint 5
- [ ] Performance: answer query in <3 seconds
- [ ] Use existing Anthropic/OpenAI providers from Sprint 5

**Test Scenarios:**
1. RAG query returns answer with [1], [2] citations
2. Citation metadata includes all fields
3. Citation includes exact quote from chunk
4. Citation resolver maps [1] to chunk
5. Multiple citations in same answer
6. Graph traversal for reasoning path
7. Integration with SearchService
8. Performance benchmark (<3s)
9. LLM generates citations correctly
10. Fallback when no relevant sources found

**Implementation Notes:**
- Extend `app/services/search_service.py` with `answer_with_citations(query: str)`
- Add `app/services/citation_service.py` for citation resolution
- Reuse existing `NeoRepository.vector_search()` from Sprint 5
- Use existing LLM provider (Anthropic Claude 3.7 preferred)

---

### Story S6-605: Graph Reasoning Queries (5 tests)
**Priority:** P1 (Enhanced capabilities)  
**Estimate:** 1 day

**Context:** Query entity relationships for reasoning and explanation.

**Acceptance Criteria:**
- [ ] Cypher query helpers in `NeoRepository`:
  - `get_entity_relationships(entity_id, depth=2)`
  - `find_path(source_entity_id, target_entity_id)`
  - `get_related_entities(entity_id, relation_type)`
- [ ] Graph traversal for "Explain this answer" feature
- [ ] Reasoning path extraction: OpenAI → [FOUNDED_BY] → Sam Altman → [EMPLOYED_BY] → Y Combinator
- [ ] Integration with RAG citations
- [ ] Performance: traverse graph depth=3 in <1 second

**Test Scenarios:**
1. Get entity relationships (depth=1)
2. Get entity relationships (depth=2)
3. Find shortest path between entities
4. Get related entities by type
5. Extract reasoning path for RAG answer

**Implementation Notes:**
- Extend `app/repositories/neo_repository.py`
- Use existing Cypher patterns from Sprint 5
- Integration with `CitationService`

---

## 🧪 Testing Strategy (Updated from Sprint 5)

### Test Organization
```
tests/
├── integration/
│   ├── pipeline/
│   │   ├── test_coref_resolver.py      # 8 tests (coreference)
│   │   └── test_relation_extractor.py  # 12 tests (relations)
│   ├── services/
│   │   ├── test_entity_linking_service.py  # 10 tests
│   │   ├── test_citation_service.py        # 10 tests
│   │   └── test_rag_with_citations.py      # Integration
│   └── repositories/
│       └── test_neo_repository_enhanced.py # 5 tests (graph queries)
└── unit/
    └── (minimal - focus on integration)
```

### Coverage Targets (Aligned with Sprint 5)
- Overall: 85%+ (Sprint 5: 85.22%)
- New transformers: 90%+ (Sprint 5: enhanced_chunker 94%, entity_extractor 94%)
- Services: 90%+
- Repositories: 95%+ (Sprint 5: neo_repository 100%)

### NO MOCKS Policy (From Sprint 5)
- All integration tests use REAL Neo4j (bolt://localhost:7687)
- All AI tests use REAL providers (Anthropic/OpenAI/Ollama)
- All embedding tests use REAL sentence-transformers
- Only unit tests for pure logic may use mocks

---

## 📊 Success Metrics

### Test Metrics
- [ ] 45 new tests added (8 + 10 + 12 + 10 + 5)
- [ ] All tests passing (excluding unavailable service errors)
- [ ] 85%+ overall coverage maintained
- [ ] 90%+ coverage on new code

### Performance Metrics
- [ ] Coreference: 1000 words in <5s
- [ ] Entity linking: 100 mentions in <10s
- [ ] Relation extraction: 50 chunks in <15s
- [ ] RAG with citations: answer in <3s
- [ ] Graph traversal: depth=3 in <1s

### Feature Completeness
- [ ] Coreference resolution working
- [ ] Canonical entities created
- [ ] Relationships extracted
- [ ] RAG returns cited answers
- [ ] Graph reasoning functional

---

## 📂 File Structure (Building on Sprint 5)

### New Files
```
app/pipeline/transformers/
├── coref_resolver.py                    # NEW: Coreference resolution
└── relation_extractor.py                # NEW: Relation extraction

app/services/
├── entity_linking_service.py            # NEW: Entity linking logic
└── citation_service.py                  # NEW: Citation resolution

app/repositories/
└── neo_repository.py                    # ENHANCED: Add relation methods
```

### Modified Files
```
app/services/search_service.py           # ENHANCED: Add answer_with_citations()
app/pipeline/etl.py                      # ENHANCED: Add coref + relations
config/ai_services.yml                   # ENHANCED: Add coref/relations config
```

---

## 🚀 Sprint Execution Plan

### Week 1: Foundation (Days 1-5)
- **Days 1-2**: Story S6-601 (Coreference)
- **Days 3-5**: Story S6-602 (Entity Linking)

### Week 2: Relations + RAG (Days 6-10)
- **Days 6-8**: Story S6-603 (Relation Extraction)
- **Days 9-10**: Story S6-604 (RAG Citations) + S6-605 (Graph Reasoning)

---

## 🔗 Integration with Sprint 5

### Reuse from Sprint 5
1. **Provider Architecture**: Use existing LLM/embedding providers
2. **Entity Extraction**: Build on existing `EntityExtractor`
3. **Neo4j Repository**: Extend existing `NeoRepository`
4. **ID Generation**: Reuse deterministic ID functions
5. **Configuration**: Extend `ai_services.yml`
6. **Test Infrastructure**: Follow Sprint 5 patterns (NO MOCKS)

### Sprint 5 → Sprint 6 Data Flow
```
Sprint 5 Output:                Sprint 6 Enhancements:
Document → Chunks               → Add coreference links
Chunks → Mentions               → Link to canonical Entities
Mentions → Entities             → Extract Relations
Entities (isolated)             → Entities (connected via relations)
```

---

## 🎯 Definition of Done

- [ ] All 45 tests passing
- [ ] 85%+ test coverage maintained
- [ ] NO MOCKS in integration tests
- [ ] All performance benchmarks met
- [ ] Documentation updated
- [ ] Code reviewed and committed
- [ ] Technical debt audit clean (4 lint errors or fewer)
- [ ] Ready for Sprint 7 (FastAPI + Visualization)

---

**Updated:** October 12, 2025  
**Status:** Ready to start  
**Prerequisites:** Sprint 5 complete ✅ (77/77 tests passing, 85.22% coverage)
