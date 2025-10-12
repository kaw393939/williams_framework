"""Loader implementation that persists processed content to storage backends."""
from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.models import LibraryFile, ProcessedContent
from app.core.types import ContentSource
from app.core.exceptions import StorageError
from app.core.telemetry import log_event
from app.intelligence.embeddings import generate_embedding

from .base import ContentLoader


class LibraryContentLoader(ContentLoader):
    """Persist processed content across storage backends and return metadata."""

    def __init__(
        self,
        postgres_repo: Any,
        redis_repo: Any,
        qdrant_repo: Any,
        minio_repo: Any,
        *,
        bucket_prefix: str = "librarian",
        cache_ttl: int = 60 * 60,
    ) -> None:
        self.postgres_repo = postgres_repo
        self.redis_repo = redis_repo
        self.qdrant_repo = qdrant_repo
        self.minio_repo = minio_repo
        self.bucket_prefix = bucket_prefix
        self.cache_ttl = cache_ttl

    async def load(self, processed: ProcessedContent) -> LibraryFile:
        record_id = str(uuid4())
        await self.postgres_repo.create_processing_record(
            record_id=record_id,
            content_url=str(processed.url),
            operation="store",
            status="started",
        )

        try:
            tier = self._tier_for_quality(processed.screening_result.estimated_quality)
            file_key = self._build_file_key(str(processed.url))
            markdown_content = self._render_markdown(processed, tier)

            try:
                await self._run_blocking(
                    self.minio_repo.upload_to_tier,
                    key=file_key,
                    content=markdown_content,
                    tier=tier,
                    bucket_prefix=self.bucket_prefix,
                    metadata={
                        "title": processed.title,
                        "quality_score": f"{processed.screening_result.estimated_quality:.2f}",
                        "source_type": processed.source_type.value if isinstance(processed.source_type, ContentSource) else str(processed.source_type),
                    },
                )
            except Exception as minio_exc:
                log_event({
                    "event_type": "storage.minio.failure",
                    "stage": "loader",
                    "operation": "upload_to_tier",
                    "bucket": f"{self.bucket_prefix}-{tier}",
                    "key": file_key,
                    "error_message": str(minio_exc),
                    "exception_type": type(minio_exc).__name__,
                })
                raise

            embedding = await generate_embedding(processed.summary)
            content_id = hashlib.md5(str(processed.url).encode("utf-8")).hexdigest()

            await self._run_blocking(
                self.qdrant_repo.add,
                content_id=content_id,
                vector=embedding,
                metadata={
                    "url": str(processed.url),
                    "title": processed.title,
                    "quality_score": processed.screening_result.estimated_quality,
                    "tags": processed.tags,
                    "tier": tier,
                },
            )

            cache_payload = processed.model_dump(mode="json")
            await self.redis_repo.set_json(
                self._cache_key(content_id),
                cache_payload,
                ttl=self.cache_ttl,
            )

            library_file = LibraryFile(
                file_path=Path(f"library/{tier}/{file_key}"),
                url=processed.url,
                source_type=processed.source_type,
                tier=tier,
                quality_score=processed.screening_result.estimated_quality,
                title=processed.title,
                tags=processed.tags,
            )

            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="completed",
            )

            return library_file

        except Exception as exc:  # pragma: no cover - error path validated in tests
            log_event({
                "event_type": "pipeline.error",
                "stage": "loader",
                "operation": "store",
                "content_url": str(processed.url),
                "error_message": str(exc),
                "exception_type": type(exc).__name__,
            })
            await self.postgres_repo.update_processing_record_status(
                record_id=record_id,
                status="failed",
                error_message=str(exc),
            )
            raise StorageError(f"Failed to store processed content: {exc}") from exc

    async def _run_blocking(self, func: Any, /, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def _tier_for_quality(quality: float) -> str:
        if quality >= 9.0:
            return "tier-a"
        if quality >= 7.0:
            return "tier-b"
        if quality >= 5.0:
            return "tier-c"
        return "tier-d"

    @staticmethod
    def _build_file_key(url: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")
        if not slug:
            slug = "content"
        return f"{slug}.md"

    @staticmethod
    def _render_markdown(processed: ProcessedContent, tier: str) -> str:
        lines = [
            f"# {processed.title}",
            "",
            f"- Source: {processed.url}",
            f"- Tier: {tier}",
            f"- Quality Score: {processed.screening_result.estimated_quality:.2f}",
            f"- Decision: {processed.screening_result.decision}",
            f"- Tags: {', '.join(processed.tags) if processed.tags else 'none'}",
            "",
            "## Summary",
            processed.summary,
            "",
        ]

        if processed.key_points:
            lines.append("## Key Points")
            for point in processed.key_points:
                lines.append(f"- {point}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _cache_key(content_id: str) -> str:
        return f"processed:{content_id}"
