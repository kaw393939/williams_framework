"""Relation Extractor Transformer for ETL Pipeline.

Extracts relationships between entities in document chunks.
Part of Story S6-603: Relation Extraction.
"""

from typing import Any
from app.repositories.neo_repository import NeoRepository
from app.services.relation_extraction_service import RelationExtractionService


class RelationExtractor:
    """Transformer that extracts relations between entities."""

    def __init__(self, neo_repo: NeoRepository):
        """Initialize relation extractor.
        
        Args:
            neo_repo: Neo4j repository for storing relations
        """
        self._relation_service = RelationExtractionService(neo_repo)
        self._neo_repo = neo_repo

    def transform(self, chunks: list[Any]) -> list[Any]:
        """Extract relations from chunks.
        
        Args:
            chunks: List of document chunks with entities
            
        Returns:
            Same chunks (relations stored in Neo4j as side effect)
        """
        for chunk in chunks:
            # Extract relations for each chunk
            self._relation_service.extract_relations(chunk.id)
        
        return chunks
