"""Unit tests for RelationExtractionService utility methods."""
import pytest
from unittest.mock import Mock

from app.services.relation_extraction_service import RelationExtractionService


class TestRelationExtractionServiceUtilities:
    """Test utility methods in RelationExtractionService."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing utilities."""
        mock_repo = Mock()
        return RelationExtractionService(neo_repo=mock_repo)

    def test_calculate_confidence_strong_founded(self, service):
        """Test high confidence for FOUNDED with strong pattern."""
        confidence = service._calculate_relation_confidence("FOUNDED", "founded")
        assert confidence == 0.95

    def test_calculate_confidence_strong_cofounded(self, service):
        """Test high confidence for co-founded pattern."""
        confidence = service._calculate_relation_confidence("FOUNDED", "co-founded")
        assert confidence == 0.95

    def test_calculate_confidence_strong_employed_by(self, service):
        """Test high confidence for EMPLOYED_BY pattern."""
        confidence = service._calculate_relation_confidence("EMPLOYED_BY", "works at")
        assert confidence == 0.95

    def test_calculate_confidence_strong_located_headquartered(self, service):
        """Test high confidence for headquartered in pattern."""
        confidence = service._calculate_relation_confidence("LOCATED_IN", "headquartered in")
        assert confidence == 0.95

    def test_calculate_confidence_weak_located_in(self, service):
        """Test lower confidence for ambiguous 'in'."""
        confidence = service._calculate_relation_confidence("LOCATED_IN", "in")
        assert confidence == 0.7

    def test_calculate_confidence_default(self, service):
        """Test default medium confidence."""
        confidence = service._calculate_relation_confidence("UNKNOWN", "some text")
        assert confidence == 0.85

    def test_calculate_confidence_case_insensitive(self, service):
        """Test that matching is case-insensitive."""
        confidence = service._calculate_relation_confidence("FOUNDED", "FOUNDED")
        assert confidence == 0.95

    def test_extract_temporal_info_with_year(self, service):
        """Test extracting year from text."""
        result = service._extract_temporal_info("Founded in 2020")
        assert result["year"] == "2020"

    def test_extract_temporal_info_multiple_years(self, service):
        """Test extracting first year when multiple present."""
        result = service._extract_temporal_info("Between 1999 and 2020")
        assert result["year"] in ["1999", "2020"]

    def test_extract_temporal_info_no_year(self, service):
        """Test when no year is present."""
        result = service._extract_temporal_info("No date here")
        assert result == {}

    def test_extract_temporal_info_nineteenth_century(self, service):
        """Test extracting 19th century year."""
        result = service._extract_temporal_info("In 1985 something happened")
        assert result["year"] == "1985"

    def test_extract_temporal_info_twenty_first_century(self, service):
        """Test extracting 21st century year."""
        result = service._extract_temporal_info("Since 2024")
        assert result["year"] == "2024"
