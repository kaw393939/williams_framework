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
    video_details = {
        "title": "Official Music Video",
        "author": "Rick Astley",
        "length": 212,
        "publish_date": "2009-10-25",
    }

    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            assert vid_id == video_id
            return [{"text": transcript_text}]

    class MockYouTube:
        def __init__(self, url):
            assert url == url

        @property
        def title(self):
            return video_details["title"]

        @property
        def author(self):
            return video_details["author"]

        @property
        def length(self):
            return video_details["length"]

        @property
        def publish_date(self):
            return video_details["publish_date"]

        @property
        def description(self):
            return "Video description."

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTube", MockYouTube)

    extractor = YouTubeExtractor()
    raw_content = await extractor.extract(url)

    assert str(raw_content.url) == url
    assert raw_content.raw_text == transcript_text
    assert raw_content.metadata["title"] == video_details["title"]
    assert raw_content.metadata["author"] == video_details["author"]
    assert raw_content.metadata["duration"] == video_details["length"]
    assert raw_content.metadata["published_at"] == video_details["publish_date"]


@pytest.mark.asyncio
async def test_youtube_extractor_falls_back_to_description(monkeypatch):
    """If transcript is unavailable, the description should be used as raw_text."""
    url = "https://www.youtube.com/watch?v=no-transcript"
    video_id = "no-transcript"
    video_description = "This is the video description."

    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            raise Exception("Transcript not available")

    class MockYouTube:
        def __init__(self, url):
            assert url == url

        @property
        def description(self):
            return video_description

        # Add other properties to satisfy the extractor
        title = "A Video"
        author = "An Author"
        length = 120
        publish_date = "2025-01-01"

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTube", MockYouTube)

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

    class MockYouTube:
        def __init__(self, url):
            raise Exception("Failed to fetch video data")

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTube", MockYouTube)

    extractor = YouTubeExtractor()
    with pytest.raises(ExtractionError):
        await extractor.extract(url)
