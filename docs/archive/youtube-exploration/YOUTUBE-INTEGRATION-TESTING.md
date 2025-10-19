# YouTube Integration Testing Guide

## Overview

This guide covers the comprehensive integration testing suite for YouTube video processing in the Williams Librarian system. The tests exercise the complete pipeline from video URL ingestion to retrieval and RAG functionality.

## Test Video

**Default Test Video**: https://youtu.be/zZtHnwoZAT8
- Duration: ~15 minutes
- Used for quick integration testing
- Configurable via environment variable

## Test Suite Structure

### 1. TestYouTubeExtraction
Tests the extraction layer - getting video metadata and transcripts.

**Tests**:
- `test_extract_video_metadata` - Verify all metadata fields extracted
- `test_extract_video_id` - Handle various URL formats
- `test_transcript_not_empty` - Ensure transcript content exists

**What it validates**:
- ✓ Video URL processing
- ✓ Metadata extraction (title, author, duration, publish date)
- ✓ Transcript fetching
- ✓ Content type identification

### 2. TestYouTubeIngestion
Tests the complete ingestion pipeline from extraction to storage.

**Tests**:
- `test_ingest_youtube_video` - Full ingestion workflow
- `test_chunks_created` - Content chunking
- `test_embeddings_created` - Vector embedding generation

**What it validates**:
- ✓ Content storage in database
- ✓ Chunking algorithm
- ✓ Embedding generation
- ✓ Data persistence

**Expected behavior**:
- 15-minute video → 20-50 chunks (depends on content)
- Each chunk has embeddings (typically 384 or 1536 dimensions)
- Chunks maintain order and context

### 3. TestYouTubeRetrieval
Tests search and retrieval functionality.

**Tests**:
- `test_semantic_search` - Vector similarity search
- `test_filter_by_source` - Source type filtering
- `test_search_by_metadata` - Metadata-based search

**What it validates**:
- ✓ Semantic search returns relevant results
- ✓ Filtering by source type works
- ✓ Search by title/author functions
- ✓ Result ranking by relevance

### 4. TestYouTubeRAG
Tests RAG (Retrieval Augmented Generation) capabilities.

**Tests**:
- `test_rag_query_with_citations` - Answer generation with sources
- `test_rag_answer_quality` - Answer relevance and quality
- `test_rag_citation_accuracy` - Citation correctness

**What it validates**:
- ✓ Question answering from video content
- ✓ Citation generation
- ✓ Answer quality and relevance
- ✓ Source attribution accuracy

### 5. TestYouTubeGraphRelations
Tests Neo4j graph database relationships.

**Tests**:
- `test_video_content_relationship` - Content node creation
- `test_video_chunk_relationships` - Chunk linking
- `test_entity_extraction` - Named entity extraction

**What it validates**:
- ✓ Content nodes in Neo4j
- ✓ HAS_CHUNK relationships
- ✓ Entity extraction and MENTIONS relationships
- ✓ Graph structure integrity

### 6. TestMultipleVideos
Tests processing videos of different lengths.

**Tests**:
- `test_process_multiple_videos` - Short and medium videos
- `test_process_long_video` - 3+ hour videos (requires config)

**What it validates**:
- ✓ Handling videos of various durations
- ✓ Performance at scale
- ✓ Resource management

### 7. TestYouTubeErrorHandling
Tests error scenarios and edge cases.

**Tests**:
- `test_invalid_url` - Invalid YouTube URLs
- `test_private_video` - Private/unavailable videos
- `test_video_without_transcript` - Fallback mechanisms

**What it validates**:
- ✓ Graceful error handling
- ✓ Appropriate exceptions raised
- ✓ Fallback to description when transcript unavailable

### 8. TestYouTubePerformance
Tests performance benchmarks.

**Tests**:
- `test_extraction_speed` - Extraction performance
- `test_ingestion_speed` - Full pipeline performance

**Performance targets**:
- 15-minute video extraction: < 30 seconds
- Full ingestion pipeline: < 2 minutes

## Configuration

### Environment Variables

```bash
# Default test video (overrides all)
export TEST_YOUTUBE_URL="https://youtu.be/YOUR_VIDEO_ID"

# Specific size categories
export TEST_YOUTUBE_SHORT="https://youtu.be/SHORT_VIDEO"    # < 30 min
export TEST_YOUTUBE_MEDIUM="https://youtu.be/MEDIUM_VIDEO"  # 30-60 min
export TEST_YOUTUBE_LONG="https://youtu.be/LONG_VIDEO"      # 3+ hours
```

### Test Video Selection

The test suite uses a tiered approach:
1. **Short videos** (default): Fast testing, quick feedback
2. **Medium videos** (optional): Standard testing scenarios
3. **Long videos** (optional): Stress testing, requires special handling

### Configuration File

Use `tests/integration/youtube_test_config.py` to view and manage test configurations:

```bash
python tests/integration/youtube_test_config.py
```

## Running Tests

### Run All YouTube Integration Tests

```bash
poetry run pytest tests/integration/test_youtube_end_to_end.py -v
```

### Run Specific Test Classes

```bash
# Just extraction tests
poetry run pytest tests/integration/test_youtube_end_to_end.py::TestYouTubeExtraction -v

# Just RAG tests
poetry run pytest tests/integration/test_youtube_end_to_end.py::TestYouTubeRAG -v

# Just performance tests
poetry run pytest tests/integration/test_youtube_end_to_end.py::TestYouTubePerformance -v
```

### Run Specific Tests

```bash
# Single test
poetry run pytest tests/integration/test_youtube_end_to_end.py::TestYouTubeExtraction::test_extract_video_metadata -v

# Tests matching pattern
poetry run pytest tests/integration/test_youtube_end_to_end.py -v -k "extract"
poetry run pytest tests/integration/test_youtube_end_to_end.py -v -k "rag"
```

### Run with Different Video

```bash
TEST_YOUTUBE_URL="https://youtu.be/DIFFERENT_VIDEO" \
  poetry run pytest tests/integration/test_youtube_end_to_end.py -v
```

### Show Test Output

```bash
# Show print statements
poetry run pytest tests/integration/test_youtube_end_to_end.py -v -s

# Show detailed failures
poetry run pytest tests/integration/test_youtube_end_to_end.py -v --tb=long

# Stop on first failure
poetry run pytest tests/integration/test_youtube_end_to_end.py -v -x
```

## Prerequisites

### Required Services

All services must be running before tests:

1. **Neo4j** (port 7687)
   ```bash
   docker-compose up neo4j -d
   ```

2. **Qdrant** (port 6333)
   ```bash
   docker-compose up qdrant -d
   ```

3. **PostgreSQL** (port 5432)
   ```bash
   docker-compose up postgres -d
   ```

4. **Redis** (port 6379)
   ```bash
   docker-compose up redis -d
   ```

5. **MinIO** (port 9000)
   ```bash
   docker-compose up minio -d
   ```

### Start All Services

```bash
docker-compose up -d
```

### Verify Services

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Service Health Checks

Tests automatically skip if required services are unavailable:

```python
@pytest.mark.skipif(not is_neo4j_available(), reason="Neo4j not available")
def test_something():
    ...
```

## Expected Results

### Successful Test Run Output

```
tests/integration/test_youtube_end_to_end.py::TestYouTubeExtraction::test_extract_video_metadata PASSED
✓ Extracted video: Video Title Here
  Duration: 897s
  Author: Channel Name
  Transcript length: 15234 chars

tests/integration/test_youtube_end_to_end.py::TestYouTubeIngestion::test_chunks_created PASSED
✓ Created 42 chunks from video

tests/integration/test_youtube_end_to_end.py::TestYouTubeRAG::test_rag_query_with_citations PASSED
✓ RAG Query: 'What is the main topic discussed in this video?'
  Answer: The video discusses...
  Citations: 5

======================== 25 passed in 45.3s =========================
```

### Test Coverage

The integration tests exercise:
- **Extraction layer**: YouTubeExtractor
- **Service layer**: ContentService, SearchService, RAGService
- **Repository layer**: NeoRepository, QdrantRepository
- **Pipeline**: Full ingestion workflow
- **Graph**: Neo4j relationships and entities

## Troubleshooting

### Test Failures

#### "Neo4j is not available"
```bash
# Start Neo4j
docker-compose up neo4j -d

# Check logs
docker-compose logs neo4j

# Verify connection
nc -zv localhost 7687
```

#### "Qdrant is not available"
```bash
# Start Qdrant
docker-compose up qdrant -d

# Check logs
docker-compose logs qdrant

# Verify connection
curl http://localhost:6333/health
```

#### "Video extraction failed"
- Check internet connectivity
- Verify video URL is valid and public
- Check if video has transcript available
- Review pytube/youtube-transcript-api versions

#### "Embeddings not created"
- Verify embedding service is configured
- Check API keys if using external service (OpenAI, Cohere)
- Review embedding dimension configuration

#### "RAG query failed"
- Ensure LLM service is configured
- Check API keys
- Verify sufficient context chunks retrieved

### Performance Issues

#### "Tests running slowly"
- Reduce test video duration
- Skip long video tests
- Run specific test classes instead of full suite
- Check service resource allocation (Docker memory limits)

#### "Memory errors"
- Increase Docker memory limits
- Use smaller embedding models
- Process fewer chunks in parallel

### Data Cleanup

Tests should automatically clean up, but if needed:

```python
# Manual cleanup
from app.repositories.neo_repository import NeoRepository

neo_repo = NeoRepository()
neo_repo.clear_database()
neo_repo.close()
```

Or via Cypher:

```cypher
// Delete all test data
MATCH (n) DETACH DELETE n
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: YouTube Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
      
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run YouTube integration tests
        env:
          TEST_YOUTUBE_URL: ${{ secrets.TEST_YOUTUBE_URL }}
        run: |
          poetry run pytest tests/integration/test_youtube_end_to_end.py -v
```

## Metrics and Monitoring

### Key Metrics to Track

1. **Test execution time**: Should remain stable
2. **Chunk count**: Should be consistent for same video
3. **Search relevance**: Top results should be pertinent
4. **RAG answer quality**: Qualitative assessment
5. **Error rate**: Should be 0% for valid videos

### Logging

Tests include verbose output:

```python
print(f"\n✓ Extracted video: {metadata['title']}")
print(f"  Duration: {metadata['duration']}s")
print(f"  Chunks: {len(chunks)}")
```

Enable with `-s` flag:

```bash
poetry run pytest tests/integration/test_youtube_end_to_end.py -v -s
```

## Best Practices

### Test Video Selection

1. **Use public videos**: Avoid private or region-locked
2. **Choose stable content**: Avoid videos that might be deleted
3. **Select appropriate length**: 10-20 minutes for regular testing
4. **Verify transcript availability**: Test videos should have captions

### Test Maintenance

1. **Update test videos**: If videos become unavailable
2. **Review performance targets**: Adjust as system evolves
3. **Add new test cases**: As features are added
4. **Document failures**: Include reproduction steps

### Development Workflow

1. **Run tests locally**: Before pushing changes
2. **Test specific areas**: When making focused changes
3. **Full suite before release**: Comprehensive validation
4. **Monitor CI results**: Catch environment-specific issues

## Advanced Testing Scenarios

### Testing Long Videos (3+ Hours)

Requires configuration:

```bash
export TEST_YOUTUBE_LONG="https://youtu.be/LONG_VIDEO_ID"
poetry run pytest tests/integration/test_youtube_end_to_end.py::TestMultipleVideos::test_process_long_video -v
```

Expected behavior:
- Video split into segments (future enhancement)
- Parallel processing (future enhancement)
- More chunks created (50-200+)
- Longer processing time (proportional)

### Testing Multiple Videos in Parallel

```python
# Custom test script
import asyncio
from tests.integration.test_youtube_end_to_end import *

async def test_batch_processing():
    video_urls = [
        "https://youtu.be/VIDEO1",
        "https://youtu.be/VIDEO2",
        "https://youtu.be/VIDEO3",
    ]
    
    tasks = [process_video(url) for url in video_urls]
    results = await asyncio.gather(*tasks)
    
    assert all(results)
```

### Testing With Real-Time Data

```python
# Test with live YouTube data
@pytest.mark.live
async def test_latest_video_from_channel():
    channel_id = "UC..."
    latest_video = await get_latest_video(channel_id)
    
    raw_content = await youtube_extractor.extract(latest_video.url)
    assert raw_content is not None
```

## Future Enhancements

### Planned Test Additions

1. **Comment extraction testing** (Phase 4)
   - Verify comment retrieval
   - Test sentiment analysis
   - Validate topic extraction

2. **Audio processing testing** (Phase 2-3)
   - FFMPEG audio extraction
   - Segment splitting validation
   - Whisper transcription quality

3. **Long video handling** (Phase 5)
   - Segment coordination
   - Parallel processing
   - Cross-segment entity resolution

4. **Performance benchmarking**
   - Detailed timing breakdowns
   - Resource utilization metrics
   - Scalability testing

## Related Documentation

- [YOUTUBE-ADVANCED-ARCHITECTURE.md](YOUTUBE-ADVANCED-ARCHITECTURE.md) - Architecture design
- [testing-guide.md](testing-guide.md) - General testing guide
- [testing_with_real_data.md](testing_with_real_data.md) - Real data testing strategies

## Support

For issues or questions:
1. Check test output for specific error messages
2. Review service logs (`docker-compose logs`)
3. Verify configuration (`python tests/integration/youtube_test_config.py`)
4. Check video accessibility (can you watch it on YouTube?)

## Summary

This integration test suite provides comprehensive coverage of YouTube video processing from ingestion to retrieval. It validates the entire pipeline, ensures data quality, and catches regressions early in development.

**Key Features**:
- ✅ Complete pipeline testing
- ✅ Configurable test videos
- ✅ Multiple test scenarios
- ✅ Performance validation
- ✅ Error handling verification
- ✅ Graph relationship validation
- ✅ RAG functionality testing

Run regularly to ensure system reliability! 🎬
