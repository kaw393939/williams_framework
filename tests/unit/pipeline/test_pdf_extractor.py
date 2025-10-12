from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from app.core.exceptions import ExtractionError
from app.core.models import RawContent
from app.core.types import ContentSource
from app.pipeline.extractors import pdf as pdf_module
from app.pipeline.extractors.pdf import PDFDocumentExtractor


class DummyAsyncClient:
    def __init__(self, response: httpx.Response | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.requested_urls: list[str] = []

    async def get(self, url: str) -> httpx.Response:
        self.requested_urls.append(url)
        if self._error:
            raise self._error
        if self._response is None:
            raise RuntimeError("No response configured")
        return self._response


@dataclass
class _FakePage:
    text: str

    def extract_text(self) -> str:
        return self.text


class _FakePdfReader:
    def __init__(self, pages: list[str], metadata: dict[str, str] | None = None):
        self.pages = [_FakePage(text) for text in pages]
        self.metadata = metadata or {}


def _make_pdf_response(url: str, content: bytes | None = None) -> httpx.Response:
    data = content or b"%PDF-1.4\n%fake test pdf\n"
    return httpx.Response(
        status_code=200,
        content=data,
        headers={"content-type": "application/pdf"},
        request=httpx.Request("GET", url),
    )


@pytest.mark.asyncio
async def test_pdf_extractor_normalizes_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://example.com/reports/ai-safety.pdf"
    fake_reader = _FakePdfReader(
        pages=[
            "Artificial Intelligence Safety\nAlignment requires rigorous evaluation.",
            "Second page reinforces rigorous testing principles.",
        ],
        metadata={
            "/Title": "  AI Safety Fundamentals  ",
            "/Author": "Ada Lovelace",
            "/Subject": "Safety",
        },
    )
    monkeypatch.setattr(pdf_module, "PdfReader", lambda stream: fake_reader)

    response = _make_pdf_response(url)
    client = DummyAsyncClient(response=response)
    extractor = PDFDocumentExtractor(client=client)

    result = await extractor.extract(url)

    assert isinstance(result, RawContent)
    assert result.source_type is ContentSource.PDF
    assert "Artificial Intelligence Safety" in result.raw_text
    assert result.metadata["title"] == "AI Safety Fundamentals"
    assert result.metadata["author"] == "Ada Lovelace"
    assert result.metadata["page_count"] == 2
    assert result.metadata["summary"].startswith("Artificial Intelligence Safety")
    assert result.metadata["content_type"] == "application/pdf"
    assert client.requested_urls == [url]


@pytest.mark.asyncio
async def test_pdf_extractor_uses_filename_when_title_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://example.com/papers/future-of-work.pdf"
    fake_reader = _FakePdfReader(pages=["Future of work analysis."], metadata={})
    monkeypatch.setattr(pdf_module, "PdfReader", lambda stream: fake_reader)

    response = _make_pdf_response(url)
    client = DummyAsyncClient(response=response)
    extractor = PDFDocumentExtractor(client=client)

    result = await extractor.extract(url)

    assert result.metadata["title"] == "future-of-work"
    assert result.metadata["author"] == "unknown"
    assert result.metadata["page_count"] == 1


@pytest.mark.asyncio
async def test_pdf_extractor_raises_when_no_text(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://example.com/empty.pdf"
    fake_reader = _FakePdfReader(pages=["   \n   "], metadata={})
    monkeypatch.setattr(pdf_module, "PdfReader", lambda stream: fake_reader)

    response = _make_pdf_response(url)
    client = DummyAsyncClient(response=response)
    extractor = PDFDocumentExtractor(client=client)

    with pytest.raises(ExtractionError):
        await extractor.extract(url)
