"""Relation Extraction Service for Story S6-603.

Extracts relationships between entities using pattern matching and spaCy dependency parsing.
Supports: EMPLOYED_BY, FOUNDED, CITES, LOCATED_IN.
"""

import re
from typing import Any
import spacy
from datetime import datetime

from app.repositories.neo_repository import NeoRepository


class RelationExtractionService:
    """Service for extracting relationships between entities."""

    def __init__(self, neo_repo: NeoRepository):
        """Initialize relation extraction service.
        
        Args:
            neo_repo: Neo4j repository for storing relationships
        """
        self._neo_repo = neo_repo
        
        # Load spaCy model for dependency parsing
        try:
            self._nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback if model not loaded
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
            self._nlp = spacy.load("en_core_web_sm")
        
        # Define relation patterns
        self._patterns = {
            "EMPLOYED_BY": [
                r"\b(works? at|employed by|joined|employee of)\b",
            ],
            "FOUNDED": [
                r"\b(founded|started|established|created|co-founded)\b",
            ],
            "CITES": [
                r"\b(according to|referenced|cited|per|says)\b",
            ],
            "LOCATED_IN": [
                r"\b(based in|located in|headquartered in|in)\b",
            ],
        }

    def extract_relations(self, chunk_id: str) -> list[dict[str, Any]]:
        """Extract relationships from a chunk.
        
        Args:
            chunk_id: Chunk ID to extract relations from
            
        Returns:
            List of extracted relations with metadata
        """
        # Get chunk text and entities
        chunk = self._neo_repo.get_chunk(chunk_id)
        if not chunk:
            return []
        
        text = chunk.get("text", "")
        entities = self._get_chunk_entities(chunk_id)
        
        if len(entities) < 2:
            # Need at least 2 entities to form a relationship
            return []
        
        # Process text with spaCy
        doc = self._nlp(text)
        
        # Extract relations using pattern matching
        relations = []
        
        # Try each relation type
        for rel_type, patterns in self._patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Pattern found - try to extract relation
                    extracted = self._extract_relation_by_pattern(
                        text, doc, entities, rel_type, pattern, chunk_id
                    )
                    if extracted:
                        relations.extend(extracted)
        
        # Store relations in Neo4j
        for relation in relations:
            self._store_relation(relation)
        
        return relations

    def _get_chunk_entities(self, chunk_id: str) -> list[dict[str, Any]]:
        """Get all entities mentioned in a chunk.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            List of entity dictionaries with text, type, offsets
        """
        query = """
        MATCH (m:Mention)-[:FOUND_IN]->(c:Chunk {id: $chunk_id})
        MATCH (m)-[:REFERS_TO]->(e:Entity)
        RETURN e.text as text,
               e.entity_type as entity_type,
               e.id as entity_id,
               m.offset_in_chunk as offset
        ORDER BY m.offset_in_chunk
        """
        
        results = self._neo_repo.execute_query(query, {"chunk_id": chunk_id})
        return [dict(r) for r in results]

    def _extract_relation_by_pattern(
        self,
        text: str,
        doc: Any,  # spaCy Doc
        entities: list[dict[str, Any]],
        rel_type: str,
        pattern: str,
        chunk_id: str,
    ) -> list[dict[str, Any]]:
        """Extract relation using pattern matching.
        
        Args:
            text: Chunk text
            doc: spaCy Doc object
            entities: List of entities in chunk
            rel_type: Relationship type (EMPLOYED_BY, FOUNDED, etc.)
            pattern: Regex pattern that matched
            chunk_id: Source chunk ID
            
        Returns:
            List of extracted relations
        """
        relations = []
        
        # Find pattern match position
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return relations
        
        pattern_start = match.start()
        pattern_end = match.end()
        
        # Find entities before and after pattern
        subject = None
        object_entity = None
        
        for entity in entities:
            offset = entity["offset"]
            entity_end = offset + len(entity["text"])
            
            # Entity before pattern = subject
            if entity_end <= pattern_start:
                subject = entity
            # Entity after pattern = object
            elif offset >= pattern_end and object_entity is None:
                object_entity = entity
        
        # Handle passive voice for FOUNDED
        if rel_type == "FOUNDED" and "by" in text[pattern_start:pattern_end + 20].lower():
            # "OpenAI was founded by Sam Altman" - swap subject/object
            if subject and object_entity:
                subject, object_entity = object_entity, subject
        
        if subject and object_entity:
            # Calculate confidence based on pattern clarity
            confidence = self._calculate_relation_confidence(rel_type, match.group(0))
            
            # Extract temporal information if present
            temporal_info = self._extract_temporal_info(text)
            
            relation = {
                "type": rel_type,
                "subject_text": subject["text"],
                "subject_id": subject["entity_id"],
                "object_text": object_entity["text"],
                "object_id": object_entity["entity_id"],
                "confidence": confidence,
                "evidence_text": text,
                "source_chunk_id": chunk_id,
                "pattern_matched": match.group(0),
            }
            
            if temporal_info:
                relation.update(temporal_info)
            
            relations.append(relation)
        
        return relations

    def _calculate_relation_confidence(self, rel_type: str, matched_text: str) -> float:
        """Calculate confidence score for a relation.
        
        Args:
            rel_type: Relationship type
            matched_text: The text that matched the pattern
            
        Returns:
            Confidence score (0.5-1.0)
        """
        # Exact strong patterns get high confidence
        strong_patterns = {
            "FOUNDED": ["founded", "co-founded", "established"],
            "EMPLOYED_BY": ["works at", "employed by"],
            "LOCATED_IN": ["based in", "headquartered in"],
            "CITES": ["according to", "referenced"],
        }
        
        matched_lower = matched_text.lower().strip()
        
        if rel_type in strong_patterns:
            if any(pattern in matched_lower for pattern in strong_patterns[rel_type]):
                return 0.95
        
        # Weaker patterns
        if rel_type == "LOCATED_IN" and matched_lower == "in":
            return 0.7  # Ambiguous
        
        # Default medium confidence
        return 0.85

    def _extract_temporal_info(self, text: str) -> dict[str, str]:
        """Extract temporal information from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            Dictionary with year, month, date if found
        """
        temporal = {}
        
        # Extract year (4 digits)
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if year_match:
            temporal["year"] = year_match.group(0)
        
        return temporal

    def _store_relation(self, relation: dict[str, Any]) -> None:
        """Store a relationship in Neo4j.
        
        Args:
            relation: Relation dictionary with subject, object, type, confidence, etc.
        """
        query = f"""
        MATCH (subject:Entity {{id: $subject_id}})
        MATCH (object:Entity {{id: $object_id}})
        MERGE (subject)-[r:{relation['type']}]->(object)
        ON CREATE SET
            r.confidence = $confidence,
            r.evidence_text = $evidence_text,
            r.source_chunk_id = $source_chunk_id,
            r.extracted_at = datetime(),
            r.pattern_matched = $pattern_matched
        ON MATCH SET
            r.confidence = CASE 
                WHEN r.confidence < $confidence THEN $confidence 
                ELSE r.confidence 
            END
        RETURN r
        """
        
        params = {
            "subject_id": relation["subject_id"],
            "object_id": relation["object_id"],
            "confidence": relation["confidence"],
            "evidence_text": relation["evidence_text"],
            "source_chunk_id": relation["source_chunk_id"],
            "pattern_matched": relation.get("pattern_matched", ""),
        }
        
        # Add temporal info if present
        if "year" in relation:
            query = query.replace(
                "r.pattern_matched = $pattern_matched",
                "r.pattern_matched = $pattern_matched,\n            r.year = $year"
            )
            params["year"] = relation["year"]
        
        self._neo_repo.execute_write(query, params)

    def batch_extract_relations(self, chunk_ids: list[str]) -> list[dict[str, Any]]:
        """Extract relations from multiple chunks (batch processing).
        
        Args:
            chunk_ids: List of chunk IDs
            
        Returns:
            List of all extracted relations
        """
        all_relations = []
        
        for chunk_id in chunk_ids:
            relations = self.extract_relations(chunk_id)
            all_relations.extend(relations)
        
        return all_relations
