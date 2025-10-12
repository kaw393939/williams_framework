"""Base interfaces for storing processed content via the ETL pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models import LibraryFile, ProcessedContent


class ContentLoader(ABC):
    """Abstract base class responsible for persisting processed content."""

    @abstractmethod
    async def load(self, processed: ProcessedContent) -> LibraryFile | None:
        """Persist *processed* content and optionally return the resulting library item."""
        raise NotImplementedError
