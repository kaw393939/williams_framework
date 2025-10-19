# Code Issues Found - October 12, 2025

## Bug #1: Pagination Bug in SearchService.query_with_citations()

**File**: `app/services/search_service.py`  
**Lines**: 145-215  
**Severity**: Medium  
**Status**: Found, needs fix

### Description
The `query_with_citations()` method has a logical error in how it handles pagination and citation references.

### The Problem

```python
# 1. Get chunks and create ALL citations
chunks = self._get_relevant_chunks(query, max_citations)
citations = []
for i, chunk in enumerate(chunks[:max_citations], 1):
    citation = self.citation_service.create_citation(...)
    citations.append(citation)

# 2. Generate answer using ALL chunks (references [1], [2], [3], ...)
if self.llm_provider:
    context = "\n\n".join([
        f"[{i+1}] {chunk['text']}"
        for i, chunk in enumerate(chunks[:max_citations])
    ])
    answer = self.llm_provider.generate(prompt)  # Answer includes [1], [2], [3]...

# 3. THEN paginate citations
start_idx = (page - 1) * page_size
end_idx = start_idx + page_size
paginated_citations = citations[start_idx:end_idx]  # Only returns subset!

return {
    "answer": answer,  # References [1], [2], [3]...
    "citations": paginated_citations,  # But only has [4], [5], [6] if page=2!
}
```

### Impact
- User on page 2 gets an answer that says "According to [1] and [2]..." but citations [1] and [2] are NOT in the paginated results
- Citation numbers don't match between answer and citations list
- Breaks citation resolution for paginated results

### Recommended Fix

**Option 1**: Don't paginate citations in this method (simplest)
```python
# Generate answer with all citations
# Return all citations - let the caller paginate if needed
return {
    "answer": answer,
    "citations": citations,  # All citations
    "total_count": len(citations)
}
```

**Option 2**: Only generate answer for citations on current page
```python
# Paginate FIRST
start_idx = (page - 1) * page_size
end_idx = start_idx + page_size
paginated_citations = citations[start_idx:end_idx]

# Generate answer using ONLY paginated citations
if self.llm_provider:
    context = "\n\n".join([
        f"[{i+1}] {citation['quote_text']}"
        for i, citation in enumerate(paginated_citations)
    ])
    # Answer now only references citations that are actually returned
    answer = self.llm_provider.generate(prompt)
```

**Option 3**: Renumber citations for each page
```python
# After pagination, renumber citations to start from 1
for i, citation in enumerate(paginated_citations, 1):
    citation["citation_number"] = i
    citation["citation_id"] = f"[{i}]"
```

### Test Case to Verify Bug
```python
def test_query_with_citations_pagination_bug():
    """Test that paginated citations match answer references."""
    # Create 10 chunks
    mock_neo_repo.execute_query.return_value = [
        {"id": f"chunk{i}", "text": f"Text {i}", "url": "test.com"}
        for i in range(10)
    ]
    
    # Mock LLM to return answer with citation numbers
    mock_llm_provider.generate.return_value = "Answer with [1], [2], [3]"
    
    # Get page 2 (should return citations 6-10)
    result = service.query_with_citations(
        "test",
        max_citations=10,
        page=2,
        page_size=5
    )
    
    # BUG: Answer references [1], [2], [3]
    # But citations on page 2 are [6], [7], [8], [9], [10]
    assert "[1]" in result["answer"]  # Answer mentions [1]
    assert result["citations"][0]["citation_id"] == "[6]"  # But first citation is [6]!
    # This is the bug!
```

---

## Potential Issue #2: Missing Error Handling in _get_relevant_chunks

**File**: `app/services/search_service.py`  
**Lines**: 217-240  
**Severity**: Low  
**Status**: Needs review

### Description
The `_get_relevant_chunks()` method assumes chunks have `created_at` field but doesn't handle if it's missing.

```python
cypher_query = """
MATCH (c:Chunk)-[:PART_OF]->(d:Document)
RETURN c.id as id, c.text as text, d.url as url
ORDER BY c.created_at DESC  # What if created_at doesn't exist?
LIMIT $limit
"""
```

### Recommended Fix
Add `COALESCE` for missing created_at:
```python
cypher_query = """
MATCH (c:Chunk)-[:PART_OF]->(d:Document)
RETURN c.id as id, c.text as text, d.url as url
ORDER BY COALESCE(c.created_at, datetime()) DESC
LIMIT $limit
"""
```

---

## Code Quality Issues

### 1. Inconsistent Error Handling in search_service.py

**Lines 78-81**: Returns empty list with just a warning
```python
if not query or not query.strip():
    logger.warning("Empty query provided to search")
    return []
```

**Lines 84-87**: Returns empty list with error
```python
else:
    logger.error("No embedder or cache available for search")
    return []
```

**Lines 98-100**: Returns empty list with error
```python
else:
    logger.error("No Qdrant client or repository available for search")
    return []
```

**Recommendation**: Be consistent - either all warnings or all errors for similar conditions.

---

## Test Coverage Gaps (Leading to Undiscovered Bugs)

### High-Risk Uncovered Code

1. **neo_repository.py** (19% coverage)
   - 160 lines of database operations uncovered
   - Likely has edge cases around null handling
   - Connection error handling not tested

2. **search_service.py** (54% coverage)
   - The pagination bug above is in uncovered code (lines 205-209)
   - This is why the bug wasn't caught!

3. **LLM Providers** (0% coverage)
   - No tests for error handling
   - API failures not tested
   - Rate limiting not tested

### Recommendation
**Focus testing on the search_service pagination logic IMMEDIATELY** to prevent this bug from reaching production.

---

## Summary

- **1 confirmed bug**: Pagination in `query_with_citations()`
- **1 potential issue**: Missing null handling in Cypher query
- **Several code quality improvements** needed

These issues were found by examining code with low test coverage. This demonstrates why reaching 95%+ coverage is critical.
