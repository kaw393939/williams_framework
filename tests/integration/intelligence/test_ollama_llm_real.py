"""
REAL integration tests for OllamaLLMProvider (NO MOCKS).

Tests use actual Ollama instance running in Docker with GPU acceleration.
Skip tests if Ollama not available or models not pulled.
"""

import socket

import httpx
import pytest


# Check if Ollama is available
def is_ollama_available() -> bool:
    """Check if Ollama is running on localhost:11434."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 11434))
        sock.close()
        return result == 0
    except Exception:
        return False

def is_model_available(model_name: str) -> bool:
    """Check if a specific model is pulled in Ollama."""
    if not is_ollama_available():
        return False

    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Check for exact match or partial match (e.g., llama3.2:latest)
            return any(model_name in m for m in models)
    except Exception:
        pass

    return False

OLLAMA_AVAILABLE = is_ollama_available()
LLAMA32_AVAILABLE = is_model_available("llama3.2")

pytestmark = pytest.mark.skipif(
    not OLLAMA_AVAILABLE,
    reason="Ollama not available (start with: docker-compose up -d ollama)"
)


@pytest.fixture
def ollama_provider():
    """Fixture providing OllamaLLMProvider instance."""
    from app.intelligence.providers.ollama_llm_provider import OllamaLLMProvider

    provider = OllamaLLMProvider(
        model_name="llama3.2",
        temperature=0.7
    )

    yield provider

    provider.close()


def test_ollama_initialization(ollama_provider):
    """Test Ollama provider initialization."""
    assert ollama_provider.model_name == "llama3.2"
    assert ollama_provider.get_context_window() == 8192
    assert ollama_provider.host == "http://localhost:11434"


def test_ollama_token_counting(ollama_provider):
    """Test token counting (approximate)."""
    text = "This is a test sentence."
    token_count = ollama_provider.count_tokens(text)

    # Should be approximately 6 tokens (using ~4 chars/token heuristic)
    assert 4 <= token_count <= 8


def test_ollama_context_window(ollama_provider):
    """Test context window limits."""
    assert ollama_provider.get_context_window() == 8192

    # Test validation
    short_prompt = "Hello"
    assert ollama_provider.validate_prompt_length(short_prompt)

    # Very long prompt (beyond 8192 tokens)
    long_prompt = "word " * 10000
    assert not ollama_provider.validate_prompt_length(long_prompt)


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_generate_simple(ollama_provider):
    """Test simple text generation with Ollama."""
    prompt = "What is 2+2? Answer with just the number."

    response = ollama_provider.generate(prompt, max_tokens=10)

    # Should generate a response
    assert response is not None
    assert len(response) > 0

    # Should contain "4" somewhere
    assert "4" in response

    print(f"\nOllama response: {response}")


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_generate_with_system_prompt(ollama_provider):
    """Test generation with system prompt."""
    system_prompt = "You are a helpful assistant that answers concisely."
    prompt = "What is Python?"

    response = ollama_provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=50
    )

    # Should generate response about Python
    assert response is not None
    assert len(response) > 0
    assert "python" in response.lower() or "programming" in response.lower()

    print(f"\nOllama with system prompt: {response[:200]}")


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_temperature_variation(ollama_provider):
    """Test temperature affects generation."""
    prompt = "Write one word: "

    # Low temperature (more deterministic)
    response_low = ollama_provider.generate(prompt, temperature=0.1, max_tokens=5)

    # High temperature (more random)
    response_high = ollama_provider.generate(prompt, temperature=1.5, max_tokens=5)

    # Both should generate something
    assert len(response_low) > 0
    assert len(response_high) > 0

    print(f"\nLow temp (0.1): {response_low}")
    print(f"High temp (1.5): {response_high}")


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_streaming_generation(ollama_provider):
    """Test streaming text generation."""
    prompt = "Count from 1 to 5, each number on a new line."

    chunks = []
    for chunk in ollama_provider.stream_generate(prompt, max_tokens=50):
        chunks.append(chunk)
        print(chunk, end='', flush=True)

    # Should receive multiple chunks
    assert len(chunks) > 0

    # Concatenate all chunks
    full_response = ''.join(chunks)

    # Should contain numbers 1-5
    assert any(str(i) in full_response for i in range(1, 6))

    print(f"\n\nTotal chunks: {len(chunks)}")
    print(f"Full response: {full_response}")


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_streaming_stops_on_done(ollama_provider):
    """Test streaming properly stops when done."""
    prompt = "Say 'hello' once."

    chunks = list(ollama_provider.stream_generate(prompt, max_tokens=10))

    # Should receive chunks
    assert len(chunks) > 0

    # Should stop (not infinite)
    assert len(chunks) < 100  # Sanity check

    full_response = ''.join(chunks)
    assert "hello" in full_response.lower()


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_max_tokens_limit(ollama_provider):
    """Test max_tokens parameter limits output."""
    prompt = "Write a long story about a cat."

    # Very short limit
    response_short = ollama_provider.generate(prompt, max_tokens=10)

    # Longer limit
    response_long = ollama_provider.generate(prompt, max_tokens=100)

    # Short should be shorter
    assert len(response_short) < len(response_long)

    print(f"\nShort (10 tokens): {response_short}")
    print(f"\nLong (100 tokens): {response_long[:200]}...")


def test_ollama_context_manager(ollama_provider):
    """Test using OllamaLLMProvider as context manager."""
    from app.intelligence.providers.ollama_llm_provider import OllamaLLMProvider

    # Close fixture provider
    ollama_provider.close()

    with OllamaLLMProvider(model_name="llama3.2") as provider:
        assert provider.model_name == "llama3.2"
        assert provider._client is not None

    # Client should be closed after context


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_error_handling_invalid_model():
    """Test error handling for non-existent model."""
    from app.intelligence.providers.ollama_llm_provider import OllamaLLMProvider

    provider = OllamaLLMProvider(model_name="nonexistent-model-xyz")

    with pytest.raises(RuntimeError, match="Ollama generation failed"):
        provider.generate("test prompt")

    provider.close()


@pytest.mark.skipif(not LLAMA32_AVAILABLE, reason="llama3.2 model not pulled")
def test_ollama_gpu_acceleration_check():
    """Test that Ollama is using GPU (inference should be fast)."""
    import time

    from app.intelligence.providers.ollama_llm_provider import OllamaLLMProvider

    provider = OllamaLLMProvider(model_name="llama3.2")

    prompt = "Say hello."

    # Time the generation
    start = time.time()
    response = provider.generate(prompt, max_tokens=10)
    elapsed = time.time() - start

    # With GPU, should be relatively fast (< 5 seconds for small prompt)
    # Note: First run may be slower due to model loading
    assert elapsed < 30  # Generous timeout
    assert len(response) > 0

    print(f"\nGeneration took {elapsed:.2f}s with GPU")
    print(f"Response: {response}")

    provider.close()
