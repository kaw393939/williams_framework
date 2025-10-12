import inspect
from pathlib import Path

import pytest

from app.core.models import LibraryFile, ProcessedContent, RawContent, ScreeningResult
from app.core.types import ContentSource


@pytest.mark.asyncio
async def test_content_pipeline_runs_in_sequence():
    from app.pipeline.etl import ContentPipeline, PipelineResult
    from app.pipeline.extractors.base import ContentExtractor
    from app.pipeline.loaders.base import ContentLoader
    from app.pipeline.transformers.base import ContentTransformer

    class DummyExtractor(ContentExtractor):
        async def extract(self, url: str) -> RawContent:
            return RawContent(
                url=url,
                source_type=ContentSource.WEB,
                raw_text="example",
                metadata={"title": "Example"},
            )

    class DummyTransformer(ContentTransformer):
        async def transform(self, raw_content: RawContent) -> ProcessedContent:
            return ProcessedContent(
                url=raw_content.url,
                source_type=raw_content.source_type,
                title=raw_content.metadata["title"],
                summary="summary",
                key_points=["point"],
                tags=["tag"],
                screening_result=ScreeningResult(
                    screening_score=8.0,
                    decision="ACCEPT",
                    reasoning="ok",
                    estimated_quality=8.5,
                ),
            )

    class DummyLoader(ContentLoader):
        async def load(self, processed: ProcessedContent) -> LibraryFile:
            return LibraryFile(
                file_path=Path(
                    processed.url.path and processed.url.path or "example.json"
                ),
                url=processed.url,
                source_type=processed.source_type,
                tier="tier-b",
                quality_score=processed.screening_result.estimated_quality,
                title=processed.title,
                tags=processed.tags,
            )

    pipeline = ContentPipeline(
        extractor=DummyExtractor(),
        transformer=DummyTransformer(),
        loader=DummyLoader(),
    )

    result = await pipeline.run("https://example.com/article")

    assert isinstance(result, PipelineResult)
    assert result.raw_content.raw_text == "example"
    assert result.processed_content.summary == "summary"
    assert result.load_result.tier == "tier-b"


def test_extractor_is_abstract():
    from app.pipeline.extractors.base import ContentExtractor

    assert inspect.isabstract(ContentExtractor)
    assert "extract" in ContentExtractor.__abstractmethods__


def test_transformer_is_abstract():
    from app.pipeline.transformers.base import ContentTransformer

    assert inspect.isabstract(ContentTransformer)
    assert "transform" in ContentTransformer.__abstractmethods__


def test_loader_is_abstract():
    from app.pipeline.loaders.base import ContentLoader

    assert inspect.isabstract(ContentLoader)
    assert "load" in ContentLoader.__abstractmethods__
