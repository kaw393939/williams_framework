# Architecture Comparison: Current vs. Neo4j Provenance-First

## Side-by-Side System Architecture

### Current Architecture (Sprints 1-4)

```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                       │
│                                                             │
│  URL → HTMLExtractor → BasicTransformer → LibraryLoader    │
│         │                   │                   │           │
│         ↓                   ↓                   ↓           │
│    fetch HTML        extract text       create markdown    │
│    parse content     summarize          assign tier         │
│                      extract tags       quality score       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────┴─────────────────────┐
         │                                          │
┌────────▼────────┐                    ┌────────────▼───────────┐
│     Qdrant      │                    │        MinIO           │
│                 │                    │                        │
│  • Embeddings   │                    │  • Markdown files      │
│  • Vectors      │                    │  • Organized by tier   │
│  • Metadata     │                    │    - tier-a (best)     │
│                 │                    │    - tier-b            │
│  Search:        │                    │    - tier-c            │
│  Vector only    │                    │    - tier-d (worst)    │
│                 │                    │                        │
└─────────────────┘                    └────────────────────────┘

Data Model:
  • Document (flat structure)
  • Vector embeddings
  • File paths
  
Query Capabilities:
  ✅ Semantic search (vector similarity)
  ❌ No entity queries
  ❌ No relationship queries
  ❌ No provenance trails
  ❌ No graph traversal

Citations:
  ⚡ Basic: Document URL only
```

---

### Proposed Architecture (Neo4j Provenance-First)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       ADVANCED INGESTION PIPELINE                        │
│                                                                          │
│  URL → Fetch → Chunk → Coref → NER → Link → Relations → Embed → Index  │
│         │       │       │       │      │       │          │        │     │
│         ↓       ↓       ↓       ↓      ↓       ↓          ↓        ↓     │
│      MinIO   MinIO   Coref   SpaCy  Alias  Pattern    BGE-M3   Neo4j   │
│      raw/    chunks  chains  entities  DB   Extract    vectors  Graph   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
    ┌───────────────▼──────────┐      ┌────────────▼──────────────┐
    │        Neo4j Graph       │      │    MinIO Storage          │
    │                          │      │                           │
    │  Nodes:                  │      │  raw/{tier}/{doc_id}/     │
    │  • :Document             │      │    source.ext             │
    │    - doc_id              │      │                           │
    │    - sha256              │      │  derived/{tier}/{doc_id}/ │
    │    - tier                │      │    manifest.json          │
    │    - quality_score       │      │    chunks.jsonl           │
    │  • :Chunk                │      │    coref.jsonl            │
    │    - chunk_id            │      │    mentions.jsonl         │
    │    - text                │      │    links.jsonl            │
    │    - offsets [s,e]       │      │    relations.jsonl        │
    │    - vec (embeddings)    │      │    embeddings.jsonl       │
    │  • :Entity               │      │    page_map.json          │
    │    - eid                 │      │    lineage.jsonl          │
    │    - name                │      │                           │
    │    - type (PERSON/ORG)   │      └───────────────────────────┘
    │    - vec (optional)      │
    │                          │
    │  Relationships:          │
    │  (d)-[:HAS_CHUNK]->(c)   │
    │  (c)-[:MENTIONS]->(e)    │
    │    {start, end, quote,   │
    │     coref_chain_id}      │
    │  (e1)-[:REL]->(e2)       │
    │    {type, conf, prov}    │
    │                          │
    │  Vector Indexes:         │
    │  • chunk_vec_idx         │
    │  • entity_vec_idx        │
    │                          │
    └──────────────────────────┘

Data Model:
  • Rich graph (nodes + relationships)
  • Full provenance chains
  • Byte-level offsets
  • Canonical entities
  • Typed relationships

Query Capabilities:
  ✅ Semantic search (vector + graph)
  ✅ Entity queries ("show all mentions of OpenAI")
  ✅ Relationship queries ("who founded what?")
  ✅ Provenance trails (answer → chunks → entities → sources)
  ✅ Graph traversal (2-hop: "OpenAI → founded_by → Sam Altman → also_founded → ?")
  ✅ Filtered search (by entities, dates, relationships)

Citations:
  ✅ Advanced: URL + byte offsets + quote + page/bbox
```

---

## Feature Comparison Matrix

| Feature | Current (Qdrant) | Proposed (Neo4j) | Business Impact |
|---------|------------------|------------------|-----------------|
| **Basic Search** | ✅ Vector similarity | ✅ Vector + graph-guided | Improved relevance |
| **Entity Recognition** | ❌ None | ✅ PERSON, ORG, GPE, LAW, DATE | Structured knowledge |
| **Entity Linking** | ❌ None | ✅ Canonical IDs + aliases | Disambiguation |
| **Relationships** | ❌ None | ✅ EMPLOYED_BY, FOUNDED, CITES | Discover connections |
| **Citations** | ⚡ URL only | ✅ URL + offsets + quote + page | Trust & verifiability |
| **Provenance** | ❌ None | ✅ Full lineage tracking | Audit trail |
| **Coreference** | ❌ None | ✅ Chain tracking | Resolve pronouns |
| **Graph Viz** | ❌ None | ✅ D3/GraphML export | Visual exploration |
| **"Explain Answer"** | ❌ None | ✅ Subgraph export | Transparency |
| **Idempotency** | ⚡ Partial | ✅ Deterministic IDs | Reliable re-ingest |
| **Page Mapping** | ❌ None | ✅ Char→page/bbox for PDFs | Precise highlights |

---

## RAG Query Comparison

### Current System

**Query**: "What did OpenAI say about safety?"

**Process**:
1. Embed query → vector
2. Qdrant vector search → top-K chunks
3. LLM generates answer from chunks
4. Return answer + document URLs

**Response**:
```json
{
  "answer": "OpenAI emphasized responsible AI development...",
  "sources": [
    {"url": "https://openai.com/blog/safety", "title": "Safety Post"}
  ]
}
```

**User Experience**:
- ❌ Can't verify which sentence supports answer
- ❌ Can't see which entities mentioned
- ❌ Can't explore related entities
- ❌ Can't trace reasoning

---

### Neo4j System

**Query**: "What did OpenAI say about safety?"

**Process**:
1. Embed query → vector
2. Graph prefilter: Get chunks mentioning "OpenAI" AND "safety" entities
3. Vector search within filtered set
4. Cross-encoder rerank
5. LLM generates answer with **citation markers**
6. Extract provenance for each citation

**Response**:
```json
{
  "answer": "OpenAI emphasized responsible AI development [1], particularly in the context of AGI alignment [2]...",
  "citations": [
    {
      "id": 1,
      "doc_id": "d_abcd1234efgh5678",
      "chunk_id": "d_abcd...:1200:1890",
      "source_uri": "https://openai.com/blog/safety",
      "quote": "We prioritize safety in all stages of development",
      "offsets": [1264, 1342],
      "page_ref": {"page": 3, "bbox": [98, 240, 480, 310]},
      "entities_mentioned": [
        {"eid": "E:ORG:openai", "name": "OpenAI"},
        {"eid": "E:CONCEPT:safety", "name": "AI Safety"}
      ]
    },
    {
      "id": 2,
      "doc_id": "d_xyz789...",
      "chunk_id": "d_xyz...:3400:4100",
      "source_uri": "https://openai.com/alignment",
      "quote": "AGI alignment research is our top priority",
      "offsets": [3456, 3512],
      "page_ref": {"page": 1, "bbox": [120, 180, 520, 240]},
      "entities_mentioned": [
        {"eid": "E:ORG:openai", "name": "OpenAI"},
        {"eid": "E:CONCEPT:agi-alignment", "name": "AGI Alignment"}
      ]
    }
  ],
  "explain_url": "/v1/rag/explain?chunk_ids=d_abcd...:1200:1890,d_xyz...:3400:4100",
  "meta": {"latency_ms": 412}
}
```

**User Experience**:
- ✅ Click [1] → highlights exact sentence in original PDF (page 3, bounding box)
- ✅ See entities mentioned in each citation
- ✅ Click "Explain" → see graph of OpenAI → safety → AGI alignment relationships
- ✅ Trace reasoning path through knowledge graph
- ✅ Verify every claim has source

---

## Cost Comparison

| Aspect | Current (Qdrant) | Neo4j (Proposed) | Delta |
|--------|------------------|------------------|-------|
| **Docker Containers** | 4 (Postgres, Redis, Qdrant, MinIO) | 5 (+Neo4j) | +1 container |
| **Memory (Dev)** | ~4 GB | ~6 GB | +2 GB |
| **Storage (per 1000 docs)** | ~500 MB vectors | ~800 MB (graph + vectors) | +300 MB |
| **Ingestion Time** | ~10 sec/doc | ~30 sec/doc (NER+linking) | 3x slower |
| **Query Latency** | ~100ms | ~200ms (graph+vector) | 2x slower |
| **Monthly Cost (Cloud)** | ~$50 (Qdrant cloud) | ~$80 (Neo4j Aura + Qdrant) | +$30/mo |
| **Development Time** | ✅ Complete (Sprint 1-4) | +6 weeks (Sprint 5-7) | +6 weeks |

**Analysis**: Worthwhile tradeoff for significantly enhanced capabilities.

---

## Migration Path Visualization

### Option A: FastAPI First (Not Recommended)

```
Current State (Sprint 4)
         ↓
   ┌─────────────┐
   │  Sprint 5:  │  Build FastAPI streaming for OLD pipeline
   │  FastAPI    │  40 tests, 2k LOC
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Sprint 6:  │  Build Neo4j foundation
   │  Neo4j (1)  │  45 tests, 3k LOC
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Sprint 7:  │  Add linking + relations
   │  Neo4j (2)  │  48 tests, 3k LOC
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Sprint 8:  │  ⚠️ REBUILD FastAPI for NEW pipeline
   │  FastAPI    │  40 tests, 2k LOC (WASTED EFFORT)
   │  REWORK     │
   └─────────────┘

Total: 4 sprints, 173 tests, ~10k LOC
       ⚠️ Complete rebuild of FastAPI streaming
```

### Option B: Neo4j First (Recommended)

```
Current State (Sprint 4)
         ↓
   ┌─────────────┐
   │  Sprint 5:  │  Build Neo4j foundation + NER
   │  Neo4j (1)  │  45 tests, 3k LOC
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Sprint 6:  │  Add linking + relations
   │  Neo4j (2)  │  48 tests, 3k LOC
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Sprint 7:  │  Build FastAPI streaming for NEW pipeline
   │  FastAPI    │  40 tests, 2k LOC
   │  (one time)  │  ✅ Built once correctly
   └─────────────┘

Total: 3 sprints, 133 tests, ~8k LOC
       ✅ No rework, clean architecture
```

---

## Implementation Complexity

### Pipeline Stages

```
CURRENT PIPELINE (3 stages):
┌──────────┐    ┌──────────────┐    ┌────────────┐
│ Extract  │ → │  Transform   │ → │    Load    │
│  (HTTP)  │    │  (Summary)   │    │  (MinIO)   │
└──────────┘    └──────────────┘    └────────────┘
   Simple           Simple            Simple

NEW PIPELINE (8 stages):
┌──────┐  ┌──────┐  ┌──────┐  ┌─────┐  ┌──────┐  ┌──────────┐  ┌────────┐  ┌──────┐
│Fetch │→│Chunk │→│Coref │→│ NER │→│ Link │→│Relations │→│ Embed  │→│Index │
│      │  │      │  │      │  │     │  │      │  │          │  │        │  │      │
└──────┘  └──────┘  └──────┘  └─────┘  └──────┘  └──────────┘  └────────┘  └──────┘
 Medium    Medium    Complex   Complex  Complex    Complex      Medium     Medium

Complexity: 3x more stages, 5x more complexity
```

---

## Risk Assessment

| Risk | Current Path | Neo4j First | Mitigation |
|------|-------------|-------------|------------|
| **Timeline Delay** | Low | Medium | Phased sprints, clear milestones |
| **Technical Complexity** | Low | High | Proven tech stack (Neo4j, SpaCy), TDD |
| **Cost Overrun** | Low | Medium | Local-first, cost caps per stage |
| **Rework/Waste** | **HIGH** ⚠️ | Low | Neo4j first = no FastAPI rebuild |
| **Test Coverage** | ✅ 98% | ✅ 90%+ | TDD with real services |
| **User Value** | Medium | **HIGH** ✅ | Citations + graph = differentiation |

---

## Stakeholder Impact

### For Users (Researchers/Creators)

**Current**:
- ✅ Find similar content
- ❌ Can't verify sources precisely
- ❌ Can't explore relationships

**Neo4j**:
- ✅ Find similar content
- ✅ **Click citation → highlight exact quote**
- ✅ **Explore: "What else did this person do?"**
- ✅ **See visual graph of concepts**

### For Enterprise Customers

**Current**:
- ⚡ Basic search
- ❌ No audit trail

**Neo4j**:
- ✅ **Full provenance** (compliance)
- ✅ **Entity linking** (consistent terminology)
- ✅ **Relationship discovery** (business intelligence)
- ✅ **Graph export** (integrate with existing tools)

### For Investors

**Current**:
- "Another AI search tool"

**Neo4j**:
- **"Provenance-tracked knowledge graph with explainable AI"**
- Stronger IP position
- Higher defensibility
- Enterprise-ready architecture

---

## Decision Framework

### Proceed with Neo4j First if:
- ✅ **Strategic Value** > Short-term speed
- ✅ Team comfortable with 6-week timeline
- ✅ Graph capabilities align with business vision
- ✅ Citations + provenance are core differentiators
- ✅ Willing to defer UI improvements for better foundation

### Proceed with FastAPI First if:
- ❌ Need visible progress immediately
- ❌ Citations not priority
- ❌ Graph features "nice to have"
- ❌ Can't afford 6-week investment
- ❌ Okay with complete rebuild later

---

**Recommendation**: **Neo4j First** - The foundation is worth getting right.
