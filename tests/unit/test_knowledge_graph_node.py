"""Unit tests for KnowledgeGraphNode Pydantic model.

Following TDD RED-GREEN-REFACTOR cycle.
"""
from datetime import datetime
import pytest
from pydantic import ValidationError
from app.core.models import KnowledgeGraphNode


class TestKnowledgeGraphNode:
    """Test suite for KnowledgeGraphNode Pydantic model."""

    def test_knowledge_graph_node_valid(self):
        """Test creating valid KnowledgeGraphNode."""
        # Arrange
        data = {
            "node_id": "concept-neural-networks",
            "label": "Neural Networks",
            "node_type": "concept",
            "properties": {
                "description": "Artificial neural networks for deep learning",
                "importance": "high"
            },
            "created_at": datetime(2025, 10, 9, 12, 0, 0)
        }
        
        # Act
        node = KnowledgeGraphNode(**data)
        
        # Assert
        assert node.node_id == "concept-neural-networks"
        assert node.label == "Neural Networks"
        assert node.node_type == "concept"
        assert node.properties["importance"] == "high"

    def test_knowledge_graph_node_types(self):
        """Test valid node types."""
        valid_types = ["concept", "topic", "person", "organization", "technology"]
        
        for node_type in valid_types:
            node = KnowledgeGraphNode(
                node_id=f"test-{node_type}",
                label=f"Test {node_type}",
                node_type=node_type,
                properties={}
            )
            assert node.node_type == node_type

    def test_knowledge_graph_node_id_required(self):
        """Test that node_id is required and non-empty."""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGraphNode(
                label="Test",
                node_type="concept",
                properties={}
            )
        assert "node_id" in str(exc_info.value).lower()
        
        # Empty node_id
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGraphNode(
                node_id="",
                label="Test",
                node_type="concept",
                properties={}
            )
        assert "node_id" in str(exc_info.value).lower()

    def test_knowledge_graph_node_label_required(self):
        """Test that label is required and non-empty."""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGraphNode(
                node_id="test-node",
                node_type="concept",
                properties={}
            )
        assert "label" in str(exc_info.value).lower()

    def test_knowledge_graph_node_properties_optional(self):
        """Test that properties can be empty dict."""
        node = KnowledgeGraphNode(
            node_id="simple-node",
            label="Simple Node",
            node_type="concept",
            properties={}
        )
        assert node.properties == {}

    def test_knowledge_graph_node_with_properties(self):
        """Test node with various properties."""
        node = KnowledgeGraphNode(
            node_id="complex-node",
            label="Complex Concept",
            node_type="concept",
            properties={
                "description": "A complex multi-faceted concept",
                "tags": ["ai", "ml", "deep-learning"],
                "confidence": 0.95,
                "source_count": 5
            }
        )
        assert node.properties["confidence"] == 0.95
        assert len(node.properties["tags"]) == 3

    def test_knowledge_graph_node_created_at_defaults(self):
        """Test that created_at defaults to current time."""
        before = datetime.now()
        
        node = KnowledgeGraphNode(
            node_id="test-node",
            label="Test",
            node_type="topic",
            properties={}
        )
        
        after = datetime.now()
        assert before <= node.created_at <= after

    def test_knowledge_graph_node_json_serialization(self):
        """Test JSON serialization."""
        node = KnowledgeGraphNode(
            node_id="serialize-test",
            label="Serialization Test",
            node_type="technology",
            properties={"version": "2.0"},
            created_at=datetime(2025, 10, 9, 12, 0, 0)
        )
        
        json_data = node.model_dump()
        assert json_data["node_id"] == "serialize-test"
        assert json_data["node_type"] == "technology"

    def test_knowledge_graph_node_person(self):
        """Test node representing a person."""
        node = KnowledgeGraphNode(
            node_id="person-geoffrey-hinton",
            label="Geoffrey Hinton",
            node_type="person",
            properties={
                "role": "AI Researcher",
                "affiliation": "University of Toronto",
                "known_for": "Deep Learning"
            }
        )
        assert node.label == "Geoffrey Hinton"
        assert node.properties["role"] == "AI Researcher"

    def test_knowledge_graph_node_organization(self):
        """Test node representing an organization."""
        node = KnowledgeGraphNode(
            node_id="org-openai",
            label="OpenAI",
            node_type="organization",
            properties={
                "founded": "2015",
                "focus": "AI Safety and Research"
            }
        )
        assert node.node_type == "organization"
