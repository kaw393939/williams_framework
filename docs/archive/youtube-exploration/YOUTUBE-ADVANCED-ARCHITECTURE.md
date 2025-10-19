# Advanced YouTube Processing Architecture

## Executive Summary

This document outlines a comprehensive architecture for extracting maximum value from YouTube videos, including transcripts, metadata, comments, and handling long-form content (3+ hours) through intelligent segmentation and parallel processing.

## Current State Analysis

### Existing Implementation
The current `YouTubeExtractor` provides basic functionality:
- ✅ Video ID extraction
- ✅ Transcript fetching via `youtube-transcript-api`
- ✅ Basic metadata (title, author, duration, publish date)
- ✅ Fallback to description if transcript unavailable

### Limitations
- ❌ No comment extraction
- ❌ No handling of long videos (3+ hours)
- ❌ No chapter/timestamp extraction
- ❌ Limited metadata (missing views, likes, tags, category)
- ❌ No speaker diarization
- ❌ No audio extraction for custom transcription
- ❌ No parallel processing for long videos

---

## Enhanced Architecture

### 1. Multi-Layer Data Extraction

#### Layer 1: Video Metadata (Rich Context)
```python
class EnhancedVideoMetadata:
    # Basic Info
    video_id: str
    title: str
    description: str
    duration_seconds: int
    
    # Engagement Metrics
    view_count: int
    like_count: int
    comment_count: int
    
    # Classification
    category: str
    tags: list[str]
    language: str
    
    # Temporal
    published_at: datetime
    uploaded_at: datetime
    
    # Channel Info
    channel_id: str
    channel_name: str
    channel_subscriber_count: int
    
    # Content Structure
    chapters: list[Chapter]  # Timestamps and titles
    playlist_info: Optional[PlaylistInfo]
    
    # Technical
    resolution: str
    format: str
    has_captions: bool
    caption_languages: list[str]
```

#### Layer 2: Transcript with Timestamps
```python
class TimestampedTranscript:
    segments: list[TranscriptSegment]
    
class TranscriptSegment:
    start_time: float
    end_time: float
    text: str
    confidence: float
    speaker_id: Optional[int]  # For diarization
    chapter_id: Optional[str]
```

#### Layer 3: Comments (Community Insights)
```python
class CommentData:
    comments: list[Comment]
    total_count: int
    engagement_score: float
    
class Comment:
    comment_id: str
    text: str
    author: str
    like_count: int
    published_at: datetime
    is_reply: bool
    parent_comment_id: Optional[str]
    sentiment_score: Optional[float]
```

### 2. Long Video Processing Strategy

#### Problem
- YouTube transcript API may timeout on 3+ hour videos
- Memory constraints with full video processing
- Need for parallel processing

#### Solution: Intelligent Segmentation

```
┌─────────────────────────────────────────────────────────┐
│         Long Video (3+ hours)                           │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  Chapter Detection            │
         │  - Use YouTube chapters       │
         │  - Detect scene changes       │
         │  - Split by silence           │
         └──────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
   ┌──────────────┐          ┌──────────────┐
   │  Segment 1   │   ...    │  Segment N   │
   │  (15-30 min) │          │  (15-30 min) │
   └──────────────┘          └──────────────┘
          │                           │
          └─────────────┬─────────────┘
                        ▼
              ┌──────────────────┐
              │ Parallel Processing│
              │  - Transcription  │
              │  - Embedding      │
              │  - Entity Extract │
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Merge & Index   │
              │  - Maintain       │
              │    continuity     │
              │  - Cross-ref      │
              └──────────────────┘
```

### 3. Audio Extraction & Custom Transcription

#### When to Use Custom Transcription
1. No YouTube transcript available
2. Better quality needed (Whisper > YouTube auto-captions)
3. Speaker diarization required
4. Multiple languages in video

#### FFMPEG Audio Processing Pipeline

```python
class AudioProcessor:
    def extract_audio(self, video_url: str, output_path: str) -> str:
        """Extract audio from YouTube video using yt-dlp + ffmpeg."""
        # Use yt-dlp to download audio-only stream
        cmd = [
            'yt-dlp',
            '-f', 'bestaudio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '0',  # Best quality
            '-o', output_path,
            video_url
        ]
        
    def split_audio(
        self, 
        audio_path: str, 
        segment_duration: int = 1800  # 30 minutes
    ) -> list[str]:
        """Split long audio into segments using FFMPEG."""
        # Get audio duration
        duration = self._get_audio_duration(audio_path)
        
        # Calculate segments
        segments = []
        for i in range(0, int(duration), segment_duration):
            output = f"{audio_path}_segment_{i}.mp3"
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-ss', str(i),  # Start time
                '-t', str(segment_duration),  # Duration
                '-acodec', 'copy',  # Fast, no re-encoding
                output
            ]
            segments.append(output)
        
        return segments
    
    def smart_split_by_silence(
        self,
        audio_path: str,
        min_silence_duration: float = 2.0,
        silence_threshold: int = -40  # dB
    ) -> list[tuple[float, float]]:
        """Split audio at natural silence points using FFMPEG."""
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-af', f'silencedetect=n={silence_threshold}dB:d={min_silence_duration}',
            '-f', 'null',
            '-'
        ]
        # Parse output for silence timestamps
        # Return list of (start, end) tuples for segments
```

### 4. Enhanced Transcription with Whisper

```python
class WhisperTranscriber:
    def __init__(self, model_size: str = "large-v3"):
        """Initialize Whisper model.
        
        Models: tiny, base, small, medium, large-v3
        Accuracy: tiny < base < small < medium < large-v3
        Speed: tiny > base > small > medium > large-v3
        """
        import whisper
        self.model = whisper.load_model(model_size)
    
    def transcribe_with_diarization(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> TranscriptResult:
        """Transcribe with speaker detection."""
        result = self.model.transcribe(
            audio_path,
            language=language,
            task='transcribe',
            word_timestamps=True,
            # Enable speaker diarization
            initial_prompt="Identify different speakers."
        )
        
        # Post-process with pyannote.audio for better diarization
        from pyannote.audio import Pipeline
        diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization"
        )
        diarization = diarization_pipeline(audio_path)
        
        # Merge transcription with speaker labels
        return self._merge_transcript_with_speakers(
            result, diarization
        )
```

### 5. Comment Processing Architecture

```python
class CommentProcessor:
    def extract_comments(
        self,
        video_id: str,
        max_comments: int = 1000,
        include_replies: bool = True
    ) -> CommentData:
        """Extract comments using YouTube Data API v3."""
        from googleapiclient.discovery import build
        
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        comments = []
        next_page_token = None
        
        while len(comments) < max_comments:
            response = youtube.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token,
                order='relevance'  # Get most relevant first
            ).execute()
            
            # Process comments
            for item in response['items']:
                comment = self._parse_comment(item)
                comments.append(comment)
                
                if include_replies and 'replies' in item:
                    replies = self._parse_replies(item['replies'])
                    comments.extend(replies)
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        return CommentData(
            comments=comments,
            total_count=len(comments),
            engagement_score=self._calculate_engagement(comments)
        )
    
    def analyze_sentiment(self, comments: list[Comment]) -> dict:
        """Analyze comment sentiment distribution."""
        from transformers import pipeline
        
        sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
        
        results = sentiment_analyzer([c.text for c in comments])
        
        return {
            'positive': sum(1 for r in results if r['label'] == 'POSITIVE'),
            'negative': sum(1 for r in results if r['label'] == 'NEGATIVE'),
            'average_score': sum(r['score'] for r in results) / len(results)
        }
    
    def extract_key_topics(self, comments: list[Comment]) -> list[str]:
        """Extract key discussion topics from comments."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import LatentDirichletAllocation
        
        # Combine comment texts
        texts = [c.text for c in comments]
        
        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english'
        )
        tfidf = vectorizer.fit_transform(texts)
        
        # Topic modeling
        lda = LatentDirichletAllocation(n_components=5)
        lda.fit(tfidf)
        
        # Extract top words per topic
        feature_names = vectorizer.get_feature_names_out()
        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_words = [feature_names[i] for i in topic.argsort()[-5:]]
            topics.append(", ".join(top_words))
        
        return topics
```

### 6. Integration Pipeline

```python
class AdvancedYouTubeProcessor:
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.transcriber = WhisperTranscriber()
        self.comment_processor = CommentProcessor()
    
    async def process_video(
        self,
        video_url: str,
        extract_audio: bool = False,
        extract_comments: bool = True,
        max_segment_duration: int = 1800  # 30 minutes
    ) -> ProcessedVideo:
        """Comprehensive video processing pipeline."""
        
        # 1. Extract basic metadata
        metadata = await self._extract_metadata(video_url)
        
        # 2. Determine processing strategy
        is_long_video = metadata.duration_seconds > 3600  # 1 hour
        
        # 3. Get transcript
        if metadata.has_captions:
            # Use YouTube transcript (faster)
            transcript = await self._get_youtube_transcript(metadata.video_id)
        else:
            # Extract audio and transcribe with Whisper
            audio_path = await self.audio_processor.extract_audio(video_url)
            
            if is_long_video:
                # Split audio into segments
                segments = self.audio_processor.split_audio(
                    audio_path,
                    segment_duration=max_segment_duration
                )
                
                # Parallel transcription
                transcript_segments = await asyncio.gather(*[
                    self._transcribe_segment(seg) for seg in segments
                ])
                
                transcript = self._merge_transcripts(transcript_segments)
            else:
                transcript = await self.transcriber.transcribe(audio_path)
        
        # 4. Extract comments
        comments = None
        if extract_comments:
            comments = await self.comment_processor.extract_comments(
                metadata.video_id
            )
            
            # Analyze sentiment
            sentiment = self.comment_processor.analyze_sentiment(comments.comments)
            
            # Extract topics
            topics = self.comment_processor.extract_key_topics(comments.comments)
        
        # 5. Build comprehensive result
        return ProcessedVideo(
            metadata=metadata,
            transcript=transcript,
            comments=comments,
            sentiment_analysis=sentiment if comments else None,
            discussion_topics=topics if comments else None
        )
```

---

## Implementation Roadmap

### Phase 1: Enhanced Metadata Extraction (Week 1)
- [ ] Implement rich metadata extraction
- [ ] Add chapter detection
- [ ] Extract playlist information
- [ ] Add engagement metrics (views, likes)

### Phase 2: Audio Processing (Week 2)
- [ ] Integrate yt-dlp for audio download
- [ ] Implement FFMPEG audio splitting
- [ ] Add silence-based segmentation
- [ ] Create audio quality assessment

### Phase 3: Advanced Transcription (Week 3)
- [ ] Integrate Whisper model
- [ ] Implement speaker diarization
- [ ] Add confidence scoring
- [ ] Handle multiple languages

### Phase 4: Comment Processing (Week 4)
- [ ] Integrate YouTube Data API v3
- [ ] Implement comment extraction
- [ ] Add sentiment analysis
- [ ] Extract discussion topics
- [ ] Build comment-to-transcript linking

### Phase 5: Long Video Handling (Week 5)
- [ ] Implement segment coordinator
- [ ] Add parallel processing
- [ ] Create segment merging logic
- [ ] Add cross-segment entity resolution

### Phase 6: Integration & Testing (Week 6)
- [ ] End-to-end integration tests
- [ ] Performance optimization
- [ ] Error handling & retries
- [ ] Documentation

---

## Technical Requirements

### Dependencies
```toml
[tool.poetry.dependencies]
# Existing
youtube-transcript-api = "^0.6.0"
pytube = "^15.0.0"

# New
yt-dlp = "^2024.0.0"  # Better YouTube downloader
openai-whisper = "^20231117"  # Transcription
pyannote-audio = "^2.1.1"  # Speaker diarization
google-api-python-client = "^2.100.0"  # YouTube Data API
transformers = "^4.35.0"  # Sentiment analysis
scikit-learn = "^1.3.0"  # Topic modeling
ffmpeg-python = "^0.2.0"  # FFMPEG wrapper
```

### System Requirements
- FFMPEG installed (`apt-get install ffmpeg`)
- GPU recommended for Whisper (large models)
- Minimum 16GB RAM for long video processing
- YouTube Data API v3 key

### Environment Variables
```bash
YOUTUBE_API_KEY=your_api_key_here
WHISPER_MODEL_SIZE=large-v3  # or small/medium for faster
MAX_SEGMENT_DURATION=1800  # 30 minutes
ENABLE_SPEAKER_DIARIZATION=true
EXTRACT_COMMENTS=true
MAX_COMMENTS_PER_VIDEO=1000
```

---

## Quality Metrics

### Transcription Quality Targets
- **Word Error Rate (WER)**: < 5% for clear audio
- **Speaker Diarization Accuracy**: > 90%
- **Timestamp Accuracy**: ±0.5 seconds

### Performance Targets
- **15-minute video**: < 2 minutes processing time
- **3-hour video**: < 20 minutes processing time (with parallelization)
- **Comment extraction**: < 30 seconds for 1000 comments

### Data Quality Targets
- **Metadata completeness**: > 95%
- **Comment sentiment accuracy**: > 85%
- **Topic relevance**: Manual validation required

---

## Cost Considerations

### YouTube Data API Costs
- Free tier: 10,000 units/day
- CommentThreads.list: 1 unit per request (100 comments)
- ~100 requests for 10,000 comments = 100 units
- Can process ~100 videos/day with comments in free tier

### Compute Costs
- **CPU transcription**: $0.01-0.05 per hour of video
- **GPU transcription**: $0.10-0.50 per hour (faster, better quality)
- **Storage**: ~100MB per hour of audio at high quality

### Optimization Strategies
1. Cache transcripts to avoid re-processing
2. Use smaller Whisper models for drafts
3. Batch process during off-peak hours
4. Use YouTube transcripts when available (free)

---

## Future Enhancements

1. **Visual Analysis**
   - Extract keyframes
   - OCR on screen text
   - Detect presentation slides

2. **Multi-Modal Understanding**
   - Align transcript with visual content
   - Detect code examples in programming videos
   - Extract diagrams and charts

3. **Interactive Features**
   - Time-coded citations
   - Jump-to-topic navigation
   - Question answering with video timestamps

4. **Quality Improvements**
   - Punctuation restoration
   - Capitalization normalization
   - Technical term correction

---

## Conclusion

This architecture provides a comprehensive approach to extracting maximum value from YouTube videos, handling long-form content efficiently, and building a rich knowledge graph from video metadata, transcripts, and community discussions.

The modular design allows incremental implementation while maintaining compatibility with the existing system.
