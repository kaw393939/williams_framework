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
                    "description": "CLI fallback description."
                }

    monkeypatch.setattr("app.pipeline.extractors.youtube.YouTubeTranscriptApi", MockYouTubeTranscriptApi)
    monkeypatch.setattr("app.pipeline.extractors.youtube.yt_dlp", MockYtDlp)

    buffer = io.StringIO()
    exit_code = main([url, "--json"], stream=buffer)
    assert exit_code == 0
    data = json.loads(buffer.getvalue())
    assert data["raw"]["raw_text"] == transcript_text
    assert data["raw"]["metadata"]["title"] == video_details["title"]
