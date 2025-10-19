# Creator Assistant v0.1 — Implementation Plan

**Status:** Phase PLAN  
**Date:** October 14, 2025  
**Scope:** Three creator endpoints + civic RFP probe + YouTube fixpack (optional)

---

## 1) Files to Create (9 new files)

### Services (5 files)

```
app/services/creator_insights_service.py        (~150 LOC)
app/services/creator_outline_service.py         (~200 LOC)
app/services/creator_metadata_service.py        (~120 LOC)
app/services/civic_rfp_probe.py                 (~100 LOC)
```

### API Layer (1 file)

```
app/api/creator_endpoints.py                    (~180 LOC)
```

### Tests (3 files)

```
tests/integration/creator/test_topic_map.py           (~200 LOC, 6 tests)
tests/integration/creator/test_creator_outline.py     (~250 LOC, 7 tests)
tests/integration/creator/test_creator_metadata.py    (~180 LOC, 5 tests)
tests/integration/civic/test_civic_rfp_probe.py       (~150 LOC, 3 tests)
```

### Documentation (1 file)

```
docs/creator/README.md                          (~100 LOC)
```

**Total:** ~1,630 LOC across 9 files (within budget: < 2,000 LOC)

---

## 2) Files to Modify (surgical edits)

### Existing Services (small additions)

```
app/services/search_service.py
- Add: answer_with_citations(query: str, filters: dict) -> dict
  (~40 LOC if WL_YT_RAG_CITATIONS implemented)
```

### Feature Flags (add 3 flags)

```
app/core/config.py
- Add: WL_YT_TOPIC_MAP: bool = False
- Add: WL_CREATOR_ASSIST: bool = False
- Add: WL_YT_RAG_CITATIONS: bool = False
```

### Neo4j Repository (1 small query helper)

```
app/repositories/neo_repository.py
- Add: get_channel_entities_with_mentions(channel_id: str, limit: int) -> list[dict]
  (~30 LOC)
```

---

## 3) Endpoint Specifications

### GET /api/creator/topic-map

**Flag:** `WL_YT_TOPIC_MAP`

**Query Params:**
- `channel_id` (required): YouTube channel ID
- `limit` (optional, default=10): Max entities/relations to return

**Response (200):**
```json
{
  "channel_id": "UCXXXX",
  "entities": [
    {"id": "E1", "text": "OpenAI", "type": "ORG", "mentions": 12}
  ],
  "relations": [
    {"type": "CITES", "source": "E1", "target": "E2", "count": 7}
  ],
  "sample_questions": [
    "What companies does Sam Altman discuss?",
    "How does OpenAI relate to AGI research?"
  ]
}
```

**Error (404):** Channel not found or no videos ingested  
**Error (403):** Flag disabled

---

### POST /api/creator/outline

**Flag:** `WL_CREATOR_ASSIST`

**Request Body:**
```json
{
  "video_ids": ["yt:O2DqGGlliCA", "yt:abc123"],
  "goal": "Explain my provenance system to beginners",
  "sections": 5,
  "style": "educator"
}
```

**Response (200):**
```json
{
  "outline_markdown": "# Episode Outline\n\n## 1. Introduction to Provenance [1]\n\nProvenance tracking ensures...",
  "citations": [
    {
      "idx": 1,
      "doc_url": "https://youtube.com/watch?v=O2DqGGlliCA",
      "chunk_id": "urn:chunk:abc-def-123",
      "byte_offset": 1024,
      "timestamp": "00:02:15",
      "quote": "Provenance tracking ensures..."
    }
  ],
  "sources_used": 2
}
```

**Error (404):** Video(s) not found  
**Error (403):** Flag disabled

---

### POST /api/creator/metadata

**Flag:** `WL_CREATOR_ASSIST`

**Request Body:**
```json
{
  "outline_markdown": "# Episode Outline\n\n...",
  "channel_id": "UCXXXX",
  "tone": "educational",
  "max_tags": 12
}
```

**Response (200):**
```json
{
  "title": "Provenance-Powered AI: How It Works",
  "description": "In this episode, we explore how provenance tracking [1] enables verifiable AI systems [2].\n\nSources:\n1) https://youtube.com/watch?v=...\n2) https://youtube.com/watch?v=...",
  "tags": ["knowledge graph", "provenance", "neo4j", "AI", "verification"],
  "citations": [
    {"idx": 1, "doc_url": "https://youtube.com/watch?v=...", ...}
  ]
}
```

**Error (400):** Invalid outline format  
**Error (403):** Flag disabled

---

## 4) Service Logic Breakdown

### CreatorInsightsService.build_topic_map()

**Flow:**
1. Query Postgres: Get latest N videos for `channel_id`
2. Query Neo4j: 
   ```cypher
   MATCH (e:Entity)<-[:MENTIONS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
   WHERE d.doc_id IN $video_doc_ids
   RETURN e.entity_id, e.text, e.entity_type, count(*) as mentions
   ORDER BY mentions DESC
   LIMIT $limit
   ```
3. Query Neo4j relations:
   ```cypher
   MATCH (e1:Entity)-[r:RELATION]->(e2:Entity)
   WHERE e1.entity_id IN $top_entity_ids AND e2.entity_id IN $top_entity_ids
   RETURN type(r), e1.entity_id, e2.entity_id, count(*) as freq
   ORDER BY freq DESC
   LIMIT $limit
   ```
4. Generate sample questions:
   - Template: "What {relation_type} exist between {entity1} and {entity2}?"
   - Pick top 5 relations by frequency

**Performance:** < 2s for small channel (10 videos, 50 entities)

---

### CreatorOutlineService.build_outline()

**Flow (WL_YT_RAG_CITATIONS=true):**
1. For each section (1..N):
   - Generate section query: f"{goal} - Section {i}: {section_topic}"
   - Call `SearchService.answer_with_citations(query, filters={'video_id__in': video_ids})`
   - Collect answer + citations
2. Assemble markdown with inline [1][2][3] references
3. Build unified citation map (dedupe by chunk_id)
4. Return {outline_markdown, citations, sources_used}

**Flow (WL_YT_RAG_CITATIONS=false - FALLBACK):**
1. Query Qdrant: Get top-K chunks for each video (filter by video_id)
2. LLM summarization: "Summarize these chunks into N sections for goal: {goal}"
3. Extract doc_url + timestamp from chunk metadata
4. Build simple citations list (no inline [1][2] mapping)
5. Return {outline_markdown, citations, sources_used}

**Performance:** < 3s for 2 videos, 5 sections (with RAG)

---

### CreatorMetadataService.generate_metadata()

**Flow:**
1. Parse outline_markdown → extract entity mentions (regex or NER)
2. Query Neo4j: Get entity types + relations for mentions
3. Generate tags:
   - Primary: entity texts (ORG, PERSON names)
   - Secondary: relation types (FOUNDED, WORKED_AT)
   - Filter: lowercase, dedupe, sort by frequency
   - Cap at `max_tags`
4. Generate 3 title variants:
   - Pattern 1: "{Main Entity}: {Topic}" (< 70 chars)
   - Pattern 2: "How {Entity1} and {Entity2} {Relation}" (< 70 chars)
   - Pattern 3: "{Goal} Explained" (< 70 chars)
   - Pick shortest valid title
5. Generate description:
   - Extract first paragraph from outline
   - Add inline citation refs if present
   - Append "Sources:\n1) {url}\n2) {url}..." footer
6. Return {title, description, tags, citations}

**Performance:** < 1s

---

### CivicRfpProbeService.ingest_structured_findings()

**Flow:**
1. Validate payload structure (required: query, claims, sources)
2. For each claim:
   - Create ProvenanceStatement:
     ```python
     statement = ProvenanceStatement(
         statement_id=generate_statement_id("urn:agent:gpt-5-web", claim["text"]),
         agent_id="urn:agent:gpt-5-web",
         claim_text=claim["text"],
         confidence=claim["confidence"],
         evidence=[
             EvidenceSegment(
                 source_url=claim["source_url"],
                 byte_range=tuple(claim["byte_range"]),
                 quote_text=claim["quote"]
             )
         ]
     )
     ```
   - Store in Neo4j:
     ```cypher
     CREATE (s:Statement {statement_id: $id, claim_text: $text, confidence: $conf, ...})
     CREATE (a:Agent {agent_id: "urn:agent:gpt-5-web"})-[:GENERATED]->(s)
     ```
   - If `claim["critical"] == true`:
     - Add to verification queue (Redis list: `verification:queue:critical`)
3. Return summary: {stored: len(claims), queued_for_verification: count(critical)}

**Performance:** < 500ms for 10 claims

---

## 5) Test Specifications

### tests/integration/creator/test_topic_map.py

**Setup:**
- Ingest 3 test videos with known entities (OpenAI, Sam Altman, AGI)
- Create Neo4j entities + MENTIONS relationships

**Tests:**
1. `test_returns_top_entities_and_relations`
   - Call `/api/creator/topic-map?channel_id=test&limit=5`
   - Assert: entities list has ≥3 items
   - Assert: relations list has ≥1 item
   - Assert: sample_questions list has 5 items

2. `test_limits_videos`
   - Ingest 20 videos
   - Call with `limit=10`
   - Assert: entities list has ≤10 items

3. `test_includes_suggested_questions`
   - Call endpoint
   - Assert: each question contains entity names from response

4. `test_flag_gate_enforced`
   - Set `WL_YT_TOPIC_MAP=false`
   - Call endpoint
   - Assert: 403 response

5. `test_handles_missing_channel`
   - Call with non-existent channel_id
   - Assert: 404 response

6. `test_perf_under_2s_small_channel`
   - Ingest 10 videos (small channel)
   - Time endpoint call
   - Assert: duration < 2.0 seconds

---

### tests/integration/creator/test_creator_outline.py

**Setup:**
- Ingest 2 test videos with known content
- Create chunks in Qdrant with metadata

**Tests:**
1. `test_build_outline_returns_markdown_with_sections`
   - POST with sections=5
   - Assert: markdown contains 5 "##" headers

2. `test_includes_inline_citations_and_map`
   - Enable `WL_YT_RAG_CITATIONS`
   - POST request
   - Assert: markdown contains [1][2] references
   - Assert: citations list matches referenced indices

3. `test_uses_multiple_videos`
   - POST with video_ids=[v1, v2]
   - Assert: sources_used == 2
   - Assert: citations reference both videos

4. `test_respects_sections_and_style`
   - POST with sections=3, style="technical"
   - Assert: markdown has 3 sections
   - Assert: tone reflects "technical" (check for technical keywords)

5. `test_flag_gate_enforced`
   - Set `WL_CREATOR_ASSIST=false`
   - POST request
   - Assert: 403 response

6. `test_perf_under_3s_small_input`
   - POST with 2 videos, 5 sections
   - Time request
   - Assert: duration < 3.0 seconds

7. `test_fallback_without_rag_citations`
   - Set `WL_YT_RAG_CITATIONS=false`
   - POST request
   - Assert: markdown generated
   - Assert: citations contain doc_url + timestamp (no [1][2] indices)

---

### tests/integration/creator/test_creator_metadata.py

**Setup:**
- Pre-create outline with known entities/citations

**Tests:**
1. `test_generates_title_desc_tags`
   - POST with outline
   - Assert: title exists and ≤70 chars
   - Assert: description exists
   - Assert: tags list has ≥3 items

2. `test_includes_citations_in_description`
   - POST with outline containing citations
   - Assert: description contains "Sources:" footer
   - Assert: sources list matches input citations

3. `test_respects_max_tags`
   - POST with max_tags=5
   - Assert: len(tags) ≤ 5

4. `test_flag_gate_enforced`
   - Set `WL_CREATOR_ASSIST=false`
   - POST request
   - Assert: 403 response

5. `test_metadata_uses_outline_entities`
   - POST with outline mentioning "OpenAI", "Neo4j"
   - Assert: tags contain "openai" or "neo4j"

---

### tests/integration/civic/test_civic_rfp_probe.py

**Setup:**
- Mock GPT-5 web research payload

**Tests:**
1. `test_ingest_creates_statements_with_citations`
   - Call `ingest_structured_findings(payload)`
   - Query Neo4j: MATCH (s:Statement) WHERE s.claim_text CONTAINS "Newark RFP"
   - Assert: statement exists with correct evidence

2. `test_marks_critical_facts_for_verification`
   - Payload with 2 critical claims, 1 non-critical
   - Call ingest
   - Assert: response.queued_for_verification == 2
   - Assert: Redis list `verification:queue:critical` has 2 items

3. `test_handles_missing_fields_gracefully`
   - Payload with incomplete claim (missing source_url)
   - Call ingest
   - Assert: 400 error with clear message

---

## 6) Risk Assessment

### 🟢 Low Risk

- **Topic Map:** Straightforward Neo4j aggregation queries
- **SEO Metadata:** Simple entity extraction + templating
- **Civic Probe:** Direct A2AP statement creation

### 🟡 Medium Risk

- **Outline with RAG Citations:**
  - **Risk:** SearchService.answer_with_citations() doesn't exist yet
  - **Mitigation:** Implement fallback mode (basic provenance) first
  - **Estimate:** +2 hours to add citation logic to SearchService

- **Performance Targets:**
  - **Risk:** Neo4j queries might be slow on large channels (1000+ videos)
  - **Mitigation:** Test with realistic data sizes, add indexes if needed
  - **Estimate:** May need 1-2 hours query optimization

### 🔴 High Risk (None in scope)

All deliverables use existing infrastructure with proven patterns.

---

## 7) Implementation Order (Sequence)

### Phase 1: Foundation (Day 1)
1. Add feature flags to `app/core/config.py`
2. Create `app/services/creator_insights_service.py` (topic map only)
3. Add Neo4j helper: `get_channel_entities_with_mentions()`
4. Create `app/api/creator_endpoints.py` (topic-map route only)
5. Write `tests/integration/creator/test_topic_map.py`
6. **Checkpoint:** Topic map endpoint working, tests green

### Phase 2: Outline (Day 2)
7. Create `app/services/creator_outline_service.py` (fallback mode first)
8. Implement outline generation without full RAG citations
9. Add outline route to `creator_endpoints.py`
10. Write `tests/integration/creator/test_creator_outline.py`
11. **Checkpoint:** Outline endpoint working with basic citations

### Phase 3: Metadata (Day 2)
12. Create `app/services/creator_metadata_service.py`
13. Add metadata route to `creator_endpoints.py`
14. Write `tests/integration/creator/test_creator_metadata.py`
15. **Checkpoint:** All 3 creator endpoints working

### Phase 4: Civic Probe (Day 3)
16. Create `app/services/civic_rfp_probe.py`
17. Write `tests/integration/civic/test_civic_rfp_probe.py`
18. **Checkpoint:** A2AP ingestion validated

### Phase 5: Optional RAG Citations (Day 3-4)
19. Implement `SearchService.answer_with_citations()`
20. Update `CreatorOutlineService` to use RAG when flag enabled
21. Fix 7 YouTube test failures
22. **Checkpoint:** Full RAG citations working

### Phase 6: Documentation (Day 4)
23. Create `docs/creator/README.md` with curl examples
24. Run full test suite + coverage report
25. Write `summary.md`
26. **Checkpoint:** v0.1 complete

---

## 8) Dependencies Check

### Existing Services (✅ Available)
- `ContentService` - for video metadata
- `EntityService` - for Neo4j entity queries
- `QdrantRepository` - for vector search
- `PostgresRepository` - for content registry
- `RedisRepository` - for caching + queues

### New Dependencies (❌ None Required)
No new packages needed. All use existing:
- openai (embeddings)
- neo4j
- qdrant-client
- asyncpg
- redis

---

## 9) Coverage Delta Estimate

**Current:** 98.9% (997/1008 tests passing)

**New Coverage:**
- `creator_insights_service.py`: 100% (6 tests)
- `creator_outline_service.py`: 95% (7 tests, some branches conditional on flag)
- `creator_metadata_service.py`: 100% (5 tests)
- `civic_rfp_probe.py`: 100% (3 tests)
- `creator_endpoints.py`: 90% (flag gates + error handling)

**Expected Delta:** +2.5% on touched files

---

## 10) Success Criteria (Checklist)

- [ ] 3 feature flags added and default to `false`
- [ ] GET /api/creator/topic-map returns entities + relations + questions
- [ ] POST /api/creator/outline returns markdown with citations
- [ ] POST /api/creator/metadata returns title + description + tags
- [ ] CivicRfpProbeService ingests claims → ProvenanceStatements
- [ ] 21 integration tests added and passing
- [ ] No mocks used in integration tests
- [ ] Performance targets met (topic-map < 2s, outline < 3s)
- [ ] Coverage delta +2% or more
- [ ] docs/creator/README.md created with curl examples
- [ ] summary.md produced with implementation report

---

## 11) Stop Conditions

If any of these occur, halt and report:

1. **Refactor Required:** Existing service needs major changes (>100 LOC)
2. **New Dependency:** Need to add package not in pyproject.toml
3. **Schema Change:** Neo4j/Postgres schema needs migration
4. **Performance Issue:** Queries take >5s even after optimization
5. **Scope Creep:** Feature request beyond brief specifications

---

**Status:** PLAN COMPLETE - Ready for Phase BUILD  
**Estimated LOC:** 1,630 across 9 new files  
**Estimated Time:** 3-4 days  
**Risk Level:** Low-Medium (RAG citations only uncertainty)

**Ready to proceed?** Confirm and I'll begin Phase BUILD starting with Phase 1 (Topic Map).
