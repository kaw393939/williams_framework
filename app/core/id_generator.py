"""
Deterministic ID generation for provenance tracking.

This module provides functions for generating deterministic IDs for:
- Documents (SHA256 of normalized URL)
- Chunks (document ID + byte offset)
- Mentions (chunk ID + entity text + offset)
- Entities (normalized entity text)

All IDs are deterministic - same input always produces same ID.
This enables deduplication and idempotent operations.
"""

import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent ID generation.

    Normalization rules:
    - Convert to lowercase
    - Remove trailing slashes
    - Sort query parameters
    - Remove fragments (#)
    - Convert http:// to https://
    - Remove www. prefix

    Args:
        url: URL to normalize

    Returns:
        Normalized URL string

    Examples:
        >>> normalize_url("HTTP://WWW.Example.com/path/")
        'https://example.com/path'
        >>> normalize_url("https://example.com/path?b=2&a=1")
        'https://example.com/path?a=1&b=2'
    """
    # Parse URL
    parsed = urlparse(url.lower())

    # Force HTTPS
    scheme = 'https'

    # Remove www. prefix
    netloc = parsed.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]

    # Remove trailing slash from path
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'

    # Sort query parameters
    params = ''
    if parsed.query:
        query_dict = parse_qs(parsed.query)
        # Sort by key, convert back to string
        sorted_query = sorted(query_dict.items())
        params = urlencode(sorted_query, doseq=True)

    # Reconstruct without fragment
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        '',  # params (rarely used)
        params,
        ''   # no fragment
    ))

    return normalized


def generate_doc_id(url: str) -> str:
    """
    Generate deterministic document ID from URL.

    Uses SHA256 hash of normalized URL to ensure:
    - Same URL always produces same ID
    - Different representations of same URL produce same ID
    - Collision probability is negligible (2^-256)

    Args:
        url: Document URL

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> id1 = generate_doc_id("https://example.com/article")
        >>> id2 = generate_doc_id("http://www.example.com/article/")
        >>> id1 == id2  # Same normalized URL
        True
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def generate_chunk_id(doc_id: str, start_offset: int) -> str:
    """
    Generate deterministic chunk ID from document ID and byte offset.

    Format: {doc_id}_{start_offset:010d}
    - doc_id: SHA256 hash of document (64 chars)
    - start_offset: Zero-padded to 10 digits (supports up to 10GB docs)

    Args:
        doc_id: Document ID (from generate_doc_id)
        start_offset: Byte offset where chunk starts in document

    Returns:
        Chunk ID string

    Examples:
        >>> doc_id = generate_doc_id("https://example.com/doc")
        >>> chunk_id = generate_chunk_id(doc_id, 1024)
        >>> chunk_id.endswith("_0000001024")
        True
    """
    return f"{doc_id}_{start_offset:010d}"


def generate_mention_id(
    chunk_id: str,
    entity_text: str,
    offset_in_chunk: int
) -> str:
    """
    Generate deterministic mention ID.

    A "mention" is a specific occurrence of an entity in a chunk.
    Uses hash of: chunk_id + normalized entity text + offset

    Args:
        chunk_id: Chunk ID (from generate_chunk_id)
        entity_text: Raw entity text (e.g., "Albert Einstein")
        offset_in_chunk: Character offset within chunk where mention starts

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> chunk_id = generate_chunk_id("doc123", 0)
        >>> mention_id = generate_mention_id(chunk_id, "Einstein", 42)
        >>> len(mention_id)
        64
    """
    # Normalize entity text (lowercase, strip whitespace)
    normalized_entity = entity_text.strip().lower()

    # Combine all components
    mention_key = f"{chunk_id}|{normalized_entity}|{offset_in_chunk}"

    return hashlib.sha256(mention_key.encode('utf-8')).hexdigest()


def generate_entity_id(entity_text: str, entity_type: str) -> str:
    """
    Generate deterministic entity ID.

    An "entity" represents a unique concept (person, org, location, etc.)
    Uses hash of normalized text + type to allow same text with different types.

    Args:
        entity_text: Entity text (e.g., "Albert Einstein")
        entity_type: Entity type (e.g., "PERSON", "ORG", "GPE")

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> entity_id = generate_entity_id("Einstein", "PERSON")
        >>> entity_id2 = generate_entity_id("einstein", "PERSON")
        >>> entity_id == entity_id2  # Case-insensitive
        True
        >>> entity_id3 = generate_entity_id("Einstein", "ORG")
        >>> entity_id != entity_id3  # Different type = different entity
        True
    """
    # Normalize: lowercase, strip whitespace, collapse multiple spaces
    normalized_text = ' '.join(entity_text.strip().lower().split())

    # Normalize type: uppercase
    normalized_type = entity_type.upper()

    entity_key = f"{normalized_text}|{normalized_type}"

    return hashlib.sha256(entity_key.encode('utf-8')).hexdigest()


def generate_file_id(file_path: str, content: bytes | None = None) -> str:
    """
    Generate deterministic file ID.

    For local files, uses hash of file path + content hash.
    If content not provided, uses path only (less robust).

    Args:
        file_path: Absolute or relative file path
        content: Optional file content bytes for content-based hashing

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> file_id = generate_file_id("/path/to/file.pdf", b"content")
        >>> len(file_id)
        64
    """
    if content is not None:
        # Content-based ID (best - survives file moves)
        content_hash = hashlib.sha256(content).hexdigest()
        path_hash = hashlib.sha256(file_path.encode('utf-8')).hexdigest()
        combined = f"{path_hash}|{content_hash}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    else:
        # Path-only ID (fallback if content unavailable)
        return hashlib.sha256(file_path.encode('utf-8')).hexdigest()
