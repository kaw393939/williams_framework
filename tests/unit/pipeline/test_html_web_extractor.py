import httpx
import pytest

from app.core.types import ContentSource
from app.core.exceptions import ExtractionError
from app.core.models import RawContent
from app.pipeline.extractors.html import HTMLWebExtractor


class DummyAsyncClient:
    def __init__(self, response: httpx.Response | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.requested_urls: list[str] = []

    async def get(self, url: str) -> httpx.Response:
        self.requested_urls.append(url)
        if self._error:
            raise self._error
        if not self._response:
            raise RuntimeError("No response configured")
        return self._response


@pytest.mark.asyncio
async def test_html_web_extractor_success_html_page():
    url = "https://example.com/article"
    html = """<html><head><title>Example Article</title></head><body><p>Hello world.</p><p>Second paragraph.</p></body></html>"""
    response = httpx.Response(
        status_code=200,
        text=html,
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", url),
    )
    client = DummyAsyncClient(response=response)
    extractor = HTMLWebExtractor(client=client)

    result = await extractor.extract(url)

    assert isinstance(result, RawContent)
    assert str(result.url) == url
    assert result.source_type is ContentSource.WEB
    assert "Hello world." in result.raw_text
    assert result.metadata["title"] == "Example Article"
    assert result.metadata["summary"].startswith("Hello world.")
    assert client.requested_urls == [url]


@pytest.mark.asyncio
async def test_html_web_extractor_raises_on_http_error():
    url = "https://example.com/boom"
    error = httpx.HTTPError("network failure")
    client = DummyAsyncClient(error=error)
    extractor = HTMLWebExtractor(client=client)

    with pytest.raises(ExtractionError) as exc:
        await extractor.extract(url)

    assert url in str(exc.value)


@pytest.mark.asyncio
async def test_html_web_extractor_rejects_empty_content():
    url = "https://example.com/empty"
    response = httpx.Response(
        status_code=200,
        text="   \n\n   ",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", url),
    )
    client = DummyAsyncClient(response=response)
    extractor = HTMLWebExtractor(client=client)

    with pytest.raises(ExtractionError):
        await extractor.extract(url)


@pytest.mark.asyncio
async def test_html_web_extractor_handles_plain_text():
    url = "https://example.com/plain.txt"
    body = "First line\nSecond line"
    response = httpx.Response(
        status_code=200,
        text=body,
        headers={"content-type": "text/plain"},
        request=httpx.Request("GET", url),
    )
    client = DummyAsyncClient(response=response)
    extractor = HTMLWebExtractor(client=client)

    result = await extractor.extract(url)

    assert str(result.url) == url
    assert result.metadata["title"] == "plain.txt"
    assert result.metadata["summary"].startswith("First line")
    assert result.raw_text.startswith("First line")
