"""Integration tests for coreference resolution (Story S6-601).

Tests the CorefResolver transformer that resolves pronouns to entities
using spaCy coreference capabilities and stores COREF_WITH relationships in Neo4j.

TDD Approach: RED-GREEN-REFACTOR
- Write failing tests first
- Implement CorefResolver to make tests pass
- Refactor for clarity and performance
- NO MOCKS: Real Neo4j, real spaCy

Coverage Target: 85%+
"""
from __future__ import annotations

import time
from datetime import datetime

import pytest

from app.core.id_generator import generate_chunk_id, generate_doc_id, generate_mention_id
from app.core.models import RawContent
from app.pipeline.transformers.coref_resolver import CorefResolver
from app.pipeline.transformers.entity_extractor import EntityExtractor
from app.repositories.neo_repository import NeoRepository


# neo_repo fixture is provided by tests/integration/conftest.py


@pytest.fixture
def entity_extractor(neo_repo):
    """Entity extractor from Sprint 5."""
    return EntityExtractor(
        neo_repo=neo_repo,
        llm_provider=None,  # Not needed for these tests
        entity_types=["PERSON", "ORGANIZATION", "LOCATION"],
    )


@pytest.fixture
def coref_resolver(neo_repo):
    """Coreference resolver under test."""
    return CorefResolver(neo_repo=neo_repo)


@pytest.fixture
def sample_doc_with_coref(neo_repo):
    """Sample document with pronouns for coref testing.
    
    Text contains:
    - "Sam Altman" (PERSON) mentioned first
    - "He" pronoun referring back to Sam Altman
    - "OpenAI" (ORG) mentioned
    - "It" pronoun referring back to OpenAI
    """
    url = "https://example.com/coref-test"
    doc_id = generate_doc_id(url)
    
    # Create document
    neo_repo.create_document(
        doc_id=doc_id,
        url=url,
        title="Coref Test Doc",
        metadata={"test": True, "content_type": "text/plain"},
    )
    
    # Create chunk with coref text
    chunk_text = (
        "Sam Altman is the CEO of OpenAI. "
        "He founded the company in 2015. "
        "OpenAI develops AI systems. "
        "It has created GPT models."
    )
    chunk_id = generate_chunk_id(doc_id, 0)
    
    neo_repo.create_chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text=chunk_text,
        start_offset=0,
        end_offset=len(chunk_text),
        embedding=None,
    )
    
    # Create entity mentions (simulating EntityExtractor output)
    # Mention 1: "Sam Altman" (PERSON)
    mention_id_sam = generate_mention_id(chunk_id, "Sam Altman", 0)
    entity_id_sam = neo_repo.create_entity_mention(
        mention_id=mention_id_sam,
        chunk_id=chunk_id,
        text="Sam Altman",
        entity_type="PERSON",
        start_offset=0,
        end_offset=10,
        confidence=0.95,
    )
    
    # Mention 2: "OpenAI" (ORG) - first occurrence
    mention_id_openai = generate_mention_id(chunk_id, "OpenAI", 25)
    entity_id_openai = neo_repo.create_entity_mention(
        mention_id=mention_id_openai,
        chunk_id=chunk_id,
        text="OpenAI",
        entity_type="ORGANIZATION",
        start_offset=25,
        end_offset=31,
        confidence=0.95,
    )
    
    return {
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "text": chunk_text,
        "url": url,
        "mentions": {
            "sam_altman": {"mention_id": mention_id_sam, "entity_id": entity_id_sam},
            "openai": {"mention_id": mention_id_openai, "entity_id": entity_id_openai},
        },
    }


class TestCorefResolution:
    """Test suite for coreference resolution (Story S6-601)."""
    
    def test_resolve_he_pronoun_to_person(self, coref_resolver, neo_repo, sample_doc_with_coref):
        """Test 1: Resolve 'he' pronoun to PERSON entity mention.
        
        Expected behavior:
        - "He" in "He founded the company" resolves to "Sam Altman"
        - COREF_WITH relationship created between pronoun and entity mention
        - Relationship has metadata (text, cluster_id)
        """
        # Arrange
        doc_id = sample_doc_with_coref["doc_id"]
        chunk_id = sample_doc_with_coref["chunk_id"]
        chunk_text = sample_doc_with_coref["text"]
        sam_mention_id = sample_doc_with_coref["mentions"]["sam_altman"]["mention_id"]
        
        raw_content = RawContent(
            url=sample_doc_with_coref["url"],
            source_type="text",
            raw_text=chunk_text,
            metadata={},
        )
        
        # Act
        result = coref_resolver.transform(raw_content)
        
        # Assert
        assert isinstance(result, RawContent)
        assert result.metadata.get("coref_processed") is True
        
        # Query Neo4j for coreference relationships
        with neo_repo._driver.session() as session:
            query = """
            MATCH (m1:Mention {text: 'Sam Altman'})-[r:COREF_WITH]-(m2:Mention)
            WHERE m2.text = 'he' OR m2.text = 'He'
            RETURN m1, r, m2
            """
            coref_result = session.run(query).single()
            
            assert coref_result is not None, "Expected COREF_WITH relationship for 'He' -> 'Sam Altman'"
            
            rel = coref_result["r"]
            assert rel["cluster_id"] is not None
            assert "text" in rel
    
    def test_resolve_it_pronoun_to_org(self, coref_resolver, neo_repo, sample_doc_with_coref):
        """Test 2: Resolve 'it' pronoun to ORG entity mention.
        
        Expected behavior:
        - "It" in "It has created GPT models" resolves to "OpenAI"
        - COREF_WITH relationship created
        - Correct cluster assignment
        """
        # Arrange
        doc_id = sample_doc_with_coref["doc_id"]
        chunk_text = sample_doc_with_coref["text"]
        openai_mention_id = sample_doc_with_coref["mentions"]["openai"]["mention_id"]
        
        raw_content = RawContent(
            url=sample_doc_with_coref["url"],
            source_type="text",
            raw_text=chunk_text,
            metadata={},
        )
        
        # Act
        result = coref_resolver.transform(raw_content)
        
        # Assert
        with neo_repo._driver.session() as session:
            query = """
            MATCH (m1:Mention {text: 'OpenAI'})-[r:COREF_WITH]-(m2:Mention)
            WHERE m2.text = 'it' OR m2.text = 'It'
            RETURN m1, r, m2
            """
            coref_result = session.run(query).single()
            
            assert coref_result is not None, "Expected COREF_WITH relationship for 'It' -> 'OpenAI'"
            
            rel = coref_result["r"]
            assert rel["cluster_id"] is not None
    
    def test_create_coref_relationships_in_neo4j(self, coref_resolver, neo_repo, sample_doc_with_coref):
        """Test 3: Create COREF_WITH relationships in Neo4j.
        
        Expected behavior:
        - Relationships stored with proper attributes
        - Bidirectional or single direction (design choice)
        - Cluster IDs assigned consistently
        """
        # Arrange
        chunk_text = sample_doc_with_coref["text"]
        raw_content = RawContent(
            url=sample_doc_with_coref["url"],
            source_type="text",
            raw_text=chunk_text,
            metadata={},
        )
        
        # Act
        result = coref_resolver.transform(raw_content)
        
        # Assert - count COREF_WITH relationships
        with neo_repo._driver.session() as session:
            query = "MATCH ()-[r:COREF_WITH]->() RETURN count(r) as count"
            count_result = session.run(query).single()
            
            assert count_result["count"] >= 2, "Expected at least 2 coreference relationships"
            
            # Verify relationship attributes
            query = "MATCH ()-[r:COREF_WITH]->() RETURN r LIMIT 1"
            rel_result = session.run(query).single()
            rel = rel_result["r"]
            
            assert "cluster_id" in rel
            assert "created_at" in rel or "timestamp" in rel
    
    def test_retrieve_coref_chains_for_document(self, coref_resolver, neo_repo, sample_doc_with_coref):
        """Test 4: Retrieve coreference chains for document.
        
        Expected behavior:
        - Query returns all mentions in same coref cluster
        - Cluster contains original entity + all pronouns
        - Can traverse graph to find all coreferent mentions
        """
        # Arrange
        doc_id = sample_doc_with_coref["doc_id"]
        chunk_text = sample_doc_with_coref["text"]
        
        raw_content = RawContent(
            url=sample_doc_with_coref["url"],
            source_type="text",
            raw_text=chunk_text,
            metadata={},
        )
        
        # Act
        coref_resolver.transform(raw_content)
        
        # Assert - retrieve coref chains
        chains = neo_repo.get_coref_chains(doc_id)
        
        assert len(chains) >= 2, "Expected at least 2 coref chains (Sam Altman, OpenAI)"
        
        # Verify chain structure
        for chain in chains:
            assert "cluster_id" in chain
            assert "mentions" in chain
            assert len(chain["mentions"]) >= 2  # Original + pronoun
    
    def test_integration_with_entity_extractor(
        self, entity_extractor, coref_resolver, neo_repo, sample_doc_with_coref
    ):
        """Test 5: Integration with EntityExtractor from Sprint 5.
        
        Expected behavior:
        - EntityExtractor runs first (creates mentions)
        - CorefResolver runs second (links mentions)
        - Pipeline order: extract entities → resolve coreferences
        - Both transformers work together seamlessly
        """
        # Arrange - fresh document without pre-created mentions
        url = "https://example.com/integration-test"
        doc_id = generate_doc_id(url)
        
        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Integration Test",
            metadata={"content_type": "text/plain"},
        )
        
        chunk_text = "Elon Musk founded Tesla. He is also CEO of SpaceX."
        chunk_id = generate_chunk_id(doc_id, 0)
        
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=chunk_text,
            start_offset=0,
            end_offset=len(chunk_text),
            embedding=None,
        )
        
        raw_content = RawContent(
            url=url,
            source_type="text",
            raw_text=chunk_text,
            metadata={},
        )
        
        # Act - run both transformers
        entity_result = entity_extractor.transform(raw_content)
        coref_result = coref_resolver.transform(raw_content)
        
        # Assert
        # EntityExtractor may return ProcessedContent, but CorefResolver returns RawContent
        assert isinstance(coref_result, RawContent)
        assert coref_result.metadata.get("coref_processed") is True
        
        # Verify entity mentions exist
        with neo_repo._driver.session() as session:
            mentions_query = "MATCH (m:Mention) WHERE m.chunk_id = $chunk_id RETURN count(m) as count"
            mentions_count = session.run(mentions_query, chunk_id=chunk_id).single()["count"]
            assert mentions_count >= 2, "Expected entity mentions from EntityExtractor"
            
            # Verify coref relationships exist
            coref_query = "MATCH ()-[r:COREF_WITH]->() RETURN count(r) as count"
            coref_count = session.run(coref_query).single()["count"]
            assert coref_count >= 1, "Expected coref relationships from CorefResolver"
    
    def test_configuration_via_ai_services_yml(self, test_settings, neo_repo):
        """Test 6: Configuration via ai_services.yml.
        
        Expected behavior:
        - Coref can be enabled/disabled via config
        - Configuration loaded from ai_services.yml
        - Settings include: enabled, min_confidence, max_distance
        """
        # Arrange - coref resolver with config
        coref_config = {
            "enabled": True,
            "min_confidence": 0.7,
            "max_cluster_distance": 5,  # sentences
        }
        
        coref_resolver = CorefResolver(neo_repo=neo_repo, config=coref_config)
        
        # Act
        assert coref_resolver.enabled is True
        assert coref_resolver.min_confidence == 0.7
        assert coref_resolver.max_cluster_distance == 5
        
        # Test disabled config
        coref_resolver_disabled = CorefResolver(
            neo_repo=neo_repo, config={"enabled": False}
        )
        
        assert coref_resolver_disabled.enabled is False
    
    def test_performance_1000_words_under_5_seconds(self, coref_resolver, neo_repo):
        """Test 7: Performance benchmark - 1000 words in <5 seconds.
        
        Expected behavior:
        - Process ~1000 word document in <5 seconds
        - Includes entity extraction + coref resolution
        - Meets Sprint 6 performance target
        """
        # Arrange - create 1000-word document
        url = "https://example.com/performance-test"
        doc_id = generate_doc_id(url)
        
        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Performance Test",
            metadata={"content_type": "text/plain"},
        )
        
        # Generate ~1000 words with coref patterns
        long_text = (
            "Sam Altman is the CEO of OpenAI. He founded the company in 2015. "
            "OpenAI develops AI systems. It has created GPT models. "
        ) * 50  # ~1000 words
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=long_text,
            start_offset=0,
            end_offset=len(long_text),
            embedding=None,
        )
        
        raw_content = RawContent(
            url=url,
            source_type="text",
            raw_text=long_text,
            metadata={},
        )
        
        # Act - measure performance
        start_time = time.time()
        result = coref_resolver.transform(raw_content)
        elapsed = time.time() - start_time
        
        # Assert
        assert elapsed < 5.0, f"Coref resolution took {elapsed:.2f}s, expected <5s"
        assert isinstance(result, RawContent)
        assert result.metadata.get("coref_processed") is True
    
    def test_pipeline_integration_full_etl(
        self, entity_extractor, coref_resolver, neo_repo
    ):
        """Test 8: Pipeline integration test (full ETL).
        
        Expected behavior:
        - Document → Chunk → Entity Extraction → Coref Resolution
        - All stages work together
        - Neo4j graph populated correctly
        - End-to-end validation
        """
        # Arrange - simulate full pipeline
        url = "https://example.com/pipeline-test"
        doc_id = generate_doc_id(url)
        
        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Pipeline Test",
            metadata={"content_type": "text/plain"},
        )
        
        chunk_text = (
            "Microsoft was founded by Bill Gates and Paul Allen. "
            "The company is headquartered in Redmond. "
            "It develops Windows and Office products. "
            "Bill Gates served as CEO until 2000. "
            "He transitioned to Chief Software Architect role."
        )
        chunk_id = generate_chunk_id(doc_id, 0)
        
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=chunk_text,
            start_offset=0,
            end_offset=len(chunk_text),
            embedding=None,
        )
        
        raw_content = RawContent(
            url=url,
            source_type="text",
            raw_text=chunk_text,
            metadata={},
        )
        
        # Act - run full pipeline
        entity_result = entity_extractor.transform(raw_content)
        coref_result = coref_resolver.transform(raw_content)
        
        # Assert - validate full graph
        with neo_repo._driver.session() as session:
            # Verify document exists
            doc_query = "MATCH (d:Document {doc_id: $doc_id}) RETURN d"
            doc = session.run(doc_query, doc_id=doc_id).single()
            assert doc is not None
            
            # Verify chunks exist
            chunk_query = "MATCH (c:Chunk {chunk_id: $chunk_id}) RETURN c"
            chunk = session.run(chunk_query, chunk_id=chunk_id).single()
            assert chunk is not None
            
            # Verify entity mentions exist
            mentions_query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})-[:CONTAINS_MENTION]->(m:Mention)
            RETURN count(m) as count
            """
            mentions_count = session.run(mentions_query, chunk_id=chunk_id).single()["count"]
            assert mentions_count >= 3, "Expected multiple entity mentions"
            
            # Verify coref relationships exist
            coref_query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})-[:CONTAINS_MENTION]->(m:Mention)-[r:COREF_WITH]->()
            RETURN count(r) as count
            """
            coref_count = session.run(coref_query, chunk_id=chunk_id).single()["count"]
            assert coref_count >= 1, "Expected coref relationships"
            
            # Verify coref chains
            chains = neo_repo.get_coref_chains(doc_id)
            assert len(chains) >= 2, "Expected multiple coref chains"
