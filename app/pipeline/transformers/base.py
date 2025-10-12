"""Base interfaces for transforming raw content in the ETL pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models import ProcessedContent, RawContent


class ContentTransformer(ABC):
    """Abstract base class for converting raw content into processed form."""

    @abstractmethod
    async def transform(self, raw_content: RawContent) -> ProcessedContent:
        """Transform *raw_content* into a :class:`ProcessedContent`."""
        raise NotImplementedError
