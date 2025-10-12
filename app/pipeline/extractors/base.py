"""Base interfaces for content extractors used in the ETL pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models import RawContent


class ContentExtractor(ABC):
    """Abstract base class for retrieving raw content from a source."""

    @abstractmethod
    async def extract(self, url: str) -> RawContent:
        """Fetch raw content for the given *url*."""
        raise NotImplementedError
