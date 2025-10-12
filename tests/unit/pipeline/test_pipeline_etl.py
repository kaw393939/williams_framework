import pytest
from unittest.mock import patch
from app.pipeline.etl import ContentPipeline
from app.pipeline.extractors.base import ContentExtractor
from app.pipeline.transformers.base import ContentTransformer
from app.pipeline.loaders.base import ContentLoader
from app.core.models import RawContent, ProcessedContent, ScreeningResult
from app.core.types import ContentSource

@pytest.mark.asyncio
async def test_pipeline_emits_telemetry_on_extractor_error(monkeypatch):
    class FailingExtractor(ContentExtractor):
        async def extract(self, url: str):
            raise RuntimeError("extractor failed")

    class DummyTransformer(ContentTransformer):
        async def transform(self, raw_content: RawContent):
            sr = ScreeningResult(screening_score=8.0, decision="ACCEPT", reasoning="ok", estimated_quality=8.0)
            return ProcessedContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                title="t",
                summary="s",
                key_points=[],
                tags=[],
                screening_result=sr,
            )

    class DummyLoader(ContentLoader):
        async def load(self, processed: ProcessedContent):
            return None

    pipeline = ContentPipeline(
        extractor=FailingExtractor(),
        transformer=DummyTransformer(),
        loader=DummyLoader(),
    )
    with patch("app.core.telemetry.log_event") as log_event:
        with pytest.raises(RuntimeError):
            await pipeline.run("https://fail.com")
        event = log_event.call_args[0][0]
        assert event["stage"] == "extractor"
        assert event["event_type"] == "pipeline.error"

@pytest.mark.asyncio
async def test_pipeline_emits_telemetry_on_transformer_error(monkeypatch):
    class DummyExtractor(ContentExtractor):
        async def extract(self, url: str):
            return RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text="hi")

    class FailingTransformer(ContentTransformer):
        async def transform(self, raw_content: RawContent):
            raise ValueError("transformer failed")

    class DummyLoader(ContentLoader):
        async def load(self, processed: ProcessedContent):
            return None

    pipeline = ContentPipeline(
        extractor=DummyExtractor(),
        transformer=FailingTransformer(),
        loader=DummyLoader(),
    )
    with patch("app.core.telemetry.log_event") as log_event:
        with pytest.raises(ValueError):
            await pipeline.run("https://fail.com")
        event = log_event.call_args[0][0]
        assert event["stage"] == "transformer"
        assert event["event_type"] == "pipeline.error"

@pytest.mark.asyncio
async def test_pipeline_emits_telemetry_on_loader_error(monkeypatch):
    class DummyExtractor(ContentExtractor):
        async def extract(self, url: str):
            return RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text="hi")

    class DummyTransformer(ContentTransformer):
        async def transform(self, raw_content: RawContent):
            sr = ScreeningResult(screening_score=8.0, decision="ACCEPT", reasoning="ok", estimated_quality=8.0)
            return ProcessedContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                title="t",
                summary="s",
                key_points=[],
                tags=[],
                screening_result=sr,
            )

    class FailingLoader(ContentLoader):
        async def load(self, processed: ProcessedContent):
            raise Exception("loader failed")

    pipeline = ContentPipeline(
        extractor=DummyExtractor(),
        transformer=DummyTransformer(),
        loader=FailingLoader(),
    )
    with patch("app.core.telemetry.log_event") as log_event:
        with pytest.raises(Exception):
            await pipeline.run("https://fail.com")
        event = log_event.call_args[0][0]
        assert event["stage"] == "loader"
        assert event["event_type"] == "pipeline.error"
