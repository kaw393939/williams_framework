# Plugin Development Guide

## Overview

The Williams Framework AI Librarian is designed with extensibility as a core principle. The plugin system allows you to add new functionality without modifying core code.

## Plugin Types

### 1. ExtractorPlugin
Extract content from new sources (e.g., Twitter, Discord, Slack)

### 2. TransformerPlugin
Add custom content transformations (e.g., translation, text-to-speech)

### 3. ToolPlugin
Integrate external tools (e.g., web scraping APIs, OCR services)

### 4. VisualizationPlugin
Add custom visualizations to the UI (e.g., timeline view, map view)

## Base Plugin Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class PluginMetadata(BaseModel):
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    requires: list[str] = []  # Dependencies
    config_schema: Optional[Dict[str, Any]] = None

class Plugin(ABC):
    """Base plugin interface"""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if plugin is healthy"""
        pass
```

## ExtractorPlugin

### Interface

```python
from app.core.types import ContentSource, RawContent

class ExtractorPlugin(Plugin):
    """Base class for content extractors"""
    
    @abstractmethod
    def can_extract(self, source: ContentSource) -> bool:
        """Check if this extractor can handle the source"""
        pass
    
    @abstractmethod
    async def extract(self, source: ContentSource) -> RawContent:
        """Extract content from source"""
        pass
```

### Example: Twitter Extractor

```python
from app.plugins.base import ExtractorPlugin, PluginMetadata
from app.core.types import ContentSource, RawContent, ContentType
import httpx
from datetime import datetime

class TwitterExtractorPlugin(ExtractorPlugin):
    """Extract content from Twitter/X"""
    
    def __init__(self):
        self._api_key: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="twitter-extractor",
            version="1.0.0",
            author="Kevin Williams",
            description="Extract tweets and threads from Twitter/X",
            requires=["httpx>=0.27.0"],
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "api_secret": {"type": "string"}
                },
                "required": ["api_key", "api_secret"]
            }
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with Twitter API credentials"""
        self._api_key = config["api_key"]
        self._api_secret = config["api_secret"]
        
        self._client = httpx.AsyncClient(
            base_url="https://api.twitter.com/2",
            headers={"Authorization": f"Bearer {self._api_key}"}
        )
    
    async def shutdown(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
    
    async def health_check(self) -> bool:
        """Check API connection"""
        try:
            response = await self._client.get("/tweets/sample/stream")
            return response.status_code == 200
        except Exception:
            return False
    
    def can_extract(self, source: ContentSource) -> bool:
        """Check if URL is a tweet"""
        return "twitter.com" in source.url or "x.com" in source.url
    
    async def extract(self, source: ContentSource) -> RawContent:
        """Extract tweet content"""
        # Parse tweet ID from URL
        tweet_id = self._parse_tweet_id(source.url)
        
        # Fetch tweet data
        response = await self._client.get(
            f"/tweets/{tweet_id}",
            params={
                "tweet.fields": "text,author_id,created_at,public_metrics",
                "expansions": "author_id",
                "user.fields": "username,name"
            }
        )
        
        data = response.json()
        tweet = data["data"]
        author = data["includes"]["users"][0]
        
        return RawContent(
            source_url=source.url,
            content_type=ContentType.SOCIAL_MEDIA,
            raw_text=tweet["text"],
            title=f"Tweet by @{author['username']}",
            author=author["name"],
            published_date=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")),
            extraction_metadata={
                "likes": tweet["public_metrics"]["like_count"],
                "retweets": tweet["public_metrics"]["retweet_count"],
                "replies": tweet["public_metrics"]["reply_count"]
            },
            extractor_name="twitter-extractor",
            extractor_version="1.0.0",
            extracted_at=datetime.now()
        )
    
    def _parse_tweet_id(self, url: str) -> str:
        """Extract tweet ID from URL"""
        # https://twitter.com/user/status/1234567890
        parts = url.split("/")
        return parts[-1]
```

### Example: Notion Extractor

```python
class NotionExtractorPlugin(ExtractorPlugin):
    """Extract content from Notion pages"""
    
    def __init__(self):
        self._notion_client = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="notion-extractor",
            version="1.0.0",
            author="Kevin Williams",
            description="Extract pages and databases from Notion",
            requires=["notion-client>=2.0.0"],
            config_schema={
                "type": "object",
                "properties": {
                    "integration_token": {"type": "string"}
                },
                "required": ["integration_token"]
            }
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        from notion_client import AsyncClient
        self._notion_client = AsyncClient(auth=config["integration_token"])
    
    async def shutdown(self) -> None:
        # Notion client doesn't need explicit cleanup
        pass
    
    async def health_check(self) -> bool:
        try:
            await self._notion_client.users.me()
            return True
        except Exception:
            return False
    
    def can_extract(self, source: ContentSource) -> bool:
        return "notion.so" in source.url
    
    async def extract(self, source: ContentSource) -> RawContent:
        # Parse page ID from URL
        page_id = self._parse_page_id(source.url)
        
        # Fetch page content
        page = await self._notion_client.pages.retrieve(page_id)
        blocks = await self._notion_client.blocks.children.list(page_id)
        
        # Convert blocks to text
        text_content = self._blocks_to_text(blocks["results"])
        
        return RawContent(
            source_url=source.url,
            content_type=ContentType.DOCUMENT,
            raw_text=text_content,
            title=self._get_page_title(page),
            extraction_metadata={
                "page_id": page_id,
                "last_edited": page["last_edited_time"]
            },
            extractor_name="notion-extractor",
            extractor_version="1.0.0",
            extracted_at=datetime.now()
        )
    
    def _parse_page_id(self, url: str) -> str:
        # https://notion.so/Page-Title-abc123
        return url.split("-")[-1].split("?")[0]
    
    def _blocks_to_text(self, blocks: list) -> str:
        """Convert Notion blocks to plain text"""
        text_parts = []
        for block in blocks:
            if block["type"] == "paragraph":
                text_parts.append(self._rich_text_to_plain(block["paragraph"]["rich_text"]))
            elif block["type"] == "heading_1":
                text_parts.append("# " + self._rich_text_to_plain(block["heading_1"]["rich_text"]))
            # ... handle other block types
        return "\n\n".join(text_parts)
    
    def _rich_text_to_plain(self, rich_text: list) -> str:
        return "".join([rt["plain_text"] for rt in rich_text])
    
    def _get_page_title(self, page: dict) -> str:
        """Extract page title from properties"""
        # Notion pages have different property types for titles
        for prop in page["properties"].values():
            if prop["type"] == "title":
                return self._rich_text_to_plain(prop["title"])
        return "Untitled"
```

## TransformerPlugin

### Interface

```python
from app.core.types import ProcessedContent

class TransformerPlugin(Plugin):
    """Base class for content transformers"""
    
    @abstractmethod
    async def transform(self, content: ProcessedContent) -> ProcessedContent:
        """Transform processed content"""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Execution order (lower = earlier)"""
        pass
```

### Example: Translation Plugin

```python
class TranslationPlugin(TransformerPlugin):
    """Translate content to English"""
    
    def __init__(self):
        self._translator = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="translator",
            version="1.0.0",
            author="Kevin Williams",
            description="Translate content to English using DeepL",
            requires=["deepl>=1.16.0"],
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "target_lang": {"type": "string", "default": "EN"}
                },
                "required": ["api_key"]
            }
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        import deepl
        self._translator = deepl.Translator(config["api_key"])
        self._target_lang = config.get("target_lang", "EN")
    
    async def shutdown(self) -> None:
        pass
    
    async def health_check(self) -> bool:
        try:
            usage = await self._translator.get_usage()
            return usage.character.limit > usage.character.count
        except Exception:
            return False
    
    def get_priority(self) -> int:
        return 10  # Run early in pipeline
    
    async def transform(self, content: ProcessedContent) -> ProcessedContent:
        """Translate if not English"""
        # Detect language
        detected_lang = await self._detect_language(content.clean_text[:500])
        
        if detected_lang != "EN":
            # Translate
            translated = await self._translator.translate_text(
                content.clean_text,
                target_lang=self._target_lang
            )
            
            # Update content
            content.clean_text = translated.text
            content.metadata["original_language"] = detected_lang
            content.metadata["translated"] = True
        
        return content
    
    async def _detect_language(self, text: str) -> str:
        """Detect text language"""
        from langdetect import detect
        return detect(text).upper()
```

## ToolPlugin

### Interface

```python
class ToolPlugin(Plugin):
    """Base class for external tools"""
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute tool"""
        pass
```

### Example: OCR Plugin

```python
class OCRPlugin(ToolPlugin):
    """Extract text from images using OCR"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ocr-tool",
            version="1.0.0",
            author="Kevin Williams",
            description="Extract text from images using Tesseract",
            requires=["pytesseract>=0.3.10", "Pillow>=10.0.0"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        import pytesseract
        self._ocr = pytesseract
        
        # Configure tesseract path if provided
        if "tesseract_cmd" in config:
            pytesseract.pytesseract.tesseract_cmd = config["tesseract_cmd"]
    
    async def shutdown(self) -> None:
        pass
    
    async def health_check(self) -> bool:
        try:
            # Check if tesseract is installed
            from PIL import Image
            import numpy as np
            
            # Test with dummy image
            dummy = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
            self._ocr.image_to_string(dummy)
            return True
        except Exception:
            return False
    
    async def execute(self, image_path: str, language: str = "eng") -> str:
        """Extract text from image"""
        from PIL import Image
        
        img = Image.open(image_path)
        text = self._ocr.image_to_string(img, lang=language)
        return text
```

## VisualizationPlugin

### Interface

```python
import streamlit as st

class VisualizationPlugin(Plugin):
    """Base class for UI visualizations"""
    
    @abstractmethod
    def render(self, data: Any) -> None:
        """Render visualization in Streamlit"""
        pass
    
    @abstractmethod
    def get_tab_name(self) -> str:
        """Name for UI tab"""
        pass
```

### Example: Timeline Visualization

```python
class TimelinePlugin(VisualizationPlugin):
    """Timeline view of content"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="timeline-viz",
            version="1.0.0",
            author="Kevin Williams",
            description="Timeline visualization of library content",
            requires=["plotly>=5.18.0"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass
    
    async def health_check(self) -> bool:
        return True
    
    def get_tab_name(self) -> str:
        return "Timeline"
    
    def render(self, library_files: list[LibraryFile]) -> None:
        """Render timeline"""
        import plotly.express as px
        import pandas as pd
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                "date": f.created_at,
                "title": f.title,
                "quality": f.quality_tier
            }
            for f in library_files
        ])
        
        # Create timeline
        fig = px.scatter(
            df,
            x="date",
            y="quality",
            hover_data=["title"],
            title="Content Timeline"
        )
        
        st.plotly_chart(fig, use_container_width=True)
```

## Plugin Manager

### Registration

```python
from app.plugins.base import Plugin, PluginManager

# Initialize manager
plugin_manager = PluginManager()

# Register plugin
await plugin_manager.register(
    TwitterExtractorPlugin(),
    config={"api_key": "...", "api_secret": "..."}
)

# Get plugin by name
twitter_plugin = plugin_manager.get("twitter-extractor")

# List all plugins
plugins = plugin_manager.list_all()
```

### Configuration

**config/plugins.yaml**:
```yaml
plugins:
  - name: twitter-extractor
    enabled: true
    config:
      api_key: ${TWITTER_API_KEY}
      api_secret: ${TWITTER_API_SECRET}
  
  - name: notion-extractor
    enabled: true
    config:
      integration_token: ${NOTION_TOKEN}
  
  - name: translator
    enabled: false  # Disabled by default
    config:
      api_key: ${DEEPL_API_KEY}
      target_lang: EN
```

## Plugin Discovery

### Auto-Discovery

Place plugins in `plugins/` directory:

```
plugins/
├── extractors/
│   ├── twitter_extractor.py
│   └── notion_extractor.py
├── transformers/
│   └── translator.py
└── tools/
    └── ocr.py
```

### Manual Registration

```python
from app.plugins.extractors.twitter_extractor import TwitterExtractorPlugin

plugin_manager.register(TwitterExtractorPlugin(), config={...})
```

## Testing Plugins

### Unit Tests

```python
import pytest
from app.plugins.extractors.twitter_extractor import TwitterExtractorPlugin
from app.core.types import ContentSource, ContentType

@pytest.mark.asyncio
async def test_twitter_extractor():
    """Test Twitter extraction"""
    plugin = TwitterExtractorPlugin()
    
    await plugin.initialize({
        "api_key": "test_key",
        "api_secret": "test_secret"
    })
    
    source = ContentSource(
        url="https://twitter.com/user/status/1234567890",
        content_type=ContentType.SOCIAL_MEDIA
    )
    
    assert plugin.can_extract(source) is True
    
    # Test extraction (mock API)
    # ... 
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_twitter_extractor_real_api():
    """Test with real Twitter API"""
    plugin = TwitterExtractorPlugin()
    
    await plugin.initialize({
        "api_key": os.getenv("TWITTER_API_KEY"),
        "api_secret": os.getenv("TWITTER_API_SECRET")
    })
    
    # Use a known tweet URL
    source = ContentSource(
        url="https://twitter.com/OpenAI/status/...",
        content_type=ContentType.SOCIAL_MEDIA
    )
    
    raw_content = await plugin.extract(source)
    
    assert raw_content.raw_text is not None
    assert raw_content.author is not None
```

## Best Practices

### 1. Error Handling

```python
async def extract(self, source: ContentSource) -> RawContent:
    try:
        # Extraction logic
        ...
    except httpx.HTTPError as e:
        raise PluginError(f"HTTP error: {e}")
    except Exception as e:
        raise PluginError(f"Extraction failed: {e}")
```

### 2. Configuration Validation

```python
async def initialize(self, config: Dict[str, Any]) -> None:
    # Validate config against schema
    from jsonschema import validate
    validate(config, self.metadata.config_schema)
    
    # Initialize
    ...
```

### 3. Resource Cleanup

```python
async def shutdown(self) -> None:
    # Close connections
    if self._client:
        await self._client.aclose()
    
    # Cancel tasks
    if self._background_task:
        self._background_task.cancel()
```

### 4. Health Monitoring

```python
async def health_check(self) -> bool:
    try:
        # Quick connectivity check
        response = await self._client.get("/health")
        return response.status_code == 200
    except Exception:
        return False
```

### 5. Logging

```python
import logging

logger = logging.getLogger(__name__)

async def extract(self, source: ContentSource) -> RawContent:
    logger.info(f"Extracting from {source.url}")
    
    try:
        result = await self._do_extract(source)
        logger.debug(f"Extracted {len(result.raw_text)} characters")
        return result
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise
```

## Publishing Plugins

### 1. Package Structure

```
my-plugin/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── williams_librarian_myplugin/
│       ├── __init__.py
│       └── plugin.py
└── tests/
    └── test_plugin.py
```

### 2. pyproject.toml

```toml
[project]
name = "williams-librarian-twitter"
version = "1.0.0"
description = "Twitter extractor plugin for Williams Librarian"
authors = [{name = "Kevin Williams", email = "..."}]
dependencies = [
    "httpx>=0.27.0"
]

[project.entry-points."williams_librarian.plugins"]
twitter = "williams_librarian_twitter:TwitterExtractorPlugin"
```

### 3. Installation

```bash
pip install williams-librarian-twitter
```

Plugin will be auto-discovered via entry points.

## Plugin Repository

Official plugins: https://github.com/kevinwilliams/williams-librarian-plugins

Submit your plugin via Pull Request!
