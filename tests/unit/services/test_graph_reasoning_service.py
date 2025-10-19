"""Unit tests for GraphReasoningService."""

import pytest
from unittest.mock import Mock, MagicMock

from app.services.graph_reasoning_service import GraphReasoningService


@pytest.fixture
def mock_neo_repo():
    """Create mock Neo4j repository."""
    return Mock()


@pytest.fixture
def graph_service(mock_neo_repo):
    """Create GraphReasoningService instance."""
    return GraphReasoningService(mock_neo_repo)


def test_graph_service_initialization(mock_neo_repo):
    """Test GraphReasoningService initializes correctly."""
    service = GraphReasoningService(mock_neo_repo)
    assert service._neo_repo == mock_neo_repo


def test_get_entity_relationships_basic(graph_service, mock_neo_repo):
    """Test getting entity relationships with default pagination."""
    mock_results = [
        {
            "type": "WORKS_FOR",
            "target_entity": "Apple Inc",
            "target_type": "ORG",
            "confidence": 0.95,
            "evidence": "Steve Jobs works for Apple"
        },
        {
            "type": "FOUNDED",
            "target_entity": "Apple Inc",
            "target_type": "ORG",
            "confidence": 0.9,
            "evidence": "Steve Jobs founded Apple"
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.get_entity_relationships("Steve Jobs")
    
    assert result["total_count"] == 2
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["total_pages"] == 1
    assert len(result["relationships"]) == 2
    assert result["relationships"][0]["type"] == "WORKS_FOR"


def test_get_entity_relationships_with_pagination(graph_service, mock_neo_repo):
    """Test entity relationships with custom pagination."""
    # Create 25 mock relationships
    mock_results = [
        {
            "type": f"REL_{i}",
            "target_entity": f"Entity_{i}",
            "target_type": "PERSON",
            "confidence": 0.8,
            "evidence": f"Evidence {i}"
        }
        for i in range(25)
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    # Get page 2 with page size 10
    result = graph_service.get_entity_relationships(
        "Test Entity",
        page=2,
        page_size=10
    )
    
    assert result["total_count"] == 25
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert result["total_pages"] == 3
    assert len(result["relationships"]) == 10
    # Page 2 should have items 10-19
    assert result["relationships"][0]["type"] == "REL_10"


def test_get_entity_relationships_with_type_filter(graph_service, mock_neo_repo):
    """Test filtering relationships by type."""
    mock_results = []
    mock_neo_repo.execute_query.return_value = mock_results
    
    graph_service.get_entity_relationships(
        "Steve Jobs",
        relationship_type="WORKS_FOR"
    )
    
    # Verify query was called with relationship type filter
    call_args = mock_neo_repo.execute_query.call_args
    query = call_args[0][0]
    assert ":WORKS_FOR" in query


def test_get_entity_relationships_empty_results(graph_service, mock_neo_repo):
    """Test when no relationships found."""
    mock_neo_repo.execute_query.return_value = []
    
    result = graph_service.get_entity_relationships("Unknown Entity")
    
    assert result["total_count"] == 0
    assert len(result["relationships"]) == 0
    assert result["total_pages"] == 0


def test_find_path_between_entities_success(graph_service, mock_neo_repo):
    """Test finding paths between two entities."""
    mock_results = [
        {
            "nodes": ["Steve Jobs", "Apple Inc", "iPhone"],
            "relationships": ["FOUNDED", "CREATED"],
            "path_length": 2
        },
        {
            "nodes": ["Steve Jobs", "NeXT", "Apple Inc", "iPhone"],
            "relationships": ["FOUNDED", "ACQUIRED_BY", "CREATED"],
            "path_length": 3
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.find_path_between_entities(
        "Steve Jobs",
        "iPhone",
        max_depth=5,
        max_paths=3
    )
    
    assert len(result["paths"]) == 2
    assert result["start_entity"] == "Steve Jobs"
    assert result["end_entity"] == "iPhone"
    assert result["max_depth"] == 5
    assert result["paths"][0]["length"] == 2
    assert result["paths"][1]["length"] == 3


def test_find_path_between_entities_no_path(graph_service, mock_neo_repo):
    """Test when no path exists between entities."""
    mock_neo_repo.execute_query.return_value = []
    
    result = graph_service.find_path_between_entities(
        "Entity A",
        "Unrelated Entity"
    )
    
    assert len(result["paths"]) == 0


def test_find_path_between_entities_custom_depth(graph_service, mock_neo_repo):
    """Test path finding with custom max depth."""
    mock_neo_repo.execute_query.return_value = []
    
    graph_service.find_path_between_entities(
        "A",
        "B",
        max_depth=3,
        max_paths=5
    )
    
    # Verify query includes max_depth in MATCH pattern
    call_args = mock_neo_repo.execute_query.call_args
    query = call_args[0][0]
    assert "*..3" in query  # max_depth=3


def test_explain_answer_with_entities(graph_service, mock_neo_repo):
    """Test explaining answer with entity relationships."""
    # Mock graph results
    mock_node1 = {"id": "1", "text": "Python", "entity_type": "TECHNOLOGY"}
    mock_node2 = {"id": "2", "text": "Guido van Rossum", "entity_type": "PERSON"}
    mock_rel = Mock()
    mock_rel.type = "CREATED_BY"
    mock_rel.get = lambda k, default=None: 0.9 if k == "confidence" else default
    
    mock_results = [
        {
            "nodes": [mock_node1, mock_node2],
            "relationships": [mock_rel]
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.explain_answer(
        "Python was created by Guido van Rossum",
        ["Python", "Guido van Rossum"]
    )
    
    assert "graph" in result
    assert len(result["graph"]["nodes"]) >= 2
    assert len(result["graph"]["edges"]) >= 1
    assert result["entity_count"] >= 2
    assert result["evidence"] == "Python was created by Guido van Rossum"


def test_explain_answer_insufficient_entities(graph_service, mock_neo_repo):
    """Test explain answer with less than 2 entities."""
    result = graph_service.explain_answer(
        "Single entity answer",
        ["Python"]
    )
    
    assert result["graph"]["nodes"] == []
    assert result["graph"]["edges"] == []
    assert result["evidence"] == []


def test_explain_answer_no_entities(graph_service, mock_neo_repo):
    """Test explain answer with no entities."""
    result = graph_service.explain_answer("No entities", [])
    
    assert result["graph"]["nodes"] == []
    assert result["graph"]["edges"] == []


def test_explain_answer_builds_edges_correctly(graph_service, mock_neo_repo):
    """Test that edges are constructed with correct source/target."""
    mock_node1 = {"id": "1", "text": "A", "entity_type": "TYPE1"}
    mock_node2 = {"id": "2", "text": "B", "entity_type": "TYPE2"}
    mock_rel = Mock()
    mock_rel.type = "RELATES_TO"
    mock_rel.get = lambda k, default=None: 0.8 if k == "confidence" else default
    
    mock_results = [
        {
            "nodes": [mock_node1, mock_node2],
            "relationships": [mock_rel]
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.explain_answer("Test", ["A", "B"])
    
    edges = result["graph"]["edges"]
    assert len(edges) >= 1
    assert edges[0]["source"] == "A"
    assert edges[0]["target"] == "B"
    assert edges[0]["type"] == "RELATES_TO"
    assert edges[0]["confidence"] == 0.8


def test_find_related_entities_basic(graph_service, mock_neo_repo):
    """Test finding related entities."""
    mock_results = [
        {
            "text": "Apple Inc",
            "entity_type": "ORG",
            "confidence": 0.95,
            "relationship_type": "WORKS_FOR"
        },
        {
            "text": "Steve Wozniak",
            "entity_type": "PERSON",
            "confidence": 0.9,
            "relationship_type": "CO_FOUNDED_WITH"
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.find_related_entities("Steve Jobs")
    
    assert result["total_count"] == 2
    assert len(result["entities"]) == 2
    assert result["entities"][0]["text"] == "Apple Inc"


def test_find_related_entities_with_type_filter(graph_service, mock_neo_repo):
    """Test filtering related entities by type."""
    mock_neo_repo.execute_query.return_value = []
    
    graph_service.find_related_entities(
        "Steve Jobs",
        entity_type_filter="ORG"
    )
    
    # Verify query includes type filter
    call_args = mock_neo_repo.execute_query.call_args
    query = call_args[0][0]
    params = call_args[0][1]
    assert "entity_type" in query or "AND target.entity_type" in query
    assert params.get("entity_type") == "ORG"


def test_find_related_entities_pagination(graph_service, mock_neo_repo):
    """Test pagination of related entities."""
    # Create 15 mock entities
    mock_results = [
        {
            "text": f"Entity_{i}",
            "entity_type": "PERSON",
            "confidence": 0.8,
            "relationship_type": "RELATES_TO"
        }
        for i in range(15)
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.find_related_entities(
        "Central Entity",
        page=2,
        page_size=5
    )
    
    assert result["total_count"] == 15
    assert result["page"] == 2
    assert result["page_size"] == 5
    assert len(result["entities"]) == 5
    assert result["entities"][0]["text"] == "Entity_5"


def test_find_related_entities_custom_sorting(graph_service, mock_neo_repo):
    """Test custom sorting of related entities."""
    mock_neo_repo.execute_query.return_value = []
    
    graph_service.find_related_entities(
        "Entity",
        sort_by="text",
        sort_order="asc"
    )
    
    # Verify query includes sort clause
    call_args = mock_neo_repo.execute_query.call_args
    query = call_args[0][0]
    assert "ORDER BY" in query
    assert "text" in query or "confidence" in query


def test_traverse_graph_basic(graph_service, mock_neo_repo):
    """Test basic graph traversal."""
    mock_results = [
        {
            "nodes": [
                {"id": "1", "text": "A", "entity_type": "TYPE1"},
                {"id": "2", "text": "B", "entity_type": "TYPE2"}
            ],
            "edges": [
                {"type": "RELATES_TO", "confidence": 0.9}
            ],
            "depth": 1
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.traverse_graph("A", max_depth=3)
    
    assert "nodes" in result
    assert "edges" in result
    assert result["max_depth_reached"] == 3
    assert result["node_count"] >= 2
    assert result["edge_count"] >= 1


def test_traverse_graph_deduplicates_nodes(graph_service, mock_neo_repo):
    """Test that traverse_graph deduplicates nodes."""
    # Same node appears in multiple paths
    mock_results = [
        {
            "nodes": [
                {"id": "1", "text": "A", "entity_type": "TYPE1"},
                {"id": "2", "text": "B", "entity_type": "TYPE2"}
            ],
            "edges": [{"type": "REL1", "confidence": 0.9}],
            "depth": 1
        },
        {
            "nodes": [
                {"id": "1", "text": "A", "entity_type": "TYPE1"},
                {"id": "3", "text": "C", "entity_type": "TYPE3"}
            ],
            "edges": [{"type": "REL2", "confidence": 0.8}],
            "depth": 1
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.traverse_graph("A")
    
    # Node A should only appear once
    node_ids = [n.get("id") or n.get("text") for n in result["nodes"]]
    assert len(node_ids) == len(set(node_ids))  # All unique


def test_traverse_graph_custom_depth(graph_service, mock_neo_repo):
    """Test graph traversal with custom depth."""
    mock_neo_repo.execute_query.return_value = []
    
    graph_service.traverse_graph("A", max_depth=5)
    
    # Verify query includes max_depth
    call_args = mock_neo_repo.execute_query.call_args
    query = call_args[0][0]
    assert "*..5" in query


def test_traverse_graph_empty_results(graph_service, mock_neo_repo):
    """Test traversal when no connected entities found."""
    mock_neo_repo.execute_query.return_value = []
    
    result = graph_service.traverse_graph("Isolated Entity")
    
    assert result["node_count"] == 0
    assert result["edge_count"] == 0
    assert result["nodes"] == []
    assert result["edges"] == []


def test_traverse_graph_breadth_first(graph_service, mock_neo_repo):
    """Test specifying breadth-first traversal."""
    mock_neo_repo.execute_query.return_value = []
    
    # Should accept traversal_type parameter
    result = graph_service.traverse_graph(
        "A",
        max_depth=3,
        traversal_type="breadth_first"
    )
    
    # Should complete without error
    assert "nodes" in result
    assert "edges" in result


def test_traverse_graph_depth_first(graph_service, mock_neo_repo):
    """Test specifying depth-first traversal."""
    mock_neo_repo.execute_query.return_value = []
    
    result = graph_service.traverse_graph(
        "A",
        max_depth=3,
        traversal_type="depth_first"
    )
    
    assert "nodes" in result
    assert "edges" in result


def test_explain_answer_handles_multiple_paths(graph_service, mock_neo_repo):
    """Test explain_answer with multiple graph paths."""
    # Create multiple paths
    mock_results = [
        {
            "nodes": [
                {"id": "1", "text": "A", "entity_type": "TYPE1"},
                {"id": "2", "text": "B", "entity_type": "TYPE2"}
            ],
            "relationships": [Mock(type="REL1", get=lambda k, d=None: 0.9 if k == "confidence" else d)]
        },
        {
            "nodes": [
                {"id": "2", "text": "B", "entity_type": "TYPE2"},
                {"id": "3", "text": "C", "entity_type": "TYPE3"}
            ],
            "relationships": [Mock(type="REL2", get=lambda k, d=None: 0.8 if k == "confidence" else d)]
        }
    ]
    mock_neo_repo.execute_query.return_value = mock_results
    
    result = graph_service.explain_answer("Test", ["A", "B", "C"])
    
    # Should collect nodes from all paths
    assert result["entity_count"] >= 3
    assert len(result["graph"]["edges"]) >= 2


def test_find_path_between_entities_respects_max_paths(graph_service, mock_neo_repo):
    """Test that max_paths parameter is used in query."""
    mock_neo_repo.execute_query.return_value = []
    
    graph_service.find_path_between_entities(
        "A",
        "B",
        max_paths=10
    )
    
    # Verify LIMIT is set to max_paths
    call_args = mock_neo_repo.execute_query.call_args
    query = call_args[0][0]
    params = call_args[0][1]
    assert params.get("max_paths") == 10
