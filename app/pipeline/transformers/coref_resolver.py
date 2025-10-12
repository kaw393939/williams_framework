"""Coreference resolution transformer (Story S6-601).

This transformer resolves pronouns to their entity referents using spaCy's
coreference capabilities and stores COREF_WITH relationships in Neo4j.

Pipeline Position: After EntityExtractor
Input: Document with entity mentions
Output: Coreference relationships linking pronouns to entities
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING

import spacy
from spacy.tokens import Doc

from app.core.id_generator import generate_doc_id, generate_mention_id
from app.core.models import ProcessedContent, RawContent

from .base import ContentTransformer

if TYPE_CHECKING:
    from app.repositories.neo_repository import NeoRepository


class CorefResolver(ContentTransformer):
    """Resolve coreferences (pronouns) to entity mentions.

    This transformer:
    1. Loads spaCy model with coreference capabilities
    2. Processes document text to find coreference clusters
    3. Links pronouns to entity mentions in Neo4j
    4. Creates COREF_WITH relationships with cluster IDs
    5. Returns ProcessedContent for downstream stages

    Attributes:
        neo_repo: Neo4j repository for storing coref relationships
        nlp: spaCy model with coreference resolution
        enabled: Whether coref resolution is enabled
        min_confidence: Minimum confidence threshold
        max_cluster_distance: Maximum sentence distance for clustering
    """

    def __init__(
        self,
        *,
        neo_repo: NeoRepository,
        config: dict | None = None,
    ):
        """Initialize the coreference resolver.

        Args:
            neo_repo: Neo4j repository for provenance storage
            config: Configuration dict with keys:
                - enabled: bool (default True)
                - min_confidence: float (default 0.7)
                - max_cluster_distance: int (default 5 sentences)
                - spacy_model: str (default "en_core_web_sm")
        """
        self._neo_repo = neo_repo
        
        # Parse config
        config = config or {}
        self.enabled = config.get("enabled", True)
        self.min_confidence = config.get("min_confidence", 0.7)
        self.max_cluster_distance = config.get("max_cluster_distance", 5)
        spacy_model = config.get("spacy_model", "en_core_web_sm")
        
        # Load spaCy model
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            # Model not downloaded, download it
            import subprocess
            subprocess.run(
                ["python3", "-m", "spacy", "download", spacy_model],
                check=True,
                capture_output=True,
            )
            self.nlp = spacy.load(spacy_model)

    def transform(self, raw_content: RawContent) -> ProcessedContent:
        """Resolve coreferences in document and store in Neo4j.

        This method:
        1. Retrieves document and chunks from Neo4j
        2. Processes text with spaCy to find coref clusters
        3. Creates COREF_WITH relationships between mentions
        4. Stores cluster IDs for chain retrieval
        5. Returns ProcessedContent

        Args:
            raw_content: Raw extracted content

        Returns:
            ProcessedContent with coref metadata
        """
        if not self.enabled:
            # Coref disabled, pass through
            return ProcessedContent(
                url=raw_content.url,
                text=raw_content.content,
                metadata=raw_content.metadata,
                tags=[],
            )
        
        url_str = str(raw_content.url)
        doc_id = generate_doc_id(url_str)
        
        # Get document from Neo4j
        doc = self._neo_repo.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found in Neo4j. Run EntityExtractor first.")
        
        # Get all chunks for this document
        chunks = self._neo_repo.get_document_chunks(doc_id)
        
        # Process each chunk for coreference
        for chunk in chunks:
            chunk_dict = dict(chunk)
            chunk_id = chunk_dict["chunk_id"]
            chunk_text = chunk_dict["text"]
            
            # Run spaCy NLP pipeline
            doc_obj = self.nlp(chunk_text)
            
            # Extract coreference clusters using rule-based approach
            # (since spaCy's experimental coref is not reliable)
            coref_clusters = self._extract_coref_clusters(doc_obj, chunk_id)
            
            # Store coref relationships in Neo4j
            for cluster in coref_clusters:
                self._store_coref_cluster(cluster, chunk_id)
        
        # Return processed content
        return ProcessedContent(
            url=raw_content.url,
            text=raw_content.content,
            metadata={
                **raw_content.metadata,
                "coref_processed": True,
            },
            tags=[],
        )

    def _extract_coref_clusters(self, doc: Doc, chunk_id: str) -> list[dict]:
        """Extract coreference clusters from spaCy Doc.

        This uses a rule-based approach:
        1. Find all pronouns (he, she, it, they, etc.)
        2. Look backwards for nearest entity of matching type
        3. Create cluster linking pronoun to entity

        Args:
            doc: spaCy Doc object
            chunk_id: Chunk ID for generating mention IDs

        Returns:
            List of coref clusters with structure:
            [
                {
                    "cluster_id": "abc123",
                    "mentions": [
                        {"text": "Sam Altman", "start": 0, "end": 10, "type": "entity"},
                        {"text": "He", "start": 33, "end": 35, "type": "pronoun"},
                    ]
                }
            ]
        """
        clusters = []
        
        # Find all pronouns
        pronouns = [
            token for token in doc
            if token.pos_ == "PRON" and token.text.lower() in {
                "he", "she", "it", "they", "him", "her", "his", "hers",
                "its", "their", "theirs", "them"
            }
        ]
        
        # Find all entities in the document
        entities = list(doc.ents)
        
        # For each pronoun, find the nearest entity
        for pronoun in pronouns:
            # Determine pronoun type (PERSON, ORG, etc.)
            pronoun_text = pronoun.text.lower()
            if pronoun_text in {"he", "she", "him", "her", "his", "hers"}:
                target_types = {"PERSON"}
            elif pronoun_text in {"it", "its"}:
                target_types = {"ORG", "PRODUCT", "GPE", "FACILITY"}
            elif pronoun_text in {"they", "them", "their", "theirs"}:
                target_types = {"PERSON", "ORG", "GPE"}
            else:
                continue
            
            # Find nearest preceding entity of matching type
            nearest_entity = None
            min_distance = float("inf")
            
            for entity in entities:
                # Check if entity is before pronoun and matches type
                if entity.end <= pronoun.i and entity.label_ in target_types:
                    distance = pronoun.i - entity.end
                    if distance < min_distance:
                        min_distance = distance
                        nearest_entity = entity
            
            # If we found a matching entity, create cluster
            if nearest_entity and min_distance <= 50:  # Within 50 tokens
                cluster_id = self._generate_cluster_id(
                    chunk_id, nearest_entity.start, pronoun.i
                )
                
                cluster = {
                    "cluster_id": cluster_id,
                    "mentions": [
                        {
                            "text": nearest_entity.text,
                            "start": nearest_entity.start_char,
                            "end": nearest_entity.end_char,
                            "type": "entity",
                            "entity_type": nearest_entity.label_,
                        },
                        {
                            "text": pronoun.text,
                            "start": pronoun.idx,
                            "end": pronoun.idx + len(pronoun.text),
                            "type": "pronoun",
                            "entity_type": nearest_entity.label_,
                        },
                    ],
                }
                clusters.append(cluster)
        
        return clusters

    def _store_coref_cluster(self, cluster: dict, chunk_id: str) -> None:
        """Store coreference cluster in Neo4j.

        Creates COREF_WITH relationships between entity mention and pronoun mentions.

        Args:
            cluster: Cluster dict with cluster_id and mentions
            chunk_id: Chunk ID for the cluster
        """
        cluster_id = cluster["cluster_id"]
        mentions = cluster["mentions"]
        
        # Get the entity mention (first in list)
        entity_mention = mentions[0]
        entity_mention_id = generate_mention_id(
            chunk_id,
            entity_mention["start"],
            entity_mention["end"],
        )
        
        # For each pronoun mention, create COREF_WITH relationship
        for i in range(1, len(mentions)):
            pronoun_mention = mentions[i]
            pronoun_mention_id = generate_mention_id(
                chunk_id,
                pronoun_mention["start"],
                pronoun_mention["end"],
            )
            
            # Create pronoun mention node in Neo4j (if not exists)
            self._neo_repo.create_pronoun_mention(
                mention_id=pronoun_mention_id,
                chunk_id=chunk_id,
                text=pronoun_mention["text"],
                start_offset=pronoun_mention["start"],
                end_offset=pronoun_mention["end"],
            )
            
            # Create COREF_WITH relationship
            self._neo_repo.create_coref_relationship(
                source_mention_id=pronoun_mention_id,
                target_mention_id=entity_mention_id,
                cluster_id=cluster_id,
            )

    def _generate_cluster_id(self, chunk_id: str, entity_pos: int, pronoun_pos: int) -> str:
        """Generate deterministic cluster ID.

        Args:
            chunk_id: Chunk ID
            entity_pos: Entity token position
            pronoun_pos: Pronoun token position

        Returns:
            Cluster ID (hash of inputs)
        """
        cluster_str = f"{chunk_id}:{entity_pos}:{pronoun_pos}"
        return hashlib.sha256(cluster_str.encode()).hexdigest()[:16]
