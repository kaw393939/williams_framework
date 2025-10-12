import asyncio
from pathlib import Path

import pytest

from app.core.models import LibraryFile, ProcessedContent, ScreeningResult
from app.core.types import ContentSource
from app.pipeline.loaders.library import LibraryContentLoader


class FakePostgresRepo:
    def __init__(self) -> None:
        self.created = []
        self.updated = []

    async def create_processing_record(self, **kwargs):
        self.created.append(kwargs)

    async def update_processing_record_status(self, **kwargs):
        self.updated.append(kwargs)


class FakeRedisRepo:
    def __init__(self) -> None:
        self.entries = {}

    async def set_json(self, key, value, ttl=None):
        self.entries[key] = {"value": value, "ttl": ttl}


class FakeQdrantRepo:
    def __init__(self) -> None:
        self.calls = []

    def add(self, *, content_id, vector, metadata):
        self.calls.append({
            "content_id": content_id,
            "vector": vector,
            "metadata": metadata,
        })


class FakeMinioRepo:
    def __init__(self) -> None:
        self.calls = []

    def upload_to_tier(self, *, key, content, tier, bucket_prefix, metadata):
        self.calls.append({
            "key": key,
            "content": content,
            "tier": tier,
            "bucket_prefix": bucket_prefix,
            "metadata": metadata,
        })
        return {"key": key, "tier": tier, "bucket": f"{bucket_prefix}-{tier}"}


@pytest.fixture(autouse=True)
def stub_to_thread(monkeypatch):
    async def _immediate(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _immediate)


def _make_processed(quality: float) -> ProcessedContent:
    return ProcessedContent(
        url="https://example.com/insights",
        source_type=ContentSource.WEB,
        title="Industry Insights",
        summary="A concise overview of industry trends and forecasts.",
        key_points=["Trend one", "Forecast two"],
        tags=["industry", "trends"],
        screening_result=ScreeningResult(
            screening_score=quality - 0.5,
            decision="ACCEPT" if quality >= 7.5 else "MAYBE",
            reasoning="Sufficient quality",
            estimated_quality=quality,
        ),
    )


@pytest.mark.asyncio
async def test_loader_persists_processed_content():
    postgres = FakePostgresRepo()
    redis_repo = FakeRedisRepo()
    qdrant = FakeQdrantRepo()
    minio = FakeMinioRepo()

    loader = LibraryContentLoader(
        postgres_repo=postgres,
        redis_repo=redis_repo,
        qdrant_repo=qdrant,
        minio_repo=minio,
        bucket_prefix="librarian",
        cache_ttl=600,
    )

    processed = _make_processed(quality=8.2)

    result = await loader.load(processed)

    assert isinstance(result, LibraryFile)
    assert result.tier == "tier-b"
    assert result.file_path == Path("library/tier-b/https-example-com-insights.md")

    assert len(postgres.created) == 1
    assert postgres.created[0]["operation"] == "store"
    assert postgres.updated[-1]["status"] == "completed"

    assert len(minio.calls) == 1
    minio_call = minio.calls[0]
    assert minio_call["tier"] == "tier-b"
    assert "Industry Insights" in minio_call["content"]

    assert len(qdrant.calls) == 1
    qdrant_call = qdrant.calls[0]
    assert qdrant_call["metadata"]["tier"] == "tier-b"
    assert qdrant_call["metadata"]["title"] == processed.title

    content_id = qdrant_call["content_id"]
    assert redis_repo.entries[f"processed:{content_id}"]["ttl"] == 600


@pytest.mark.asyncio
async def test_loader_updates_failure_status_when_storage_fails():
    postgres = FakePostgresRepo()
    redis_repo = FakeRedisRepo()
    qdrant = FakeQdrantRepo()

    class FailingMinio(FakeMinioRepo):
        def upload_to_tier(self, *args, **kwargs):
            raise RuntimeError("minio unavailable")

    loader = LibraryContentLoader(
        postgres_repo=postgres,
        redis_repo=redis_repo,
        qdrant_repo=qdrant,
        minio_repo=FailingMinio(),
    )

    processed = _make_processed(quality=6.1)

    with pytest.raises(Exception):
        await loader.load(processed)

    assert postgres.updated[-1]["status"] == "failed"
    assert not qdrant.calls
    assert not redis_repo.entries
