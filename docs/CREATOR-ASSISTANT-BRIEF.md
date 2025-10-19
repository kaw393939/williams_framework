# Agent Brief — Williams Librarian (Claude, MCP)

**Role:** Implement precisely. Ship minimal, provable value.  
**Mode:** Two-Phase (PLAN → BUILD).  
**Stop rules:** If refactor or new deps are required beyond scope, halt and report.

---

## 0) Product Targets (v0.1)

**Primary use case:** Creator Assistant for a YouTube channel (low-stakes, high ROI).  
**Secondary probe:** Civic RFP Assistant (thin vertical to prove A2AP ingestion).

We want three concrete outcomes for creators:

1. **Topic Map** from channel videos (entities + relations + sample questions).
2. **Cited Episode Outline** from selected videos (inline [1][2] citations).
3. **SEO Metadata** (title, description, tags) referencing those citations.

All are **flag-gated** and integrate with existing services (Neo4j, Qdrant, Postgres, MinIO).  
No mocks in integration tests.

---

## 1) Feature Flags (off by default)

* `WL_YT_TOPIC_MAP`
* `WL_CREATOR_ASSIST`
* `WL_YT_RAG_CITATIONS` (optional fixpack to improve citations)

---

## 2) Deliverables (tight scope)

### A) Topic Map (Channel) — `WL_YT_TOPIC_MAP`

**Endpoint**

```
GET /api/creator/topic-map?channel_id=UCXXXX&limit=10
```

**Response**

```json
{
  "channel_id": "UCXXXX",
  "entities": [{"id":"E1","text":"OpenAI","type":"ORG","mentions":12}],
  "relations": [{"type":"CITES","source":"E1","target":"E2","count":7}],
  "sample_questions": ["What companies appear with Sam Altman?", "…"]
}
```

**Service**

```python
# app/services/creator_insights_service.py
class CreatorInsightsService:
    async def build_topic_map(self, *, channel_id: str, limit: int = 10) -> dict: ...
```

**Behavior**

* Pull latest N videos for channel from Postgres.
* Join to Neo4j mentions/relations; aggregate by frequency & confidence.
* Produce 5 suggested questions derived from the graph.

**Tests (integration, real services)**

```
tests/integration/creator/test_topic_map.py
- test_returns_top_entities_and_relations
- test_limits_videos
- test_includes_suggested_questions
- test_flag_gate_enforced
- test_handles_missing_channel
- test_perf_under_2s_small_channel
```

---

### B) Cited Episode Outline — `WL_CREATOR_ASSIST` (uses `WL_YT_RAG_CITATIONS` if ON)

**Endpoint**

```
POST /api/creator/outline
Body: {
  "video_ids": ["yt:O2DqGGlliCA", "yt:..."],
  "goal": "Explain my provenance system to beginners",
  "sections": 5,
  "style": "educator"
}
```

**Response**

```json
{
  "outline_markdown": "# Episode Outline\n\n## 1. ... [1]\n",
  "citations": [
    {"idx":1,"doc_url":"...","chunk_id":"...","byte_offset":123,"timestamp":"00:02:15"}
  ],
  "sources_used": 2
}
```

**Service**

```python
# app/services/creator_outline_service.py
class CreatorOutlineService:
    async def build_outline(
      *, video_ids: list[str], goal: str, sections: int = 5, style: str = "educator"
    ) -> dict: ...
```

**Behavior**

* Retrieve chunks (Qdrant filter by video_ids); pull provenance (Neo4j).
* If `WL_YT_RAG_CITATIONS`=true → use SearchService.answer_with_citations(query) per section and assemble inline [1][2] citations + map.
* Else fallback: summarize relevant chunks; include basic provenance (doc_url + timestamp) without numeric index mapping.

**Tests (integration)**

```
tests/integration/creator/test_creator_outline.py
- test_build_outline_returns_markdown_with_sections
- test_includes_inline_citations_and_map
- test_uses_multiple_videos
- test_respects_sections_and_style
- test_flag_gate_enforced
- test_perf_under_3s_small_input
- test_fallback_without_rag_citations
```

---

### C) SEO Metadata — `WL_CREATOR_ASSIST`

**Endpoint**

```
POST /api/creator/metadata
Body: {
  "outline_markdown": "...",
  "channel_id": "UCXXXX",
  "tone": "educational",
  "max_tags": 12
}
```

**Response**

```json
{
  "title": "Provenance-Powered AI: How It Works",
  "description": "In this episode... [1][2]\n\nSources:\n1) ...",
  "tags": ["knowledge graph","provenance","neo4j"],
  "citations": [...]
}
```

**Service**

```python
# app/services/creator_metadata_service.py
class CreatorMetadataService:
    async def generate_metadata(
      *, outline_markdown: str, channel_id: str, tone: str = "educational", max_tags: int = 12
    ) -> dict: ...
```

**Behavior**

* Extract entities/relations from outline to propose tags (dedupe, cap at max).
* Generate 3 title variants; pick best by length ≤ 70 chars, clarity, uniqueness.
* Description includes inline citations and "Sources" footer if provided.

**Tests (integration)**

```
tests/integration/creator/test_creator_metadata.py
- test_generates_title_desc_tags
- test_includes_citations_in_description
- test_respects_max_tags
- test_flag_gate_enforced
- test_metadata_uses_outline_entities
```

---

## 3) OPTIONAL Fixpack — YouTube RAG Citations (`WL_YT_RAG_CITATIONS`)

**Goal:** Make outline citations strong and flip residual YT test failures.  
**Scope (surgical)**

* Ensure video chunk embeddings in Qdrant carry metadata: `video_id`, `doc_url`, `timestamp_start`.
* Implement/complete `SearchService.answer_with_citations(query)`:
  * vector top-K with filter by `video_id in (…)`
  * return `answer`, inline indices `[1][2][3]`, and a citation map `{idx→doc_url, chunk_id, byte_offset, timestamp}`.
* Verify Neo4j links: `(:Video)-[:HAS_CHUNK]->(:Chunk)` and `(:Chunk)-[:PART_OF]->(:Document)` exist on path used by services.
* Turn the 7 YT reds green without changing test names/locations.

---

## 4) Civic RFP Assistant (thin probe)

**Purpose:** Validate A2AP ingestion path and government-grade precision on budgets/deadlines.

**Intake Contract (function only, no UI)**

```python
# app/services/civic_rfp_probe.py
class CivicRfpProbeService:
    async def ingest_structured_findings(self, payload: dict) -> dict: ...
```

**Input (expected from web research agent)**

```json
{
  "query": "Find infrastructure RFPs in Newark, NJ over $1M",
  "claims": [
    {
      "text": "Newark RFP #2025-456 has $2,500,000 budget",
      "critical": true,
      "confidence": 0.92,
      "source_url": "https://newark.gov/rfps/2025-456",
      "byte_range": [120, 148],
      "quote": "Budget: $2,500,000",
      "deadline": "2025-02-15"
    }
  ],
  "sources": ["https://newark.gov/rfps/2025-456", "..."]
}
```

**Behavior**

* Convert to **A2AP** `ProvenanceStatement` records and persist (Neo4j).
* Tag **critical** facts (budget, deadline, agency) for verification queue.
* Return a summary `{stored: n, queued_for_verification: m}`.

**Tests (integration)**

```
tests/integration/civic/test_civic_rfp_probe.py
- test_ingest_creates_statements_with_citations
- test_marks_critical_facts_for_verification
- test_handles_missing_fields_gracefully
```

---

## 5) API Wiring & Files (keep small)

* `app/api/creator_endpoints.py` (routes + flag gates)
* `app/services/creator_insights_service.py`
* `app/services/creator_outline_service.py`
* `app/services/creator_metadata_service.py`
* `app/services/civic_rfp_probe.py` (thin)
* Tests under `tests/integration/creator/` and `tests/integration/civic/`
* `docs/creator/README.md` (curl examples)

> If edits to `SearchService`/repositories are needed for small filters or DTOs, keep them surgical.

---

## 6) Engineering Guardrails

* **No new infra**; use existing Neo4j, Qdrant, Postgres, MinIO, Redis.
* **No mocks** in integration tests.
* **Perf targets:** topic-map < 2s small channel; outline < 3s small input.
* **Coverage delta:** +2% on touched files.
* **Format/type/test tasks** (run before finalizing):
  * `ruff/black/isort`
  * `mypy app/`
  * `pytest -q`
  * `pytest --cov=app --cov-report=term-missing`

**PLAN → BUILD discipline**

* Phase PLAN: create `plan.md` with file list, endpoints, tests, and risk notes.
* Phase BUILD: implement exactly those files. If scope pressure appears, stop and report.

**MCP/VS Code behavior**

* Make small, complete PR-sized edits.
* Prefer additive files; avoid refactors.
* Keep edit count and LOC within budget.

---

## 7) Acceptance Criteria (v0.1)

* Three endpoints working when flags ON, returning specified JSON shapes.
* Integration tests added and green against real services.
* Outline produces inline citations that resolve to existing chunks (or basic provenance fallback when RAG flag OFF).
* SEO description includes a "Sources" footer if citations exist.
* Civic probe converts structured claims into A2AP statements and queues critical facts.

---

## 8) Reporting Back (single file)

Produce `summary.md` with:

* Implemented files & endpoints
* Test list and run summary
* Flags touched and default states
* Known limitations / next obvious improvements

---

**That's it.** This gives Claude a precise, finishable slice for the Creator Assistant (plus the thin civic probe) with zero ambiguity and strong tests.
