"""HTML extractor implementation for the pipeline."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.core.exceptions import ExtractionError
from app.core.models import RawContent
from app.core.types import ContentSource

from .base import ContentExtractor


class HTMLWebExtractor(ContentExtractor):
    """Retrieve and normalise HTML content from the public web."""

    def __init__(self, client: httpx.AsyncClient | None = None, *, timeout: float = 10.0):
        self._client = client
        self._timeout = timeout

    async def extract(self, url: str) -> RawContent:
        response = await self._fetch(url)
        return self._to_raw_content(url, response)

    async def _fetch(self, url: str) -> httpx.Response:
        try:
            if self._client is not None:
                response = await self._client.get(url)
            else:
                async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                    response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExtractionError(f"Failed to fetch content from {url}: {exc}") from exc

        return response

    def _to_raw_content(self, url: str, response: httpx.Response) -> RawContent:
        text = response.text
        content_type = response.headers.get("content-type", "").lower()

        metadata: dict[str, str] = {}
        extracted_text = text

        if "html" in content_type or text.lstrip().startswith("<"):
            extracted = trafilatura.extract(text, url=url, include_comments=False)
            if extracted:
                extracted_text = extracted
            title_tag = BeautifulSoup(text, "html.parser").find("title")
            if title_tag and title_tag.text.strip():
                metadata["title"] = title_tag.text.strip()

        if "title" not in metadata:
            metadata["title"] = self._default_title(url)

        cleaned = extracted_text.strip()
        if not cleaned:
            raise ExtractionError(f"No textual content could be extracted from {url}")

        first_line = cleaned.splitlines()[0].strip()
        metadata.setdefault("summary", first_line[:200])
        metadata.setdefault("content_type", content_type or "unknown")

        return RawContent(
            url=url,
            source_type=ContentSource.WEB,
            raw_text=cleaned,
            metadata=metadata,
            extracted_at=datetime.now(),
        )

    @staticmethod
    def _default_title(url: str) -> str:
        parsed = urlparse(url)
        candidate = parsed.path.rstrip("/").split("/")[-1]
        if not candidate:
            candidate = parsed.netloc or url
        return candidate or url
