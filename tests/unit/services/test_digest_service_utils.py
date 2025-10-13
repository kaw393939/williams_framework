"""Unit tests for DigestService utility methods."""
import json
import pytest

from app.services.digest_service import DigestService


class TestDigestServiceUtilities:
    """Test utility methods in DigestService."""

    def test_parse_metadata_with_dict(self):
        """Test parsing metadata when it's already a dict."""
        metadata = {"key": "value", "count": 42}
        result = DigestService._parse_metadata(metadata)
        assert result == metadata

    def test_parse_metadata_with_json_string(self):
        """Test parsing metadata from JSON string."""
        metadata_dict = {"author": "Test", "year": 2024}
        metadata_str = json.dumps(metadata_dict)
        result = DigestService._parse_metadata(metadata_str)
        assert result == metadata_dict

    def test_parse_metadata_empty_dict(self):
        """Test parsing empty metadata dict."""
        result = DigestService._parse_metadata({})
        assert result == {}

    def test_parse_metadata_empty_json_string(self):
        """Test parsing empty JSON string."""
        result = DigestService._parse_metadata("{}")
        assert result == {}

    def test_format_tags_html_single_tag(self):
        """Test formatting a single tag."""
        result = DigestService._format_tags_html(["python"])
        assert "python" in result
        assert 'background-color: #e5e7eb' in result
        assert 'span' in result

    def test_format_tags_html_multiple_tags(self):
        """Test formatting multiple tags."""
        tags = ["python", "testing", "coverage"]
        result = DigestService._format_tags_html(tags)
        for tag in tags:
            assert tag in result
        # Should have 3 spans
        assert result.count('<span') == 3

    def test_format_tags_html_empty_list(self):
        """Test formatting empty tag list."""
        result = DigestService._format_tags_html([])
        assert result == ""

    def test_format_tags_html_special_characters(self):
        """Test formatting tags with special characters."""
        tags = ["C++", "data-science", "AI/ML"]
        result = DigestService._format_tags_html(tags)
        for tag in tags:
            assert tag in result
