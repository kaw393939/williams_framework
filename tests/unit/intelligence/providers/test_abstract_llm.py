"""Tests for AbstractLLMProvider interface."""

import pytest
from unittest.mock import Mock
from typing import Generator

from app.intelligence.providers.abstract_llm import AbstractLLMProvider


class MockLLMProvider(AbstractLLMProvider):
    """Concrete implementation for testing abstract interface."""
    
    def __init__(self, model_name: str, context_window: int = 4096, **kwargs):
        super().__init__(model_name, **kwargs)
        self._context_window = context_window
    
    def generate(self, prompt, system_prompt=None, max_tokens=None, temperature=None, **kwargs):
        """Generate mock response."""
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        
        # Simple mock response
        response = f"Response to: {prompt[:50]}"
        if system_prompt:
            response = f"[System: {system_prompt[:20]}] {response}"
        return response
    
    def stream_generate(self, prompt, system_prompt=None, max_tokens=None, temperature=None, **kwargs):
        """Generate mock streaming response."""
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        
        response = f"Streaming response to: {prompt[:30]}"
        
        # Yield word by word
        for word in response.split():
            yield word + " "
    
    def get_context_window(self) -> int:
        return self._context_window
    
    def count_tokens(self, text: str) -> int:
        """Simple token counter (approximately words)."""
        return len(text.split())


class TestAbstractLLMProvider:
    """Test suite for AbstractLLMProvider interface."""
    
    def test_interface_contract(self):
        """Test that abstract interface enforces required methods."""
        # Cannot instantiate abstract class directly
        with pytest.raises(TypeError):
            AbstractLLMProvider("test-model")
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        provider = MockLLMProvider("test-llm", context_window=4096)
        
        assert provider.get_model_name() == "test-llm"
        assert provider.get_context_window() == 4096
    
    def test_generate_basic(self):
        """Test basic text generation."""
        provider = MockLLMProvider("test-llm")
        
        prompt = "What is the capital of France?"
        response = provider.generate(prompt)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "Response to:" in response
    
    def test_generate_with_system_prompt(self):
        """Test generation with system prompt."""
        provider = MockLLMProvider("test-llm")
        
        response = provider.generate(
            prompt="Tell me about AI",
            system_prompt="You are a helpful assistant"
        )
        
        assert isinstance(response, str)
        assert "[System:" in response
    
    def test_generate_empty_prompt_raises(self):
        """Test that empty prompt raises ValueError."""
        provider = MockLLMProvider("test-llm")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            provider.generate("")
    
    def test_stream_generate_basic(self):
        """Test streaming text generation."""
        provider = MockLLMProvider("test-llm")
        
        prompt = "Explain quantum computing"
        stream = provider.stream_generate(prompt)
        
        assert isinstance(stream, Generator)
        
        # Collect all chunks
        chunks = list(stream)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        
        # Reconstruct full response
        full_response = "".join(chunks)
        assert len(full_response) > 0
    
    def test_stream_generate_empty_prompt_raises(self):
        """Test that empty prompt raises ValueError in streaming."""
        provider = MockLLMProvider("test-llm")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            list(provider.stream_generate(""))
    
    def test_count_tokens(self):
        """Test token counting."""
        provider = MockLLMProvider("test-llm")
        
        text = "This is a test with seven tokens"
        token_count = provider.count_tokens(text)
        
        assert token_count == 7
    
    def test_validate_prompt_length_valid(self):
        """Test prompt validation when within context window."""
        provider = MockLLMProvider("test-llm", context_window=100)
        
        prompt = "Short prompt"
        assert provider.validate_prompt_length(prompt) is True
    
    def test_validate_prompt_length_invalid(self):
        """Test prompt validation when exceeding context window."""
        provider = MockLLMProvider("test-llm", context_window=10)
        
        # Create prompt with 15 words
        prompt = " ".join(["word"] * 15)
        assert provider.validate_prompt_length(prompt) is False
    
    def test_validate_prompt_with_system_prompt(self):
        """Test prompt validation including system prompt."""
        provider = MockLLMProvider("test-llm", context_window=20)
        
        prompt = " ".join(["word"] * 8)  # 8 tokens
        system_prompt = " ".join(["system"] * 8)  # 8 tokens
        
        # Total 16 tokens, under 20 limit
        assert provider.validate_prompt_length(prompt, system_prompt) is True
        
        # Add more to exceed
        prompt_long = " ".join(["word"] * 15)  # 15 tokens
        # Total 23 tokens, over 20 limit
        assert provider.validate_prompt_length(prompt_long, system_prompt) is False
    
    def test_get_config(self):
        """Test that config is stored and retrievable."""
        provider = MockLLMProvider(
            "test-llm",
            8192,  # context_window as positional arg
            temperature=0.7,
            max_tokens=2048
        )
        
        config = provider.get_config()
        assert config['temperature'] == 0.7
        assert config['max_tokens'] == 2048
    
    def test_different_context_windows(self):
        """Test providers with different context windows."""
        # Small context
        provider_small = MockLLMProvider("small", context_window=2048)
        assert provider_small.get_context_window() == 2048
        
        # Medium context
        provider_medium = MockLLMProvider("medium", context_window=8192)
        assert provider_medium.get_context_window() == 8192
        
        # Large context
        provider_large = MockLLMProvider("large", context_window=128000)
        assert provider_large.get_context_window() == 128000
    
    def test_model_name_storage(self):
        """Test that model name is stored correctly."""
        provider = MockLLMProvider("gpt-4o-mini")
        assert provider.get_model_name() == "gpt-4o-mini"
