"""Unit tests for ScreeningResult Pydantic model.

Following TDD RED-GREEN-REFACTOR cycle.
This test should FAIL initially since ScreeningResult doesn't exist yet.
"""
import pytest
from pydantic import ValidationError

from app.core.models import ScreeningResult


class TestScreeningResult:
    """Test suite for ScreeningResult Pydantic model."""

    def test_screening_result_valid_accept(self):
        """Test creating valid ScreeningResult with ACCEPT decision."""
        # Arrange
        data = {
            "screening_score": 8.5,
            "decision": "ACCEPT",
            "reasoning": "High quality content with clear value",
            "estimated_quality": 8.7
        }

        # Act
        result = ScreeningResult(**data)

        # Assert
        assert result.screening_score == 8.5
        assert result.decision == "ACCEPT"
        assert result.reasoning == "High quality content with clear value"
        assert result.estimated_quality == 8.7

    def test_screening_result_valid_reject(self):
        """Test creating valid ScreeningResult with REJECT decision."""
        # Arrange
        data = {
            "screening_score": 3.2,
            "decision": "REJECT",
            "reasoning": "Low quality content with minimal value",
            "estimated_quality": 3.0
        }

        # Act
        result = ScreeningResult(**data)

        # Assert
        assert result.screening_score == 3.2
        assert result.decision == "REJECT"
        assert result.estimated_quality == 3.0

    def test_screening_result_score_validation_bounds(self):
        """Test that screening_score must be between 0 and 10."""
        # Test lower bound violation
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=-1.0,
                decision="REJECT",
                reasoning="Invalid",
                estimated_quality=0.0
            )
        assert "screening_score" in str(exc_info.value)

        # Test upper bound violation
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=11.0,
                decision="ACCEPT",
                reasoning="Invalid",
                estimated_quality=10.0
            )
        assert "screening_score" in str(exc_info.value)

        # Test valid boundaries
        result_min = ScreeningResult(
            screening_score=0.0,
            decision="REJECT",
            reasoning="Minimum score",
            estimated_quality=0.0
        )
        assert result_min.screening_score == 0.0

        result_max = ScreeningResult(
            screening_score=10.0,
            decision="ACCEPT",
            reasoning="Maximum score",
            estimated_quality=10.0
        )
        assert result_max.screening_score == 10.0

    def test_screening_result_quality_validation_bounds(self):
        """Test that estimated_quality must be between 0 and 10."""
        # Test lower bound violation
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=5.0,
                decision="MAYBE",
                reasoning="Invalid quality",
                estimated_quality=-0.5
            )
        assert "estimated_quality" in str(exc_info.value)

        # Test upper bound violation
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=5.0,
                decision="MAYBE",
                reasoning="Invalid quality",
                estimated_quality=10.5
            )
        assert "estimated_quality" in str(exc_info.value)

    def test_screening_result_decision_validation(self):
        """Test that decision must be ACCEPT, REJECT, or MAYBE."""
        # Valid decisions
        for decision in ["ACCEPT", "REJECT", "MAYBE"]:
            result = ScreeningResult(
                screening_score=5.0,
                decision=decision,
                reasoning=f"Testing {decision}",
                estimated_quality=5.0
            )
            assert result.decision == decision

        # Invalid decision
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=5.0,
                decision="INVALID",
                reasoning="Invalid decision",
                estimated_quality=5.0
            )
        assert "decision" in str(exc_info.value)

    def test_screening_result_reasoning_required(self):
        """Test that reasoning is required and must be non-empty."""
        # Missing reasoning
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=5.0,
                decision="ACCEPT",
                estimated_quality=5.0
            )
        assert "reasoning" in str(exc_info.value)

        # Empty reasoning
        with pytest.raises(ValidationError) as exc_info:
            ScreeningResult(
                screening_score=5.0,
                decision="ACCEPT",
                reasoning="",
                estimated_quality=5.0
            )
        assert "reasoning" in str(exc_info.value)

    def test_screening_result_json_serialization(self):
        """Test that ScreeningResult can be serialized to JSON."""
        # Arrange
        result = ScreeningResult(
            screening_score=7.5,
            decision="ACCEPT",
            reasoning="Good content",
            estimated_quality=7.8
        )

        # Act
        json_data = result.model_dump()

        # Assert
        assert json_data["screening_score"] == 7.5
        assert json_data["decision"] == "ACCEPT"
        assert json_data["reasoning"] == "Good content"
        assert json_data["estimated_quality"] == 7.8

    def test_screening_result_from_json(self):
        """Test creating ScreeningResult from JSON data."""
        # Arrange
        json_data = {
            "screening_score": 6.5,
            "decision": "MAYBE",
            "reasoning": "Needs review",
            "estimated_quality": 6.0
        }

        # Act
        result = ScreeningResult(**json_data)

        # Assert
        assert result.screening_score == 6.5
        assert result.decision == "MAYBE"

    def test_screening_result_immutability(self):
        """Test that ScreeningResult is immutable (frozen)."""
        # Arrange
        result = ScreeningResult(
            screening_score=8.0,
            decision="ACCEPT",
            reasoning="Test",
            estimated_quality=8.0
        )

        # Act & Assert
        with pytest.raises((ValidationError, AttributeError)):
            result.screening_score = 9.0
