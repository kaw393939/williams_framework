import pytest

from app.core.models import RawContent
from app.core.types import ContentSource
from app.pipeline.transformers.basic import BasicContentTransformer


@pytest.mark.asyncio
async def test_basic_transformer_generates_summary_key_points_tags():
    text = (
        "Artificial intelligence is transforming industries worldwide. "
        "Companies leverage machine learning to automate processes and gain insights. "
        "However, successful adoption requires careful planning and ethical considerations."
    )

    raw = RawContent(
        url="https://example.com/ai",
        source_type=ContentSource.WEB,
        raw_text=text,
        metadata={"title": "AI Transformation"},
    )

    transformer = BasicContentTransformer()
    processed = await transformer.transform(raw)

    assert processed.url == raw.url
    assert processed.title == "AI Transformation"
    assert processed.summary.startswith("Artificial intelligence is transforming industries worldwide")
    assert len(processed.summary) <= 400
    assert processed.key_points
    assert processed.key_points[0].startswith("Artificial intelligence")
    assert processed.tags
    assert "intelligence" in processed.tags
    assert processed.screening_result.decision in {"ACCEPT", "MAYBE", "REJECT"}


@pytest.mark.asyncio
async def test_basic_transformer_handles_short_text():
    text = "Short update about productivity hacks."

    raw = RawContent(
        url="https://example.com/short",
        source_type=ContentSource.WEB,
        raw_text=text,
        metadata={},
    )

    transformer = BasicContentTransformer()
    processed = await transformer.transform(raw)

    assert processed.title.startswith("https://example.com")
    assert processed.summary == text
    assert processed.key_points == [text]
    assert processed.tags
    assert processed.screening_result.screening_score >= 0.0
