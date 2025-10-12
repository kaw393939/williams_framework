import io
import json

import pytest

from app.core.models import RawContent, ProcessedContent, ScreeningResult
from app.core.types import ContentSource
from app.pipeline import cli as cli_module
from app.pipeline.cli import main


@pytest.mark.asyncio
async def test_run_pipeline_defaults_to_pdf_extractor(monkeypatch):
    url = "https://example.com/data/report.pdf"
    observed: list[str] = []

    async def fake_extract(self, target_url: str):
        observed.append(target_url)
        raise RuntimeError("stop pipeline")

    monkeypatch.setattr("app.pipeline.cli.PDFDocumentExtractor.extract", fake_extract, raising=False)

    with pytest.raises(RuntimeError):
        await cli_module.run_pipeline(url)

    assert observed == [url]


def test_cli_ingests_pdf_and_outputs_json(monkeypatch):
    url = "https://example.com/research/ai-progress.pdf"

    async def fake_extract(self, target_url: str) -> RawContent:
        assert target_url == url
        return RawContent(
            url=target_url,
            source_type=ContentSource.PDF,
            raw_text="AI progress is accelerating with better evaluation benchmarks.",
            metadata={"title": "AI Progress 2025", "author": "Researcher"},
        )

    async def fake_transform(self, raw: RawContent) -> ProcessedContent:
        return ProcessedContent(
            url=raw.url,
            source_type=raw.source_type,
            title=raw.metadata["title"],
            summary="Concise summary of AI progress.",
            key_points=["Benchmarks improving", "Safety research growing"],
            tags=["ai", "safety"],
            screening_result=ScreeningResult(
                screening_score=8.2,
                decision="ACCEPT",
                reasoning="High quality research overview.",
                estimated_quality=8.7,
            ),
        )

    stored_payload: dict[str, str] = {}

    def fake_upload_to_tier(self, *, key: str, content: str | bytes, tier: str, bucket_prefix: str, metadata=None):
        stored_payload.update({
            "key": key,
            "tier": tier,
            "content": content.decode("utf-8") if isinstance(content, bytes) else content,
            "metadata": metadata or {},
        })
        return {"key": key, "bucket": f"{bucket_prefix}-{tier}", "metadata": metadata or {}}

    def fake_add(self, *, content_id: str, vector: list[float], metadata: dict[str, str]):
        stored_payload["vector_metadata"] = metadata

    async def fake_set_json(self, key: str, value, ttl=None):
        stored_payload["cache_key"] = key

    async def fake_create_processing_record(self, **payload):
        stored_payload.setdefault("record_status", []).append({"status": "started"})

    async def fake_update_processing_record_status(self, **payload):
        stored_payload.setdefault("record_status", []).append(payload)

    monkeypatch.setattr("app.pipeline.cli.PDFDocumentExtractor.extract", fake_extract, raising=False)
    monkeypatch.setattr("app.pipeline.cli.BasicContentTransformer.transform", fake_transform, raising=False)
    monkeypatch.setattr("app.pipeline.cli._LocalObjectStore.upload_to_tier", fake_upload_to_tier, raising=False)
    monkeypatch.setattr("app.pipeline.cli._LocalVectorStore.add", fake_add, raising=False)
    monkeypatch.setattr("app.pipeline.cli._InMemoryCache.set_json", fake_set_json, raising=False)
    monkeypatch.setattr("app.pipeline.cli._InMemoryProcessingRepository.create_processing_record", fake_create_processing_record, raising=False)
    monkeypatch.setattr("app.pipeline.cli._InMemoryProcessingRepository.update_processing_record_status", fake_update_processing_record_status, raising=False)

    buffer = io.StringIO()
    exit_code = main([url, "--json"], stream=buffer)

    assert exit_code == 0

    data = json.loads(buffer.getvalue())
    assert data["raw"]["source_type"] == ContentSource.PDF.value
    assert data["processed"]["title"] == "AI Progress 2025"
    assert data["library_file"]["tier"].startswith("tier-")
    assert stored_payload["tier"] == data["library_file"]["tier"]
    assert "Concise summary" in stored_payload["content"]