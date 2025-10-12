import io
import json

import pytest

from app.pipeline.cli import main


@pytest.mark.integration
def test_cli_ingests_youtube_and_outputs_json(monkeypatch):
    url = "https://www.youtube.com/watch?v=cliTest"
    transcript_text = "CLI integration test transcript."
    video_details = {
        "title": "CLI Test Video",
        "author": "CLI Author",
        "length": 123,
        "publish_date": "2025-10-12",
    }

    class MockYouTubeTranscriptApi:
        @staticmethod
        def get_transcript(vid_id):
            return [{"text": transcript_text}]

    class MockYouTube:
        def __init__(self, url):
            pass
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
            return "CLI fallback description."

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTube", MockYouTube)

    buffer = io.StringIO()
    exit_code = main([url, "--json"], stream=buffer)
    assert exit_code == 0
    data = json.loads(buffer.getvalue())
    assert data["raw"]["raw_text"] == transcript_text
    assert data["raw"]["metadata"]["title"] == video_details["title"]
