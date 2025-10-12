"""Core domain types for the Williams Librarian.

This module defines the fundamental types used throughout the application,
including enums and type aliases that represent core business concepts.
"""
from enum import Enum


class ContentSource(str, Enum):
    """Enumeration of supported content source types.

    The Williams Librarian can process content from various sources.
    Each source type may require different extraction strategies.

    Attributes:
        WEB: Web pages and articles (HTML content)
        YOUTUBE: YouTube videos (transcripts and metadata)
        PDF: PDF documents (text extraction)
        TEXT: Plain text files or direct text input
    """

    WEB = "web"
    YOUTUBE = "youtube"
    PDF = "pdf"
    TEXT = "text"
