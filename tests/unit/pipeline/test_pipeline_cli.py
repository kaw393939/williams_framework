import io
import json

import pytest

from app.core.models import LibraryFile, ProcessedContent, RawContent, ScreeningResult
from app.core.types import ContentSource
from app.pipeline.cli import build_pipeline_for_url, format_result, main, run_pipeline
from app.pipeline.etl import PipelineResult
from app.pipeline.extractors import PDFDocumentExtractor


class FakePipeline:
    def __init__(self, result):
        self._result = result
        self.runs = []

    async def run(self, url: str):
        self.runs.append(url)
        return self._result


@pytest.fixture
def sample_result():
    raw = RawContent(
        url="https://example.com/post",
        source_type=ContentSource.WEB,
        raw_text="Content body",
        metadata={"title": "Example Post"},
    )

    processed = ProcessedContent(
        url=raw.url,
        source_type=raw.source_type,
        title="Example Post",
        summary="Short summary",
        key_points=["Point 1"],
        tags=["example"],
        screening_result=ScreeningResult(
            screening_score=8.5,
            decision="ACCEPT",
            reasoning="Looks good",
            estimated_quality=8.8,
        ),
    )

    library_file = LibraryFile(
        file_path="library/tier-b/example.md",
        url=processed.url,
        source_type=processed.source_type,
        tier="tier-b",
        quality_score=processed.screening_result.estimated_quality,
        title=processed.title,
        tags=processed.tags,
    )

    return PipelineResult(raw_content=raw, processed_content=processed, load_result=library_file)


@pytest.mark.asyncio
async def test_run_pipeline_uses_supplied_pipeline(sample_result):
    pipeline = FakePipeline(sample_result)
    result = await run_pipeline("https://example.com/post", pipeline=pipeline)

    assert result is sample_result
    assert pipeline.runs == ["https://example.com/post"]


def test_main_prints_summary_and_returns_zero(sample_result):
    pipeline = FakePipeline(sample_result)
    buffer = io.StringIO()

    exit_code = main(["https://example.com/post"], pipeline_factory=lambda: pipeline, stream=buffer)

    assert exit_code == 0
    output = buffer.getvalue()
    assert "Example Post" in output
    assert "library/tier-b/example.md" in output


def test_main_returns_error_code_on_failure(monkeypatch):
    def raising_factory():
        raise RuntimeError("boom")

    buffer = io.StringIO()
    exit_code = main(["https://example.com/post"], pipeline_factory=raising_factory, stream=buffer)

    assert exit_code == 1


def test_format_result_json(sample_result):
    payload = format_result(sample_result, output_format="json")
    data = json.loads(payload)
    assert data["processed"]["title"] == "Example Post"
    assert data["library_file"]["tier"] == "tier-b"


def test_build_pipeline_for_url_selects_pdf_extractor():
    pipeline = build_pipeline_for_url("https://example.com/report.pdf")
    assert isinstance(pipeline.extractor, PDFDocumentExtractor)


@pytest.mark.asyncio
async def test_run_pipeline_uses_pdf_extractor_for_pdf_urls(monkeypatch):
    calls: list[str] = []

    async def fake_extract(self, url: str):  # pragma: no cover - exercised via test
        calls.append(url)
        raise RuntimeError("trigger failure to stop pipeline")

    monkeypatch.setattr(PDFDocumentExtractor, "extract", fake_extract, raising=False)

    url = "https://example.com/papers/ai-safety.pdf"
    with pytest.raises(RuntimeError):
        await run_pipeline(url)

    assert calls == [url]


def test_main_logs_error_when_pipeline_run_fails(monkeypatch, capsys):
    class FailingPipeline:
        async def run(self, url: str):
            raise RuntimeError("simulated failure")

    pipeline = FailingPipeline()
    exit_code = main(["https://example.com/data.pdf"], pipeline_factory=lambda: pipeline, stream=io.StringIO())

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Pipeline execution failed for https://example.com/data.pdf" in captured.err


# RED TESTS FOR S1-204: Batch CLI ingest with partial failure reporting

def test_main_accepts_multiple_urls(sample_result):
    """Test that CLI can accept multiple URL arguments."""
    pipeline = FakePipeline(sample_result)
    buffer = io.StringIO()

    exit_code = main(
        ["https://example.com/post1", "https://example.com/post2", "https://example.com/post3"],
        pipeline_factory=lambda: pipeline,
        stream=buffer
    )

    assert exit_code == 0
    assert pipeline.runs == ["https://example.com/post1", "https://example.com/post2", "https://example.com/post3"]


def test_batch_mode_continues_on_partial_failure(sample_result):
    """Test that batch processing continues when one URL fails."""
    class PartiallyFailingPipeline:
        def __init__(self):
            self.runs = []

        async def run(self, url: str):
            self.runs.append(url)
            if "fail" in url:
                raise RuntimeError("simulated failure")
            return sample_result

    pipeline = PartiallyFailingPipeline()
    buffer = io.StringIO()

    exit_code = main(
        ["https://example.com/ok1", "https://example.com/fail", "https://example.com/ok2"],
        pipeline_factory=lambda: pipeline,
        stream=buffer
    )

    # Should process all URLs despite one failure
    assert pipeline.runs == ["https://example.com/ok1", "https://example.com/fail", "https://example.com/ok2"]
    # Should return non-zero exit code when any URL fails
    assert exit_code != 0


def test_batch_json_output_includes_per_url_status(sample_result):
    """Test that batch JSON output reports success/failure for each URL."""
    class PartiallyFailingPipeline:
        async def run(self, url: str):
            if "fail" in url:
                raise ValueError("extraction failed")
            return sample_result

    pipeline = PartiallyFailingPipeline()
    buffer = io.StringIO()

    main(
        ["https://example.com/ok", "https://example.com/fail", "--json"],
        pipeline_factory=lambda: pipeline,
        stream=buffer
    )

    output = json.loads(buffer.getvalue())
    assert "results" in output
    assert len(output["results"]) == 2

    # First URL should succeed
    assert output["results"][0]["url"] == "https://example.com/ok"
    assert output["results"][0]["status"] == "success"

    # Second URL should fail
    assert output["results"][1]["url"] == "https://example.com/fail"
    assert output["results"][1]["status"] == "error"
    assert "error_message" in output["results"][1]


def test_batch_output_includes_summary_statistics(sample_result):
    """Test that batch output includes success/failure summary."""
    class PartiallyFailingPipeline:
        async def run(self, url: str):
            if "fail" in url:
                raise RuntimeError("simulated failure")
            return sample_result

    pipeline = PartiallyFailingPipeline()
    buffer = io.StringIO()

    main(
        ["https://example.com/ok1", "https://example.com/fail1", "https://example.com/ok2", "https://example.com/fail2", "--json"],
        pipeline_factory=lambda: pipeline,
        stream=buffer
    )

    output = json.loads(buffer.getvalue())
    assert "summary" in output
    assert output["summary"]["total"] == 4
    assert output["summary"]["successful"] == 2
    assert output["summary"]["failed"] == 2
