"""
Integration tests for Neo4j schema and CRUD operations.

Tests the full provenance schema:
- Document nodes
- Chunk nodes with PART_OF relationships
- Entity nodes
- Mention nodes with FOUND_IN and REFERS_TO relationships

Uses REAL Neo4j (no mocks) - requires Docker stack running.
"""

import pytest
from app.repositories.neo_repository import NeoRepository
from app.core.id_generator import (
    generate_doc_id,
    generate_chunk_id,
    generate_entity_id,
    generate_mention_id
)


@pytest.fixture
def neo_repo():
    """Fixture providing Neo4j repository with clean database."""
    repo = NeoRepository()
    
    # Verify connectivity
    try:
        repo.verify_connectivity()
    except RuntimeError:
        pytest.skip("Neo4j not available")
    
    # Clear database for clean test
    repo.clear_database()
    
    # Initialize schema
    repo.initialize_schema()
    
    yield repo
    
    # Cleanup
    repo.close()


class TestSchemaInitialization:
    """Test Neo4j schema setup."""
    
    def test_initialize_schema(self, neo_repo):
        """Test that schema initialization creates constraints and indexes."""
        # Schema already initialized in fixture
        # Just verify we can query without errors
        count = neo_repo.get_node_count()
        assert count == 0  # Should be empty after clear
    
    def test_schema_idempotent(self, neo_repo):
        """Test that schema initialization can be run multiple times."""
        # Run again - should not error
        neo_repo.initialize_schema()
        
        # Should still work
        count = neo_repo.get_node_count()
        assert count == 0


class TestDocumentOperations:
    """Test Document node CRUD operations."""
    
    def test_create_document(self, neo_repo):
        """Test creating a document node."""
        url = "https://example.com/article"
        doc_id = generate_doc_id(url)
        
        doc = neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Test Article",
            metadata={"author": "John Doe"}
        )
        
        assert doc is not None
        assert doc["id"] == doc_id
        assert doc["url"] == url
        assert doc["title"] == "Test Article"
        assert doc["metadata"]["author"] == "John Doe"
    
    def test_get_document(self, neo_repo):
        """Test retrieving a document by ID."""
        url = "https://example.com/article"
        doc_id = generate_doc_id(url)
        
        # Create
        neo_repo.create_document(doc_id=doc_id, url=url, title="Test")
        
        # Retrieve
        doc = neo_repo.get_document(doc_id)
        
        assert doc is not None
        assert doc["id"] == doc_id
        assert doc["url"] == url
    
    def test_get_nonexistent_document(self, neo_repo):
        """Test getting document that doesn't exist returns None."""
        doc = neo_repo.get_document("nonexistent_id")
        assert doc is None
    
    def test_document_id_deterministic(self, neo_repo):
        """Test that same URL produces same document ID."""
        url1 = "https://example.com/article"
        url2 = "http://www.example.com/article/"  # Different but normalizes same
        
        doc_id1 = generate_doc_id(url1)
        doc_id2 = generate_doc_id(url2)
        
        assert doc_id1 == doc_id2
        
        # Creating with either URL should update same node
        neo_repo.create_document(doc_id=doc_id1, url=url1, title="Version 1")
        neo_repo.create_document(doc_id=doc_id2, url=url2, title="Version 2")
        
        # Should only have one document
        count = neo_repo.get_node_count("Document")
        assert count == 1
        
        # Should have latest title
        doc = neo_repo.get_document(doc_id1)
        assert doc["title"] == "Version 2"


class TestChunkOperations:
    """Test Chunk node CRUD and relationships."""
    
    def test_create_chunk(self, neo_repo):
        """Test creating a chunk with PART_OF relationship."""
        # Create document first
        url = "https://example.com/doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
        
        # Create chunk
        chunk_id = generate_chunk_id(doc_id, 0)
        chunk = neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="This is a test chunk.",
            start_offset=0,
            end_offset=21,
            page_number=1
        )
        
        assert chunk is not None
        assert chunk["id"] == chunk_id
        assert chunk["text"] == "This is a test chunk."
        assert chunk["start_offset"] == 0
        assert chunk["end_offset"] == 21
        assert chunk["page_number"] == 1
    
    def test_chunk_part_of_relationship(self, neo_repo):
        """Test that chunk is linked to document via PART_OF."""
        url = "https://example.com/doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="Chunk text",
            start_offset=0,
            end_offset=10
        )
        
        # Query relationship
        query = """
        MATCH (c:Chunk {id: $chunk_id})-[:PART_OF]->(d:Document)
        RETURN d.id as doc_id
        """
        result = neo_repo.execute_query(query, {"chunk_id": chunk_id})
        
        assert len(result) == 1
        assert result[0]["doc_id"] == doc_id
    
    def test_get_document_chunks(self, neo_repo):
        """Test retrieving all chunks for a document in order."""
        url = "https://example.com/doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
        
        # Create multiple chunks
        offsets = [0, 100, 200]
        for offset in offsets:
            chunk_id = generate_chunk_id(doc_id, offset)
            neo_repo.create_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=f"Chunk at {offset}",
                start_offset=offset,
                end_offset=offset + 50
            )
        
        # Retrieve all chunks
        chunks = neo_repo.get_document_chunks(doc_id)
        
        assert len(chunks) == 3
        # Should be ordered by offset
        assert chunks[0]["start_offset"] == 0
        assert chunks[1]["start_offset"] == 100
        assert chunks[2]["start_offset"] == 200
    
    def test_chunk_with_heading(self, neo_repo):
        """Test chunk with heading context (for markdown)."""
        url = "https://example.com/doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
        
        chunk_id = generate_chunk_id(doc_id, 0)
        chunk = neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="Chunk text",
            start_offset=0,
            end_offset=10,
            heading="Introduction > Background"
        )
        
        assert chunk["heading"] == "Introduction > Background"


class TestEntityOperations:
    """Test Entity node CRUD."""
    
    def test_create_entity(self, neo_repo):
        """Test creating an entity node."""
        entity_id = generate_entity_id("Einstein", "PERSON")
        
        entity = neo_repo.create_entity(
            entity_id=entity_id,
            text="Einstein",
            entity_type="PERSON",
            confidence=0.95
        )
        
        assert entity is not None
        assert entity["id"] == entity_id
        assert entity["text"] == "Einstein"
        assert entity["entity_type"] == "PERSON"
        assert entity["confidence"] == 0.95
        assert entity["mention_count"] == 1
    
    def test_entity_mention_count_increments(self, neo_repo):
        """Test that mention_count increments on duplicate entity creation."""
        entity_id = generate_entity_id("Einstein", "PERSON")
        
        # Create first time
        neo_repo.create_entity(entity_id=entity_id, text="Einstein", entity_type="PERSON")
        entity1 = neo_repo.get_entity(entity_id)
        assert entity1["mention_count"] == 1
        
        # Create again (should increment count)
        neo_repo.create_entity(entity_id=entity_id, text="Einstein", entity_type="PERSON")
        entity2 = neo_repo.get_entity(entity_id)
        assert entity2["mention_count"] == 2
    
    def test_different_entity_types(self, neo_repo):
        """Test that same text with different types creates different entities."""
        # "Washington" as person
        person_id = generate_entity_id("Washington", "PERSON")
        neo_repo.create_entity(person_id, "Washington", "PERSON")
        
        # "Washington" as place
        place_id = generate_entity_id("Washington", "GPE")
        neo_repo.create_entity(place_id, "Washington", "GPE")
        
        # Should have 2 distinct entities
        count = neo_repo.get_node_count("Entity")
        assert count == 2


class TestMentionOperations:
    """Test Mention nodes and relationships."""
    
    def test_create_mention(self, neo_repo):
        """Test creating a mention linking chunk to entity."""
        # Setup: document, chunk, entity
        url = "https://example.com/doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="Einstein was a physicist.",
            start_offset=0,
            end_offset=26
        )
        
        entity_id = generate_entity_id("Einstein", "PERSON")
        neo_repo.create_entity(entity_id=entity_id, text="Einstein", entity_type="PERSON")
        
        # Create mention
        mention_id = generate_mention_id(chunk_id, "Einstein", 0)
        mention = neo_repo.create_mention(
            mention_id=mention_id,
            chunk_id=chunk_id,
            entity_id=entity_id,
            offset_in_chunk=0,
            confidence=0.98
        )
        
        assert mention is not None
        assert mention["id"] == mention_id
        assert mention["offset_in_chunk"] == 0
        assert mention["confidence"] == 0.98
    
    def test_mention_relationships(self, neo_repo):
        """Test that mention has FOUND_IN and REFERS_TO relationships."""
        # Setup
        url = "https://example.com/doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="Einstein text",
            start_offset=0,
            end_offset=13
        )
        
        entity_id = generate_entity_id("Einstein", "PERSON")
        neo_repo.create_entity(entity_id=entity_id, text="Einstein", entity_type="PERSON")
        
        mention_id = generate_mention_id(chunk_id, "Einstein", 0)
        neo_repo.create_mention(
            mention_id=mention_id,
            chunk_id=chunk_id,
            entity_id=entity_id,
            offset_in_chunk=0
        )
        
        # Query relationships
        query = """
        MATCH (m:Mention {id: $mention_id})-[:FOUND_IN]->(c:Chunk)
        MATCH (m)-[:REFERS_TO]->(e:Entity)
        RETURN c.id as chunk_id, e.id as entity_id
        """
        result = neo_repo.execute_query(query, {"mention_id": mention_id})
        
        assert len(result) == 1
        assert result[0]["chunk_id"] == chunk_id
        assert result[0]["entity_id"] == entity_id
    
    def test_get_entity_mentions(self, neo_repo):
        """Test retrieving all mentions of an entity."""
        # Create 2 documents with same entity
        urls = ["https://example.com/doc1", "https://example.com/doc2"]
        doc_ids = []
        chunk_ids = []
        
        for url in urls:
            doc_id = generate_doc_id(url)
            doc_ids.append(doc_id)
            neo_repo.create_document(doc_id=doc_id, url=url, title="Doc")
            
            chunk_id = generate_chunk_id(doc_id, 0)
            chunk_ids.append(chunk_id)
            neo_repo.create_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text="Einstein was here",
                start_offset=0,
                end_offset=17
            )
        
        # Create entity
        entity_id = generate_entity_id("Einstein", "PERSON")
        neo_repo.create_entity(entity_id=entity_id, text="Einstein", entity_type="PERSON")
        
        # Create mentions in both chunks
        for chunk_id in chunk_ids:
            mention_id = generate_mention_id(chunk_id, "Einstein", 0)
            neo_repo.create_mention(
                mention_id=mention_id,
                chunk_id=chunk_id,
                entity_id=entity_id,
                offset_in_chunk=0
            )
        
        # Get all mentions
        mentions = neo_repo.get_entity_mentions(entity_id)
        
        assert len(mentions) == 2
        # Each result should have mention, chunk, and document
        assert all("m" in m and "c" in m and "d" in m for m in mentions)


class TestProvenanceGraph:
    """Test the full provenance graph structure."""
    
    def test_complete_provenance_chain(self, neo_repo):
        """Test creating complete chain: Document -> Chunk -> Mention -> Entity."""
        # Document
        url = "https://example.com/article"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Article")
        
        # Chunk
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="Albert Einstein published his theory in 1905.",
            start_offset=0,
            end_offset=46,
            page_number=1
        )
        
        # Entities
        person_id = generate_entity_id("Albert Einstein", "PERSON")
        neo_repo.create_entity(person_id, "Albert Einstein", "PERSON")
        
        date_id = generate_entity_id("1905", "DATE")
        neo_repo.create_entity(date_id, "1905", "DATE")
        
        # Mentions
        mention1_id = generate_mention_id(chunk_id, "Albert Einstein", 0)
        neo_repo.create_mention(mention1_id, chunk_id, person_id, 0)
        
        mention2_id = generate_mention_id(chunk_id, "1905", 41)
        neo_repo.create_mention(mention2_id, chunk_id, date_id, 41)
        
        # Query full graph
        query = """
        MATCH path = (d:Document)<-[:PART_OF]-(c:Chunk)<-[:FOUND_IN]-(m:Mention)-[:REFERS_TO]->(e:Entity)
        WHERE d.id = $doc_id
        RETURN count(path) as path_count
        """
        result = neo_repo.execute_query(query, {"doc_id": doc_id})
        
        # Should have 2 complete paths (one for each entity mention)
        assert result[0]["path_count"] == 2
    
    def test_trace_claim_to_source(self, neo_repo):
        """Test tracing a claim back to exact document location."""
        # Setup complete provenance
        url = "https://example.com/research.pdf"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Research Paper")
        
        chunk_id = generate_chunk_id(doc_id, 12450)  # Specific byte offset
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="The study found a 23% improvement.",
            start_offset=12450,
            end_offset=12485,
            page_number=47
        )
        
        entity_id = generate_entity_id("23%", "PERCENT")
        neo_repo.create_entity(entity_id, "23%", "PERCENT")
        
        mention_id = generate_mention_id(chunk_id, "23%", 16)
        neo_repo.create_mention(mention_id, chunk_id, entity_id, 16)
        
        # Trace back: Given entity mention, find source
        query = """
        MATCH (e:Entity {id: $entity_id})<-[:REFERS_TO]-(m:Mention)
              -[:FOUND_IN]->(c:Chunk)-[:PART_OF]->(d:Document)
        RETURN 
            d.url as source_url,
            d.title as source_title,
            c.page_number as page,
            c.start_offset as byte_offset,
            c.text as context,
            m.offset_in_chunk as char_offset
        """
        result = neo_repo.execute_query(query, {"entity_id": entity_id})
        
        assert len(result) == 1
        trace = result[0]
        
        # Can trace claim to exact location
        assert trace["source_url"] == url
        assert trace["source_title"] == "Research Paper"
        assert trace["page"] == 47
        assert trace["byte_offset"] == 12450
        assert trace["char_offset"] == 16
        assert "23% improvement" in trace["context"]
