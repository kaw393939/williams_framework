"""Command-line entry point for running the content pipeline."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO
from urllib.parse import urlparse

from app.core.models import LibraryFile, ProcessedContent, RawContent

from .etl import ContentPipeline, PipelineResult
from .extractors import HTMLWebExtractor, PDFDocumentExtractor
from .extractors.youtube import YouTubeExtractor
from .transformers import BasicContentTransformer
from .loaders import LibraryContentLoader


async def run_pipeline(url: str, *, pipeline: ContentPipeline | None = None) -> PipelineResult:
    """Execute the pipeline for *url* using the provided or default pipeline."""

    pipeline = pipeline or build_pipeline_for_url(url)
    return await pipeline.run(url)


def build_default_pipeline() -> ContentPipeline:
    """Build a pipeline wired with default extractor, transformer, and loader."""

    return ContentPipeline(
        extractor=HTMLWebExtractor(),
        transformer=BasicContentTransformer(),
        loader=_build_loader(),
    )


def build_pipeline_for_url(url: str) -> ContentPipeline:
    """Build a pipeline that routes to the appropriate extractor for *url*."""

    def _looks_like_youtube(url: str) -> bool:
        parsed = urlparse(url)
        return (
            "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc
        )

    if _looks_like_pdf(url):
        extractor = PDFDocumentExtractor()
    elif _looks_like_youtube(url):
        extractor = YouTubeExtractor()
    else:
        extractor = HTMLWebExtractor()
    transformer = BasicContentTransformer()
    loader = _build_loader()
    return ContentPipeline(extractor=extractor, transformer=transformer, loader=loader)


def _build_loader() -> LibraryContentLoader:
    postgres_repo = _InMemoryProcessingRepository()
    redis_repo = _InMemoryCache()
    qdrant_repo = _LocalVectorStore()
    minio_repo = _LocalObjectStore(root=Path("data/library"))

    return LibraryContentLoader(
        postgres_repo=postgres_repo,
        redis_repo=redis_repo,
        qdrant_repo=qdrant_repo,
        minio_repo=minio_repo,
    )


def _looks_like_pdf(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return path.endswith(".pdf") or ".pdf" in path


def format_result(result: PipelineResult, *, output_format: str = "text") -> str:
    """Format *result* for console output."""

    if output_format == "json":
        payload = {
            "raw": result.raw_content.model_dump(mode="json"),
            "processed": result.processed_content.model_dump(mode="json"),
            "library_file": result.load_result.model_dump(mode="json") if result.load_result else None,
        }
        return json.dumps(payload, indent=2)

    lines = [
        f"URL: {result.raw_content.url}",
        f"Title: {result.processed_content.title}",
        f"Summary: {result.processed_content.summary[:200]}",
        f"Tags: {', '.join(result.processed_content.tags) if result.processed_content.tags else 'none'}",
    ]

    if result.load_result:
        lines.append(f"Stored at: {result.load_result.file_path}")

    return "\n".join(lines)


def main(
    argv: Iterable[str] | None = None,
    *,
    pipeline_factory: Callable[[], ContentPipeline] | None = None,
    stream: TextIO | None = None,
) -> int:
    """CLI entry point. Returns process exit code."""

    parser = argparse.ArgumentParser(description="Run the Williams Librarian content pipeline")
    parser.add_argument("url", nargs="+", help="URL(s) to ingest")
    parser.add_argument("--json", action="store_true", help="Emit pipeline result as JSON")
    args = parser.parse_args(list(argv) if argv is not None else None)

    target_stream = stream or sys.stdout
    urls = args.url if isinstance(args.url, list) else [args.url]

    # Single URL mode (backward compatibility)
    if len(urls) == 1:
        factory = pipeline_factory or (lambda: build_pipeline_for_url(urls[0]))
        try:
            pipeline = factory()
            result = asyncio.run(run_pipeline(urls[0], pipeline=pipeline))
        except Exception as exc:  # pragma: no cover - exercised via test asserting exit != 0
            print(f"Pipeline execution failed for {urls[0]}: {exc}", file=sys.stderr)
            return 1

        output_format = "json" if args.json else "text"
        print(format_result(result, output_format=output_format), file=target_stream)
        return 0

    # Batch mode (multiple URLs)
    results = []
    for url in urls:
        factory = pipeline_factory or (lambda: build_pipeline_for_url(url))
        try:
            pipeline = factory()
            result = asyncio.run(run_pipeline(url, pipeline=pipeline))
            results.append({
                "url": url,
                "status": "success",
                "result": result
            })
        except Exception as exc:
            results.append({
                "url": url,
                "status": "error",
                "error_message": str(exc)
            })
            print(f"Pipeline execution failed for {url}: {exc}", file=sys.stderr)

    # Calculate summary
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful

    # Format output
    if args.json:
        output = {
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed
            },
            "results": [
                {
                    "url": r["url"],
                    "status": r["status"],
                    **({"library_file": r["result"].load_result.model_dump(mode="json")} if r["status"] == "success" and r["result"].load_result else {}),
                    **({"error_message": r["error_message"]} if r["status"] == "error" else {})
                }
                for r in results
            ]
        }
        print(json.dumps(output, indent=2), file=target_stream)
    else:
        print(f"\nBatch Summary: {successful}/{len(results)} successful, {failed} failed", file=target_stream)
        for r in results:
            if r["status"] == "success":
                print(f"✓ {r['url']}", file=target_stream)
            else:
                print(f"✗ {r['url']}: {r['error_message']}", file=target_stream)

    return 1 if failed > 0 else 0


class _InMemoryProcessingRepository:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    async def create_processing_record(self, **payload: Any) -> None:
        self.records.append({**payload})

    async def update_processing_record_status(self, **payload: Any) -> None:
        self.records.append({**payload})


class _InMemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.values[key] = {"value": value, "ttl": ttl}


class _LocalVectorStore:
    def __init__(self) -> None:
        self.points: list[dict[str, Any]] = []

    def add(self, *, content_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        self.points.append(
            {
                "content_id": content_id,
                "vector": vector,
                "metadata": metadata,
            }
        )


class _LocalObjectStore:
    def __init__(self, *, root: Path) -> None:
        self.root = root

    def upload_to_tier(
        self,
        *,
        key: str,
        content: str | bytes,
        tier: str,
        bucket_prefix: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        tier_dir = self.root / tier
        tier_dir.mkdir(parents=True, exist_ok=True)
        path = tier_dir / key
        data = content.encode("utf-8") if isinstance(content, str) else content
        path.write_bytes(data)
        return {"key": key, "bucket": f"{bucket_prefix}-{tier}", "metadata": metadata or {}}
