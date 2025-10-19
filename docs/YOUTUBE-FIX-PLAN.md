# YouTube Integration Fix - Implementation Plan

**Date:** October 14, 2025  
**Goal:** Fix 7 skipped YouTube tests to achieve 100% pass rate

---

## Current State Analysis

The 7 skipped tests fail because:

1. **ContentService** stores only summary embedding, not chunk embeddings
2. **ContentService** doesn't add YouTube-specific metadata (video_id, channel, published_at)
3. **ContentService** doesn't create Neo4j Content/Chunk nodes
4. **SearchService** doesn't support metadata filters (source='youtube')
5. **SearchService.query_with_citations()** is incomplete (no citation resolver)

---

## Implementation Strategy

### Phase 1: Fix Qdrant Integration (A - Make Search Work)

**File:** `app/services/content_service.py`

**Changes Needed:**
1. Add proper text chunking using EnhancedChunker
2. Generate embeddings for each chunk (not just summary)
3. Store chunks in Qdrant with YouTube-specific payload:
   ```python
   payload = {
       "source": "youtube",  # NEW
       "video_id": metadata.get("video_id"),  # NEW
       "channel": metadata.get("author"),  # NEW
       "published_at": metadata.get("published_at"),  # NEW
       "chunk_id": chunk_id,  # NEW
       "chunk_index": i,  # NEW
       "content_id": content_id,
       "url": str(processed.url),
       "title": processed.title,
       "quality_score": quality,
       "tags": processed.tags,
       "tier": tier,
       "text": chunk_text  # NEW - store actual text for retrieval
   }
   ```

**New Methods:**
- `_chunk_and_embed_content(raw_content, processed) -> list[dict]`
- `_store_chunks_in_qdrant(chunks, content_id, metadata)`

###Phase 2: Fix Neo4j Integration (C - Wire Graph Edges)

**File:** `app/services/content_service.py`

**Changes Needed:**
1. Add `neo_repo: NeoRepository` to constructor
2. Create Content node during ingestion
3. Create Chunk nodes for each chunk
4. Create HAS_CHUNK relationships
5. Wrap in single Neo4j transaction

**New Cypher Queries:**
```cypher
// Create Video/Content node
MERGE (v:Content {content_id: $content_id})
SET v.url = $url,
    v.title = $title,
    v.source_type = $source_type,
    v.video_id = $video_id,
    v.channel = $channel,
    v.published_at = $published_at,
    v.created_at = datetime()

// Create Chunk nodes with HAS_CHUNK relationships
UNWIND $chunks AS chunk
MERGE (c:Chunk {chunk_id: chunk.chunk_id})
SET c.text = chunk.text,
    c.chunk_index = chunk.chunk_index,
    c.byte_start = chunk.byte_start,
    c.byte_end = chunk.byte_end
MERGE (v)-[:HAS_CHUNK {position: chunk.chunk_index}]->(c)
```

### Phase 3: Fix SearchService (A - Metadata Filters)

**File:** `app/services/search_service.py`

**Changes Needed:**
1. Add `filters` parameter to `search()` method
2. Convert filters to Qdrant filter format
3. Support source='youtube', video_id, etc.

**Example:**
```python
async def search(
    self,
    query: str,
    top_k: int = 10,
    min_score: float = 0.0,
    filters: dict | None = None  # NEW
) -> list[SearchResult]:
    # ... existing code ...
    
    # Build Qdrant filter
    qdrant_filter = None
    if filters:
        qdrant_filter = self._build_qdrant_filter(filters)
    
    # Search with filters
    if self.qdrant_repository:
        raw_results = await self.qdrant_repository.search_by_vector(
            query_vector=query_embedding,
            top_k=top_k,
            filter=qdrant_filter  # NEW
        )
```

### Phase 4: Fix RAG Citations (B - Citation Resolver)

**File:** `app/services/search_service.py`

**Changes Needed:**
1. Build citation map BEFORE LLM call
2. Add LLM prompt guards
3. Post-process to validate citation indices

**New Method:**
```python
def _build_citation_map(self, chunks: list) -> dict:
    """Build citation table with exact references."""
    table = {}
    for i, chunk in enumerate(chunks, start=1):
        table[i] = {
            "doc_url": chunk.get("url"),
            "chunk_id": chunk.get("chunk_id"),
            "page_or_ts": chunk.get("page") or chunk.get("t_start"),
            "byte_start": chunk.get("byte_start"),
            "byte_end": chunk.get("byte_end"),
            "quote_text": self._extract_quote(chunk.get("text"), query),
            "confidence": chunk.get("score", 0.0)
        }
    return table
```

**Enhanced Prompt:**
```python
system_prompt = """You are a helpful assistant that answers questions with citations.

CITATION RULES:
1. Use ONLY citation indices [1] through [N] provided in the citations table
2. DO NOT invent new citation indices
3. Each claim must have at least one citation
4. Place citations immediately after the claim: "The sky is blue [1]."

Citations available: [1] through [{}]
""".format(len(citation_map))
```

---

## Implementation Order

1. ✅ **Qdrant payload enhancement** (30 min)
   - Add YouTube metadata fields
   - Fix collection name consistency
   
2. ✅ **Chunking and embedding** (45 min)
   - Use EnhancedChunker
   - Generate embeddings per chunk
   - Store in Qdrant with full payload

3. ✅ **Neo4j Content/Chunk nodes** (45 min)
   - Add neo_repo to ContentService
   - Create nodes in transaction
   - Add HAS_CHUNK relationships

4. ✅ **SearchService filters** (30 min)
   - Add filters parameter
   - Build Qdrant filter objects
   - Test with source='youtube'

5. ✅ **Citation resolver** (60 min)
   - Build citation map
   - Add LLM guards
   - Validate indices

6. ✅ **Un-skip tests** (15 min)
   - Remove @pytest.mark.skip decorators
   - Run tests
   - Fix any remaining issues

**Total Estimated Time:** 3-4 hours

---

## Testing Strategy

### Unit Tests (Fast)
- Test chunking with mock data
- Test citation map building
- Test filter construction

### Integration Tests (Real Services)
- Un-skip YouTube tests one by one
- Verify with actual YouTube video
- Check Neo4j for nodes/relationships
- Verify Qdrant has all chunks

### Guardrail Tests (NEW)
```python
def test_qdrant_collection_contract():
    """Ensure collection has correct dim/distance."""
    collection = qdrant.get_collection("content_chunks")
    assert collection.config.vectors.size == 384
    assert collection.config.vectors.distance == Distance.COSINE

def test_citation_indices_valid():
    """Ensure all citation indices exist in map."""
    response = search_service.query_with_citations("test query")
    indices = extract_citation_indices(response.answer)
    assert all(i in response.citation_map for i in indices)

def test_has_chunk_relationships():
    """Ensure HAS_CHUNK edges exist after ingestion."""
    content_id = content_service.ingest_content(youtube_content)
    chunk_count = neo_repo.execute_query(
        "MATCH (c:Content {content_id: $id})-[:HAS_CHUNK]->(ch) RETURN count(ch)",
        {"id": content_id}
    )[0]["count(ch)"]
    assert chunk_count >= 1
```

---

## Success Criteria

- ✅ All 7 YouTube tests pass
- ✅ Search returns results for YouTube content
- ✅ RAG generates answers with valid citations
- ✅ Neo4j has Content and Chunk nodes
- ✅ Qdrant has chunks with YouTube metadata
- ✅ Guardrail tests pass

---

## Risk Mitigation

**Risk:** Breaking existing tests  
**Mitigation:** Run full test suite after each change

**Risk:** Performance degradation (chunking + embedding)  
**Mitigation:** Use asyncio.gather() for parallel embedding generation

**Risk:** Transaction failures in Neo4j  
**Mitigation:** Proper error handling and rollback

**Risk:** Qdrant collection size explosion  
**Mitigation:** Use consistent collection name, add TTL/cleanup

---

## Next Steps

1. Start with Qdrant payload enhancement (safest, highest impact)
2. Add chunking and embedding
3. Add Neo4j integration
4. Fix SearchService filters
5. Implement citation resolver
6. Un-skip tests and verify

This plan directly addresses all 7 failing tests and sets up proper infrastructure for YouTube content processing.
