"""PDF extractor implementation for the content pipeline."""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from app.core.exceptions import ExtractionError
from app.core.models import RawContent
from app.core.types import ContentSource

from .base import ContentExtractor


class PDFDocumentExtractor(ContentExtractor):
    """Retrieve and normalize textual content from PDF documents."""

    def __init__(self, client: httpx.AsyncClient | None = None, *, timeout: float = 10.0) -> None:
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
        except httpx.HTTPError as exc:  # pragma: no cover - exercised via unit tests
            raise ExtractionError(f"Failed to fetch PDF from {url}: {exc}") from exc

        return response

    def _to_raw_content(self, url: str, response: httpx.Response) -> RawContent:
        content_type = (response.headers.get("content-type") or "application/pdf").split(";")[0].lower()

        try:
            reader = PdfReader(io.BytesIO(response.content))
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ExtractionError(f"Failed to parse PDF from {url}: {exc}") from exc

        text = self._extract_text(reader)
        if not text:
            raise ExtractionError(f"No textual content could be extracted from PDF {url}")

        metadata = self._build_metadata(url, reader, text, content_type)

        return RawContent(
            url=url,
            source_type=ContentSource.PDF,
            raw_text=text,
            metadata=metadata,
            extracted_at=datetime.now(),
        )

    @staticmethod
    def _extract_text(reader: PdfReader) -> str:
        chunks: list[str] = []
        for page in getattr(reader, "pages", []):
            try:
                extracted = page.extract_text() or ""
            except Exception:  # pragma: no cover - extremely rare parsing failure
                extracted = ""
            cleaned = extracted.strip()
            if cleaned:
                chunks.append(cleaned)
        return "\n\n".join(chunks).strip()

    def _build_metadata(
        self,
        url: str,
        reader: PdfReader,
        text: str,
        content_type: str,
    ) -> dict[str, str | int]:
        pdf_metadata = getattr(reader, "metadata", {}) or {}

        title = self._clean_str(pdf_metadata.get("/Title")) or self._default_title(url)
        author = self._clean_str(pdf_metadata.get("/Author")) or "unknown"
        subject = self._clean_str(pdf_metadata.get("/Subject"))

        summary_source = next((line.strip() for line in text.splitlines() if line.strip()), text)
        summary = summary_source[:200]

        metadata: dict[str, str | int] = {
            "title": title,
            "author": author,
            "page_count": len(getattr(reader, "pages", [])),
            "summary": summary,
            "content_type": content_type,
        }
        if subject:
            metadata["subject"] = subject
        return metadata

    @staticmethod
    def _clean_str(value: object | None) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _default_title(url: str) -> str:
        parsed = urlparse(url)
        candidate = parsed.path.rstrip("/").split("/")[-1]
        if candidate:
            candidate = Path(candidate).stem or candidate
        if not candidate:
            candidate = parsed.netloc or url
        return candidate or url
