"""
MinIO Repository for S3-compatible object storage.

Manages file storage in MinIO with bucket organization and metadata support.
"""
from io import BytesIO
from typing import Any

from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error


class MinIORepository:
    """
    Repository for managing file storage in MinIO (S3-compatible).

    Provides methods for uploading, downloading, deleting files with metadata
    and tier-based bucket organization.
    """

    def __init__(
        self,
        client: Minio,
        bucket_name: str | None = None
    ):
        """
        Initialize MinIORepository.

        Args:
            client: MinIO client instance
            bucket_name: Default bucket name (created if doesn't exist)
        """
        self.client = client
        self.bucket_name = bucket_name

        # Create bucket if specified
        if bucket_name:
            self._ensure_bucket_exists(bucket_name)

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as e:
            # Bucket might have been created by another process
            if e.code != 'BucketAlreadyOwnedByYou':
                raise

    def create_tier_buckets(self, prefix: str = "librarian") -> None:
        """
        Create all tier buckets for quality-based organization.

        Args:
            prefix: Bucket name prefix (e.g., "librarian" -> "librarian-tier-a")
        """
        tiers = ["tier-a", "tier-b", "tier-c", "tier-d"]
        for tier in tiers:
            bucket_name = f"{prefix}-{tier}"
            self._ensure_bucket_exists(bucket_name)

    def upload_file(
        self,
        key: str,
        content: str | bytes,
        metadata: dict[str, str] | None = None,
        content_type: str = "text/markdown"
    ) -> dict[str, Any]:
        """
        Upload file to default bucket.

        Args:
            key: Object key/path in bucket
            content: File content (string or bytes)
            metadata: Optional metadata dict
            content_type: MIME type

        Returns:
            Dict with upload result (key, etag, etc.)
        """
        # Convert string to bytes if needed
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        # Create BytesIO object
        data = BytesIO(content_bytes)
        data_length = len(content_bytes)

        # Upload
        result = self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=key,
            data=data,
            length=data_length,
            content_type=content_type,
            metadata=metadata
        )

        return {
            "key": key,
            "etag": result.etag,
            "bucket": self.bucket_name,
            "version_id": result.version_id
        }

    def upload_to_tier(
        self,
        key: str,
        content: str | bytes,
        tier: str,
        bucket_prefix: str = "librarian",
        metadata: dict[str, str] | None = None,
        content_type: str = "text/markdown"
    ) -> dict[str, Any]:
        """
        Upload file to specific tier bucket.

        Args:
            key: Object key
            content: File content
            tier: Tier name (tier-a, tier-b, tier-c, tier-d)
            bucket_prefix: Bucket prefix
            metadata: Optional metadata
            content_type: MIME type

        Returns:
            Dict with upload result
        """
        bucket_name = f"{bucket_prefix}-{tier}"
        self._ensure_bucket_exists(bucket_name)

        # Convert string to bytes if needed
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        data = BytesIO(content_bytes)
        data_length = len(content_bytes)

        result = self.client.put_object(
            bucket_name=bucket_name,
            object_name=key,
            data=data,
            length=data_length,
            content_type=content_type,
            metadata=metadata
        )

        return {
            "key": key,
            "etag": result.etag,
            "bucket": bucket_name,
            "tier": tier
        }

    def download_file(
        self,
        key: str,
        as_bytes: bool = False
    ) -> str | bytes | None:
        """
        Download file from default bucket.

        Args:
            key: Object key
            as_bytes: Return bytes instead of string

        Returns:
            File content as string or bytes, None if not found
        """
        try:
            response = self.client.get_object(self.bucket_name, key)
            content = response.read()
            response.close()
            response.release_conn()

            if as_bytes:
                return content
            return content.decode('utf-8')
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise

    def delete_file(self, key: str) -> None:
        """
        Delete file from default bucket.

        Args:
            key: Object key
        """
        try:
            self.client.remove_object(self.bucket_name, key)
        except S3Error as e:
            if e.code != 'NoSuchKey':
                raise

    def delete_files(self, keys: list[str]) -> None:
        """
        Delete multiple files from default bucket.

        Args:
            keys: List of object keys
        """
        for key in keys:
            self.delete_file(key)

    def file_exists(self, key: str) -> bool:
        """
        Check if file exists in default bucket.

        Args:
            key: Object key

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket_name, key)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise

    def list_files(self, prefix: str = "") -> list[dict[str, Any]]:
        """
        List files in default bucket.

        Args:
            prefix: Optional prefix filter

        Returns:
            List of file info dicts
        """
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )

            files = []
            for obj in objects:
                files.append({
                    "key": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified
                })
            return files
        except S3Error:
            return []

    def get_file_metadata(self, key: str) -> Any | None:
        """
        Get file metadata and stats.

        Args:
            key: Object key

        Returns:
            StatObject or None if not found
        """
        try:
            return self.client.stat_object(self.bucket_name, key)
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise

    def update_file_metadata(
        self,
        key: str,
        metadata: dict[str, str]
    ) -> None:
        """
        Update file metadata without re-uploading content.

        Args:
            key: Object key
            metadata: New metadata dict
        """
        # MinIO requires copying object to update metadata
        source = CopySource(self.bucket_name, key)

        self.client.copy_object(
            bucket_name=self.bucket_name,
            object_name=key,
            source=source,
            metadata=metadata,
            metadata_directive="REPLACE"
        )

    def move_between_tiers(
        self,
        key: str,
        from_tier: str,
        to_tier: str,
        bucket_prefix: str = "librarian"
    ) -> None:
        """
        Move file from one tier bucket to another.

        Args:
            key: Object key
            from_tier: Source tier (e.g., "tier-c")
            to_tier: Destination tier (e.g., "tier-a")
            bucket_prefix: Bucket prefix
        """
        from_bucket = f"{bucket_prefix}-{from_tier}"
        to_bucket = f"{bucket_prefix}-{to_tier}"

        # Ensure destination bucket exists
        self._ensure_bucket_exists(to_bucket)

        # Copy to new tier
        source = CopySource(from_bucket, key)
        self.client.copy_object(
            bucket_name=to_bucket,
            object_name=key,
            source=source
        )

        # Delete from old tier
        self.client.remove_object(from_bucket, key)
