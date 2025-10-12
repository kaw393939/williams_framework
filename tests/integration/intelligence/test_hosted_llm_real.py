"""
REAL integration tests for OpenAI and Anthropic LLM Providers (NO MOCKS).

Tests use actual API keys and make real API calls.
Skip tests if API keys not available.
"""

import os

import pytest

# Check if API keys are available
OPENAI_KEY_AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))
ANTHROPIC_KEY_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))


# OpenAI Tests
@pytest.fixture
def openai_provider():
    """Fixture providing OpenAILLMProvider instance."""
    if not OPENAI_KEY_AVAILABLE:
        pytest.skip("OPENAI_API_KEY not set")

    from app.intelligence.providers.openai_llm_provider import OpenAILLMProvider

    provider = OpenAILLMProvider(
        model_name="gpt-4o-mini",
        temperature=0.7
    )

    return provider


@pytest.mark.skipif(not OPENAI_KEY_AVAILABLE, reason="OPENAI_API_KEY not set")
def test_openai_initialization(openai_provider):
    """Test OpenAI provider initialization."""
    assert openai_provider.model_name == "gpt-4o-mini"
    assert openai_provider.get_context_window() == 128000
    assert openai_provider.client is not None


@pytest.mark.skipif(not OPENAI_KEY_AVAILABLE, reason="OPENAI_API_KEY not set")
def test_openai_generate_simple(openai_provider):
    """Test simple text generation with OpenAI."""
    prompt = "What is 2+2? Answer with just the number."

    response = openai_provider.generate(prompt, max_tokens=10)

    # Should generate a response
    assert response is not None
    assert len(response) > 0

    # Should contain "4" somewhere
    assert "4" in response

    print(f"\nOpenAI response: {response}")


@pytest.mark.skipif(not OPENAI_KEY_AVAILABLE, reason="OPENAI_API_KEY not set")
def test_openai_generate_with_system_prompt(openai_provider):
    """Test generation with system prompt."""
    system_prompt = "You are a helpful assistant that answers very concisely."
    prompt = "What is Python in one sentence?"

    response = openai_provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=50
    )

    # Should generate response about Python
    assert response is not None
    assert len(response) > 0
    assert "python" in response.lower() or "programming" in response.lower()

    print(f"\nOpenAI with system prompt: {response}")


@pytest.mark.skipif(not OPENAI_KEY_AVAILABLE, reason="OPENAI_API_KEY not set")
def test_openai_streaming_generation(openai_provider):
    """Test streaming text generation."""
    prompt = "Count from 1 to 3, each number on a new line."

    chunks = []
    for chunk in openai_provider.stream_generate(prompt, max_tokens=50):
        chunks.append(chunk)
        print(chunk, end='', flush=True)

    # Should receive multiple chunks
    assert len(chunks) > 0

    # Concatenate all chunks
    full_response = ''.join(chunks)

    # Should contain numbers 1-3
    assert any(str(i) in full_response for i in range(1, 4))

    print(f"\n\nTotal chunks: {len(chunks)}")


@pytest.mark.skipif(not OPENAI_KEY_AVAILABLE, reason="OPENAI_API_KEY not set")
def test_openai_token_counting(openai_provider):
    """Test token counting with tiktoken."""
    text = "This is a test sentence."
    token_count = openai_provider.count_tokens(text)

    # Should return reasonable token count
    assert 4 <= token_count <= 10

    print(f"\nTokens for '{text}': {token_count}")


# Anthropic Tests
@pytest.fixture
def anthropic_provider():
    """Fixture providing AnthropicLLMProvider instance."""
    if not ANTHROPIC_KEY_AVAILABLE:
        pytest.skip("ANTHROPIC_API_KEY not set")

    from app.intelligence.providers.anthropic_llm_provider import AnthropicLLMProvider

    provider = AnthropicLLMProvider(
        model_name="claude-3-7-sonnet-20250219",
        temperature=0.7
    )

    return provider


@pytest.mark.skipif(not ANTHROPIC_KEY_AVAILABLE, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_initialization(anthropic_provider):
    """Test Anthropic provider initialization."""
    assert anthropic_provider.model_name == "claude-3-7-sonnet-20250219"
    assert anthropic_provider.get_context_window() == 200000
    assert anthropic_provider.client is not None


@pytest.mark.skipif(not ANTHROPIC_KEY_AVAILABLE, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_generate_simple(anthropic_provider):
    """Test simple text generation with Anthropic."""
    prompt = "What is 2+2? Answer with just the number."

    response = anthropic_provider.generate(prompt, max_tokens=10)

    # Should generate a response
    assert response is not None
    assert len(response) > 0

    # Should contain "4" somewhere
    assert "4" in response

    print(f"\nAnthropic response: {response}")


@pytest.mark.skipif(not ANTHROPIC_KEY_AVAILABLE, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_generate_with_system_prompt(anthropic_provider):
    """Test generation with system prompt."""
    system_prompt = "You are a helpful assistant that answers very concisely."
    prompt = "What is Python in one sentence?"

    response = anthropic_provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=50
    )

    # Should generate response about Python
    assert response is not None
    assert len(response) > 0
    assert "python" in response.lower() or "programming" in response.lower()

    print(f"\nAnthropic with system prompt: {response}")


@pytest.mark.skipif(not ANTHROPIC_KEY_AVAILABLE, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_streaming_generation(anthropic_provider):
    """Test streaming text generation."""
    prompt = "Count from 1 to 3, each number on a new line."

    chunks = []
    for chunk in anthropic_provider.stream_generate(prompt, max_tokens=50):
        chunks.append(chunk)
        print(chunk, end='', flush=True)

    # Should receive multiple chunks
    assert len(chunks) > 0

    # Concatenate all chunks
    full_response = ''.join(chunks)

    # Should contain numbers 1-3
    assert any(str(i) in full_response for i in range(1, 4))

    print(f"\n\nTotal chunks: {len(chunks)}")


@pytest.mark.skipif(not ANTHROPIC_KEY_AVAILABLE, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_large_context_window(anthropic_provider):
    """Test that Anthropic supports large context (200k tokens)."""
    assert anthropic_provider.get_context_window() == 200000

    # Create a fairly long prompt (simulate large context)
    long_text = "word " * 1000  # ~1000 words
    token_count = anthropic_provider.count_tokens(long_text)

    # Should handle it (well under 200k limit)
    assert token_count < anthropic_provider.get_context_window()
    assert anthropic_provider.validate_prompt_length(long_text)


def test_missing_api_keys_raise_errors():
    """Test that missing API keys raise proper errors."""
    # Temporarily unset keys
    original_openai = os.environ.pop("OPENAI_API_KEY", None)
    original_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)

    try:
        # OpenAI should raise
        from app.intelligence.providers.openai_llm_provider import OpenAILLMProvider
        with pytest.raises(ValueError, match="API key not found"):
            OpenAILLMProvider()

        # Anthropic should raise
        from app.intelligence.providers.anthropic_llm_provider import AnthropicLLMProvider
        with pytest.raises(ValueError, match="API key not found"):
            AnthropicLLMProvider()

    finally:
        # Restore keys
        if original_openai:
            os.environ["OPENAI_API_KEY"] = original_openai
        if original_anthropic:
            os.environ["ANTHROPIC_API_KEY"] = original_anthropic
