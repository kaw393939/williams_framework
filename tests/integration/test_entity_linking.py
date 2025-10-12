"""Integration tests for Story S6-602: Canonical Entity Linking.

Test Philosophy: RED-GREEN-REFACTOR with real services (NO MOCKS)
Coverage Target: 85%+

Story Goals:
- Consolidate entity mentions across documents into canonical entities
- Fuzzy matching and deduplication (OpenAI vs OpenAI Inc.)
- Confidence scoring (exact: 1.0, fuzzy: 0.8-0.99, context: 0.6-0.79)
- LINKED_TO relationships with confidence scores
- Batch linking performance (100 mentions <10s)
"""

import pytest
from app.repositories.neo_repository import NeoRepository
from app.services.entity_linking_service import EntityLinkingService
from app.core.id_generator import generate_doc_id, generate_chunk_id, generate_entity_id, generate_mention_id


class TestEntityLinking:
    """Test suite for canonical entity linking (Story S6-602)."""

    @pytest.fixture
    def neo_repo(self):
        """Neo4j repository for graph operations."""
        repo = NeoRepository()
        yield repo
        # Cleanup after each test
        repo.clear_database()

    @pytest.fixture
    def entity_linking_service(self, neo_repo):
        """Entity linking service with Neo4j backend."""
        return EntityLinkingService(neo_repo)

    @pytest.fixture
    def sample_document_with_mentions(self, neo_repo):
        """Create test document with entity mentions."""
        url = "https://example.com/test-doc"
        doc_id = generate_doc_id(url)
        
        # Create document
        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Entity Linking Test",
            metadata={"content_type": "text/plain"},
        )
        
        # Create chunk
        chunk_text = "Sam Altman is the CEO of OpenAI. He founded the company in 2015."
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
        sam_mention_id = generate_mention_id(chunk_id, "Sam Altman", 0)
        openai_mention_id = generate_mention_id(chunk_id, "OpenAI", 28)
        
        # Create mentions with entities
        sam_entity_id = neo_repo.create_entity_mention(
            mention_id=sam_mention_id,
            chunk_id=chunk_id,
            text="Sam Altman",
            entity_type="PERSON",
            start_offset=0,
            end_offset=10,
        )
        
        openai_entity_id = neo_repo.create_entity_mention(
            mention_id=openai_mention_id,
            chunk_id=chunk_id,
            text="OpenAI",
            entity_type="ORG",
            start_offset=28,
            end_offset=34,
        )
        
        return {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "mentions": {
                "sam_altman": {
                    "mention_id": sam_mention_id,
                    "entity_id": sam_entity_id,
                    "text": "Sam Altman",
                    "type": "PERSON",
                },
                "openai": {
                    "mention_id": openai_mention_id,
                    "entity_id": openai_entity_id,
                    "text": "OpenAI",
                    "type": "ORG",
                },
            },
        }

    def test_link_single_mention_to_canonical_entity(
        self, entity_linking_service, neo_repo, sample_document_with_mentions
    ):
        """Test 1: Link single mention to new canonical entity.
        
        Expected behavior:
        - Create canonical Entity node
        - Link Mention to Entity with LINKED_TO relationship
        - Confidence score = 1.0 (exact match)
        - Entity has canonical_name, entity_type, mention_count=1
        """
        # Arrange
        sam_mention_id = sample_document_with_mentions["mentions"]["sam_altman"]["mention_id"]
        
        # Act
        canonical_entity_id = entity_linking_service.link_mention(
            mention_id=sam_mention_id,
            canonical_name="Sam Altman",
            entity_type="PERSON",
        )
        
        # Assert
        assert canonical_entity_id is not None
        
        # Verify canonical entity exists
        with neo_repo._driver.session() as session:
            query = """
            MATCH (e:Entity {id: $entity_id})
            RETURN e.canonical_name as name, e.entity_type as type, e.mention_count as count
            """
            result = session.run(query, entity_id=canonical_entity_id).single()
            assert result is not None
            assert result["name"] == "Sam Altman"
            assert result["type"] == "PERSON"
            assert result["count"] == 1
            
            # Verify LINKED_TO relationship
            link_query = """
            MATCH (m:Mention {id: $mention_id})-[r:LINKED_TO]->(e:Entity {id: $entity_id})
            RETURN r.confidence as confidence
            """
            link_result = session.run(
                link_query, mention_id=sam_mention_id, entity_id=canonical_entity_id
            ).single()
            assert link_result is not None
            assert link_result["confidence"] == 1.0  # Exact match

    def test_link_multiple_mentions_to_same_entity(
        self, entity_linking_service, neo_repo
    ):
        """Test 2: Link multiple mentions to same canonical entity (same document).
        
        Expected behavior:
        - Multiple mentions link to same Entity
        - Entity mention_count increments
        - All LINKED_TO relationships have confidence scores
        """
        # Arrange - create document with multiple "OpenAI" mentions
        url = "https://example.com/multi-mention"
        doc_id = generate_doc_id(url)
        
        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Multiple Mentions Test",
            metadata={},
        )
        
        chunk_text = "OpenAI released GPT-4. OpenAI is based in San Francisco."
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=chunk_text,
            start_offset=0,
            end_offset=len(chunk_text),
            embedding=None,
        )
        
        # Create two OpenAI mentions
        mention1_id = generate_mention_id(chunk_id, "OpenAI", 0)
        mention2_id = generate_mention_id(chunk_id, "OpenAI", 23)
        
        neo_repo.create_entity_mention(
            mention_id=mention1_id,
            chunk_id=chunk_id,
            text="OpenAI",
            entity_type="ORG",
            start_offset=0,
            end_offset=6,
        )
        
        neo_repo.create_entity_mention(
            mention_id=mention2_id,
            chunk_id=chunk_id,
            text="OpenAI",
            entity_type="ORG",
            start_offset=23,
            end_offset=29,
        )
        
        # Act - link both mentions to same canonical entity
        entity_id1 = entity_linking_service.link_mention(
            mention_id=mention1_id,
            canonical_name="OpenAI",
            entity_type="ORG",
        )
        
        entity_id2 = entity_linking_service.link_mention(
            mention_id=mention2_id,
            canonical_name="OpenAI",
            entity_type="ORG",
        )
        
        # Assert
        assert entity_id1 == entity_id2  # Same canonical entity
        
        with neo_repo._driver.session() as session:
            # Verify mention_count = 2
            query = "MATCH (e:Entity {id: $entity_id}) RETURN e.mention_count as count"
            result = session.run(query, entity_id=entity_id1).single()
            assert result["count"] == 2
            
            # Verify both LINKED_TO relationships exist
            link_query = """
            MATCH (m:Mention)-[r:LINKED_TO]->(e:Entity {id: $entity_id})
            RETURN count(m) as mention_count
            """
            link_result = session.run(link_query, entity_id=entity_id1).single()
            assert link_result["mention_count"] == 2

    def test_entity_deduplication_across_documents(
        self, entity_linking_service, neo_repo
    ):
        """Test 3: Entity deduplication across documents.
        
        Expected behavior:
        - "OpenAI" in doc1 + "OpenAI Inc." in doc2 → same canonical entity
        - Fuzzy matching identifies variants
        - Entity aliases stored: ["OpenAI", "OpenAI Inc."]
        """
        # Arrange - create two documents with entity variants
        url1 = "https://example.com/doc1"
        doc1_id = generate_doc_id(url1)
        neo_repo.create_document(doc_id=doc1_id, url=url1, title="Doc 1", metadata={})
        
        chunk1_id = generate_chunk_id(doc1_id, 0)
        neo_repo.create_chunk(chunk1_id, doc1_id, "OpenAI released GPT-4.", 0, 22, None)
        
        mention1_id = generate_mention_id(chunk1_id, "OpenAI", 0)
        neo_repo.create_entity_mention(mention1_id, chunk1_id, "OpenAI", "ORG", 0, 6)
        
        url2 = "https://example.com/doc2"
        doc2_id = generate_doc_id(url2)
        neo_repo.create_document(doc_id=doc2_id, url=url2, title="Doc 2", metadata={})
        
        chunk2_id = generate_chunk_id(doc2_id, 0)
        neo_repo.create_chunk(chunk2_id, doc2_id, "OpenAI Inc. is an AI company.", 0, 30, None)
        
        mention2_id = generate_mention_id(chunk2_id, "OpenAI Inc.", 0)
        neo_repo.create_entity_mention(mention2_id, chunk2_id, "OpenAI Inc.", "ORG", 0, 11)
        
        # Act - link both mentions (service should detect they're the same entity)
        entity_id1 = entity_linking_service.link_mention(
            mention_id=mention1_id,
            canonical_name="OpenAI",
            entity_type="ORG",
        )
        
        entity_id2 = entity_linking_service.link_mention(
            mention_id=mention2_id,
            canonical_name="OpenAI Inc.",  # Slightly different name
            entity_type="ORG",
        )
        
        # Assert - should be linked to same canonical entity
        assert entity_id1 == entity_id2
        
        with neo_repo._driver.session() as session:
            # Verify entity has both aliases
            query = "MATCH (e:Entity {id: $entity_id}) RETURN e.aliases as aliases"
            result = session.run(query, entity_id=entity_id1).single()
            aliases = result["aliases"]
            assert "OpenAI" in aliases
            assert "OpenAI Inc." in aliases

    def test_fuzzy_matching(self, entity_linking_service, neo_repo):
        """Test 4: Fuzzy matching ("Open AI" → "OpenAI").
        
        Expected behavior:
        - Similar names link to same entity
        - Confidence score 0.8-0.99 for fuzzy match
        - Normalized matching (case-insensitive, whitespace)
        """
        # Arrange
        url = "https://example.com/fuzzy"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Fuzzy Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(chunk_id, doc_id, "Open AI is innovative.", 0, 22, None)
        
        mention_id = generate_mention_id(chunk_id, "Open AI", 0)
        neo_repo.create_entity_mention(mention_id, chunk_id, "Open AI", "ORG", 0, 7)
        
        # Act - link with canonical name "OpenAI" (service should fuzzy match)
        entity_id = entity_linking_service.link_mention(
            mention_id=mention_id,
            canonical_name="OpenAI",  # Different from "Open AI"
            entity_type="ORG",
        )
        
        # Assert
        with neo_repo._driver.session() as session:
            query = """
            MATCH (m:Mention {id: $mention_id})-[r:LINKED_TO]->(e:Entity)
            RETURN r.confidence as confidence, e.canonical_name as name
            """
            result = session.run(query, mention_id=mention_id).single()
            assert result is not None
            assert result["name"] == "OpenAI"
            assert 0.8 <= result["confidence"] < 1.0  # Fuzzy match confidence

    def test_confidence_scoring(self, entity_linking_service, neo_repo):
        """Test 5: Confidence scoring (exact/fuzzy/context).
        
        Expected behavior:
        - Exact match: confidence = 1.0
        - Fuzzy match: confidence = 0.8-0.99
        - Context similarity: confidence = 0.6-0.79
        """
        # Test exact match
        url = "https://example.com/confidence"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Confidence Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(chunk_id, doc_id, "Tesla Inc. makes cars.", 0, 22, None)
        
        mention_id = generate_mention_id(chunk_id, "Tesla Inc.", 0)
        neo_repo.create_entity_mention(mention_id, chunk_id, "Tesla Inc.", "ORG", 0, 10)
        
        # Act - exact match
        entity_id = entity_linking_service.link_mention(
            mention_id=mention_id,
            canonical_name="Tesla Inc.",  # Exact match
            entity_type="ORG",
        )
        
        # Assert exact match confidence
        with neo_repo._driver.session() as session:
            query = """
            MATCH (m:Mention {id: $mention_id})-[r:LINKED_TO]->(:Entity)
            RETURN r.confidence as confidence
            """
            result = session.run(query, mention_id=mention_id).single()
            assert result["confidence"] == 1.0

    def test_create_linked_to_relationships(
        self, entity_linking_service, neo_repo, sample_document_with_mentions
    ):
        """Test 6: Create LINKED_TO relationships with confidence.
        
        Expected behavior:
        - LINKED_TO edge has confidence, linked_at timestamp
        - Relationship properties stored correctly
        """
        # Arrange
        mention_id = sample_document_with_mentions["mentions"]["openai"]["mention_id"]
        
        # Act
        entity_id = entity_linking_service.link_mention(
            mention_id=mention_id,
            canonical_name="OpenAI",
            entity_type="ORG",
        )
        
        # Assert
        with neo_repo._driver.session() as session:
            query = """
            MATCH (m:Mention {id: $mention_id})-[r:LINKED_TO]->(e:Entity {id: $entity_id})
            RETURN r.confidence as confidence, r.linked_at as linked_at
            """
            result = session.run(query, mention_id=mention_id, entity_id=entity_id).single()
            assert result is not None
            assert result["confidence"] is not None
            assert result["linked_at"] is not None

    def test_entity_attributes(self, entity_linking_service, neo_repo):
        """Test 7: Entity attributes stored correctly.
        
        Expected behavior:
        - canonical_name, entity_type, mention_count
        - aliases: [] list of variant names
        - created_at timestamp
        """
        # Arrange
        url = "https://example.com/attrs"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Attrs Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(chunk_id, doc_id, "Microsoft is big.", 0, 17, None)
        
        mention_id = generate_mention_id(chunk_id, "Microsoft", 0)
        neo_repo.create_entity_mention(mention_id, chunk_id, "Microsoft", "ORG", 0, 9)
        
        # Act
        entity_id = entity_linking_service.link_mention(
            mention_id=mention_id,
            canonical_name="Microsoft",
            entity_type="ORG",
        )
        
        # Assert all attributes
        with neo_repo._driver.session() as session:
            query = """
            MATCH (e:Entity {id: $entity_id})
            RETURN e.canonical_name as name, e.entity_type as type,
                   e.mention_count as count, e.aliases as aliases, e.created_at as created
            """
            result = session.run(query, entity_id=entity_id).single()
            assert result["name"] == "Microsoft"
            assert result["type"] == "ORG"
            assert result["count"] == 1
            assert isinstance(result["aliases"], list)
            assert result["created"] is not None

    def test_batch_linking_performance(self, entity_linking_service, neo_repo):
        """Test 8: Batch linking performance (100 mentions <10s).
        
        Expected behavior:
        - Process 100 mentions in <10 seconds
        - Batch operations efficient
        - No performance degradation with scale
        """
        import time
        
        # Arrange - create 100 entity mentions
        url = "https://example.com/batch"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Batch Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(chunk_id, doc_id, "Batch test chunk.", 0, 17, None)
        
        mention_ids = []
        for i in range(100):
            mention_id = generate_mention_id(chunk_id, f"Entity{i}", i * 10)
            neo_repo.create_entity_mention(
                mention_id=mention_id,
                chunk_id=chunk_id,
                text=f"Entity{i}",
                entity_type="ORG",
                start_offset=i * 10,
                end_offset=i * 10 + 7,
            )
            mention_ids.append((mention_id, f"Entity{i}"))
        
        # Act - batch link
        start_time = time.time()
        entity_ids = entity_linking_service.batch_link_mentions(
            mentions=[
                {"mention_id": mid, "canonical_name": name, "entity_type": "ORG"}
                for mid, name in mention_ids
            ]
        )
        elapsed = time.time() - start_time
        
        # Assert
        assert len(entity_ids) == 100
        assert elapsed < 10.0, f"Batch linking took {elapsed:.2f}s (expected <10s)"

    def test_transaction_rollback_on_error(self, entity_linking_service, neo_repo):
        """Test 9: Transaction rollback on linking failure.
        
        Expected behavior:
        - If linking fails mid-batch, rollback all changes
        - Database consistency maintained
        - No partial links created
        """
        # Arrange - create valid mentions + intentionally trigger error
        url = "https://example.com/rollback"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Rollback Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(chunk_id, doc_id, "Rollback test.", 0, 14, None)
        
        mention_id = generate_mention_id(chunk_id, "Entity", 0)
        neo_repo.create_entity_mention(mention_id, chunk_id, "Entity", "ORG", 0, 6)
        
        # Act - try to link with invalid data (should fail)
        with pytest.raises(Exception):
            entity_linking_service.link_mention(
                mention_id="INVALID_MENTION_ID",  # This should fail
                canonical_name="Entity",
                entity_type="ORG",
            )
        
        # Assert - no partial Entity created
        with neo_repo._driver.session() as session:
            query = "MATCH (e:Entity {canonical_name: 'Entity'}) RETURN count(e) as count"
            result = session.run(query).single()
            assert result["count"] == 0  # No entity created due to rollback

    def test_integration_with_neo_repository(
        self, entity_linking_service, neo_repo, sample_document_with_mentions
    ):
        """Test 10: Integration with Sprint 5 NeoRepository.
        
        Expected behavior:
        - Uses existing NeoRepository methods
        - Compatible with Sprint 5 entity extraction
        - Entity IDs deterministic (use generate_entity_id)
        """
        # Arrange
        mention_id = sample_document_with_mentions["mentions"]["sam_altman"]["mention_id"]
        
        # Act
        canonical_entity_id = entity_linking_service.link_mention(
            mention_id=mention_id,
            canonical_name="Sam Altman",
            entity_type="PERSON",
        )
        
        # Assert - verify entity ID follows Sprint 5 conventions
        expected_entity_id = generate_entity_id("Sam Altman", "PERSON")
        assert canonical_entity_id == expected_entity_id
        
        # Verify can retrieve using NeoRepository methods
        entity = neo_repo.get_entity(canonical_entity_id)
        assert entity is not None
        assert entity["canonical_name"] == "Sam Altman"
