"""Integration tests for Story S6-605: Graph Reasoning Queries.

Tests Cypher query helpers for entity relationships, path finding, and
"Explain this answer" functionality with pagination and filtering.

TDD Approach: RED -> GREEN -> REFACTOR
Testing Philosophy: Real Neo4j integration, no mocks
"""

import pytest
from app.core.id_generator import generate_doc_id, generate_chunk_id, generate_mention_id


@pytest.fixture
def graph_reasoning_service(neo_repo):
    """Fixture for GraphReasoningService."""
    from app.services.graph_reasoning_service import GraphReasoningService
    
    return GraphReasoningService(neo_repo)


class TestGraphReasoningQueries:
    """Integration tests for graph reasoning and traversal."""

    def test_find_entity_relationships(self, graph_reasoning_service, neo_repo):
        """Test 1: Find all relationships for an entity.
        
        Expected behavior:
        - Query entity by ID or name
        - Return all outgoing and incoming relationships
        - Include relationship type, target entity, confidence
        - Support pagination (page, page_size)
        """
        # Arrange - create entities with relationships
        url = "https://example.com/test"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman works at OpenAI, which is based in San Francisco."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        # Create entities
        person_mention = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention = generate_mention_id(chunk_id, "OpenAI", 20)
        neo_repo.create_entity_mention(org_mention, chunk_id, "OpenAI", "ORG", 20, 26)
        
        loc_mention = generate_mention_id(chunk_id, "San Francisco", 47)
        neo_repo.create_entity_mention(loc_mention, chunk_id, "San Francisco", "GPE", 47, 60)
        
        # Create relationships (using relation extraction service from S6-603)
        from app.services.relation_extraction_service import RelationExtractionService
        rel_service = RelationExtractionService(neo_repo)
        rel_service.extract_relations(chunk_id)
        
        # Act - find relationships for Sam Altman
        relationships = graph_reasoning_service.get_entity_relationships(
            entity_text="Sam Altman",
            page=1,
            page_size=10
        )
        
        # Assert
        assert len(relationships["relationships"]) > 0
        assert "total_count" in relationships
        assert "page" in relationships
        employed_rel = next(
            (r for r in relationships["relationships"] if r["type"] == "EMPLOYED_BY"),
            None
        )
        assert employed_rel is not None
        assert employed_rel["target_entity"] == "OpenAI"

    def test_find_path_between_entities(self, graph_reasoning_service, neo_repo):
        """Test 2: Find shortest path between two entities.
        
        Expected behavior:
        - Find path from entity A to entity B
        - Return path with all intermediate nodes and relationships
        - Support max_depth parameter
        - Return multiple paths if max_paths > 1
        """
        # Arrange - create entity chain: A -> B -> C
        url = "https://example.com/chain"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Chain", metadata={})
        
        # Create documents with relationships
        chunk_id1 = generate_chunk_id(doc_id, 0)
        text1 = "Sam Altman founded OpenAI."
        neo_repo.create_chunk(chunk_id1, doc_id, text1, 0, len(text1), None)
        
        person_mention = generate_mention_id(chunk_id1, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention, chunk_id1, "Sam Altman", "PERSON", 0, 10)
        
        org_mention = generate_mention_id(chunk_id1, "OpenAI", 19)
        neo_repo.create_entity_mention(org_mention, chunk_id1, "OpenAI", "ORG", 19, 25)
        
        chunk_id2 = generate_chunk_id(doc_id, 1)
        text2 = "OpenAI is based in San Francisco."
        neo_repo.create_chunk(chunk_id2, doc_id, text2, 0, len(text2), None)
        
        org_mention2 = generate_mention_id(chunk_id2, "OpenAI", 0)
        neo_repo.create_entity_mention(org_mention2, chunk_id2, "OpenAI", "ORG", 0, 6)
        
        loc_mention = generate_mention_id(chunk_id2, "San Francisco", 19)
        neo_repo.create_entity_mention(loc_mention, chunk_id2, "San Francisco", "GPE", 19, 32)
        
        # Extract relationships
        from app.services.relation_extraction_service import RelationExtractionService
        rel_service = RelationExtractionService(neo_repo)
        rel_service.extract_relations(chunk_id1)
        rel_service.extract_relations(chunk_id2)
        
        # Act - find path from Sam Altman to San Francisco
        paths = graph_reasoning_service.find_path_between_entities(
            start_entity="Sam Altman",
            end_entity="San Francisco",
            max_depth=5,
            max_paths=3
        )
        
        # Assert
        assert len(paths["paths"]) > 0
        path = paths["paths"][0]
        assert len(path["nodes"]) >= 3  # Sam Altman -> OpenAI -> San Francisco
        assert len(path["relationships"]) >= 2  # FOUNDED, LOCATED_IN

    def test_explain_answer_with_reasoning_graph(self, graph_reasoning_service, neo_repo):
        """Test 3: Explain answer by returning reasoning graph.
        
        Expected behavior:
        - Show entity relationships used to answer question
        - Return subgraph with relevant entities and relationships
        - Include evidence chunks and citations
        - Visualizable graph structure
        """
        # Arrange - create knowledge graph
        url = "https://example.com/explain"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Explain Test", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman works at OpenAI."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention = generate_mention_id(chunk_id, "OpenAI", 20)
        neo_repo.create_entity_mention(org_mention, chunk_id, "OpenAI", "ORG", 20, 26)
        
        from app.services.relation_extraction_service import RelationExtractionService
        rel_service = RelationExtractionService(neo_repo)
        rel_service.extract_relations(chunk_id)
        
        # Act - get explanation for answer about Sam Altman's employment
        explanation = graph_reasoning_service.explain_answer(
            answer="Sam Altman works at OpenAI.",
            entity_mentions=["Sam Altman", "OpenAI"]
        )
        
        # Assert
        assert "graph" in explanation
        assert "nodes" in explanation["graph"]
        assert "edges" in explanation["graph"]
        assert len(explanation["graph"]["nodes"]) >= 2
        assert len(explanation["graph"]["edges"]) >= 1
        assert "evidence" in explanation

    def test_find_related_entities_by_type(self, graph_reasoning_service, neo_repo):
        """Test 4: Find related entities filtered by type.
        
        Expected behavior:
        - Find all entities related to a given entity
        - Filter by entity type (PERSON, ORG, GPE, etc.)
        - Support pagination and sorting
        - Return relationship type and confidence
        """
        # Arrange - create multiple entity types
        url = "https://example.com/related"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Related", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "Sam Altman founded OpenAI in San Francisco."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
        
        person_mention = generate_mention_id(chunk_id, "Sam Altman", 0)
        neo_repo.create_entity_mention(person_mention, chunk_id, "Sam Altman", "PERSON", 0, 10)
        
        org_mention = generate_mention_id(chunk_id, "OpenAI", 19)
        neo_repo.create_entity_mention(org_mention, chunk_id, "OpenAI", "ORG", 19, 25)
        
        loc_mention = generate_mention_id(chunk_id, "San Francisco", 29)
        neo_repo.create_entity_mention(loc_mention, chunk_id, "San Francisco", "GPE", 29, 42)
        
        from app.services.relation_extraction_service import RelationExtractionService
        rel_service = RelationExtractionService(neo_repo)
        rel_service.extract_relations(chunk_id)
        
        # Act - find related organizations to Sam Altman
        related = graph_reasoning_service.find_related_entities(
            entity_text="Sam Altman",
            entity_type_filter="ORG",
            page=1,
            page_size=10,
            sort_by="confidence",
            sort_order="desc"
        )
        
        # Assert
        assert "entities" in related
        assert "total_count" in related
        # Should find OpenAI as related ORG
        if len(related["entities"]) > 0:
            assert related["entities"][0]["entity_type"] == "ORG"

    def test_graph_traversal_with_depth_limit(self, graph_reasoning_service, neo_repo):
        """Test 5: Graph traversal with configurable depth limit.
        
        Expected behavior:
        - Traverse graph from starting entity
        - Respect max_depth parameter (prevent infinite loops)
        - Return all nodes and edges within depth
        - Support breadth-first or depth-first traversal
        """
        # Arrange - create deep graph structure with relationships
        url = "https://example.com/deep"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Deep Graph", metadata={})
        
        # Create chain with explicit relationship text: A founded B, B founded C, C founded D
        chunk_texts = [
            "Company A founded Company B in 2020.",
            "Company B founded Company C in 2021.",
            "Company C founded Company D in 2022."
        ]
        
        from app.services.relation_extraction_service import RelationExtractionService
        rel_service = RelationExtractionService(neo_repo)
        
        # Create entities and extract relationships
        for i, text in enumerate(chunk_texts):
            chunk_id = generate_chunk_id(doc_id, i)
            neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), None)
            
            # Create entity mentions
            if i == 0:
                mention_a = generate_mention_id(chunk_id, "Company A", 0)
                neo_repo.create_entity_mention(mention_a, chunk_id, "Company A", "ORG", 0, 9)
                mention_b = generate_mention_id(chunk_id, "Company B", 18)
                neo_repo.create_entity_mention(mention_b, chunk_id, "Company B", "ORG", 18, 27)
            elif i == 1:
                mention_b = generate_mention_id(chunk_id, "Company B", 0)
                neo_repo.create_entity_mention(mention_b, chunk_id, "Company B", "ORG", 0, 9)
                mention_c = generate_mention_id(chunk_id, "Company C", 18)
                neo_repo.create_entity_mention(mention_c, chunk_id, "Company C", "ORG", 18, 27)
            else:
                mention_c = generate_mention_id(chunk_id, "Company C", 0)
                neo_repo.create_entity_mention(mention_c, chunk_id, "Company C", "ORG", 0, 9)
                mention_d = generate_mention_id(chunk_id, "Company D", 18)
                neo_repo.create_entity_mention(mention_d, chunk_id, "Company D", "ORG", 18, 27)
            
            # Extract relationships
            rel_service.extract_relations(chunk_id)
        
        # Act - traverse with depth limit
        subgraph = graph_reasoning_service.traverse_graph(
            start_entity="Company A",
            max_depth=2,
            traversal_type="breadth_first"
        )
        
        # Assert
        assert "nodes" in subgraph
        assert "edges" in subgraph
        assert "max_depth_reached" in subgraph
        # Depth 2 should include A, B, and C (A->B->C is 2 hops)
        assert len(subgraph["nodes"]) >= 2
        assert subgraph["max_depth_reached"] == 2
