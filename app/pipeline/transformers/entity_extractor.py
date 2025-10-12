"""Entity extraction transformer with Neo4j mention tracking.

This transformer extracts named entities from chunked text and stores them
in Neo4j with full provenance tracking via mention relationships.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.id_generator import (
    generate_doc_id,
    generate_entity_id,
    generate_mention_id,
)
from app.core.models import ProcessedContent, RawContent

from .base import ContentTransformer

if TYPE_CHECKING:
    from app.intelligence.providers.abstract_llm import AbstractLLMProvider
    from app.repositories.neo_repository import NeoRepository


class EntityExtractor(ContentTransformer):
    """Extract entities from text with LLM and store mentions in Neo4j.

    This transformer:
    1. Retrieves chunks from Neo4j for a document
    2. Uses LLM to extract entities from each chunk
    3. Creates Entity nodes with type and confidence
    4. Creates Mention nodes linking chunks to entities
    5. Returns ProcessedContent for downstream stages

    Attributes:
        neo_repo: Neo4j repository for storing entities/mentions
        llm_provider: LLM provider for entity extraction
        entity_types: List of entity types to extract
    """

    def __init__(
        self,
        *,
        neo_repo: NeoRepository,
        llm_provider: AbstractLLMProvider | None = None,
        entity_types: list[str] | None = None,
    ):
        """Initialize the entity extractor.

        Args:
            neo_repo: Neo4j repository for provenance storage
            llm_provider: LLM provider for entity extraction (optional, uses fallback if None)
            entity_types: List of entity types to extract (default: PERSON, ORG, CONCEPT, LOCATION, DATE)
        """
        self._neo_repo = neo_repo
        self._llm_provider = llm_provider
        self._entity_types = entity_types or [
            "PERSON",
            "ORGANIZATION",
            "CONCEPT",
            "LOCATION",
            "DATE",
            "TECHNOLOGY",
        ]

    async def transform(self, raw_content: RawContent) -> ProcessedContent:
        """Extract entities from document chunks and store mentions in Neo4j.

        This method:
        1. Retrieves document and chunks from Neo4j
        2. Extracts entities from each chunk using LLM
        3. Creates Entity nodes with deterministic IDs
        4. Creates Mention nodes linking to chunks
        5. Returns ProcessedContent for downstream stages

        Args:
            raw_content: Raw extracted content

        Returns:
            ProcessedContent with extracted entities as tags
        """
        url_str = str(raw_content.url)

        # Generate document ID and retrieve chunks
        doc_id = generate_doc_id(url_str)

        # Get document from Neo4j
        doc = self._neo_repo.get_document(doc_id)
        if not doc:
            # Document doesn't exist yet - this transformer should run after chunker
            raise ValueError(f"Document {doc_id} not found in Neo4j. Run EnhancedChunker first.")

        # Get all chunks for this document
        chunks = self._neo_repo.get_document_chunks(doc_id)

        # Extract entities from each chunk
        all_entities = []
        for chunk in chunks:
            chunk_dict = dict(chunk)
            entities = await self._extract_entities_from_chunk(chunk_dict)
            all_entities.extend(entities)

            # Store each entity and mention in Neo4j
            for entity in entities:
                # Create entity node
                entity_id = generate_entity_id(entity["text"], entity["type"])
                self._neo_repo.create_entity(
                    entity_id=entity_id,
                    text=entity["text"],
                    entity_type=entity["type"],
                    confidence=entity.get("confidence"),
                )

                # Create mention node
                mention_id = generate_mention_id(
                    chunk_dict["id"],
                    entity["text"],
                    entity["offset"],
                )
                self._neo_repo.create_mention(
                    mention_id=mention_id,
                    chunk_id=chunk_dict["id"],
                    entity_id=entity_id,
                    offset_in_chunk=entity["offset"],
                    confidence=entity.get("confidence"),
                )

        # Generate ProcessedContent
        title = doc.get("title", "") or self._generate_title(url_str)
        summary = self._generate_summary(raw_content.raw_text)

        # Use entities as tags (unique entity texts)
        tags = list({e["text"] for e in all_entities})[:20]  # Limit to 20 tags

        # Import here to avoid circular dependency
        from app.core.models import ScreeningResult

        screening_result = ScreeningResult(
            screening_score=8.0,  # Higher score for entity-enriched content
            decision="ACCEPT",
            reasoning=f"Content enriched with {len(all_entities)} entities across {len(chunks)} chunks",
            estimated_quality=8.0,
        )

        return ProcessedContent(
            url=raw_content.url,
            source_type=raw_content.source_type,
            title=title,
            summary=summary,
            key_points=[],
            tags=tags,
            screening_result=screening_result,
            processed_at=datetime.now(),
        )

    async def _extract_entities_from_chunk(self, chunk: dict) -> list[dict]:
        """Extract entities from a single chunk using LLM.

        Args:
            chunk: Chunk dictionary with 'text' field

        Returns:
            List of entity dictionaries with text, type, offset, confidence
        """
        text = chunk.get("text", "")
        if not text:
            return []

        # If no LLM provider, use simple pattern-based extraction
        if not self._llm_provider:
            return self._fallback_entity_extraction(text)

        # Use LLM for entity extraction
        prompt = self._build_entity_extraction_prompt(text)

        try:
            response = await self._llm_provider.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.0,  # Deterministic for entity extraction
            )

            # Parse LLM response into entity list
            entities = self._parse_llm_entities(response, text)
            return entities

        except Exception:
            # Fallback to pattern-based on LLM error
            return self._fallback_entity_extraction(text)

    def _build_entity_extraction_prompt(self, text: str) -> str:
        """Build LLM prompt for entity extraction.

        Args:
            text: Chunk text

        Returns:
            Prompt string
        """
        types_str = ", ".join(self._entity_types)

        return f"""Extract named entities from the following text. For each entity, provide:
1. The exact text of the entity
2. The entity type ({types_str})
3. Character offset where it appears (0-indexed)

Text:
{text}

Format your response as JSON list:
[
  {{"text": "entity name", "type": "TYPE", "offset": 0}},
  ...
]

Only return the JSON array, no other text."""

    def _parse_llm_entities(self, response: str, chunk_text: str) -> list[dict]:
        """Parse LLM response into entity list.

        Args:
            response: LLM response text
            chunk_text: Original chunk text for validation

        Returns:
            List of entity dictionaries
        """
        import json

        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                return []

            entities_raw = json.loads(json_match.group())

            # Validate and enhance entities
            entities = []
            for entity in entities_raw:
                if not isinstance(entity, dict):
                    continue

                text = entity.get("text", "").strip()
                entity_type = entity.get("type", "").upper()

                # Validate entity exists in text
                if text and text in chunk_text:
                    # Find actual offset if not provided or incorrect
                    actual_offset = chunk_text.find(text)
                    if actual_offset == -1:
                        # Try case-insensitive
                        actual_offset = chunk_text.lower().find(text.lower())

                    if actual_offset >= 0:
                        entities.append({
                            "text": text,
                            "type": entity_type or "UNKNOWN",
                            "offset": actual_offset,
                            "confidence": 0.9,  # High confidence from LLM
                        })

            return entities

        except (json.JSONDecodeError, ValueError):
            return []

    def _fallback_entity_extraction(self, text: str) -> list[dict]:
        """Simple pattern-based entity extraction as fallback.

        Extracts:
        - Capitalized sequences (potential names/organizations)
        - Years and dates
        - Quoted terms (potential concepts)

        Args:
            text: Chunk text

        Returns:
            List of entity dictionaries
        """
        entities = []

        # Extract capitalized sequences (2+ words, excluding common words)
        stopwords = {"The", "A", "An", "In", "On", "At", "To", "For", "Of", "And", "Or", "But"}
        capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'

        for match in re.finditer(capitalized_pattern, text):
            entity_text = match.group()
            # Skip if starts with stopword
            if entity_text.split()[0] not in stopwords:
                entities.append({
                    "text": entity_text,
                    "type": "PERSON",  # Guess PERSON for capitalized sequences
                    "offset": match.start(),
                    "confidence": 0.5,  # Lower confidence for pattern-based
                })

        # Extract years
        year_pattern = r'\b(19|20)\d{2}\b'
        for match in re.finditer(year_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "DATE",
                "offset": match.start(),
                "confidence": 0.8,
            })

        # Extract quoted terms
        quoted_pattern = r'"([^"]+)"'
        for match in re.finditer(quoted_pattern, text):
            entities.append({
                "text": match.group(1),
                "type": "CONCEPT",
                "offset": match.start() + 1,  # +1 to skip opening quote
                "confidence": 0.6,
            })

        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity["text"], entity["type"])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

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
