"""Unit tests for the YouTube transcript extractor."""
from __future__ import annotations

import pytest

from app.core.exceptions import ExtractionError
from app.pipeline.extractors.youtube import YouTubeExtractor


@pytest.mark.asyncio
async def test_youtube_extractor_fetches_transcript_and_metadata(monkeypatch):
    """Verify transcript and metadata are extracted from a valid YouTube URL."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = "dQw4w9WgXcQ"
    transcript_text = "Never gonna give you up, never gonna let you down."
    
    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            assert vid_id == video_id
            return [{"text": transcript_text}]

    class MockYoutubeDL:
        def __init__(self, opts):
            pass
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def extract_info(self, url, download=False):
            return {
                "title": "Official Music Video",
                "uploader": "Rick Astley",
                "channel": "RickAstleyVEVO",
                "duration": 212,
                "upload_date": "20091025",
                "view_count": 1000000,
                "like_count": 50000,
                "description": "Video description"
            }
    
    class MockYtDlp:
        YoutubeDL = MockYoutubeDL

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.yt_dlp", MockYtDlp)

    extractor = YouTubeExtractor()
    raw_content = await extractor.extract(url)

    assert str(raw_content.url) == url
    assert raw_content.raw_text == transcript_text
    assert raw_content.metadata["title"] == "Official Music Video"
    assert raw_content.metadata["author"] == "Rick Astley"
    assert raw_content.metadata["duration"] == 212
    assert raw_content.metadata["published_at"] == "2009-10-25T00:00:00"


@pytest.mark.asyncio
async def test_youtube_extractor_falls_back_to_description(monkeypatch):
    """If transcript is unavailable, the description should be used as raw_text."""
    url = "https://www.youtube.com/watch?v=no-transcript"
    video_description = "This is the video description, used as fallback text."

    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            raise Exception("Transcript not available")

    class MockYoutubeDL:
        def __init__(self, opts):
            pass
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def extract_info(self, url, download=False):
            return {
                "title": "A Video",
                "uploader": "An Author",
                "channel": "AuthorChannel",
                "duration": 120,
                "upload_date": "20250101",
                "view_count": 1000,
                "like_count": 100,
                "description": video_description
            }
    
    class MockYtDlp:
        YoutubeDL = MockYoutubeDL

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.yt_dlp", MockYtDlp)

    extractor = YouTubeExtractor()
    raw_content = await extractor.extract(url)

    assert raw_content.raw_text == video_description


@pytest.mark.asyncio
async def test_youtube_extractor_raises_on_invalid_url():
    """Extractor should raise ExtractionError for non-YouTube URLs."""
    url = "https://example.com/not-youtube"
    extractor = YouTubeExtractor()
    with pytest.raises(ExtractionError):
        await extractor.extract(url)


@pytest.mark.asyncio
async def test_youtube_extractor_raises_on_extraction_failure(monkeypatch):
    """A generic error from the YouTube library should be wrapped in ExtractionError."""
    url = "https://www.youtube.com/watch?v=broken"

    class MockYoutubeDL:
        def __init__(self, opts):
            pass
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def extract_info(self, url, download=False):
            raise Exception("Failed to fetch video data")
    
    class MockYtDlp:
        YoutubeDL = MockYoutubeDL
    
    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            return []

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.yt_dlp", MockYtDlp)

    extractor = YouTubeExtractor()
    with pytest.raises(ExtractionError):
        await extractor.extract(url)
