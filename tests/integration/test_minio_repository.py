"""
Integration tests for MinIO Object Storage Repository.

Tests use a REAL MinIO instance running in Docker (NO MOCKS).
Following TDD methodology: RED-GREEN-REFACTOR.
"""
from uuid import uuid4

import pytest
from minio import Minio

from app.core.config import settings
from app.repositories.minio_repository import MinIORepository


@pytest.fixture
def minio_client():
    """Create a real MinIO client for testing."""
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )
    yield client
    # Cleanup: remove test buckets after tests
    try:
        buckets = client.list_buckets()
        for bucket in buckets:
            if bucket.name.startswith("test-"):
                # Remove all objects first
                objects = client.list_objects(bucket.name, recursive=True)
                for obj in objects:
                    client.remove_object(bucket.name, obj.object_name)
                # Then remove bucket
                client.remove_bucket(bucket.name)
    except Exception:
        pass


@pytest.fixture
def minio_repo(minio_client):
    """Create a MinIORepository instance with test bucket."""
    test_bucket = f"test-{uuid4().hex[:8]}"
    repo = MinIORepository(
        client=minio_client,
        bucket_name=test_bucket
    )
    yield repo
    # Cleanup handled by minio_client fixture


class TestMinIORepositoryInitialization:
    """Test repository initialization and bucket creation."""

    def test_repository_creates_bucket_if_not_exists(self, minio_client):
        """Repository should create bucket on initialization if it doesn't exist."""
        test_bucket = f"test-{uuid4().hex[:8]}"

        # Verify bucket doesn't exist
        assert not minio_client.bucket_exists(test_bucket)

        # Create repository - should create bucket
        repo = MinIORepository(
            client=minio_client,
            bucket_name=test_bucket
        )

        # Verify bucket was created
        assert minio_client.bucket_exists(test_bucket)

        # Cleanup
        minio_client.remove_bucket(test_bucket)

    def test_repository_reuses_existing_bucket(self, minio_client):
        """Repository should reuse existing bucket instead of failing."""
        test_bucket = f"test-{uuid4().hex[:8]}"

        # Create bucket manually
        minio_client.make_bucket(test_bucket)

        # Create repository - should not fail
        repo = MinIORepository(
            client=minio_client,
            bucket_name=test_bucket
        )

        # Verify bucket still exists
        assert minio_client.bucket_exists(test_bucket)

        # Cleanup
        minio_client.remove_bucket(test_bucket)

    def test_create_tier_buckets(self, minio_client):
        """Should create all tier buckets at once."""
        prefix = f"test-{uuid4().hex[:8]}"

        repo = MinIORepository(client=minio_client)
        repo.create_tier_buckets(prefix=prefix)

        # Verify all tier buckets exist
        assert minio_client.bucket_exists(f"{prefix}-tier-a")
        assert minio_client.bucket_exists(f"{prefix}-tier-b")
        assert minio_client.bucket_exists(f"{prefix}-tier-c")
        assert minio_client.bucket_exists(f"{prefix}-tier-d")

        # Cleanup
        for tier in ["tier-a", "tier-b", "tier-c", "tier-d"]:
            minio_client.remove_bucket(f"{prefix}-{tier}")


class TestMinIORepositoryUpload:
    """Test uploading files to MinIO."""

    def test_upload_text_file(self, minio_repo):
        """Should upload text content as an object."""
        key = f"{uuid4()}.md"
        content = "# Test Document\n\nThis is test content."

        # Upload file
        result = minio_repo.upload_file(key, content)

        # Verify result contains key
        assert result["key"] == key
        assert "etag" in result

        # Verify file exists
        assert minio_repo.file_exists(key)

    def test_upload_with_metadata(self, minio_repo):
        """Should upload file with custom metadata."""
        key = f"{uuid4()}.md"
        content = "# Test"
        metadata = {
            "url": "https://example.com/article",
            "title": "Test Article",
            "quality_score": "8.5",
            "source_type": "web"
        }

        # Upload with metadata
        minio_repo.upload_file(key, content, metadata=metadata)

        # Retrieve and verify metadata
        stat = minio_repo.get_file_metadata(key)
        assert stat.metadata["x-amz-meta-url"] == "https://example.com/article"
        assert stat.metadata["x-amz-meta-title"] == "Test Article"
        assert stat.metadata["x-amz-meta-quality_score"] == "8.5"

    def test_upload_bytes_content(self, minio_repo):
        """Should upload binary content."""
        key = f"{uuid4()}.bin"
        content = b"Binary content here"

        result = minio_repo.upload_file(key, content)

        assert result["key"] == key
        assert minio_repo.file_exists(key)

    def test_upload_with_content_type(self, minio_repo):
        """Should set correct content type."""
        key = f"{uuid4()}.md"
        content = "# Markdown"

        minio_repo.upload_file(key, content, content_type="text/markdown")

        stat = minio_repo.get_file_metadata(key)
        assert stat.content_type == "text/markdown"


class TestMinIORepositoryDownload:
    """Test downloading files from MinIO."""

    def test_download_text_file(self, minio_repo):
        """Should download and return text content."""
        key = f"{uuid4()}.md"
        original_content = "# Test Document\n\nThis is test content."

        # Upload first
        minio_repo.upload_file(key, original_content)

        # Download
        downloaded_content = minio_repo.download_file(key)

        # Verify content matches
        assert downloaded_content == original_content

    def test_download_nonexistent_file_returns_none(self, minio_repo):
        """Should return None for non-existent file."""
        result = minio_repo.download_file("nonexistent.md")
        assert result is None

    def test_download_binary_content(self, minio_repo):
        """Should download binary content correctly."""
        key = f"{uuid4()}.bin"
        original_content = b"Binary data \x00\x01\x02"

        minio_repo.upload_file(key, original_content)
        downloaded = minio_repo.download_file(key, as_bytes=True)

        assert downloaded == original_content


class TestMinIORepositoryDelete:
    """Test deleting files from MinIO."""

    def test_delete_file(self, minio_repo):
        """Should delete file by key."""
        key = f"{uuid4()}.md"
        minio_repo.upload_file(key, "Test content")

        # Verify exists
        assert minio_repo.file_exists(key)

        # Delete
        minio_repo.delete_file(key)

        # Verify deleted
        assert not minio_repo.file_exists(key)

    def test_delete_nonexistent_file_does_not_raise(self, minio_repo):
        """Deleting non-existent file should not raise error."""
        # Should not raise
        minio_repo.delete_file("nonexistent.md")

    def test_delete_multiple_files(self, minio_repo):
        """Should delete multiple files at once."""
        keys = [f"{uuid4()}.md" for _ in range(5)]

        # Upload files
        for key in keys:
            minio_repo.upload_file(key, f"Content for {key}")

        # Delete batch
        minio_repo.delete_files(keys[:3])

        # Verify first 3 deleted, last 2 remain
        for key in keys[:3]:
            assert not minio_repo.file_exists(key)
        for key in keys[3:]:
            assert minio_repo.file_exists(key)


class TestMinIORepositoryList:
    """Test listing files in MinIO."""

    def test_list_all_files(self, minio_repo):
        """Should list all files in bucket."""
        # Upload some files
        keys = [f"test-{i}.md" for i in range(5)]
        for key in keys:
            minio_repo.upload_file(key, f"Content {key}")

        # List files
        files = minio_repo.list_files()

        # Verify all keys present
        assert len(files) == 5
        file_keys = [f["key"] for f in files]
        for key in keys:
            assert key in file_keys

    def test_list_with_prefix(self, minio_repo):
        """Should filter files by prefix."""
        # Upload files with different prefixes
        minio_repo.upload_file("articles/1.md", "Article 1")
        minio_repo.upload_file("articles/2.md", "Article 2")
        minio_repo.upload_file("notes/1.md", "Note 1")

        # List only articles
        files = minio_repo.list_files(prefix="articles/")

        assert len(files) == 2
        for f in files:
            assert f["key"].startswith("articles/")

    def test_list_empty_bucket(self, minio_repo):
        """Should return empty list for empty bucket."""
        files = minio_repo.list_files()
        assert files == []


class TestMinIORepositoryMetadata:
    """Test metadata operations."""

    def test_get_file_metadata(self, minio_repo):
        """Should retrieve file metadata."""
        key = f"{uuid4()}.md"
        content = "# Test"
        metadata = {"title": "Test Article", "author": "Test User"}

        minio_repo.upload_file(key, content, metadata=metadata)

        stat = minio_repo.get_file_metadata(key)
        assert stat.size > 0
        assert stat.object_name == key
        assert "x-amz-meta-title" in stat.metadata

    def test_update_file_metadata(self, minio_repo):
        """Should update metadata without re-uploading file."""
        key = f"{uuid4()}.md"
        minio_repo.upload_file(key, "Content", metadata={"version": "1"})

        # Update metadata
        new_metadata = {"version": "2", "updated": "true"}
        minio_repo.update_file_metadata(key, new_metadata)

        # Verify updated
        stat = minio_repo.get_file_metadata(key)
        assert stat.metadata["x-amz-meta-version"] == "2"
        assert stat.metadata["x-amz-meta-updated"] == "true"


class TestMinIORepositoryTierOperations:
    """Test tier-based operations."""

    def test_upload_to_tier(self, minio_client):
        """Should upload file to correct tier bucket."""
        prefix = f"test-{uuid4().hex[:8]}"
        repo = MinIORepository(client=minio_client)
        repo.create_tier_buckets(prefix=prefix)

        key = f"{uuid4()}.md"
        content = "High quality content"

        # Upload to tier-a
        result = repo.upload_to_tier(
            key=key,
            content=content,
            tier="tier-a",
            bucket_prefix=prefix
        )

        # Verify in correct bucket
        assert minio_client.bucket_exists(f"{prefix}-tier-a")
        objects = list(minio_client.list_objects(f"{prefix}-tier-a"))
        assert len(objects) == 1
        assert objects[0].object_name == key

        # Cleanup
        minio_client.remove_object(f"{prefix}-tier-a", key)
        for tier in ["tier-a", "tier-b", "tier-c", "tier-d"]:
            minio_client.remove_bucket(f"{prefix}-{tier}")

    def test_move_between_tiers(self, minio_client):
        """Should move file from one tier to another."""
        prefix = f"test-{uuid4().hex[:8]}"
        repo = MinIORepository(client=minio_client)
        repo.create_tier_buckets(prefix=prefix)

        key = f"{uuid4()}.md"
        content = "Content"

        # Upload to tier-c
        repo.upload_to_tier(key, content, "tier-c", prefix)

        # Move to tier-a (quality improved)
        repo.move_between_tiers(key, "tier-c", "tier-a", prefix)

        # Verify moved
        assert not minio_client.bucket_exists(f"{prefix}-tier-c") or \
               len(list(minio_client.list_objects(f"{prefix}-tier-c"))) == 0
        objects = list(minio_client.list_objects(f"{prefix}-tier-a"))
        assert len(objects) == 1
        assert objects[0].object_name == key

        # Cleanup
        minio_client.remove_object(f"{prefix}-tier-a", key)
        for tier in ["tier-a", "tier-b", "tier-c", "tier-d"]:
            try:
                minio_client.remove_bucket(f"{prefix}-{tier}")
            except:
                pass


class TestMinIORepositoryErrorHandling:
    """Test error handling and edge cases."""

    def test_file_exists_for_nonexistent_file(self, minio_repo):
        """Should return False for non-existent file."""
        assert not minio_repo.file_exists("nonexistent.md")

    def test_upload_empty_content(self, minio_repo):
        """Should handle empty content."""
        key = f"{uuid4()}.md"
        result = minio_repo.upload_file(key, "")

        assert result["key"] == key
        downloaded = minio_repo.download_file(key)
        assert downloaded == ""

    def test_get_metadata_for_nonexistent_file(self, minio_repo):
        """Should return None for non-existent file metadata."""
        stat = minio_repo.get_file_metadata("nonexistent.md")
        assert stat is None
