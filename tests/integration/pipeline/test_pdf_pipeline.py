from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from app.core.models import LibraryFile, ProcessedContent, RawContent
from app.core.types import ContentSource
from app.pipeline.etl import ContentPipeline, PipelineResult
from app.pipeline.extractors import pdf as pdf_module
from app.pipeline.extractors.pdf import PDFDocumentExtractor
from app.pipeline.loaders.base import ContentLoader
from app.pipeline.transformers.basic import BasicContentTransformer


class DummyAsyncClient:
    def __init__(self, response: httpx.Response):
        self._response = response
        self.requested_urls: list[str] = []

    async def get(self, url: str) -> httpx.Response:
        self.requested_urls.append(url)
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
    data = content or b"%PDF-1.4\n%integration test pdf\n"
    return httpx.Response(
        status_code=200,
        content=data,
        headers={"content-type": "application/pdf"},
        request=httpx.Request("GET", url),
    )


class _CapturingLoader(ContentLoader):
    def __init__(self) -> None:
        self.calls: list[ProcessedContent] = []

    async def load(self, processed: ProcessedContent) -> LibraryFile:
        self.calls.append(processed)
        tier = self._tier_for_quality(processed.screening_result.estimated_quality)
        file_name = processed.title.lower().replace(" ", "-") + ".md"
        return LibraryFile(
            file_path=Path(f"library/{tier}/{file_name}"),
            url=processed.url,
            source_type=processed.source_type,
            tier=tier,
            quality_score=processed.screening_result.estimated_quality,
            title=processed.title,
            tags=processed.tags,
        )

    @staticmethod
    def _tier_for_quality(quality: float) -> str:
        if quality >= 9.0:
            return "tier-a"
        if quality >= 7.0:
            return "tier-b"
        if quality >= 5.0:
            return "tier-c"
        return "tier-d"


@pytest.mark.asyncio
async def test_content_pipeline_ingests_pdf_and_returns_library_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://example.com/reports/ai-safety.pdf"
    fake_reader = _FakePdfReader(
        pages=[
            "Artificial Intelligence Safety\nAlignment requires rigorous evaluation.",
            "Second page reinforces rigorous testing principles.",
        ],
        metadata={
            "/Title": "AI Safety Fundamentals",
            "/Author": "Ada Lovelace",
        },
    )
    monkeypatch.setattr(pdf_module, "PdfReader", lambda stream: fake_reader)

    response = _make_pdf_response(url)
    extractor = PDFDocumentExtractor(client=DummyAsyncClient(response=response))
    transformer = BasicContentTransformer()
    loader = _CapturingLoader()
    pipeline = ContentPipeline(extractor=extractor, transformer=transformer, loader=loader)

    result: PipelineResult = await pipeline.run(url)

    assert isinstance(result.raw_content, RawContent)
    assert result.raw_content.source_type is ContentSource.PDF
    assert result.raw_content.metadata["title"] == "AI Safety Fundamentals"

    assert isinstance(result.processed_content, ProcessedContent)
    assert result.processed_content.source_type is ContentSource.PDF

    assert isinstance(result.load_result, LibraryFile)
    assert result.load_result.source_type is ContentSource.PDF
    assert loader.calls and loader.calls[0] is result.processed_content
    assert loader.calls[0].summary
    assert loader.calls[0].screening_result.decision in {"ACCEPT", "MAYBE", "REJECT"}
