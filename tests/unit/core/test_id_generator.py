"""
Tests for deterministic ID generation.

Tests the core ID generation functions that enable provenance tracking.
All tests verify determinism and handle edge cases.
"""

from app.core.id_generator import (
    generate_chunk_id,
    generate_doc_id,
    generate_entity_id,
    generate_file_id,
    generate_mention_id,
    normalize_url,
)


class TestURLNormalization:
    """Test URL normalization for deterministic document IDs."""

    def test_normalize_url_basic(self):
        """Test basic URL normalization."""
        url = "https://example.com/path"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/path"

    def test_normalize_url_removes_trailing_slash(self):
        """Test that trailing slashes are removed."""
        assert normalize_url("https://example.com/path/") == "https://example.com/path"
        assert normalize_url("https://example.com/") == "https://example.com/"

    def test_normalize_url_converts_to_https(self):
        """Test that HTTP is converted to HTTPS."""
        assert normalize_url("http://example.com/path") == "https://example.com/path"

    def test_normalize_url_removes_www(self):
        """Test that www. prefix is removed."""
        assert normalize_url("https://www.example.com/path") == "https://example.com/path"
        assert normalize_url("http://www.example.com/path") == "https://example.com/path"

    def test_normalize_url_lowercase(self):
        """Test that URLs are converted to lowercase."""
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/path"

    def test_normalize_url_sorts_query_params(self):
        """Test that query parameters are sorted."""
        url1 = normalize_url("https://example.com/path?b=2&a=1")
        url2 = normalize_url("https://example.com/path?a=1&b=2")
        assert url1 == url2
        assert "a=1" in url1
        assert "b=2" in url1

    def test_normalize_url_removes_fragment(self):
        """Test that URL fragments are removed."""
        url = normalize_url("https://example.com/path#section")
        assert "#" not in url
        assert url == "https://example.com/path"

    def test_normalize_url_complex_example(self):
        """Test complex URL with multiple normalizations."""
        url = "HTTP://WWW.Example.COM/Path/?b=2&a=1#section"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/path?a=1&b=2"


class TestDocumentIDs:
    """Test deterministic document ID generation."""

    def test_generate_doc_id_basic(self):
        """Test basic document ID generation."""
        url = "https://example.com/article"
        doc_id = generate_doc_id(url)

        assert isinstance(doc_id, str)
        assert len(doc_id) == 64  # SHA256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in doc_id)

    def test_generate_doc_id_determinism(self):
        """Test that same URL always produces same ID."""
        url = "https://example.com/article"

        id1 = generate_doc_id(url)
        id2 = generate_doc_id(url)

        assert id1 == id2

    def test_generate_doc_id_normalization(self):
        """Test that different representations of same URL produce same ID."""
        urls = [
            "https://example.com/article",
            "http://example.com/article",
            "HTTP://WWW.EXAMPLE.COM/article/",
            "https://www.example.com/article?",
        ]

        ids = [generate_doc_id(url) for url in urls]

        # All should produce same ID after normalization
        assert len(set(ids)) == 1

    def test_generate_doc_id_different_paths_different_ids(self):
        """Test that different paths produce different IDs."""
        id1 = generate_doc_id("https://example.com/article1")
        id2 = generate_doc_id("https://example.com/article2")

        assert id1 != id2

    def test_generate_doc_id_query_params_matter(self):
        """Test that query parameters affect ID."""
        id1 = generate_doc_id("https://example.com/search?q=ai")
        id2 = generate_doc_id("https://example.com/search?q=ml")

        assert id1 != id2


class TestChunkIDs:
    """Test deterministic chunk ID generation."""

    def test_generate_chunk_id_basic(self):
        """Test basic chunk ID generation."""
        doc_id = "a" * 64  # Mock SHA256
        chunk_id = generate_chunk_id(doc_id, 0)

        assert chunk_id.startswith(doc_id)
        assert chunk_id.endswith("_0000000000")

    def test_generate_chunk_id_with_offset(self):
        """Test chunk ID with non-zero offset."""
        doc_id = "a" * 64
        chunk_id = generate_chunk_id(doc_id, 1024)

        assert chunk_id.endswith("_0000001024")

    def test_generate_chunk_id_large_offset(self):
        """Test chunk ID with large offset (multi-GB file)."""
        doc_id = "a" * 64
        chunk_id = generate_chunk_id(doc_id, 9999999999)  # ~10GB

        assert chunk_id.endswith("_9999999999")

    def test_generate_chunk_id_determinism(self):
        """Test that same inputs produce same chunk ID."""
        doc_id = generate_doc_id("https://example.com/doc")

        id1 = generate_chunk_id(doc_id, 512)
        id2 = generate_chunk_id(doc_id, 512)

        assert id1 == id2

    def test_generate_chunk_id_different_offsets(self):
        """Test that different offsets produce different IDs."""
        doc_id = generate_doc_id("https://example.com/doc")

        id1 = generate_chunk_id(doc_id, 0)
        id2 = generate_chunk_id(doc_id, 100)
        id3 = generate_chunk_id(doc_id, 1000)

        assert id1 != id2
        assert id2 != id3
        assert id1 != id3


class TestMentionIDs:
    """Test deterministic mention ID generation."""

    def test_generate_mention_id_basic(self):
        """Test basic mention ID generation."""
        chunk_id = "chunk_abc123_0000000000"
        mention_id = generate_mention_id(chunk_id, "Einstein", 42)

        assert isinstance(mention_id, str)
        assert len(mention_id) == 64  # SHA256

    def test_generate_mention_id_determinism(self):
        """Test that same inputs produce same mention ID."""
        chunk_id = "chunk_abc123_0000000000"

        id1 = generate_mention_id(chunk_id, "Einstein", 42)
        id2 = generate_mention_id(chunk_id, "Einstein", 42)

        assert id1 == id2

    def test_generate_mention_id_case_insensitive(self):
        """Test that mention IDs are case-insensitive for entity text."""
        chunk_id = "chunk_abc123_0000000000"

        id1 = generate_mention_id(chunk_id, "Einstein", 42)
        id2 = generate_mention_id(chunk_id, "einstein", 42)
        id3 = generate_mention_id(chunk_id, "EINSTEIN", 42)

        assert id1 == id2 == id3

    def test_generate_mention_id_whitespace_normalized(self):
        """Test that whitespace is normalized in entity text."""
        chunk_id = "chunk_abc123_0000000000"

        id1 = generate_mention_id(chunk_id, "  Einstein  ", 42)
        id2 = generate_mention_id(chunk_id, "Einstein", 42)

        assert id1 == id2

    def test_generate_mention_id_different_offsets(self):
        """Test that same entity at different offsets produces different IDs."""
        chunk_id = "chunk_abc123_0000000000"

        id1 = generate_mention_id(chunk_id, "Einstein", 42)
        id2 = generate_mention_id(chunk_id, "Einstein", 100)

        assert id1 != id2

    def test_generate_mention_id_different_chunks(self):
        """Test that same entity in different chunks produces different IDs."""
        id1 = generate_mention_id("chunk1", "Einstein", 42)
        id2 = generate_mention_id("chunk2", "Einstein", 42)

        assert id1 != id2


class TestEntityIDs:
    """Test deterministic entity ID generation."""

    def test_generate_entity_id_basic(self):
        """Test basic entity ID generation."""
        entity_id = generate_entity_id("Einstein", "PERSON")

        assert isinstance(entity_id, str)
        assert len(entity_id) == 64  # SHA256

    def test_generate_entity_id_determinism(self):
        """Test that same inputs produce same entity ID."""
        id1 = generate_entity_id("Einstein", "PERSON")
        id2 = generate_entity_id("Einstein", "PERSON")

        assert id1 == id2

    def test_generate_entity_id_case_insensitive_text(self):
        """Test that entity text is case-insensitive."""
        id1 = generate_entity_id("Einstein", "PERSON")
        id2 = generate_entity_id("einstein", "PERSON")
        id3 = generate_entity_id("EINSTEIN", "PERSON")

        assert id1 == id2 == id3

    def test_generate_entity_id_type_matters(self):
        """Test that entity type affects ID."""
        id1 = generate_entity_id("Washington", "PERSON")
        id2 = generate_entity_id("Washington", "GPE")  # Geographic location

        assert id1 != id2

    def test_generate_entity_id_type_case_insensitive(self):
        """Test that entity type is case-insensitive."""
        id1 = generate_entity_id("Einstein", "person")
        id2 = generate_entity_id("Einstein", "PERSON")
        id3 = generate_entity_id("Einstein", "Person")

        assert id1 == id2 == id3

    def test_generate_entity_id_whitespace_normalized(self):
        """Test that whitespace is normalized."""
        id1 = generate_entity_id("  Albert   Einstein  ", "PERSON")
        id2 = generate_entity_id("Albert Einstein", "PERSON")

        assert id1 == id2


class TestFileIDs:
    """Test deterministic file ID generation."""

    def test_generate_file_id_path_only(self):
        """Test file ID generation from path only."""
        file_id = generate_file_id("/path/to/file.pdf")

        assert isinstance(file_id, str)
        assert len(file_id) == 64  # SHA256

    def test_generate_file_id_with_content(self):
        """Test file ID generation with content hash."""
        content = b"file content here"
        file_id = generate_file_id("/path/to/file.pdf", content)

        assert isinstance(file_id, str)
        assert len(file_id) == 64

    def test_generate_file_id_content_based_determinism(self):
        """Test that same content produces same ID."""
        content = b"file content"

        id1 = generate_file_id("/path/to/file.pdf", content)
        id2 = generate_file_id("/path/to/file.pdf", content)

        assert id1 == id2

    def test_generate_file_id_different_content(self):
        """Test that different content produces different IDs."""
        id1 = generate_file_id("/path/file.pdf", b"content1")
        id2 = generate_file_id("/path/file.pdf", b"content2")

        assert id1 != id2

    def test_generate_file_id_path_vs_content_based(self):
        """Test that content-based IDs differ from path-only IDs."""
        path = "/path/to/file.pdf"
        content = b"content"

        id_path_only = generate_file_id(path)
        id_with_content = generate_file_id(path, content)

        # Should be different (content-based is more robust)
        assert id_path_only != id_with_content


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_in_url(self):
        """Test URLs with unicode characters."""
        url = "https://example.com/path/ünïcödé"
        doc_id = generate_doc_id(url)

        assert isinstance(doc_id, str)
        assert len(doc_id) == 64

    def test_unicode_in_entity_text(self):
        """Test entity IDs with unicode."""
        entity_id = generate_entity_id("François Müller", "PERSON")

        assert isinstance(entity_id, str)
        assert len(entity_id) == 64

    def test_empty_strings_handled(self):
        """Test that empty strings don't crash (though not recommended)."""
        # These should work but produce different IDs
        doc_id = generate_doc_id("https://example.com")
        entity_id = generate_entity_id("", "UNKNOWN")

        assert isinstance(doc_id, str)
        assert isinstance(entity_id, str)

    def test_very_long_entity_text(self):
        """Test entity IDs with very long text."""
        long_text = "A" * 10000
        entity_id = generate_entity_id(long_text, "PERSON")

        # Should still produce standard 64-char hash
        assert len(entity_id) == 64

    def test_special_characters_in_entity(self):
        """Test entity IDs with special characters."""
        entities = [
            ("AT&T", "ORG"),
            ("Johnson & Johnson", "ORG"),
            ("O'Reilly Media", "ORG"),
            ("Schrödinger's Cat", "CONCEPT"),
        ]

        for text, entity_type in entities:
            entity_id = generate_entity_id(text, entity_type)
            assert len(entity_id) == 64
