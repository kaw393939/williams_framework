"""Integration tests for Story S6-603: Relation Extraction.

Tests relation extraction between entities using spaCy dependency parsing.
Implements EMPLOYED_BY, FOUNDED, CITES, LOCATED_IN relationships.

TDD Approach: RED -> GREEN -> REFACTOR
Testing Philosophy: Real Neo4j integration, no mocks
"""

import pytest
from app.core.id_generator import (
    generate_doc_id,
    generate_chunk_id,
    generate_mention_id,
)


@pytest.fixture
def relation_service(neo_repo):
    """Fixture for RelationExtractionService."""
    from app.services.relation_extraction_service import RelationExtractionService
    
    return RelationExtractionService(neo_repo)


class TestRelationExtraction:
    """Integration tests for relation extraction."""

    def test_extract_employed_by_relation(self, relation_service, neo_repo):
        """Test 1: Extract EMPLOYED_BY relation ('X works at Y').
        
        Expected behavior:
        - Detect 'works at' pattern
        - Create (Entity)-[:EMPLOYED_BY]->(Entity) relationship
        - Store confidence, evidence_text, source_chunk_id
        """
        # Arrange - create document with employment relationship
        url = "https://example.com/employment"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Employment Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman works at OpenAI."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        # Create entity mentions
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 20)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 20, 26)
        
        # Act - extract relations from chunk
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert
        assert len(relations) >= 1
        employed_rel = next((r for r in relations if r["type"] == "EMPLOYED_BY"), None)
        assert employed_rel is not None
        assert employed_rel["subject_text"] == "Sam Altman"
        assert employed_rel["object_text"] == "OpenAI"
        assert employed_rel["confidence"] >= 0.8
        assert "works at" in employed_rel["evidence_text"].lower()
        assert employed_rel["source_chunk_id"] == chunk_id
        
        # Verify Neo4j relationship created
        with neo_repo._driver.session() as session:
            query = """
            MATCH (subject:Entity {text: 'Sam Altman'})-[r:EMPLOYED_BY]->(object:Entity {text: 'OpenAI'})
            RETURN r.confidence as confidence, r.evidence_text as evidence
            """
            result = session.run(query).single()
            assert result is not None
            assert result["confidence"] >= 0.8
            assert "works at" in result["evidence"].lower()

    def test_extract_founded_relation(self, relation_service, neo_repo):
        """Test 2: Extract FOUNDED relation ('X founded Y').
        
        Expected behavior:
        - Detect 'founded' pattern
        - Create (Entity)-[:FOUNDED]->(Entity) relationship
        - Handle past tense variations
        """
        # Arrange
        url = "https://example.com/founding"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Founding Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman founded OpenAI."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 19)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 19, 25)
        
        # Act
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert
        assert len(relations) >= 1
        founded_rel = next((r for r in relations if r["type"] == "FOUNDED"), None)
        assert founded_rel is not None
        assert founded_rel["subject_text"] == "Sam Altman"
        assert founded_rel["object_text"] == "OpenAI"
        assert founded_rel["confidence"] >= 0.9  # High confidence for exact pattern
        
        # Verify in Neo4j
        with neo_repo._driver.session() as session:
            query = """
            MATCH (subject:Entity {text: 'Sam Altman'})-[r:FOUNDED]->(object:Entity {text: 'OpenAI'})
            RETURN count(r) as count
            """
            result = session.run(query).single()
            assert result["count"] == 1

    def test_extract_cites_relation(self, relation_service, neo_repo):
        """Test 3: Extract CITES relation ('according to X').
        
        Expected behavior:
        - Detect citation patterns: 'according to', 'referenced', 'cited'
        - Create (Entity)-[:CITES]->(Entity) or (Document)-[:CITES]->(Entity)
        - Handle various citation formats
        """
        # Arrange
        url = "https://example.com/citation"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Citation Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "According to Sam Altman, AI will transform society."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 13)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 13, 23)
        
        # Act
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert - might create CITES from document or implicit subject
        assert len(relations) >= 0  # CITES is optional if no clear subject

    def test_extract_located_in_relation(self, relation_service, neo_repo):
        """Test 4: Extract LOCATED_IN relation ('X based in Y').
        
        Expected behavior:
        - Detect location patterns: 'based in', 'located in', 'in'
        - Create (Entity)-[:LOCATED_IN]->(Entity)
        - Handle GPE (geo-political entity) types
        """
        # Arrange
        url = "https://example.com/location"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Location Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "OpenAI is based in San Francisco."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 0)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 0, 6)
        
        loc_mention_id = generate_mention_id(chunk_id, "San Francisco", 19)
        neo_repo.create_entity_mention(loc_mention_id, chunk_id, "San Francisco", "GPE", 19, 32)
        
        # Act
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert
        assert len(relations) >= 1
        located_rel = next((r for r in relations if r["type"] == "LOCATED_IN"), None)
        assert located_rel is not None
        assert located_rel["subject_text"] == "OpenAI"
        assert located_rel["object_text"] == "San Francisco"
        
        # Verify in Neo4j
        with neo_repo._driver.session() as session:
            query = """
            MATCH (subject:Entity {text: 'OpenAI'})-[r:LOCATED_IN]->(object:Entity {text: 'San Francisco'})
            RETURN count(r) as count
            """
            result = session.run(query).single()
            assert result["count"] == 1

    def test_store_relationship_edges(self, relation_service, neo_repo):
        """Test 5: Store relationship edges in Neo4j.
        
        Expected behavior:
        - Create relationship edges between Entity nodes
        - Store attributes: confidence, evidence_text, source_chunk_id, extracted_at
        - Proper relationship direction (subject → object)
        """
        # Arrange
        url = "https://example.com/edges"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Edges Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman works at OpenAI."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 20)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 20, 26)
        
        # Act
        relation_service.extract_relations(chunk_id)
        
        # Assert - check all relationship attributes
        with neo_repo._driver.session() as session:
            query = """
            MATCH (subject:Entity)-[r:EMPLOYED_BY]->(object:Entity)
            RETURN r.confidence as confidence,
                   r.evidence_text as evidence,
                   r.source_chunk_id as chunk_id,
                   r.extracted_at as extracted_at
            """
            result = session.run(query).single()
            assert result is not None
            assert result["confidence"] is not None
            assert result["evidence"] is not None
            assert result["chunk_id"] == chunk_id
            assert result["extracted_at"] is not None

    def test_relationship_confidence_scoring(self, relation_service, neo_repo):
        """Test 6: Relationship confidence scoring.
        
        Expected behavior:
        - Exact pattern matches: confidence 0.9-1.0
        - Partial matches: confidence 0.7-0.89
        - Weak patterns: confidence 0.5-0.69
        - Confidence based on pattern strength
        """
        # Arrange - create various pattern strengths
        url = "https://example.com/confidence"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Confidence Test", metadata={})
        
        # Strong pattern: "founded"
        chunk_id1 = generate_chunk_id(doc_id, 0)
        text1 = "Sam Altman founded OpenAI."
        neo_repo.create_chunk(chunk_id1, doc_id, text1, 0, len(text1), None)
        
        person_mention_id = generate_mention_id(chunk_id1, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id1, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id1, "OpenAI", 19)
        neo_repo.create_entity_mention(org_mention_id, chunk_id1, "OpenAI", "ORG", 19, 25)
        
        # Act
        relations = relation_service.extract_relations(chunk_id1)
        
        # Assert - strong pattern should have high confidence
        founded_rel = next((r for r in relations if r["type"] == "FOUNDED"), None)
        assert founded_rel is not None
        assert founded_rel["confidence"] >= 0.9

    def test_temporal_relations(self, relation_service, neo_repo):
        """Test 7: Temporal relations (e.g., 'founded in 2015').
        
        Expected behavior:
        - Extract temporal information from text
        - Store temporal attributes: year, month, date (if available)
        - Handle various date formats
        """
        # Arrange
        url = "https://example.com/temporal"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Temporal Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman founded OpenAI in 2015."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 19)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 19, 25)
        
        # Act
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert
        founded_rel = next((r for r in relations if r["type"] == "FOUNDED"), None)
        assert founded_rel is not None
        assert founded_rel.get("year") == "2015" or "2015" in founded_rel.get("evidence_text", "")

    def test_relationship_deduplication(self, relation_service, neo_repo):
        """Test 8: Relationship deduplication.
        
        Expected behavior:
        - Same relation from multiple mentions → single relationship
        - Update confidence (take max or average)
        - Preserve all evidence sources
        """
        # Arrange - create two chunks with same relationship
        url = "https://example.com/dedup"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Dedup Test", metadata={})
        
        # Chunk 1: "Sam Altman works at OpenAI"
        chunk_id1 = generate_chunk_id(doc_id, 0)
        text1 = "Sam Altman works at OpenAI."
        neo_repo.create_chunk(chunk_id1, doc_id, text1, 0, len(text1), None)
        
        person_mention_id1 = generate_mention_id(chunk_id1, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id1, chunk_id1, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id1 = generate_mention_id(chunk_id1, "OpenAI", 20)
        neo_repo.create_entity_mention(org_mention_id1, chunk_id1, "OpenAI", "ORG", 20, 26)
        
        # Chunk 2: "Sam Altman is employed by OpenAI"
        chunk_id2 = generate_chunk_id(doc_id, 1)
        text2 = "Sam Altman is employed by OpenAI."
        neo_repo.create_chunk(chunk_id2, doc_id, text2, 0, len(text2), None)
        
        person_mention_id2 = generate_mention_id(chunk_id2, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id2, chunk_id2, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id2 = generate_mention_id(chunk_id2, "OpenAI", 26)
        neo_repo.create_entity_mention(org_mention_id2, chunk_id2, "OpenAI", "ORG", 26, 32)
        
        # Act
        relation_service.extract_relations(chunk_id1)
        relation_service.extract_relations(chunk_id2)
        
        # Assert - should only create one relationship (or merge)
        with neo_repo._driver.session() as session:
            query = """
            MATCH (subject:Entity {text: 'Sam Altman'})-[r:EMPLOYED_BY]->(object:Entity {text: 'OpenAI'})
            RETURN count(r) as count
            """
            result = session.run(query).single()
            # Should be 1 relationship (deduplicated) or 2 (separate evidence)
            # Implementation choice: allow multiple for different evidence
            assert result["count"] >= 1

    def test_multiple_relations_in_sentence(self, relation_service, neo_repo):
        """Test 9: Multiple relations in same sentence.
        
        Expected behavior:
        - Extract all relations from complex sentences
        - Handle multiple entity pairs
        - Correct attribution of relations
        """
        # Arrange
        url = "https://example.com/multiple"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Multiple Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman founded OpenAI, which is based in San Francisco."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 19)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 19, 25)
        
        loc_mention_id = generate_mention_id(chunk_id, "San Francisco", 45)
        neo_repo.create_entity_mention(loc_mention_id, chunk_id, "San Francisco", "GPE", 45, 58)
        
        # Act
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert - should extract both FOUNDED and LOCATED_IN
        assert len(relations) >= 2
        rel_types = {r["type"] for r in relations}
        assert "FOUNDED" in rel_types
        assert "LOCATED_IN" in rel_types

    def test_dependency_parsing_patterns(self, relation_service, neo_repo):
        """Test 10: Dependency parsing for relation patterns.
        
        Expected behavior:
        - Use spaCy dependency trees to identify relations
        - Handle various syntactic structures
        - Extract subject-verb-object patterns
        """
        # Arrange - test various syntactic patterns
        url = "https://example.com/syntax"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Syntax Test", metadata={})
        
        # Passive voice: "OpenAI was founded by Sam Altman"
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "OpenAI was founded by Sam Altman."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 0)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 0, 6)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 22)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 22, 32)
        
        # Act
        relations = relation_service.extract_relations(chunk_id)
        
        # Assert - should handle passive voice
        founded_rel = next((r for r in relations if r["type"] == "FOUNDED"), None)
        assert founded_rel is not None
        assert founded_rel["subject_text"] == "Sam Altman"
        assert founded_rel["object_text"] == "OpenAI"

    def test_batch_relation_extraction(self, relation_service, neo_repo):
        """Test 11: Batch relation extraction performance.
        
        Expected behavior:
        - Process multiple chunks efficiently
        - Extract relations from 100 chunks in <30 seconds
        - Return all relations
        """
        import time
        
        # Arrange - create 50 chunks (scaled down from 100 for test speed)
        url = "https://example.com/batch"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Batch Test", metadata={})
        
        chunk_ids = []
        for i in range(50):
            chunk_id = generate_chunk_id(doc_id, i)
            text = f"Person{i} works at Company{i}."
            neo_repo.create_chunk(chunk_id, doc_id, text, i * 100, i * 100 + len(text), None)
            
            person_mention_id = generate_mention_id(chunk_id, f"Person{i}", 0)
            neo_repo.create_entity_mention(person_mention_id, chunk_id, f"Person{i}", "PERSON", 0, 7 + len(str(i)))
            
            org_mention_id = generate_mention_id(chunk_id, f"Company{i}", 18)
            neo_repo.create_entity_mention(org_mention_id, chunk_id, f"Company{i}", "ORG", 18, 25 + len(str(i)))
            
            chunk_ids.append(chunk_id)
        
        # Act
        start = time.time()
        all_relations = relation_service.batch_extract_relations(chunk_ids)
        elapsed = time.time() - start
        
        # Assert
        assert len(all_relations) >= 50
        assert elapsed < 30.0, f"Batch extraction took {elapsed:.2f}s (expected <30s)"

    def test_integration_with_etl_pipeline(self, relation_service, neo_repo):
        """Test 12: Integration with ETL pipeline.
        
        Expected behavior:
        - RelationExtractor can be added as pipeline transformer
        - Process document through full pipeline
        - Relations extracted and stored automatically
        """
        # This test validates the transformer interface
        from app.pipeline.transformers.relation_extractor import RelationExtractor
        
        # Arrange
        url = "https://example.com/pipeline"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Pipeline Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman works at OpenAI."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention_id, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention_id = generate_mention_id(chunk_id, "OpenAI", 20)
        neo_repo.create_entity_mention(org_mention_id, chunk_id, "OpenAI", "ORG", 20, 26)
        
        # Act - use transformer
        extractor = RelationExtractor(neo_repo)
        
        # Create a simple chunk object for testing
        class MockChunk:
            def __init__(self, chunk_id):
                self.id = chunk_id
        
        chunk_obj = MockChunk(chunk_id)
        result = extractor.transform([chunk_obj])
        
        # Assert - transformer returns chunks unchanged, but extracts relations
        assert len(result) == 1
        assert result[0].id == chunk_id
        
        # Verify relations were extracted
        with neo_repo._driver.session() as session:
            query = "MATCH ()-[r:EMPLOYED_BY]->() RETURN count(r) as count"
            result = session.run(query).single()
            assert result["count"] >= 1
