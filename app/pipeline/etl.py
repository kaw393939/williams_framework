"""Orchestration helpers for the ETL content pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.core.models import LibraryFile, ProcessedContent, RawContent

from .extractors.base import ContentExtractor
from .loaders.base import ContentLoader
from .transformers.base import ContentTransformer


@dataclass(slots=True)
class PipelineResult:
    """Outcome returned by :class:`ContentPipeline.run`."""

    raw_content: RawContent
    processed_content: ProcessedContent
    load_result: Optional[LibraryFile]


class ContentPipeline:
    """Coordinates extractor, transformer, and loader stages with optional plugin support."""

    def __init__(
        self,
        *,
        extractor: Optional[ContentExtractor] = None,
        transformer: Optional[ContentTransformer] = None,
        loader: Optional[ContentLoader] = None,
        plugin_registry: Optional[Any] = None,
    ) -> None:
        self._extractor = extractor
        self._transformer = transformer
        self._loader = loader
        self._plugin_registry = plugin_registry
        self._initialized = False

    @property
    def extractor(self) -> Optional[ContentExtractor]:
        return self._extractor

    @property
    def transformer(self) -> Optional[ContentTransformer]:
        return self._transformer

    @property
    def loader(self) -> Optional[ContentLoader]:
        return self._loader

    async def initialize(self) -> None:
        """Initialize the pipeline and execute plugin on_load hooks."""
        from app.core.config import get_settings
        from app.core.telemetry import log_event

        if self._initialized:
            return

        settings = get_settings()

        if self._plugin_registry and settings.enable_plugins:
            plugins = self._plugin_registry.all()
            for plugin in plugins:
                context = {"pipeline": "initialized"}
                result = await plugin.on_load(context)

                # Support both dict and object responses
                if isinstance(result, dict):
                    plugin_id = result.get("plugin_id")
                    event = result.get("event")
                    payload = result.get("payload")
                else:
                    plugin_id = result.plugin_id
                    event = result.event
                    payload = result.payload

                log_event({
                    "event_type": "plugin.on_load",
                    "timestamp": None,
                    "plugin_id": plugin_id,
                    "event": event,
                    "payload": payload,
                })

        self._initialized = True

    async def before_store(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute plugin before_store hooks and return modified content."""
        from app.core.config import get_settings
        from app.core.telemetry import log_event

        modified_content = content
        settings = get_settings()

        if self._plugin_registry and settings.enable_plugins:
            plugins = self._plugin_registry.all()
            for plugin in plugins:
                result = await plugin.before_store(modified_content)

                # Support both dict and object responses
                if isinstance(result, dict):
                    plugin_id = result.get("plugin_id")
                    event = result.get("event")
                    payload = result.get("payload")
                else:
                    plugin_id = result.plugin_id
                    event = result.event
                    payload = result.payload

                modified_content = payload

                log_event({
                    "event_type": "plugin.before_store",
                    "timestamp": None,
                    "plugin_id": plugin_id,
                    "event": event,
                    "payload": payload,
                })

        return modified_content

    async def run(self, url: str) -> PipelineResult:
        """Execute the pipeline for *url* and return the aggregated result, emitting telemetry on errors."""
        from app.core.telemetry import log_event
        try:
            try:
                raw_content = await self._extractor.extract(url)
            except Exception as exc:
                log_event({
                    "event_type": "pipeline.error",
                    "timestamp": None,  # log_event will fill
                    "stage": "extractor",
                    "operation": "extract",
                    "content_url": url,
                    "error_message": str(exc),
                    "exception_type": type(exc).__name__,
                })
                raise

            try:
                processed_content = await self._transformer.transform(raw_content)
            except Exception as exc:
                log_event({
                    "event_type": "pipeline.error",
                    "timestamp": None,
                    "stage": "transformer",
                    "operation": "transform",
                    "content_url": url,
                    "error_message": str(exc),
                    "exception_type": type(exc).__name__,
                })
                raise

            try:
                load_result = await self._loader.load(processed_content)
            except Exception as exc:
                log_event({
                    "event_type": "pipeline.error",
                    "timestamp": None,
                    "stage": "loader",
                    "operation": "load",
                    "content_url": url,
                    "error_message": str(exc),
                    "exception_type": type(exc).__name__,
                })
                raise

            return PipelineResult(
                raw_content=raw_content,
                processed_content=processed_content,
                load_result=load_result,
            )
        except Exception:
            # Let the error propagate after telemetry
            raise
