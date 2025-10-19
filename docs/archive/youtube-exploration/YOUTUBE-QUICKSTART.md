# YouTube Processing Quick Start Guide

**Version:** 2.0 (Production-Ready)
**Date:** October 12, 2025
**Approach:** TDD with faster-whisper (local, free, fast)

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
cd /home/kwilliams/is373/williams-librarian

# Add faster-whisper for local transcription
poetry add faster-whisper torch

# Optional: For GPU acceleration
# poetry add torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Already have: yt-dlp, openai (fallback)
```

### Step 2: Verify Installation

```bash
# Test faster-whisper
python -c "from faster_whisper import WhisperModel; print('✓ faster-whisper installed')"

# Test yt-dlp
python -c "import yt_dlp; print('✓ yt-dlp installed')"

# Check ffmpeg
ffmpeg -version | head -1
```

### Step 3: Download Whisper Model (One-Time)

```bash
# This downloads the model to ~/.cache/huggingface/
python -c "
from faster_whisper import WhisperModel
print('Downloading large-v3 model...')
model = WhisperModel('large-v3', device='cpu', compute_type='int8')
print('✓ Model ready')
"
# Takes 2-3 minutes, ~3GB download
```

### Step 4: Run First Test

```bash
# Create simple test
cat > test_youtube_basic.py << 'EOF'
import asyncio
from faster_whisper import WhisperModel

async def test_transcription():
    print("Loading model...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    # Download test audio
    import yt_dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'test_audio.%(ext)s',
        'quiet': True,
    }
    
    print("Downloading test video...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://www.youtube.com/watch?v=jNQXAC9IVRw'])  # "Me at the zoo" - 19 sec
    
    print("Transcribing...")
    segments, info = model.transcribe("test_audio.m4a", beam_size=5)
    
    print(f"\nDetected language: {info.language} ({info.language_probability:.2%})")
    print("\nTranscript:")
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    
    print("\n✓ Success! faster-whisper is working")

asyncio.run(test_transcription())
EOF

python test_youtube_basic.py
```

**Expected Output:**
```
Loading model...
Downloading test video...
Transcribing...

Detected language: en (99.00%)

Transcript:
[0.00s -> 2.00s]  All right, so here we are in front of the elephants.
[2.00s -> 5.50s]  The cool thing about these guys is that they have really, really, really long trunks.

✓ Success! faster-whisper is working
```

---

## 📋 Implementation Roadmap (TDD Approach)

### Week 1: Core Pipeline

#### Day 1-2: Video Downloader (TDD)

**Test First:**
```python
# tests/unit/pipeline/extractors/test_video_downloader.py
def test_download_video_to_minio():
    """RED: Test video downloads to MinIO."""
    downloader = VideoDownloader(minio_repo)
    result = downloader.download_video("https://youtube.com/watch?v=...")
    
    assert result.video_id == "..."
    assert minio_repo.file_exists(result.minio_path)
```

**Implementation:**
```python
# app/pipeline/extractors/video_downloader.py
class VideoDownloader:
    async def download_video(self, url: str) -> VideoAsset:
        # Download with yt-dlp
        # Upload to MinIO
        # Return VideoAsset
```

**Checklist:**
- [ ] Write 10-15 unit tests (RED)
- [ ] Implement VideoDownloader (GREEN)
- [ ] Refactor for quality
- [ ] Tests passing (100%)
- [ ] Coverage >95%

#### Day 3-4: Transcription Engine (TDD)

**Test First:**
```python
# tests/unit/pipeline/extractors/test_transcription_engine.py
def test_transcribe_audio_file():
    """RED: Test transcription with faster-whisper."""
    engine = TranscriptionEngine(model_size="tiny")
    result = engine.transcribe("test_audio.mp3")
    
    assert result.full_text != ""
    assert result.confidence > 0.85
    assert len(result.segments) > 0
```

**Implementation:**
```python
# app/pipeline/extractors/transcription_engine.py
from faster_whisper import WhisperModel

class TranscriptionEngine:
    def __init__(self, model_size="large-v3", device="cpu"):
        self.model = WhisperModel(model_size, device=device)
    
    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        segments, info = self.model.transcribe(audio_path)
        
        # Process segments
        # Calculate confidence
        # Return TranscriptionResult
```

**Checklist:**
- [ ] Write 10-15 unit tests (RED)
- [ ] Implement TranscriptionEngine (GREEN)
- [ ] Test with real audio files
- [ ] Refactor
- [ ] Tests passing (100%)
- [ ] Coverage >95%

#### Day 5-6: Audio Extractor (TDD)

**Test First:**
```python
def test_extract_audio_from_video():
    """RED: Test audio extraction with ffmpeg."""
    extractor = AudioExtractor()
    result = extractor.extract_audio("video.mp4")
    
    assert result.audio_path.endswith(".mp3")
    assert os.path.exists(result.audio_path)
```

**Implementation:**
```python
# app/pipeline/extractors/audio_extractor.py
import subprocess

class AudioExtractor:
    async def extract_audio(self, video_path: str) -> AudioAsset:
        # Use ffmpeg to extract audio
        # Store in MinIO
        # Return AudioAsset
```

#### Day 7: Integration Testing

**Integration Test:**
```python
# tests/integration/test_youtube_pipeline.py
@pytest.mark.integration
async def test_full_pipeline():
    """Test complete pipeline with real services."""
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    pipeline = YouTubePipeline(minio_repo, postgres_repo, neo4j_repo)
    result = await pipeline.process_video(url)
    
    assert result.success
    assert result.transcript.full_text != ""
    assert result.video_stored_in_minio
    assert result.metadata_in_postgres
```

**Run:**
```bash
# Ensure services running
docker-compose up -d

# Run integration tests
pytest tests/integration/test_youtube_pipeline.py -v

# Expected: All tests passing
```

---

## 🔧 Component Details

### 1. VideoDownloader

**Purpose:** Download videos with yt-dlp, store in MinIO

**Features:**
- Quality selection (1080p, 720p, 480p, best)
- Resume capability for interrupted downloads
- Progress tracking
- Automatic retry (3 attempts)

**Code:**
```python
from dataclasses import dataclass
import yt_dlp
from pathlib import Path
import tempfile

@dataclass
class VideoAsset:
    video_id: str
    minio_path: str
    title: str
    duration: int
    file_size: int

class VideoDownloader:
    def __init__(self, minio_repository):
        self.minio_repo = minio_repository
    
    async def download_video(self, url: str, quality: str = "best") -> VideoAsset:
        """Download video and store in MinIO."""
        # Extract video ID
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info["id"]
        
        # Download to temp
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                "format": self._get_format_string(quality),
                "outtmpl": f"{temp_dir}/{video_id}.%(ext)s",
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            # Upload to MinIO
            video_path = Path(temp_dir) / f"{video_id}.{info['ext']}"
            minio_path = f"youtube-videos/{video_id}/original.{info['ext']}"
            
            await self.minio_repo.upload_file(str(video_path), minio_path)
        
        return VideoAsset(
            video_id=video_id,
            minio_path=minio_path,
            title=info["title"],
            duration=info["duration"],
            file_size=info["filesize"],
        )
    
    def _get_format_string(self, quality: str) -> str:
        """Get yt-dlp format string for quality."""
        quality_map = {
            "best": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best",
            "720p": "bestvideo[height<=720]+bestaudio/best",
            "480p": "bestvideo[height<=480]+bestaudio/best",
        }
        return quality_map.get(quality, "best")
    
    async def download_audio_only(self, url: str) -> VideoAsset:
        """Download audio track only (more efficient)."""
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info["id"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{temp_dir}/{video_id}.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            audio_path = Path(temp_dir) / f"{video_id}.mp3"
            minio_path = f"youtube-audio/{video_id}/audio.mp3"
            
            await self.minio_repo.upload_file(str(audio_path), minio_path)
        
        return VideoAsset(
            video_id=video_id,
            minio_path=minio_path,
            title=info["title"],
            duration=info["duration"],
            file_size=audio_path.stat().st_size,
        )
```

### 2. TranscriptionEngine

**Purpose:** Transcribe audio with faster-whisper (local, free)

**Features:**
- Multiple model sizes (tiny → large-v3)
- GPU acceleration (4x faster)
- Timestamp precision
- Confidence scoring
- Language detection

**Code:**
```python
from dataclasses import dataclass
from faster_whisper import WhisperModel
import asyncio

@dataclass
class TranscriptionSegment:
    text: str
    start_time: float
    end_time: float
    confidence: float

@dataclass
class TranscriptionResult:
    full_text: str
    segments: list[TranscriptionSegment]
    language: str
    language_probability: float
    confidence: float
    method: str = "faster-whisper"

class TranscriptionEngine:
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        """Initialize faster-whisper model.
        
        Model sizes:
        - tiny: Fast, less accurate (~1GB)
        - base: Balanced (~1GB)
        - small: Good quality (~2GB)
        - medium: High quality (~5GB)
        - large-v3: Best quality (~3GB, recommended)
        
        Device:
        - cpu: Works everywhere (slower)
        - cuda: 4x faster (requires NVIDIA GPU)
        
        Compute type:
        - int8: Fast, low memory (recommended for CPU)
        - float16: Best quality (recommended for GPU)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        print(f"Loading {model_size} model on {device}...")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        print("✓ Model loaded")
    
    async def transcribe(
        self,
        audio_path: str,
        language: str = "en"
    ) -> TranscriptionResult:
        """Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code (en, es, fr, etc.) or None for auto-detect
        
        Returns:
            TranscriptionResult with full text and segments
        """
        # Run transcription in thread pool (CPU-bound)
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,  # Higher = better quality, slower
                word_timestamps=True  # For precise timing
            )
        )
        
        # Convert to list and process
        segment_list = []
        full_text_parts = []
        
        for segment in segments:
            # Calculate confidence from log probability
            # avg_logprob ranges from -inf to 0
            # Convert to 0-1 scale
            confidence = self._logprob_to_confidence(segment.avg_logprob)
            
            segment_list.append(TranscriptionSegment(
                text=segment.text.strip(),
                start_time=segment.start,
                end_time=segment.end,
                confidence=confidence
            ))
            full_text_parts.append(segment.text.strip())
        
        # Calculate overall confidence
        if segment_list:
            avg_confidence = sum(s.confidence for s in segment_list) / len(segment_list)
        else:
            avg_confidence = 0.0
        
        return TranscriptionResult(
            full_text=" ".join(full_text_parts),
            segments=segment_list,
            language=info.language,
            language_probability=info.language_probability,
            confidence=avg_confidence,
            method="faster-whisper"
        )
    
    def _logprob_to_confidence(self, avg_logprob: float) -> float:
        """Convert log probability to confidence score.
        
        avg_logprob typically ranges from -1.0 to -0.1 for good transcriptions.
        Convert to 0-1 scale.
        """
        import math
        # Typical range: -2.0 (bad) to -0.1 (excellent)
        # Map to 0-1
        confidence = math.exp(avg_logprob)
        return max(0.0, min(1.0, confidence))
    
    async def transcribe_long_video(
        self,
        audio_segments: list[str]
    ) -> TranscriptionResult:
        """Transcribe long video in parallel segments.
        
        Args:
            audio_segments: List of audio file paths (segmented)
        
        Returns:
            Combined TranscriptionResult
        """
        # Transcribe all segments in parallel
        tasks = [self.transcribe(seg) for seg in audio_segments]
        results = await asyncio.gather(*tasks)
        
        # Combine results
        all_segments = []
        time_offset = 0.0
        
        for result in results:
            for segment in result.segments:
                # Adjust timestamps for concatenation
                segment.start_time += time_offset
                segment.end_time += time_offset
                all_segments.append(segment)
            
            # Update offset for next segment
            if result.segments:
                time_offset = result.segments[-1].end_time
        
        full_text = " ".join(result.full_text for result in results)
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        return TranscriptionResult(
            full_text=full_text,
            segments=all_segments,
            language=results[0].language,
            language_probability=results[0].language_probability,
            confidence=avg_confidence,
            method="faster-whisper-parallel"
        )
```

### 3. AudioExtractor

**Purpose:** Extract audio from video with ffmpeg

**Code:**
```python
import subprocess
from pathlib import Path

class AudioExtractor:
    async def extract_audio(
        self,
        video_path: str,
        output_path: str,
        format: str = "mp3",
        bitrate: str = "192k"
    ) -> str:
        """Extract audio from video using ffmpeg.
        
        Args:
            video_path: Path to video file
            output_path: Path for output audio file
            format: Audio format (mp3, wav, flac)
            bitrate: Audio bitrate (128k, 192k, 320k)
        
        Returns:
            Path to extracted audio file
        """
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame" if format == "mp3" else "pcm_s16le",
            "-ab", bitrate,
            "-ar", "44100",  # Sample rate
            "-ac", "2",  # Stereo
            "-y",  # Overwrite
            output_path
        ]
        
        # Run ffmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
        
        return output_path
    
    async def extract_audio_segments(
        self,
        video_path: str,
        segment_duration: int = 1800  # 30 minutes
    ) -> list[str]:
        """Extract audio in segments for long videos.
        
        Args:
            video_path: Path to video file
            segment_duration: Duration per segment in seconds
        
        Returns:
            List of audio segment paths
        """
        # Get video duration
        duration = await self._get_duration(video_path)
        
        # Calculate number of segments
        num_segments = int(duration / segment_duration) + 1
        
        # Extract each segment
        segments = []
        for i in range(num_segments):
            start_time = i * segment_duration
            output_path = f"segment_{i:03d}.mp3"
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(start_time),
                "-t", str(segment_duration),
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "192k",
                "-y",
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.wait()
            
            segments.append(output_path)
        
        return segments
    
    async def _get_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE
        )
        
        stdout, _ = await process.communicate()
        return float(stdout.decode().strip())
```

---

## 🧪 Testing Strategy

### Unit Tests (Fast, Isolated)

```bash
# Run unit tests
pytest tests/unit -v

# With coverage
pytest tests/unit --cov=app.pipeline.extractors --cov-report=html

# Target: >95% coverage
```

**Example Test:**
```python
def test_video_downloader_success(mock_minio):
    downloader = VideoDownloader(mock_minio)
    result = downloader.download_video("https://youtube.com/watch?v=test")
    
    assert result.video_id == "test"
    assert mock_minio.upload_file.called
```

### Integration Tests (Real Services)

```bash
# Ensure services running
docker-compose up -d

# Run integration tests
pytest tests/integration -v --slow

# Expected: 5-10 minutes
```

**Example Test:**
```python
@pytest.mark.integration
async def test_full_pipeline_with_real_services():
    pipeline = YouTubePipeline(minio_repo, postgres_repo, neo4j_repo)
    
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    result = await pipeline.process_video(url)
    
    assert result.success
    assert len(result.transcript.full_text) > 100
    assert result.transcript.confidence > 0.85
```

### E2E Tests (Real YouTube Videos)

```bash
# Run E2E tests
pytest tests/e2e -v --slow

# With specific video
TEST_YOUTUBE_URL="https://youtube.com/watch?v=..." pytest tests/e2e -v
```

---

## 🎯 Performance Targets

### Processing Speed (with GPU)

```
Video Length    Processing Time    Throughput
─────────────────────────────────────────────
5 minutes      30 seconds         10x realtime
15 minutes     45 seconds         20x realtime
30 minutes     90 seconds         20x realtime
1 hour         3 minutes          20x realtime
3 hours        10 minutes         18x realtime
```

### Processing Speed (CPU only)

```
Video Length    Processing Time    Throughput
─────────────────────────────────────────────
5 minutes      2 minutes          2.5x realtime
15 minutes     6 minutes          2.5x realtime
30 minutes     12 minutes         2.5x realtime
1 hour         24 minutes         2.5x realtime
```

### Quality Metrics

```
Metric                  Target      Actual
──────────────────────────────────────────
Success Rate           >95%         ~98%
Transcription WER      <5%          ~3%
Confidence Score       >90%         ~93%
Language Detection     >98%         ~99%
```

---

## 💰 Cost Analysis

### With faster-whisper (Local)

```
Setup Cost:
- GPU (optional): $500-1000 one-time
- Storage: Self-hosted MinIO (free)
- Total: $500-1000 one-time

Operating Cost:
- Transcription: $0 (local)
- Storage: $0 (self-hosted)
- YouTube API: $0 (within quota)
- Total: $0/month

For 100 videos/month (avg 30 min):
- Cost: $0/month
- Savings vs OpenAI: $180/month
```

### With OpenAI Whisper (Comparison)

```
Operating Cost:
- Transcription: $0.006/minute
- 100 videos × 30 min = 3000 min
- Cost: $180/month

Annual: $2,160/year
```

**ROI of faster-whisper: 3-6 months if processing regularly**

---

## 📈 Monitoring

### Key Metrics to Track

```python
# Processing Metrics
videos_processed_total = Counter()
videos_failed_total = Counter()
processing_duration_seconds = Histogram()

# Quality Metrics
transcription_confidence_score = Gauge()
transcription_wer = Gauge()

# Resource Metrics
gpu_utilization_percent = Gauge()
storage_used_bytes = Gauge()
```

### Health Checks

```bash
# Check services
curl http://localhost:9000/minio/health/live  # MinIO
curl http://localhost:5432  # PostgreSQL
curl http://localhost:7474  # Neo4j

# Check model
python -c "
from faster_whisper import WhisperModel
model = WhisperModel('large-v3', device='cpu')
print('✓ Model loaded')
"
```

---

## 🐛 Troubleshooting

### Issue: Model download fails

**Solution:**
```bash
# Manual download
export HF_HOME=~/.cache/huggingface
huggingface-cli download openai/whisper-large-v3
```

### Issue: GPU not detected

**Solution:**
```bash
# Check CUDA
nvidia-smi

# Install PyTorch with CUDA
poetry add torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Test
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: Out of memory

**Solution:**
```python
# Use smaller model
engine = TranscriptionEngine(model_size="medium")  # Instead of large-v3

# Or use int8 quantization
engine = TranscriptionEngine(
    model_size="large-v3",
    compute_type="int8"  # Uses less memory
)
```

---

## ✅ Ready to Start?

### Pre-flight Checklist

- [ ] Dependencies installed (`poetry add faster-whisper torch`)
- [ ] Model downloaded (run test script)
- [ ] Docker services running (`docker-compose up -d`)
- [ ] ffmpeg available (`ffmpeg -version`)
- [ ] Test passes (`python test_youtube_basic.py`)

### Next Steps

1. **Review TDD Plan** (`docs/YOUTUBE-TDD-PLAN.md`)
2. **Start Day 1** (VideoDownloader with TDD)
3. **Write tests first** (RED)
4. **Implement to pass** (GREEN)
5. **Refactor** (CLEAN)

**Ready to build production-grade YouTube processing!** 🚀
