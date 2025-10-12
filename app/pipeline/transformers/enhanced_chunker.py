"""Enhanced chunker with Neo4j provenance tracking.

This chunker implements semantic chunking with byte-level offset tracking,
storing chunks in Neo4j with deterministic IDs for full provenance.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.id_generator import generate_chunk_id, generate_doc_id
from app.core.models import ProcessedContent, RawContent, ScreeningResult

from .base import ContentTransformer

if TYPE_CHECKING:
    from app.repositories.neo_repository import NeoRepository


class EnhancedChunker(ContentTransformer):
    """Semantic chunker with Neo4j provenance tracking.

    This transformer:
    1. Generates deterministic document IDs
    2. Chunks text with byte-level offset tracking
    3. Stores Document and Chunk nodes in Neo4j
    4. Returns ProcessedContent for downstream pipeline stages

    Attributes:
        neo_repo: Neo4j repository for storing provenance
        chunk_size: Target size for each chunk (characters)
        chunk_overlap: Overlap between chunks (characters)
    """

    def __init__(
        self,
        *,
        neo_repo: NeoRepository,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """Initialize the enhanced chunker.

        Args:
            neo_repo: Neo4j repository for provenance storage
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self._neo_repo = neo_repo
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def transform(self, raw_content: RawContent) -> ProcessedContent:
        """Transform raw content into chunks with Neo4j provenance.

        This method:
        1. Generates deterministic document ID from URL
        2. Creates Document node in Neo4j
        3. Chunks text with semantic boundaries (sentences/paragraphs)
        4. Tracks byte offsets for each chunk
        5. Creates Chunk nodes with PART_OF→Document relationships
        6. Returns ProcessedContent for downstream stages

        Args:
            raw_content: Raw extracted content

        Returns:
            ProcessedContent with title, summary, and screening result
        """
        url_str = str(raw_content.url)
        text = raw_content.raw_text.strip()

        # Generate deterministic document ID
        doc_id = generate_doc_id(url_str)

        # Generate title early so we can use it for the document node
        title = raw_content.metadata.get("title") or self._generate_title(url_str)

        # Create Document node in Neo4j
        doc_metadata = {
            "source_type": raw_content.source_type,
            "extracted_at": raw_content.extracted_at.isoformat(),
            **raw_content.metadata,
        }

        self._neo_repo.create_document(
            doc_id=doc_id,
            url=url_str,
            title=title,
            metadata=doc_metadata,
        )

        # Chunk text with byte offset tracking
        chunks = self._chunk_text(text)

        # Store chunks in Neo4j
        for chunk_data in chunks:
            chunk_id = generate_chunk_id(doc_id, chunk_data["start_offset"])

            self._neo_repo.create_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=chunk_data["text"],
                start_offset=chunk_data["start_offset"],
                end_offset=chunk_data["end_offset"],
            )

        # Generate summary for ProcessedContent (title already generated above)
        summary = self._generate_summary(text)

        # Create screening result (accept for now, can enhance later)
        screening_result = ScreeningResult(
            screening_score=7.0,
            decision="ACCEPT",
            reasoning="Content chunked and stored with provenance tracking",
            estimated_quality=7.0,
        )

        return ProcessedContent(
            url=raw_content.url,
            source_type=raw_content.source_type,
            title=title,
            summary=summary,
            key_points=[],
            tags=[],
            screening_result=screening_result,
            processed_at=datetime.now(),
        )

    def _chunk_text(self, text: str) -> list[dict]:
        """Chunk text with semantic boundaries and byte offset tracking.

        This uses a sliding window approach with:
        - Paragraph boundaries (double newline) as primary split points
        - Sentence boundaries (period + space) as secondary split points
        - Byte-level offset tracking for provenance

        Args:
            text: Text to chunk

        Returns:
            List of chunk dictionaries with text, start_offset, end_offset, index
        """
        if not text:
            return []

        # Convert text to bytes for accurate offset tracking
        text_bytes = text.encode('utf-8')

        chunks = []
        current_byte_offset = 0
        chunk_index = 0

        while current_byte_offset < len(text_bytes):
            # Calculate chunk end with overlap
            chunk_end = min(
                current_byte_offset + self._chunk_size,
                len(text_bytes)
            )

            # Extract chunk bytes
            chunk_bytes = text_bytes[current_byte_offset:chunk_end]

            # Find semantic boundary if not at end
            if chunk_end < len(text_bytes):
                chunk_bytes = self._find_semantic_boundary(
                    text_bytes,
                    current_byte_offset,
                    chunk_end,
                )

            # Decode chunk text
            chunk_text = chunk_bytes.decode('utf-8', errors='ignore')
            chunk_end_offset = current_byte_offset + len(chunk_bytes)

            chunks.append({
                "text": chunk_text,
                "start_offset": current_byte_offset,
                "end_offset": chunk_end_offset,
                "index": chunk_index,
            })

            # Prevent infinite loop - must make forward progress
            if len(chunk_bytes) == 0:
                break

            # Move to next chunk with overlap
            next_offset = chunk_end_offset - self._chunk_overlap

            # Ensure we always move forward (no infinite loops)
            if next_offset <= current_byte_offset:
                next_offset = current_byte_offset + 1

            # If we've reached the end, stop
            if next_offset >= len(text_bytes):
                break

            current_byte_offset = next_offset
            chunk_index += 1

        return chunks

    def _find_semantic_boundary(
        self,
        text_bytes: bytes,
        start: int,
        end: int,
    ) -> bytes:
        """Find semantic boundary (paragraph or sentence) near chunk end.

        Args:
            text_bytes: Full text as bytes
            start: Start byte offset of chunk
            end: Target end byte offset

        Returns:
            Chunk bytes ending at semantic boundary
        """
        chunk_bytes = text_bytes[start:end]

        # Look for paragraph boundary (double newline)
        paragraph_match = None
        for match in re.finditer(rb'\n\n', chunk_bytes):
            paragraph_match = match

        if paragraph_match:
            return chunk_bytes[:paragraph_match.end()]

        # Look for sentence boundary (. followed by space or newline)
        sentence_match = None
        for match in re.finditer(rb'\.\s', chunk_bytes):
            sentence_match = match

        if sentence_match:
            return chunk_bytes[:sentence_match.end()]

        # No semantic boundary found, return full chunk
        return chunk_bytes

    def _generate_title(self, url: str) -> str:
        """Generate title from URL.

        Args:
            url: Content URL

        Returns:
            Generated title
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc or "Unknown"
        return f"Content from {domain}"

    def _generate_summary(self, text: str) -> str:
        """Generate basic summary from text.

        Args:
            text: Full text content

        Returns:
            Summary (first 400 characters)
        """
        max_length = 400
        if len(text) <= max_length:
            return text

        # Try to break at sentence boundary
        summary = text[:max_length]
        last_period = summary.rfind('.')

        if last_period > max_length // 2:
            return summary[:last_period + 1]

        return summary + "..."
