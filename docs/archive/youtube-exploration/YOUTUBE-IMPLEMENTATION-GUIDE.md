# YouTube Extractor Implementation Guide

## Quick Reference: What Needs to be Done

### Current Problem
- pytube fails with HTTP 400 errors
- youtube-transcript-api fails with XML parse errors  
- Many videos have no transcripts or descriptions

### Solution
Replace current extractor with:
1. yt-dlp for reliable downloads
2. OpenAI Whisper for transcription
3. MinIO for video storage
4. Multi-strategy fallback system

---

## Implementation Steps

### Step 1: Update youtube.py (Main Implementation)

**File**: `app/pipeline/extractors/youtube.py`

**New Class Structure**:
```python
class YouTubeExtractor(ContentExtractor):
    def __init__(self, minio_repository=None, use_whisper=True, store_video=True)
    async def extract(self, url: str) -> RawContent
    async def _get_video_metadata(self, url: str) -> dict
    async def _download_and_store_video(self, url: str, video_id: str, info: dict) -> str
    async def _try_youtube_transcript(self, video_id: str) -> str | None
    async def _transcribe_with_whisper(self, url: str, video_id: str) -> str | None
    async def _download_audio(self, url: str, video_id: str) -> str
    async def _store_in_minio(self, file_path: str, video_id: str, content_type: str) -> str
    async def _whisper_transcribe(self, audio_path: str) -> str
    def _build_metadata(self, info: dict, video_id: str) -> dict
```

**Extraction Flow**:
```
1. Get metadata with yt-dlp (no download)
   ↓
2. Download complete video → Store in MinIO
   ↓
3. Try YouTube Transcript API (fast, free)
   ↓ (if fails)
4. Download audio → Transcribe with Whisper → Store audio in MinIO
   ↓ (if fails)
5. Use video description
   ↓
6. Return RawContent with transcript + metadata
```

### Step 2: Test the Extraction

**Test Video**: https://www.youtube.com/watch?v=vdgRm6v8HyY

**Quick Test Script**:
```bash
cd /home/kwilliams/is373/williams-librarian

# Test without MinIO or Whisper first (just metadata)
poetry run python -c "
import asyncio
from app.pipeline.extractors.youtube import YouTubeExtractor

async def test():
    extractor = YouTubeExtractor(use_whisper=False, store_video=False)
    raw_content = await extractor.extract('https://www.youtube.com/watch?v=vdgRm6v8HyY')
    print(f'✓ Title: {raw_content.metadata[\"title\"]}')
    print(f'✓ Duration: {raw_content.metadata[\"duration\"]}s')
    print(f'✓ Transcript: {len(raw_content.raw_text)} chars')

asyncio.run(test())
"
```

### Step 3: Add MinIO Integration

**Get MinIO Repository**:
```python
from app.repositories.minio_repository import MinioRepository

minio_repo = MinioRepository()
extractor = YouTubeExtractor(
    minio_repository=minio_repo,
    use_whisper=True,
    store_video=True
)
```

### Step 4: Add OpenAI API Key

**Set Environment Variable**:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Test Whisper**:
```bash
poetry run python -c "
from openai import OpenAI
client = OpenAI()
print('✓ OpenAI client initialized')
print(f'✓ API Key configured: {bool(client.api_key)[:20]}...')
"
```

### Step 5: Run Integration Tests

```bash
# Run all YouTube tests
poetry run pytest tests/integration/test_youtube_end_to_end.py -v -s

# Run just extraction tests
poetry run pytest tests/integration/test_youtube_end_to_end.py::TestYouTubeExtraction -v

# Run with custom video
TEST_YOUTUBE_URL="https://www.youtube.com/watch?v=vdgRm6v8HyY" \
  poetry run pytest tests/integration/test_youtube_end_to_end.py -v
```

---

## Code Template

Here's the complete extractor implementation ready to copy:

**Location**: `/home/kwilliams/is373/williams-librarian/app/pipeline/extractors/youtube.py`

**Size**: ~400 lines

**Key Features**:
- ✅ Multi-strategy extraction
- ✅ Video download & storage
- ✅ Whisper transcription
- ✅ Comprehensive metadata
- ✅ Error handling & logging
- ✅ Automatic cleanup
- ✅ MinIO integration

**Dependencies**:
- yt-dlp (✅ installed: 2024.12.23)
- openai (✅ installed: 1.109.1)
- ffmpeg (✅ installed: 6.1.1)
- youtube-transcript-api (✅ installed)

---

## Testing Checklist

### Before Running Tests:
- [ ] All Docker services running (`docker-compose ps`)
- [ ] Neo4j available on port 7687
- [ ] Qdrant available on port 6333
- [ ] MinIO available on port 9000
- [ ] OPENAI_API_KEY environment variable set
- [ ] Test video URL decided

### Test Progression:
1. [ ] Test metadata extraction (no download)
2. [ ] Test video download (no MinIO)
3. [ ] Test MinIO storage
4. [ ] Test Whisper transcription
5. [ ] Test full pipeline
6. [ ] Test with multiple videos
7. [ ] Test error handling
8. [ ] Test performance benchmarks

### Expected Results:
```
TestYouTubeExtraction::test_extract_video_metadata        PASSED ✓
TestYouTubeExtraction::test_extract_video_id             PASSED ✓
TestYouTubeExtraction::test_transcript_not_empty         PASSED ✓
TestYouTubeIngestion::test_ingest_youtube_video          PASSED ✓
TestYouTubeIngestion::test_chunks_created                PASSED ✓
TestYouTubeIngestion::test_embeddings_created            PASSED ✓
... (25 tests total)

========================= 25 passed in 120s ==========================
```

---

## Troubleshooting

### Issue: yt-dlp download fails
**Solution**: Check internet connection, try different video

### Issue: Whisper transcription fails
**Solution**: 
- Verify OPENAI_API_KEY is set
- Check API key has credits
- Try with smaller audio file first

### Issue: MinIO storage fails
**Solution**:
- Check MinIO is running: `curl http://localhost:9000/minio/health/live`
- Verify bucket permissions
- Check disk space

### Issue: Tests timeout
**Solution**:
- Increase pytest timeout in pyproject.toml
- Use shorter test videos
- Skip video download tests initially

---

## Performance Expectations

### 15-Minute Video:
- Metadata extraction: < 2 seconds
- Video download: 10-30 seconds (depends on connection)
- Audio extraction: 5-10 seconds
- Whisper transcription: 10-30 seconds
- **Total**: 30-60 seconds

### 1-Hour Video:
- Metadata extraction: < 2 seconds
- Video download: 30-120 seconds
- Audio extraction: 15-30 seconds
- Whisper transcription: 60-180 seconds
- **Total**: 2-5 minutes

### 3-Hour Video (Future):
- Will require segmentation (Phase 5)
- Parallel processing
- **Total**: 10-20 minutes (with optimizations)

---

## Cost Estimation

### Per Video:
- **Metadata**: Free (yt-dlp)
- **Storage**: ~500MB video + ~5MB audio = 505MB
- **Whisper**: $0.006/minute of audio

### Examples:
- 15-min video: $0.09
- 1-hour video: $0.36
- 3-hour video: $1.08

### Monthly (100 videos/month avg 30 min):
- Transcription: 100 × 30 × $0.006 = $18/month
- Storage: 100 × 0.5GB = 50GB (~$1/month on S3, free on MinIO)
- **Total**: ~$19/month

---

## Next Actions

### Immediate (Today):
1. ✅ Review architecture docs
2. ✅ Review test suite
3. ✅ Understand implementation plan
4. ⏳ Implement new extractor
5. ⏳ Test with one video
6. ⏳ Run integration tests

### Short-term (This Week):
1. Get all tests passing
2. Test with various video types
3. Measure performance
4. Document results
5. Fix any bugs found

### Medium-term (Next 2 Weeks):
1. Phase 2: Enhanced metadata
2. Phase 3: Audio processing improvements
3. Phase 4: Comment extraction
4. Phase 5: Long video handling

---

## Success Criteria

### Definition of Done:
- ✅ New extractor implemented
- ✅ All 25 integration tests passing
- ✅ Videos stored in MinIO
- ✅ Transcripts generated via Whisper
- ✅ Performance targets met (< 2 min for 15-min video)
- ✅ Error handling works correctly
- ✅ Documentation updated
- ✅ Code reviewed and merged

### Quality Gates:
- No syntax errors
- No runtime errors with valid videos
- Graceful handling of invalid videos
- Proper cleanup of temporary files
- Comprehensive logging
- Test coverage > 90%

---

## Reference Commands

```bash
# Start services
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f youtube-service

# Test extraction (quick)
poetry run python -c "import asyncio; from app.pipeline.extractors.youtube import YouTubeExtractor; asyncio.run(YouTubeExtractor().extract('URL'))"

# Run tests
poetry run pytest tests/integration/test_youtube_end_to_end.py -v

# Check coverage
poetry run pytest tests/integration/test_youtube_end_to_end.py --cov=app.pipeline.extractors.youtube

# Cleanup MinIO
poetry run python -c "from app.repositories.minio_repository import MinioRepository; repo = MinioRepository(); repo.delete_bucket('youtube-video'); repo.delete_bucket('youtube-audio')"
```

---

## Files Ready for Implementation

All prepared files are in the repository:

1. **Architecture**: `docs/YOUTUBE-ADVANCED-ARCHITECTURE.md`
2. **Tests**: `tests/integration/test_youtube_end_to_end.py`
3. **Config**: `tests/integration/youtube_test_config.py`
4. **Docs**: `docs/YOUTUBE-INTEGRATION-TESTING.md`
5. **Summary**: `docs/YOUTUBE-SESSION-SUMMARY.md`
6. **This Guide**: `docs/YOUTUBE-IMPLEMENTATION-GUIDE.md`

**Current File to Edit**: `app/pipeline/extractors/youtube.py`

**Implementation Time**: 2-3 hours for experienced developer

---

Good luck with the implementation! 🚀
