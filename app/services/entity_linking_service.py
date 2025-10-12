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
        1. Fuzzy matches to find existing similar entities
        2. Finds or creates canonical Entity node
        3. Creates LINKED_TO relationship with confidence score
        4. Updates entity mention_count and aliases
        5. Returns canonical entity ID

        Args:
            mention_id: Mention ID to link
            canonical_name: Canonical name for the entity
            entity_type: Entity type (PERSON, ORG, etc.)

        Returns:
            Canonical entity ID
            
        Raises:
            ValueError: If mention_id does not exist
        """
        # Validate that mention exists
        mention_text = self._neo_repo.get_mention_text(mention_id)
        if mention_text is None:
            raise ValueError(f"Mention with id '{mention_id}' does not exist")
        
        # First, try to find an existing similar entity (fuzzy matching)
        similar_entity = self._find_similar_entity(canonical_name, entity_type)
        
        if similar_entity:
            # Use existing entity's ID
            entity_id = similar_entity["id"]
            # If entity already has canonical_name, use it; otherwise use the NEW canonical_name we're setting
            existing_canonical_name = similar_entity.get("canonical_name") or canonical_name
        else:
            # Generate new deterministic entity ID
            entity_id = generate_entity_id(canonical_name, entity_type)
            existing_canonical_name = canonical_name

        # Check if canonical entity already exists
        existing_entity = self._neo_repo.get_entity(entity_id)

        if existing_entity:
            # Entity exists - ensure it has canonical fields
            # (it might have been created by EntityExtractor without canonical_name)
            has_canonical = existing_entity.get("canonical_name") is not None
            
            if not has_canonical:
                # Add canonical fields to existing entity
                # Don't increment count - entity already has mention_count from creation
                self._neo_repo.create_canonical_entity(
                    entity_id=entity_id,
                    canonical_name=canonical_name,
                    entity_type=entity_type,
                    aliases=[canonical_name],
                )
            # Note: mention_count is already tracked by Sprint 5's create_entity
            # which increments on each create_entity_mention call
            
            # Calculate confidence between mention text and existing canonical name
            confidence = self._calculate_confidence(mention_text, existing_canonical_name)
            
            self._neo_repo.link_mention_to_entity(
                mention_id=mention_id,
                entity_id=entity_id,
                confidence=confidence,
            )
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
            # Calculate confidence between mention text and canonical name
            confidence = self._calculate_confidence(mention_text, canonical_name)
            
            self._neo_repo.link_mention_to_entity(
                mention_id=mention_id,
                entity_id=entity_id,
                confidence=confidence,
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
        """Calculate string similarity using substring and character matching.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        if not s1 or not s2:
            return 0.0

        # Check for exact match first
        if s1 == s2:
            return 1.0

        # Check for substring match (e.g., "openai" in "openai inc")
        shorter = s1 if len(s1) < len(s2) else s2
        longer = s2 if len(s1) < len(s2) else s1
        
        if shorter in longer:
            # Substring match - give high similarity score (0.85+)
            # Longer match = higher score
            return 0.85 + (len(shorter) / len(longer)) * 0.15
        
        # Check if they match when spaces removed (e.g., "open ai" vs "openai")
        s1_no_space = s1.replace(" ", "")
        s2_no_space = s2.replace(" ", "")
        
        if s1_no_space == s2_no_space:
            # Same text, just different spacing - high fuzzy match (0.95)
            return 0.95
        
        # Check substring without spaces
        shorter_no_space = s1_no_space if len(s1_no_space) < len(s2_no_space) else s2_no_space
        longer_no_space = s2_no_space if len(s1_no_space) < len(s2_no_space) else s1_no_space
        
        if shorter_no_space in longer_no_space:
            return 0.85 + (len(shorter_no_space) / len(longer_no_space)) * 0.10
        
        # Otherwise use character-level similarity
        common = sum(c1 == c2 for c1, c2 in zip(s1, s2))
        max_len = max(len(s1), len(s2))
        
        return common / max_len if max_len > 0 else 0.0

    def _find_similar_entity(
        self, canonical_name: str, entity_type: str
    ) -> dict[str, Any] | None:
        """Find existing entity with similar name (fuzzy matching).

        Args:
            canonical_name: Canonical name to search for
            entity_type: Entity type to filter by

        Returns:
            Existing entity dict or None if no match found
        """
        # Get all entities of this type
        all_entities = self._neo_repo.get_entities_by_type(entity_type)
        
        # Normalize the search name
        search_norm = self._normalize_text(canonical_name)
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for entity in all_entities:
            entity_name = entity.get("canonical_name") or entity.get("text", "")
            entity_norm = self._normalize_text(entity_name)
            
            # Calculate similarity
            similarity = self._string_similarity(search_norm, entity_norm)
            
            has_canonical = entity.get("canonical_name") is not None
            
            # If very similar (>80%), consider it a match
            # Prefer entities that already have canonical_name set (already linked)
            if similarity > 0.8:
                # Boost score for entities with canonical_name (prefer already-linked entities)
                effective_score = similarity + (0.1 if has_canonical else 0.0)
                
                if effective_score > best_score:
                    best_match = entity
                    best_score = effective_score
        return best_match
