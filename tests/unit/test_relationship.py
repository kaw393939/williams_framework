"""Unit tests for Relationship Pydantic model.

Following TDD RED-GREEN-REFACTOR cycle.
"""
from datetime import datetime
import pytest
from pydantic import ValidationError
from app.core.models import Relationship


class TestRelationship:
    """Test suite for Relationship Pydantic model."""

    def test_relationship_valid(self):
        """Test creating valid Relationship."""
        data = {
            "source_id": "node-1",
            "target_id": "node-2",
            "relationship_type": "related_to",
            "weight": 0.8,
            "created_at": datetime(2025, 10, 9, 12, 0, 0)
        }
        
        rel = Relationship(**data)
        
        assert rel.source_id == "node-1"
        assert rel.target_id == "node-2"
        assert rel.relationship_type == "related_to"
        assert rel.weight == 0.8

    def test_relationship_types(self):
        """Test valid relationship types."""
        types = ["related_to", "mentions", "references", "derived_from", "similar_to"]
        
        for rel_type in types:
            rel = Relationship(
                source_id="source",
                target_id="target",
                relationship_type=rel_type,
                weight=0.5
            )
            assert rel.relationship_type == rel_type

    def test_relationship_weight_bounds(self):
        """Test weight must be between 0 and 1."""
        # Below bounds
        with pytest.raises(ValidationError):
            Relationship(
                source_id="a",
                target_id="b",
                relationship_type="related_to",
                weight=-0.1
            )
        
        # Above bounds
        with pytest.raises(ValidationError):
            Relationship(
                source_id="a",
                target_id="b",
                relationship_type="related_to",
                weight=1.1
            )
        
        # Valid bounds
        rel_min = Relationship(
            source_id="a",
            target_id="b",
            relationship_type="related_to",
            weight=0.0
        )
        assert rel_min.weight == 0.0
        
        rel_max = Relationship(
            source_id="a",
            target_id="b",
            relationship_type="related_to",
            weight=1.0
        )
        assert rel_max.weight == 1.0

    def test_relationship_ids_required(self):
        """Test source_id and target_id are required."""
        with pytest.raises(ValidationError):
            Relationship(
                target_id="target",
                relationship_type="related_to",
                weight=0.5
            )
        
        with pytest.raises(ValidationError):
            Relationship(
                source_id="source",
                relationship_type="related_to",
                weight=0.5
            )

    def test_relationship_created_at_defaults(self):
        """Test created_at defaults to current time."""
        before = datetime.now()
        
        rel = Relationship(
            source_id="a",
            target_id="b",
            relationship_type="mentions",
            weight=0.7
        )
        
        after = datetime.now()
        assert before <= rel.created_at <= after

    def test_relationship_json_serialization(self):
        """Test JSON serialization."""
        rel = Relationship(
            source_id="concept-ai",
            target_id="concept-ml",
            relationship_type="related_to",
            weight=0.95,
            created_at=datetime(2025, 10, 9, 12, 0, 0)
        )
        
        json_data = rel.model_dump()
        assert json_data["source_id"] == "concept-ai"
        assert json_data["weight"] == 0.95
