"""
Content loader utilities for realistic test data.

Loads real extracted content from the fixtures directory for use in tests.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import HttpUrl

from app.core.models import RawContent
from app.core.types import ContentSource

FIXTURES_DIR = Path(__file__).parent
SAMPLE_CONTENT_DIR = FIXTURES_DIR / "sample_content"
CATALOG_PATH = FIXTURES_DIR / "sample_catalog.json"


def load_catalog() -> list[dict]:
    """Load the catalog of all sample content with metadata."""
    if not CATALOG_PATH.exists():
        return []

    with open(CATALOG_PATH, encoding='utf-8') as f:
        return json.load(f)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML-style frontmatter from markdown content.

    Returns:
        Tuple of (metadata dict, remaining content)
    """
    metadata = {}
    body = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1].strip()
            body = parts[2].strip()

            # Simple key: value parsing
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle lists in brackets
                    if value.startswith('[') and value.endswith(']'):
                        value = [v.strip().strip("'\"") for v in value[1:-1].split(',')]

                    metadata[key] = value

    return metadata, body


def load_markdown_file(relative_path: str) -> tuple[dict, str]:
    """
    Load a markdown file and parse its frontmatter.

    Args:
        relative_path: Path relative to sample_content directory

    Returns:
        Tuple of (metadata dict, content text)
    """
    file_path = SAMPLE_CONTENT_DIR / relative_path

    if not file_path.exists():
        raise FileNotFoundError(f"Sample content not found: {file_path}")

    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    return parse_frontmatter(content)


def load_as_raw_content(
    relative_path: str,
    url: Optional[str] = None,
    source_type: ContentSource = ContentSource.WEB
) -> RawContent:
    """
    Load a markdown file as a RawContent object.

    Args:
        relative_path: Path relative to sample_content directory (e.g., "blog_posts/the-illustrated-transformer.md")
        url: Optional URL to use (defaults to source_url from frontmatter or a test URL)
        source_type: Type of content source

    Returns:
        RawContent object ready for processing
    """
    metadata, body = load_markdown_file(relative_path)

    # Determine URL
    if url is None:
        url = metadata.get('source_url', f"https://example.com/test/{relative_path}")

    # Extract title and add to metadata
    title = metadata.get('title', 'Untitled')

    # Combine metadata and body for full text
    full_text = f"# {title}\n\n{body}"

    return RawContent(
        source_type=source_type,
        url=HttpUrl(url),
        raw_text=full_text,
        metadata={
            'title': title,  # Store title in metadata
            'author': metadata.get('author', 'Unknown'),
            'date': metadata.get('date', 'Unknown'),
            'tags': metadata.get('tags', []),
            'category': metadata.get('category', 'general'),
            **metadata
        },
        extracted_at=datetime.now()
    )


# Predefined samples for common test scenarios
SAMPLE_FILES = {
    'high_quality_blog': 'blog_posts/the-illustrated-transformer.md',
    'llm_evaluation': 'blog_posts/alpacaeval-fast-reliable-llm-evaluation.md',
    'arxiv_paper': 'arxiv_papers/language-models-know-what-they-know.md',
    'ai_philosophy': 'arxiv_papers/why-ai-is-harder-than-we-think.md',
    'web_article': 'web_articles/a-guide-to-building-change-resilience-in-the-age-of-ai.md',
    'ai_lab': 'ai_labs/open-llm-leaderboard.md',
}


def get_sample(sample_name: str, source_type: ContentSource = ContentSource.WEB) -> RawContent:
    """
    Get a predefined sample content by name.

    Args:
        sample_name: One of the SAMPLE_FILES keys
        source_type: Type of content source

    Returns:
        RawContent object

    Example:
        >>> content = get_sample('high_quality_blog')
        >>> assert 'Transformer' in content.metadata['title']
    """
    if sample_name not in SAMPLE_FILES:
        raise ValueError(f"Unknown sample: {sample_name}. Available: {list(SAMPLE_FILES.keys())}")

    return load_as_raw_content(SAMPLE_FILES[sample_name], source_type=source_type)


def get_all_samples() -> list[RawContent]:
    """Get all available sample content as RawContent objects."""
    return [get_sample(name) for name in SAMPLE_FILES.keys()]


def get_samples_by_category(category: str) -> list[RawContent]:
    """
    Get all samples from a specific category.

    Args:
        category: blog_posts, arxiv_papers, web_articles, or ai_labs

    Returns:
        List of RawContent objects
    """
    samples = []
    for name, path in SAMPLE_FILES.items():
        if path.startswith(f"{category}/"):
            samples.append(get_sample(name))
    return samples
