"""Unit tests for LibraryService utility methods and tier logic."""
import pytest

from app.services.library_service import LibraryService


class TestLibraryServiceUtilities:
    """Test utility methods in LibraryService."""

    def test_determine_tier_a(self):
        """Test tier determination for high quality content (tier-a)."""
        assert LibraryService._determine_tier(9.5) == "tier-a"
        assert LibraryService._determine_tier(9.0) == "tier-a"
        assert LibraryService._determine_tier(10.0) == "tier-a"

    def test_determine_tier_b(self):
        """Test tier determination for good quality content (tier-b)."""
        assert LibraryService._determine_tier(8.9) == "tier-b"
        assert LibraryService._determine_tier(7.0) == "tier-b"
        assert LibraryService._determine_tier(8.0) == "tier-b"

    def test_determine_tier_c(self):
        """Test tier determination for moderate quality content (tier-c)."""
        assert LibraryService._determine_tier(6.9) == "tier-c"
        assert LibraryService._determine_tier(5.0) == "tier-c"
        assert LibraryService._determine_tier(6.0) == "tier-c"

    def test_determine_tier_d(self):
        """Test tier determination for low quality content (tier-d)."""
        assert LibraryService._determine_tier(4.9) == "tier-d"
        assert LibraryService._determine_tier(0.0) == "tier-d"
        assert LibraryService._determine_tier(2.5) == "tier-d"

    def test_extract_tier_letter(self):
        """Test extraction of tier letter from tier identifier."""
        assert LibraryService._extract_tier_letter("tier-a") == "a"
        assert LibraryService._extract_tier_letter("tier-b") == "b"
        assert LibraryService._extract_tier_letter("tier-c") == "c"
        assert LibraryService._extract_tier_letter("tier-d") == "d"

    def test_get_bucket_prefix_with_tier_suffix(self):
        """Test bucket prefix extraction when tier suffix is present."""
        assert LibraryService._get_bucket_prefix("test-library-a") == "test-library"
        assert LibraryService._get_bucket_prefix("test-library-b") == "test-library"
        assert LibraryService._get_bucket_prefix("my-bucket-c") == "my-bucket"
        assert LibraryService._get_bucket_prefix("librarian-d") == "librarian"

    def test_get_bucket_prefix_without_tier_suffix(self):
        """Test bucket prefix extraction when no tier suffix is present."""
        assert LibraryService._get_bucket_prefix("test-library") == "test-library"
        assert LibraryService._get_bucket_prefix("my-bucket") == "my-bucket"
        assert LibraryService._get_bucket_prefix("simple") == "simple"

    def test_get_bucket_prefix_with_ambiguous_name(self):
        """Test bucket prefix with names that could be confused with tier suffixes."""
        # These should NOT be treated as tier suffixes (not at the very end)
        assert LibraryService._get_bucket_prefix("test-a-library") == "test-a-library"
        assert LibraryService._get_bucket_prefix("bucket-d-name") == "bucket-d-name"
