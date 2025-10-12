import math
from datetime import datetime

import httpx
import pytest

from app.core.models import RawContent
from app.core.types import ContentSource
from app.services import content_service


class DummyAsyncClient:
    """Simple stand-in for httpx.AsyncClient used in tests."""

    def __init__(self, response: httpx.Response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *_args, **_kwargs) -> httpx.Response:
        return self._response


@pytest.mark.asyncio
async def test_extract_web_content_parses_html(monkeypatch):
    html = """
    <html>
      <head><title>Testing Embeddings</title></head>
      <body><p>Williams Librarian builds high-quality research digests.</p></body>
    </html>
    """
    response = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html"},
        content=html.encode("utf-8"),
        request=httpx.Request("GET", "https://example.com/article"),
    )

    dummy_client = DummyAsyncClient(response)
    monkeypatch.setattr(content_service.httpx, "AsyncClient", lambda **_: dummy_client)

    result = await content_service.extract_web_content("https://example.com/article")

    assert result.metadata["title"] == "Testing Embeddings"
    assert "research digests" in result.raw_text
    assert result.source_type == ContentSource.WEB


@pytest.mark.asyncio
async def test_extract_web_content_handles_text_response(monkeypatch):
    response = httpx.Response(
        status_code=200,
        headers={"content-type": "text/plain"},
        content=b"Simple plain text content for testing.",
        request=httpx.Request("GET", "https://example.com/plain"),
    )

    monkeypatch.setattr(content_service.httpx, "AsyncClient", lambda **_: DummyAsyncClient(response))

    result = await content_service.extract_web_content("https://example.com/plain")

    assert "plain text" in result.raw_text
    assert result.metadata["title"] == "plain"


@pytest.mark.asyncio
async def test_screen_with_ai_scoring():
    sample_text = (
        "Artificial intelligence systems analyse complex datasets, derive nuanced insights, "
        "and assist researchers across medicine, climate science, and economic policy. "
        "Williams Librarian evaluates source credibility, summarises findings, and explains key shifts. "
        "By highlighting diverse perspectives the platform encourages deeper human review."
    )

    raw = RawContent(
        url="https://example.com/ai",
        source_type=ContentSource.WEB,
        raw_text=sample_text,
        metadata={"title": "AI"},
        extracted_at=datetime.now(),
    )

    result = await content_service.screen_with_ai(raw)

    assert result.decision in {"ACCEPT", "MAYBE"}
    assert 0.0 <= result.screening_score <= 10.0
    assert result.estimated_quality >= result.screening_score


@pytest.mark.asyncio
async def test_process_with_ai_generates_summary():
    text = (
        "Williams Librarian is an AI assistant designed to build high-quality research libraries. "
        "It evaluates content, summarises findings, and organises knowledge into tiers.\n\n"
        "The system also creates daily digests with actionable insights for multidisciplinary teams."
    )

    raw = RawContent(
        url="https://example.com/library",
        source_type=ContentSource.WEB,
        raw_text=text,
        metadata={"title": "Williams Librarian"},
        extracted_at=datetime.now(),
    )

    processed = await content_service.process_with_ai(raw)

    assert len(processed["summary"]) > 50
    assert len(processed["key_points"]) >= 1
    assert processed["tags"]


@pytest.mark.asyncio
async def test_generate_embedding_deterministic():
    vector_one = await content_service.generate_embedding("Williams Librarian is excellent for testing.")
    vector_two = await content_service.generate_embedding("Williams Librarian is excellent for testing.")

    assert len(vector_one) == 384
    assert vector_one == vector_two
    norm = math.sqrt(sum(component ** 2 for component in vector_one))
    assert pytest.approx(norm, rel=1e-6) == 1.0
