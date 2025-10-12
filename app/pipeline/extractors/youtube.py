"""Extracts transcripts and metadata from YouTube videos."""

from __future__ import annotations

import re
from typing import Any, cast

from app.core.exceptions import ExtractionError
from app.core.models import RawContent
from app.core.types import ContentSource
from app.pipeline.extractors.base import ContentExtractor

# Third-party libraries for YouTube extraction. These are optional at import
# time so that tests can monkeypatch the module-level symbols without requiring
# the real dependencies to be installed in the environment running the tests.
try:  # pragma: no cover - exercised via monkeypatch in tests
    from youtube_transcript_api import YouTubeTranscriptApi as _YouTubeTranscriptApi  # type: ignore
except ImportError:  # pragma: no cover - handled in extractor logic
    _YouTubeTranscriptApi = None

try:  # pragma: no cover - exercised via monkeypatch in tests
    from pytube import YouTube as _YouTube  # type: ignore
except ImportError:  # pragma: no cover - handled in extractor logic
    _YouTube = None

# Expose the imported symbols (or sentinel None) for monkeypatching in tests.
YouTubeTranscriptApi: Any | None = _YouTubeTranscriptApi
YouTube: Any | None = _YouTube


class YouTubeExtractor(ContentExtractor):
    """
    Extracts the transcript from a YouTube video, falling back to the
    description if the transcript is not available.
    """

    def __init__(self) -> None:
        pass

    async def extract(self, url: str) -> RawContent:
        missing_dependencies = [
            name
            for name, dependency in (
                ("youtube-transcript-api", YouTubeTranscriptApi),
                ("pytube", YouTube),
            )
            if dependency is None
        ]
        if missing_dependencies:
            missing = ", ".join(missing_dependencies)
            raise ExtractionError(f"Required library missing: {missing}")

        # Validate URL
        if not ("youtube.com" in url or "youtu.be" in url):
            raise ExtractionError(f"Invalid YouTube URL: {url}")

        # Extract video ID
        video_id_match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
        if not video_id_match:
            raise ExtractionError(f"Could not extract video ID from URL: {url}")
        video_id = video_id_match.group(1)

        # Fetch video metadata
        try:
            yt = cast(Any, YouTube)(url)
        except Exception as e:
            raise ExtractionError(f"Failed to fetch video data: {e}") from e

        # Try to fetch transcript
        transcript_text = None
        try:
            transcript = cast(Any, YouTubeTranscriptApi).get_transcript(video_id)
            transcript_text = " ".join([chunk["text"] for chunk in transcript if "text" in chunk])
        except Exception:
            transcript_text = None

        # Fallback to description if transcript is missing
        raw_text = transcript_text or yt.description or ""
        if not raw_text.strip():
            raise ExtractionError("No transcript or description available for this video.")

        # Build metadata
        metadata = {
            "title": getattr(yt, "title", "unknown"),
            "author": getattr(yt, "author", "unknown"),
            "duration": getattr(yt, "length", None),
            "published_at": str(getattr(yt, "publish_date", "")),
            "content_type": "video/youtube",
        }

        return RawContent(
            url=url,
            source_type=ContentSource.YOUTUBE,
            raw_text=raw_text,
            metadata=metadata,
        )
