"""Tests for AbstractEmbeddingProvider interface."""


import numpy as np
import pytest

from app.intelligence.providers.abstract_embedding import AbstractEmbeddingProvider


class MockEmbeddingProvider(AbstractEmbeddingProvider):
    """Concrete implementation for testing abstract interface."""

    def __init__(self, model_name: str, dimensions: int = 384, **kwargs):
        super().__init__(model_name, **kwargs)
        self._dimensions = dimensions

    def embed(self, text):
        """Generate mock embeddings."""
        if isinstance(text, str):
            if not text:
                raise ValueError("Text cannot be empty")
            return np.random.rand(self._dimensions)
        elif isinstance(text, list):
            if not text:
                raise ValueError("Text list cannot be empty")
            return [np.random.rand(self._dimensions) for _ in text]
        raise TypeError("Text must be str or List[str]")

    def get_dimensions(self) -> int:
        return self._dimensions

    def supports_batch(self) -> bool:
        return True


class TestAbstractEmbeddingProvider:
    """Test suite for AbstractEmbeddingProvider interface."""

    def test_interface_contract(self):
        """Test that abstract interface enforces required methods."""
        # Cannot instantiate abstract class directly
        with pytest.raises(TypeError):
            AbstractEmbeddingProvider("test-model")

    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        provider = MockEmbeddingProvider("test-model", dimensions=384)

        assert provider.get_model_name() == "test-model"
        assert provider.get_dimensions() == 384
        assert provider.supports_batch() is True

    def test_embed_single_text(self):
        """Test embedding single text string."""
        provider = MockEmbeddingProvider("test-model", dimensions=384)

        text = "This is a test document"
        embedding = provider.embed(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)

    def test_embed_batch_text(self):
        """Test embedding multiple texts."""
        provider = MockEmbeddingProvider("test-model", dimensions=768)

        texts = ["First document", "Second document", "Third document"]
        embeddings = provider.embed(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)
        assert all(emb.shape == (768,) for emb in embeddings)

    def test_embed_empty_string_raises(self):
        """Test that empty string raises ValueError."""
        provider = MockEmbeddingProvider("test-model")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            provider.embed("")

    def test_embed_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        provider = MockEmbeddingProvider("test-model")

        with pytest.raises(ValueError, match="Text list cannot be empty"):
            provider.embed([])

    def test_dimensions_validation_single(self):
        """Test dimension validation for single embedding."""
        provider = MockEmbeddingProvider("test-model", dimensions=384)

        # Correct dimensions
        embedding = np.random.rand(384)
        assert provider.validate_dimensions(embedding) is True

        # Incorrect dimensions
        wrong_embedding = np.random.rand(768)
        assert provider.validate_dimensions(wrong_embedding) is False

    def test_dimensions_validation_batch(self):
        """Test dimension validation for batch embeddings."""
        provider = MockEmbeddingProvider("test-model", dimensions=384)

        # All correct
        embeddings = [np.random.rand(384) for _ in range(3)]
        assert provider.validate_dimensions(embeddings) is True

        # One incorrect
        embeddings_mixed = [np.random.rand(384), np.random.rand(768)]
        assert provider.validate_dimensions(embeddings_mixed) is False

    def test_get_config(self):
        """Test that config is stored and retrievable."""
        provider = MockEmbeddingProvider(
            "test-model",
            384,  # dimensions as positional arg
            device="cpu",
            batch_size=32
        )

        config = provider.get_config()
        assert config['device'] == "cpu"
        assert config['batch_size'] == 32

    def test_different_dimensions(self):
        """Test providers with different embedding dimensions."""
        # Small model (384)
        provider_small = MockEmbeddingProvider("small", dimensions=384)
        assert provider_small.get_dimensions() == 384

        # Medium model (768)
        provider_medium = MockEmbeddingProvider("medium", dimensions=768)
        assert provider_medium.get_dimensions() == 768

        # Large model (1536)
        provider_large = MockEmbeddingProvider("large", dimensions=1536)
        assert provider_large.get_dimensions() == 1536

    def test_model_name_storage(self):
        """Test that model name is stored correctly."""
        provider = MockEmbeddingProvider("sentence-transformers/all-MiniLM-L6-v2")
        assert provider.get_model_name() == "sentence-transformers/all-MiniLM-L6-v2"
