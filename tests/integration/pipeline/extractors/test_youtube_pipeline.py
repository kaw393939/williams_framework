"""Integration test for YouTubeExtractor in the ContentPipeline."""
from pathlib import Path

import pytest

from app.core.models import LibraryFile, ProcessedContent
from app.pipeline.etl import ContentPipeline
from app.pipeline.extractors.youtube import YouTubeExtractor
from app.pipeline.loaders.base import ContentLoader
from app.pipeline.transformers.basic import BasicContentTransformer


class DummyLoader(ContentLoader):
    def __init__(self):
        self.calls = []
    async def load(self, processed: ProcessedContent) -> LibraryFile:
        self.calls.append(processed)
        return LibraryFile(
            file_path=Path("library/tier-b/youtube-test.md"),
            url=processed.url,
            source_type=processed.source_type,
            tier="tier-b",
            quality_score=processed.screening_result.estimated_quality,
            title=processed.title,
            tags=processed.tags,
        )

@pytest.mark.asyncio
async def test_pipeline_runs_with_youtube_extractor(monkeypatch):
    url = "https://www.youtube.com/watch?v=integrationTest"
    transcript_text = "Integration test transcript."
    video_details = {
        "title": "Integration Test Video",
        "author": "Test Author",
        "length": 100,
        "publish_date": "2025-10-12",
    }

    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            return [{"text": transcript_text}]

    class MockYtDlp:
        class YoutubeDL:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def extract_info(self, url, download=False):
                return {
                    "title": video_details["title"],
                    "uploader": video_details["author"],
                    "channel": video_details["author"],
                    "duration": video_details["length"],
                    "upload_date": video_details["publish_date"],
                    "view_count": 1000,
                    "like_count": 100,
                    "description": "Integration fallback description."
                }

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.yt_dlp", MockYtDlp)

    extractor = YouTubeExtractor()
    transformer = BasicContentTransformer()
    loader = DummyLoader()
    pipeline = ContentPipeline(extractor=extractor, transformer=transformer, loader=loader)

    result = await pipeline.run(url)
    assert str(result.raw_content.url) == url
    assert result.raw_content.raw_text == transcript_text
    assert result.raw_content.metadata["title"] == video_details["title"]
    assert loader.calls and loader.calls[0].title == video_details["title"]
