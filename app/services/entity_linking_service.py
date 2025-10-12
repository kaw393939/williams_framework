"""Entity Linking Service for Story S6-602: Canonical Entity Linking.

This service consolidates entity mentions across documents into canonical entities
using fuzzy matching, deduplication, and confidence scoring.

Responsibilities:
- Link mentions to canonical Entity nodes
- Fuzzy matching and normalization
- Confidence scoring (exact: 1.0, fuzzy: 0.8-0.99, context: 0.6-0.79)
- Entity deduplication across documents
- Batch linking for performance
"""

from typing import Any
from app.repositories.neo_repository import NeoRepository
from app.core.id_generator import generate_entity_id


class EntityLinkingService:
    """Service for linking entity mentions to canonical entities."""

    def __init__(self, neo_repo: NeoRepository):
        """Initialize entity linking service.

        Args:
            neo_repo: Neo4j repository for graph operations
        """
        self._neo_repo = neo_repo

    def link_mention(
        self,
        mention_id: str,
        canonical_name: str,
        entity_type: str,
    ) -> str:
        """Link a mention to a canonical entity.

        This method:
        1. Finds or creates canonical Entity node
        2. Creates LINKED_TO relationship with confidence score
        3. Updates entity mention_count and aliases
        4. Returns canonical entity ID

        Args:
            mention_id: Mention ID to link
            canonical_name: Canonical name for the entity
            entity_type: Entity type (PERSON, ORG, etc.)

        Returns:
            Canonical entity ID
        """
        # Generate deterministic entity ID (Sprint 5 convention)
        entity_id = generate_entity_id(canonical_name, entity_type)

        # Check if canonical entity already exists
        existing_entity = self._neo_repo.get_entity(entity_id)

        if existing_entity:
            # Entity exists - add link and update count
            confidence = self._calculate_confidence(canonical_name, canonical_name)
            self._neo_repo.link_mention_to_entity(
                mention_id=mention_id,
                entity_id=entity_id,
                confidence=confidence,
            )
            # Update mention count
            self._neo_repo.increment_entity_mention_count(entity_id)
            # Add to aliases if needed
            self._neo_repo.add_entity_alias(entity_id, canonical_name)
        else:
            # Create new canonical entity
            self._neo_repo.create_canonical_entity(
                entity_id=entity_id,
                canonical_name=canonical_name,
                entity_type=entity_type,
                aliases=[canonical_name],
            )
            # Link mention with exact confidence
            self._neo_repo.link_mention_to_entity(
                mention_id=mention_id,
                entity_id=entity_id,
                confidence=1.0,
            )

        return entity_id

    def batch_link_mentions(
        self, mentions: list[dict[str, Any]]
    ) -> list[str]:
        """Batch link multiple mentions to canonical entities.

        Args:
            mentions: List of dicts with keys: mention_id, canonical_name, entity_type

        Returns:
            List of canonical entity IDs
        """
        entity_ids = []
        
        for mention_dict in mentions:
            entity_id = self.link_mention(
                mention_id=mention_dict["mention_id"],
                canonical_name=mention_dict["canonical_name"],
                entity_type=mention_dict["entity_type"],
            )
            entity_ids.append(entity_id)
        
        return entity_ids

    def _calculate_confidence(self, mention_text: str, canonical_name: str) -> float:
        """Calculate confidence score for entity linking.

        Confidence levels:
        - 1.0: Exact match
        - 0.8-0.99: Fuzzy match (normalized strings similar)
        - 0.6-0.79: Context similarity (embeddings)

        Args:
            mention_text: Original mention text
            canonical_name: Canonical entity name

        Returns:
            Confidence score (0.6-1.0)
        """
        # Normalize both strings
        mention_norm = self._normalize_text(mention_text)
        canonical_norm = self._normalize_text(canonical_name)

        # Exact match after normalization
        if mention_norm == canonical_norm:
            return 1.0

        # Fuzzy match using character similarity
        similarity = self._string_similarity(mention_norm, canonical_norm)
        
        if similarity > 0.9:
            return 0.95  # Very close fuzzy match
        elif similarity > 0.8:
            return 0.85  # Close fuzzy match
        elif similarity > 0.7:
            return 0.75  # Moderate match
        else:
            return 0.65  # Context-based match

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text (lowercase, no extra whitespace)
        """
        return " ".join(text.lower().split())

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using character-level comparison.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        # Simple character-level similarity
        # (In production, could use Levenshtein distance or other algorithms)
        if not s1 or not s2:
            return 0.0

        # Count common characters
        common = sum(c1 == c2 for c1, c2 in zip(s1, s2))
        max_len = max(len(s1), len(s2))
        
        return common / max_len if max_len > 0 else 0.0
