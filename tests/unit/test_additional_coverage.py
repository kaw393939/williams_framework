import smtplib
from datetime import datetime
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, call

import httpx
import pytest
from minio.error import S3Error

from app.core.models import Digest, ProcessedContent, RawContent, ScreeningResult
from app.core.types import ContentSource
from app.intelligence import embeddings
from app.repositories.minio_repository import MinIORepository
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.redis_repository import RedisRepository
from app.services import content_service, digest_service, library_service
from app.services.maintenance_service import MaintenanceService


class DummyAsyncClientError:
    def __init__(self, exc: Exception):
        self._exc = exc

    async def __aenter__(self):
        raise self._exc

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyAsyncClientEmpty:
    def __init__(self):
        self._response = httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body></body></html>",
            request=httpx.Request("GET", "https://empty.example.com"),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *_, **__):
        return self._response


@pytest.mark.asyncio
async def test_screening_result_reasoning_validation():
    with pytest.raises(ValueError):
        ScreeningResult(
            screening_score=5.0,
            decision="MAYBE",
            reasoning="   ",
            estimated_quality=5.0,
        )


@pytest.mark.asyncio
async def test_raw_content_blank_text_validation():
    with pytest.raises(ValueError):
        RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text="   ")


@pytest.mark.asyncio
async def test_processed_content_blank_summary_validation():
    with pytest.raises(ValueError):
        ProcessedContent(
            url="https://example.com",
            source_type=ContentSource.WEB,
            title="Title",
            summary="   ",
            key_points=[],
            tags=[],
            screening_result=ScreeningResult(
                screening_score=7.0,
                decision="ACCEPT",
                reasoning="Valid",
                estimated_quality=7.0,
            ),
        )


@pytest.mark.asyncio
async def test_embeddings_zero_dimensions_error():
    with pytest.raises(ValueError):
        embeddings._generate_embedding("text", dimensions=0)


@pytest.mark.asyncio
async def test_embeddings_empty_text_returns_zero_vector():
    vector = await embeddings.generate_embedding("   ")
    assert all(component == 0.0 for component in vector)


@pytest.mark.asyncio
async def test_extract_web_content_http_error(monkeypatch):
    exc = httpx.HTTPError("network down")
    monkeypatch.setattr(content_service.httpx, "AsyncClient", lambda **_: DummyAsyncClientError(exc))

    with pytest.raises(content_service.ExtractionError):
        await content_service.extract_web_content("https://fails.example.com")


@pytest.mark.asyncio
async def test_extract_web_content_no_text(monkeypatch):
    class WhitespaceClient:
        def __init__(self):
            self._response = httpx.Response(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"   ",
                request=httpx.Request("GET", "https://empty.example.com"),
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_, **__):
            return self._response

    monkeypatch.setattr(content_service.trafilatura, "extract", lambda *_, **__: "")
    monkeypatch.setattr(content_service.httpx, "AsyncClient", lambda **_: WhitespaceClient())

    with pytest.raises(content_service.ExtractionError):
        await content_service.extract_web_content("https://empty.example.com")


@pytest.mark.asyncio
async def test_screen_with_ai_rejects_low_quality():
    raw = RawContent(url="https://spam.example.com", source_type=ContentSource.WEB, raw_text="spam " * 20)
    result = await content_service.screen_with_ai(raw)
    assert result.decision == "REJECT"


@pytest.mark.asyncio
async def test_digest_html_empty_state():
    service = digest_service.DigestService(postgres_repo=AsyncMock(), redis_repo=AsyncMock())
    html = await service.generate_digest_html([], datetime.now(), "Daily Digest")
    assert "No new content" in html


def test_digest_parse_metadata_passthrough():
    payload = {"title": "Example"}
    assert digest_service.DigestService._parse_metadata(payload) is payload


@pytest.mark.asyncio
async def test_digest_select_content_respects_preferred_tiers():
    postgres = AsyncMock()
    redis = AsyncMock()
    service = digest_service.DigestService(postgres_repo=postgres, redis_repo=redis)

    now = datetime.now()
    postgres.list_processing_records.return_value = [
        {
            "content_url": "https://example.com/skip",
            "metadata": {
                "quality_score": 8.2,
                "tier": "tier-b",
                "title": "Skip",
                "summary": "",
                "tags": [],
            },
            "started_at": now,
        },
        {
            "content_url": "https://example.com/include",
            "metadata": {
                "quality_score": 9.1,
                "tier": "tier-a",
                "title": "Include",
                "summary": "",
                "tags": ["library"],
            },
            "started_at": now,
        },
    ]

    items = await service.select_content_for_digest(
        date=now,
        preferred_tiers=["tier-a"],
        min_quality=7.0,
    )

    assert len(items) == 1
    assert items[0].tier == "tier-a"


@pytest.mark.asyncio
async def test_digest_generate_text_empty_items():
    service = digest_service.DigestService(postgres_repo=AsyncMock(), redis_repo=AsyncMock())
    text = await service.generate_digest_text([], datetime.now(), "Subject")
    assert "No content available for this digest" in text


@pytest.mark.asyncio
async def test_send_digest_email_failure(monkeypatch):
    service = digest_service.DigestService(postgres_repo=AsyncMock(), redis_repo=AsyncMock())
    digest = Digest(
        digest_id="test-digest",
        date=datetime.now(),
        subject="Digest",
        recipients=["user@example.com"],
        items=[],
        html_content="<p>Hi</p>",
        text_content="Hi",
    )

    class FailingSMTP:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("SMTP offline")

    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)
    sent = await service.send_digest_email(digest)
    assert sent is False


def test_embedding_normalise_zero_vector_returns_zeroes():
    assert embeddings._normalise([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]


def make_s3_error(code: str) -> S3Error:
    return S3Error(
        code=code,
        message="message",
        resource="resource",
        request_id="request_id",
        host_id="host_id",
        response=None,
    )


def test_minio_repository_handling():
    client = MagicMock()
    client.bucket_exists.return_value = False
    repo = MinIORepository(client=client, bucket_name="library")
    client.make_bucket.assert_called_once()

    # Download missing file
    client.get_object.side_effect = make_s3_error("NoSuchKey")
    assert repo.download_file("missing.txt") is None

    # Delete missing file should swallow
    client.remove_object.side_effect = make_s3_error("NoSuchKey")
    repo.delete_file("missing.txt")

    # file_exists with missing object returns False
    client.stat_object.side_effect = make_s3_error("NoSuchKey")
    assert repo.file_exists("missing.txt") is False

    # list_files returning error yields empty list
    client.list_objects.side_effect = make_s3_error("Any")
    assert repo.list_files() == []

    # metadata lookup error returns None
    client.stat_object.side_effect = make_s3_error("NoSuchKey")
    assert repo.get_file_metadata("missing.txt") is None


class StubPostgres:
    def __init__(self):
        self.queries = {}
        self.executed = []

    @staticmethod
    def _key(query: str) -> str:
        return " ".join(query.split())

    async def dbsize(self):
        return 2048

    async def fetch_one(self, query: str, *args):
        normalized = self._key(query)
        self.executed.append((normalized, args))
        return self.queries.get((normalized, args), {"count": 0})

    async def execute(self, query: str, *args):
        normalized = self._key(query)
        self.executed.append((normalized, args))


class StubRedis:
    def __init__(self):
        self.deleted = []
        self.raise_for = "error"

    async def keys(self, pattern: str):
        return ["stale", "fresh", "error"]

    async def ttl(self, key: str):
        if key == "stale":
            return 10
        if key == self.raise_for:
            raise RuntimeError("ttl failure")
        return -1

    async def delete(self, key: str):
        self.deleted.append(key)

    async def ping(self):
        return True

    async def dbsize(self):
        return 5

    async def info(self, section: str):
        return {"hits": 10}


class StubQdrant:
    collection_name = "library"

    def __init__(self, point_exists: bool = True):
        self.point_exists = point_exists

    def get_by_id(self, content_id: str):
        if content_id == "missing":
            return None
        if content_id == "error":
            raise RuntimeError("lookup error")
        return {"id": content_id}

    async def get_collection_info(self):
        return {"points": 10}


class StubMinIO:
    def list_buckets(self):
        return ["bucket-a"]

    def list_files(self):
        return [{"key": "file.json"}, {"key": "orphan.txt"}]


@pytest.mark.asyncio
async def test_maintenance_service_paths():
    postgres = StubPostgres()
    postgres.queries[(
        StubPostgres._key(
            """
                SELECT COUNT(*) as count FROM processing_records
                WHERE content_url LIKE $1
            """
        ),
        ("%orphan.txt%",),
    )] = {"count": 0}
    postgres.queries[(
        StubPostgres._key(
            """
                SELECT COUNT(*) as count FROM processing_records
                WHERE content_url LIKE $1
            """
        ),
        ("%file.json%",),
    )] = {"count": 1}
    postgres.queries[(
        StubPostgres._key(
            """
                SELECT COUNT(*) as count FROM processing_records
                WHERE status NOT IN ('started', 'completed', 'failed', 'pending')
            """
        ),
        tuple(),
    )] = {"count": 2}
    postgres.queries[(
        StubPostgres._key("SELECT COUNT(*) as count FROM processing_records WHERE content_url IS NULL"),
        tuple(),
    )] = {"count": 1}

    redis = StubRedis()
    qdrant = StubQdrant()
    minio_stub = StubMinIO()

    service = MaintenanceService(postgres, redis, qdrant, minio_stub)

    # Cleanup cache removes expiring keys and skips errors
    cleaned = await service.cleanup_old_cache_entries()
    assert cleaned == 1

    # Recompute embeddings handles missing and error cases
    summary = await service.recompute_embeddings(["existing", "missing", "error"])
    assert summary == {"total": 3, "success": 1, "failed": 2}

    # System report aggregates repository data
    report = await service.generate_system_report()
    assert report["repositories"]["postgres"]["status"] == "connected"

    # Vacuum success
    assert await service.vacuum_database() is True

    # Cleanup orphaned files counts missing records
    cleaned_orphans = await service.cleanup_orphaned_files()
    assert cleaned_orphans == 1

    # Verify data integrity captures issues
    integrity = await service.verify_data_integrity()
    assert integrity["issues_found"]


def test_minio_ensure_bucket_exists_handles_owned_error():
    client = MagicMock()
    client.bucket_exists.side_effect = make_s3_error("BucketAlreadyOwnedByYou")
    repo = MinIORepository(client=client)
    repo._ensure_bucket_exists("library")


def test_minio_ensure_bucket_exists_rethrows_other_errors():
    client = MagicMock()
    client.bucket_exists.side_effect = make_s3_error("AccessDenied")
    repo = MinIORepository(client=client)

    with pytest.raises(S3Error):
        repo._ensure_bucket_exists("library")


def test_minio_upload_file_accepts_bytes():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object.return_value = MagicMock(etag="etag", version_id="v1")
    repo = MinIORepository(client=client, bucket_name="library")
    result = repo.upload_file("key", b"data")
    assert result["etag"] == "etag"
    client.put_object.assert_called_once()


def test_minio_upload_file_accepts_string():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object.return_value = MagicMock(etag="etag", version_id="v1")
    repo = MinIORepository(client=client, bucket_name="library")
    repo.upload_file("key", "payload")
    args, kwargs = client.put_object.call_args
    stream = kwargs["data"]
    assert stream.read() == b"payload"


def test_minio_upload_to_tier_with_bytes(monkeypatch):
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object.return_value = MagicMock(etag="etag")
    repo = MinIORepository(client=client, bucket_name="library-tier-a")
    result = repo.upload_to_tier("key", b"payload", tier="tier-b", bucket_prefix="library")
    assert result["bucket"] == "library-tier-b"


def test_minio_upload_to_tier_with_string():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object.return_value = MagicMock(etag="etag")
    repo = MinIORepository(client=client, bucket_name="library-tier-a")
    repo.upload_to_tier("key", "payload", tier="tier-b", bucket_prefix="library")


class DummyPoolContext:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyConnection:
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []

    async def execute(self, query: str, *args):
        self.executed.append((" ".join(query.split()), args))


class DummyPool:
    def __init__(self, connection: DummyConnection):
        self._connection = connection

    def acquire(self):
        return DummyPoolContext(self._connection)


class LegacyQdrantResult:
    def __init__(self, identifier: str, score: float, payload: dict[str, Any]):
        self.id = identifier
        self.score = score
        self.payload = payload


class LegacyQdrantClient:
    def __init__(self):
        self.search_calls = []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return [LegacyQdrantResult("1", 0.42, {"tier": "tier-a"})]


class FailingDeleteClient:
    def delete(self, **_kwargs):
        raise RuntimeError("delete failed")


@pytest.mark.asyncio
async def test_postgres_repository_status_updates_cover_all_branches():
    repo = PostgresRepository(
        host="localhost",
        port=5432,
        database="db",
        user="user",
        password="pass",
    )
    connection = DummyConnection()
    repo.pool = DummyPool(connection)

    await repo.update_processing_record_status("rec", "completed", "done")
    await repo.update_processing_record_status("rec", "running", None)

    completed_query, completed_args = connection.executed[0]
    assert "completed_at" in completed_query
    assert completed_args[0] == "completed"

    running_query, running_args = connection.executed[1]
    assert "completed_at" not in running_query
    assert running_args[0] == "running"


@pytest.mark.asyncio
async def test_postgres_repository_list_maintenance_tasks_builds_filters(monkeypatch):
    repo = PostgresRepository(
        host="localhost",
        port=5432,
        database="db",
        user="user",
        password="pass",
    )
    captured = {}

    async def fake_fetch_all(query: str, *params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(repo, "fetch_all", fake_fetch_all)

    await repo.list_maintenance_tasks(status="pending", task_type="cleanup", limit=5)

    assert "AND status" in captured["query"]
    assert "AND task_type" in captured["query"]
    assert captured["params"][0] == "pending"
    assert captured["params"][1] == "cleanup"
    assert captured["params"][2] == 5


def _make_repo_without_init(client) -> QdrantRepository:
    repo = QdrantRepository.__new__(QdrantRepository)
    repo.client = client
    repo.collection_name = "library"
    repo.vector_size = 3
    return repo


def test_qdrant_query_falls_back_to_search_when_query_points_missing():
    client = LegacyQdrantClient()
    repo = _make_repo_without_init(client)

    results = repo.query([0.1, 0.2, 0.3], limit=1)

    assert results[0]["id"] == "1"
    assert client.search_calls, "legacy search path should be used"


def test_qdrant_filter_handles_range_and_exact_matches():
    client = LegacyQdrantClient()
    repo = _make_repo_without_init(client)

    filt = repo._build_filter({
        "quality": {"$gte": 8.0, "$lte": 9.5},
        "tier": {"$eq": "tier-a"},
        "author": "bronte",
    })

    assert len(filt.must) == 4


def test_qdrant_delete_swallows_errors():
    client = FailingDeleteClient()
    repo = _make_repo_without_init(client)

    repo.delete("content-1")
    repo.delete_batch(["content-2", "content-3"])


@pytest.mark.asyncio
async def test_redis_repository_batch_helpers_cover_missing_lines():
    repo = RedisRepository(host="localhost", port=6379)
    client = AsyncMock()
    client.setex = AsyncMock()
    client.ttl = AsyncMock(return_value=42)
    client.expire = AsyncMock(return_value=True)
    client.dbsize = AsyncMock(return_value=5)
    client.info = AsyncMock(return_value={"redis_version": "7"})
    repo.client = client

    await repo.set_json("key", {"value": 1}, ttl=30)
    client.setex.assert_awaited_once()

    assert await repo.ttl("key") == 42

    assert await repo.expire("key", 10) is True

    repo.keys = AsyncMock(return_value=["match"])
    repo.delete = AsyncMock(return_value=1)
    assert await repo.delete_pattern("pattern") == 1

    repo.keys = AsyncMock(return_value=[])
    assert await repo.delete_pattern("pattern") == 0

    assert await repo.dbsize() == 5

    assert await repo.info() == {"redis_version": "7"}


@pytest.mark.asyncio
async def test_redis_repository_decoding_and_empty_paths():
    repo = RedisRepository(host="localhost", port=6379)
    client = AsyncMock()
    client.get = AsyncMock(return_value=b"value")
    client.delete = AsyncMock(return_value=1)
    client.mget = AsyncMock(return_value=[b"one", None])
    client.keys = AsyncMock(return_value=[b"alpha", b"beta"])
    repo.client = client

    assert await repo.get("key") == "value"

    assert await repo.delete() == 0

    repo.get = AsyncMock(return_value="not-json")
    assert await repo.get_json("bad") is None

    assert await repo.mget([]) == []

    repo.decode_responses = False
    repo.client.mget = AsyncMock(return_value=[b"one", None])
    values = await repo.mget(["a", "b"])
    assert values == ["one", None]

    repo.client.keys = AsyncMock(return_value=[b"k1", b"k2"])
    assert await repo.keys("pattern") == ["k1", "k2"]


@pytest.mark.asyncio
async def test_content_service_handles_screening_failure(monkeypatch):
    postgres = AsyncMock()
    redis = AsyncMock()
    redis.get_json.return_value = None
    qdrant = MagicMock()
    minio = MagicMock()
    service = content_service.ContentService(postgres, redis, qdrant, minio)

    async def failing_screen(_: content_service.RawContent):
        raise RuntimeError("ai down")

    monkeypatch.setattr(content_service, "screen_with_ai", failing_screen)

    raw = RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text="text")

    with pytest.raises(content_service.ScreeningError):
        await service.screen_content(raw)

    postgres.update_processing_record_status.assert_awaited()


@pytest.mark.asyncio
async def test_content_service_process_content_failure(monkeypatch):
    postgres = AsyncMock()
    redis = AsyncMock()
    qdrant = MagicMock()
    minio = MagicMock()
    service = content_service.ContentService(postgres, redis, qdrant, minio)

    async def failing_process(_: RawContent):
        raise RuntimeError("process fail")

    monkeypatch.setattr(content_service, "process_with_ai", failing_process)

    raw = RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text="text")
    screening = ScreeningResult(screening_score=8.0, decision="ACCEPT", reasoning="ok", estimated_quality=8.0)

    with pytest.raises(content_service.ValidationError):
        await service.process_content(raw, screening)

    postgres.update_processing_record_status.assert_awaited_with(
        record_id=ANY,
        status="failed",
        error_message="process fail",
    )


@pytest.mark.asyncio
async def test_content_service_store_content_failure(monkeypatch):
    postgres = AsyncMock()
    redis = AsyncMock()
    qdrant = MagicMock()
    qdrant.add.return_value = None
    minio = MagicMock()
    minio.upload_to_tier.return_value = {"bucket": "library-tier-a"}
    service = content_service.ContentService(postgres, redis, qdrant, minio)

    screening = ScreeningResult(screening_score=8.5, decision="ACCEPT", reasoning="great", estimated_quality=9.5)
    processed = ProcessedContent(
        url="https://example.com/article",
        source_type=ContentSource.WEB,
        title="Example",
        summary="Summary",
        key_points=["Point"],
        tags=["tag"],
        screening_result=screening,
    )

    async def fake_to_thread(func, *args, **kwargs):
        fake_to_thread.calls += 1
        if fake_to_thread.calls == 1:
            return func(*args, **kwargs)
        raise RuntimeError("qdrant offline")

    fake_to_thread.calls = 0

    async def fake_generate_embedding(_: str):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(content_service.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(content_service, "generate_embedding", fake_generate_embedding)

    with pytest.raises(RuntimeError):
        await service.store_content(processed)

    postgres.update_processing_record_status.assert_awaited_with(
        record_id=ANY,
        status="failed",
        error_message="qdrant offline",
    )

@pytest.mark.asyncio
async def test_content_service_store_content_assigns_mid_tier(monkeypatch):
    postgres = AsyncMock()
    redis = AsyncMock()
    qdrant = MagicMock()
    minio = MagicMock()
    minio.upload_to_tier.return_value = {"bucket": "library-tier-c"}
    qdrant.add.return_value = None

    service = content_service.ContentService(postgres, redis, qdrant, minio)

    screening = ScreeningResult(screening_score=6.0, decision="ACCEPT", reasoning="solid", estimated_quality=6.2)
    processed = ProcessedContent(
        url="https://example.com/mid-tier",
        source_type=ContentSource.WEB,
        title="Mid Tier",
        summary="Summary",
        key_points=["Point"],
        tags=["tag"],
        screening_result=screening,
    )

    async def passthrough_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_generate_embedding(_: str):
        return [0.3, 0.5, 0.7]

    monkeypatch.setattr(content_service.asyncio, "to_thread", passthrough_to_thread)
    monkeypatch.setattr(content_service, "generate_embedding", fake_generate_embedding)

    await service.store_content(processed)

    _, kwargs = minio.upload_to_tier.call_args
    assert kwargs["tier"] == "c"

    _, kwargs = qdrant.add.call_args
    assert kwargs["metadata"]["tier"] == "c"

@pytest.mark.asyncio
async def test_library_service_generate_embedding_delegates(monkeypatch):
    recorded = {}

    async def fake_generate(text: str):
        recorded["text"] = text
        return [0.1, 0.2]

    monkeypatch.setattr(library_service, "_generate_embedding", fake_generate)

    vector = await library_service.generate_embedding("hello world")

    assert vector == [0.1, 0.2]
    assert recorded["text"] == "hello world"


def test_library_service_bucket_prefix_helpers():
    assert library_service.LibraryService._get_bucket_prefix("library-tier-a") == "library-tier"
    assert library_service.LibraryService._get_bucket_prefix("library") == "library"


@pytest.mark.asyncio
async def test_library_service_move_between_tiers_missing_record():
    postgres = AsyncMock()
    postgres.fetch_one = AsyncMock(return_value=None)

    service = library_service.LibraryService(
        postgres_repo=postgres,
        redis_repo=AsyncMock(),
        qdrant_repo=MagicMock(),
        minio_repo=MagicMock(),
    )

    with pytest.raises(ValueError):
        await service.move_between_tiers(
            "https://example.com/article",
            from_tier="tier-a",
            to_tier="tier-b",
        )

    postgres.fetch_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_library_service_statistics_empty_returns_defaults():
    postgres = AsyncMock()
    postgres.fetch_all = AsyncMock(return_value=[])

    service = library_service.LibraryService(
        postgres_repo=postgres,
        redis_repo=AsyncMock(),
        qdrant_repo=MagicMock(),
        minio_repo=MagicMock(),
    )

    stats = await service.get_statistics()

    assert stats.total_files == 0
    assert stats.files_by_tier == {}
    assert stats.average_quality == 0.0
    assert stats.total_tags == 0


@pytest.mark.asyncio
async def test_library_service_statistics_handles_tag_parse_error():
    now = datetime.now()
    postgres = AsyncMock()
    postgres.fetch_all = AsyncMock(
        return_value=[
            {
                "tier": "tier-a",
                "quality_score": "8.5",
                "tags": "{",
                "started_at": now,
            },
            {
                "tier": "tier-b",
                "quality_score": None,
                "tags": ["news", "ai"],
                "started_at": now,
            },
        ]
    )

    service = library_service.LibraryService(
        postgres_repo=postgres,
        redis_repo=AsyncMock(),
        qdrant_repo=MagicMock(),
        minio_repo=MagicMock(),
    )

    stats = await service.get_statistics()

    assert stats.total_files == 2
    assert stats.files_by_tier["tier-a"] == 1
    assert stats.files_by_tier["tier-b"] == 1
    assert stats.total_tags == 2
    assert stats.recent_additions == 2

@pytest.mark.asyncio
async def test_content_service_store_content_assigns_low_tier(monkeypatch):
    postgres = AsyncMock()
    redis = AsyncMock()
    qdrant = MagicMock()
    minio = MagicMock()
    minio.upload_to_tier.return_value = {"bucket": "library-tier-d"}
    qdrant.add.return_value = None

    service = content_service.ContentService(postgres, redis, qdrant, minio)

    screening = ScreeningResult(screening_score=4.0, decision="ACCEPT", reasoning="edge", estimated_quality=4.2)
    processed = ProcessedContent(
        url="https://example.com/low-tier",
        source_type=ContentSource.WEB,
        title="Low Tier",
        summary="Summary",
        key_points=["Point"],
        tags=["tag"],
        screening_result=screening,
    )

    async def passthrough(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_generate_embedding(_: str):
        return [0.1, 0.1, 0.1]

    monkeypatch.setattr(content_service.asyncio, "to_thread", passthrough)
    monkeypatch.setattr(content_service, "generate_embedding", fake_generate_embedding)

    await service.store_content(processed)

    _, kwargs = minio.upload_to_tier.call_args
    assert kwargs["tier"] == "d"

    _, kwargs = qdrant.add.call_args
    assert kwargs["metadata"]["tier"] == "d"


@pytest.mark.asyncio
async def test_content_service_process_url_rejects_after_pipeline(monkeypatch):
    service = content_service.ContentService(AsyncMock(), AsyncMock(), MagicMock(), MagicMock())

    raw = RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text="text")
    screening = ScreeningResult(screening_score=5.0, decision="REJECT", reasoning="no", estimated_quality=4.0)

    service.extract_content = AsyncMock(return_value=raw)
    service.screen_content = AsyncMock(return_value=screening)
    service.process_content = AsyncMock(return_value=None)

    with pytest.raises(content_service.ValidationError):
        await service.process_url("https://example.com")


@pytest.mark.asyncio
async def test_screen_with_ai_accepts_high_quality_content():
    import string

    tokens = []
    alpha = string.ascii_lowercase
    for i in range(200):
        letters = alpha[i % 26] + alpha[(i // 26) % 26] + alpha[(i // 676) % 26]
        tokens.append(f"lib{letters}")

    sentences = []
    for i in range(10):
        chunk = " ".join(tokens[i * 20:(i + 1) * 20])
        sentences.append(f"{chunk}.")

    text = " ".join(sentences)
    raw = RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text=text)

    result = await content_service.screen_with_ai(raw)

    assert result.decision == "ACCEPT"


@pytest.mark.asyncio
async def test_process_with_ai_provides_tag_fallback():
    text = "12345 67890 $$$"  # no alpha tokens to trigger fallback to default tag
    raw = RawContent(url="https://example.com", source_type=ContentSource.WEB, raw_text=text)

    result = await content_service.process_with_ai(raw)

    assert result["tags"] == ["general"]


def test_minio_download_file_as_bytes():
    client = MagicMock()
    client.bucket_exists.return_value = True
    bucket_response = MagicMock()
    bucket_response.read.return_value = b"data"
    repo = MinIORepository(client=client, bucket_name="library")
    client.get_object.return_value = bucket_response

    content = repo.download_file("key", as_bytes=True)
    assert content == b"data"
    bucket_response.close.assert_called_once()
    bucket_response.release_conn.assert_called_once()


def test_minio_download_file_raises_unexpected_errors():
    client = MagicMock()
    client.bucket_exists.return_value = True
    repo = MinIORepository(client=client, bucket_name="library")
    client.get_object.side_effect = make_s3_error("AccessDenied")

    with pytest.raises(S3Error):
        repo.download_file("key")


def test_minio_download_file_decodes_text():
    client = MagicMock()
    client.bucket_exists.return_value = True
    response = MagicMock()
    response.read.return_value = b"hello"
    repo = MinIORepository(client=client, bucket_name="library")
    client.get_object.return_value = response
    assert repo.download_file("key") == "hello"


def test_minio_delete_file_rethrows_unknown_errors():
    client = MagicMock()
    client.bucket_exists.return_value = True
    repo = MinIORepository(client=client, bucket_name="library")
    client.remove_object.side_effect = make_s3_error("AccessDenied")

    with pytest.raises(S3Error):
        repo.delete_file("key")


def test_minio_delete_files_invokes_each():
    client = MagicMock()
    client.bucket_exists.return_value = True
    repo = MinIORepository(client=client, bucket_name="library")
    repo.delete_file = MagicMock()
    repo.delete_files(["a", "b"])
    repo.delete_file.assert_has_calls([call("a"), call("b")])


def test_minio_file_exists_handles_missing_object():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.stat_object.side_effect = make_s3_error("NoSuchKey")
    repo = MinIORepository(client=client, bucket_name="library")
    assert repo.file_exists("key") is False


def test_minio_file_exists_rethrows_other_errors():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.stat_object.side_effect = make_s3_error("AccessDenied")
    repo = MinIORepository(client=client, bucket_name="library")
    with pytest.raises(S3Error):
        repo.file_exists("key")


def test_minio_file_exists_returns_true():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.stat_object.return_value = MagicMock()
    repo = MinIORepository(client=client, bucket_name="library")
    assert repo.file_exists("key") is True


def test_minio_list_files_gracefully_handles_error():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.list_objects.side_effect = make_s3_error("AccessDenied")
    repo = MinIORepository(client=client, bucket_name="library")
    assert repo.list_files() == []


def test_minio_list_files_collects_objects():
    client = MagicMock()
    client.bucket_exists.return_value = True
    obj = MagicMock(object_name="file", size=1, etag="e", last_modified=123)
    client.list_objects.return_value = [obj]
    repo = MinIORepository(client=client, bucket_name="library")
    assert repo.list_files() == [{"key": "file", "size": 1, "etag": "e", "last_modified": 123}]


def test_minio_get_file_metadata_returns_none_for_missing():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.stat_object.side_effect = make_s3_error("NoSuchKey")
    repo = MinIORepository(client=client, bucket_name="library")
    assert repo.get_file_metadata("key") is None


def test_minio_get_file_metadata_rethrows_other_errors():
    client = MagicMock()
    client.bucket_exists.return_value = True
    repo = MinIORepository(client=client, bucket_name="library")
    client.stat_object.side_effect = make_s3_error("AccessDenied")
    with pytest.raises(S3Error):
        repo.get_file_metadata("key")


def test_minio_update_file_metadata_replaces_metadata(monkeypatch):
    client = MagicMock()
    client.bucket_exists.return_value = True
    repo = MinIORepository(client=client, bucket_name="library")
    repo.update_file_metadata("key", {"tier": "tier-a"})
    client.copy_object.assert_called_once()


def test_minio_move_between_tiers_transfers_and_deletes():
    client = MagicMock()
    client.bucket_exists.return_value = True
    repo = MinIORepository(client=client, bucket_name="library-tier-a")
    repo._ensure_bucket_exists = MagicMock()
    repo.client.copy_object.return_value = None
    repo.client.remove_object.return_value = None

    repo.move_between_tiers("key", from_tier="tier-a", to_tier="tier-b", bucket_prefix="library")
    repo._ensure_bucket_exists.assert_called_with("library-tier-b")
    repo.client.copy_object.assert_called_once()
    repo.client.remove_object.assert_called_once()


def test_minio_create_tier_buckets_invokes_ensure_for_each():
    client = MagicMock()
    repo = MinIORepository(client=client)
    repo._ensure_bucket_exists = MagicMock()
    repo.create_tier_buckets(prefix="lib")
    repo._ensure_bucket_exists.assert_has_calls([
        call("lib-tier-a"),
        call("lib-tier-b"),
        call("lib-tier-c"),
        call("lib-tier-d"),
    ])


@pytest.mark.asyncio
async def test_maintenance_vacuum_failure():
    postgres = StubPostgres()

    async def failing_execute(query: str, *args):
        raise RuntimeError("vacuum failed")

    postgres.execute = failing_execute
    service = MaintenanceService(postgres, StubRedis(), StubQdrant(), StubMinIO())
    assert await service.vacuum_database() is False


@pytest.mark.asyncio
async def test_maintenance_system_report_errors():
    postgres = StubPostgres()

    async def failing_fetch(query: str, *args):
        raise RuntimeError("db error")

    postgres.fetch_one = failing_fetch

    class ErrorRedis(StubRedis):
        async def ping(self):
            raise RuntimeError("redis down")

    class ErrorQdrant(StubQdrant):
        async def get_collection_info(self):
            raise RuntimeError("qdrant down")

    class ErrorMinIO(StubMinIO):
        def list_buckets(self):
            raise RuntimeError("minio down")

    service = MaintenanceService(postgres, ErrorRedis(), ErrorQdrant(), ErrorMinIO())
    report = await service.generate_system_report()
    assert report["repositories"]["postgres"]["status"] == "error"
    assert report["repositories"]["redis"]["status"] == "error"
    assert report["repositories"]["qdrant"]["status"] == "error"
    assert report["repositories"]["minio"]["status"] == "error"


@pytest.mark.asyncio
async def test_verify_data_integrity_redis_failure():
    postgres = StubPostgres()

    class FailingRedis(StubRedis):
        async def ping(self):
            raise RuntimeError("ping failure")

    service = MaintenanceService(postgres, FailingRedis(), StubQdrant(), StubMinIO())
    report = await service.verify_data_integrity()
    assert any(issue["check"] == "redis_connectivity" for issue in report["issues_found"])

@pytest.mark.asyncio
async def test_maintenance_safe_repository_call_handles_exception():
    async def failing_operation():
        raise RuntimeError("nope")

    result = await MaintenanceService._safe_repository_call("redis", failing_operation)

    assert result["status"] == "error"
    assert "nope" in result["error"]


@pytest.mark.asyncio
async def test_maintenance_safe_repository_call_success():
    async def successful_operation():
        return {"ok": True}

    result = await MaintenanceService._safe_repository_call("redis", successful_operation)

    assert result == {"status": "success", "result": {"ok": True}}


@pytest.mark.asyncio
async def test_cleanup_orphaned_files_handles_bucket_and_object_errors(monkeypatch):
    class ErrorMinIO:
        def list_buckets(self):
            return ["library-tier-a"]

        def list_files(self):
            raise RuntimeError("objects broken")

    postgres = AsyncMock()
    postgres.fetch_one = AsyncMock(return_value={"count": 1})

    service = MaintenanceService(postgres, AsyncMock(), AsyncMock(), ErrorMinIO())

    printed = {}

    def capture_print(*args, **_kwargs):
        printed.setdefault("messages", []).append(args)

    monkeypatch.setattr("builtins.print", capture_print)

    cleaned = await service.cleanup_orphaned_files()

    assert cleaned == 0
    assert printed.get("messages") is None


@pytest.mark.asyncio
async def test_cleanup_orphaned_files_handles_top_level_error(monkeypatch):
    class BrokenBucketsMinIO:
        def list_buckets(self):
            raise RuntimeError("buckets down")

    service = MaintenanceService(AsyncMock(), AsyncMock(), AsyncMock(), BrokenBucketsMinIO())

    captured = {}

    def capture_print(*args, **_kwargs):
        captured.setdefault("messages", []).append(args)

    monkeypatch.setattr("builtins.print", capture_print)

    cleaned = await service.cleanup_orphaned_files()

    assert cleaned == 0
    assert captured["messages"]


@pytest.mark.asyncio
async def test_verify_data_integrity_handles_fetch_errors_and_redis_ping_false():
    class FlakyPostgres:
        def __init__(self):
            self.calls = 0

        async def fetch_one(self, *_args):
            self.calls += 1
            raise RuntimeError(f"fail-{self.calls}")

    postgres = FlakyPostgres()
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=False)

    service = MaintenanceService(postgres, redis, StubQdrant(), StubMinIO())

    report = await service.verify_data_integrity()

    issues = {issue["check"]: issue["issue"] for issue in report["issues_found"]}

    assert "processing_record_status_validation" in issues
    assert "null_content_url_check" in issues
    assert "redis_connectivity" in issues
