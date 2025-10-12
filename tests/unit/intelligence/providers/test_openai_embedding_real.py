"""
REAL tests for OpenAIEmbeddingProvider.

These tests make actual API calls to OpenAI.
Requires OPENAI_API_KEY environment variable.
Tests are skipped if API key is not available.
"""

import os

import numpy as np
import pytest

from app.intelligence.providers.openai_embedding_provider import OpenAIEmbeddingProvider

# Skip tests if OpenAI API key not available
pytestmark = pytest.mark.skipif(
    not os.getenv('OPENAI_API_KEY'),
    reason="OPENAI_API_KEY not set"
)


class TestOpenAIEmbeddingProviderReal:
    """Test suite using REAL OpenAI API."""

    @pytest.fixture
    def small_provider(self):
        """Create provider with text-embedding-3-small (1536 dims)."""
        return OpenAIEmbeddingProvider(
            model_name="text-embedding-3-small",
            dimensions=1536,
            api_key_env="OPENAI_API_KEY"
        )

    def test_initialization(self, small_provider):
        """Test that provider initializes correctly."""
        assert small_provider.get_model_name() == "text-embedding-3-small"
        assert small_provider.get_dimensions() == 1536
        assert small_provider.supports_batch() is True

    def test_embed_single_text(self, small_provider):
        """Test embedding single text with real OpenAI API."""
        text = "This is a test document about artificial intelligence and machine learning."

        embedding = small_provider.embed(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1536,)
        assert embedding.dtype == np.float32

        # OpenAI embeddings are normalized
        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01

    def test_embed_batch_text(self, small_provider):
        """Test batch embedding with real OpenAI API."""
        texts = [
            "Artificial intelligence is revolutionizing technology.",
            "Machine learning algorithms can identify patterns in data.",
            "Deep learning uses neural networks with multiple layers."
        ]

        embeddings = small_provider.embed(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)
        assert all(emb.shape == (1536,) for emb in embeddings)

        # Check that embeddings are distinct but related
        # All AI-related texts should have positive similarity
        similarity_12 = np.dot(embeddings[0], embeddings[1])
        similarity_13 = np.dot(embeddings[0], embeddings[2])
        similarity_23 = np.dot(embeddings[1], embeddings[2])

        assert similarity_12 > 0.5
        assert similarity_13 > 0.5
        assert similarity_23 > 0.5

    def test_semantic_similarity(self, small_provider):
        """Test that semantically similar texts have similar embeddings."""
        text1 = "The quick brown fox jumps over the lazy dog."
        text2 = "A fast auburn fox leaps above the sleepy canine."
        text3 = "Quantum entanglement is a phenomenon in quantum physics."

        emb1 = small_provider.embed(text1)
        emb2 = small_provider.embed(text2)
        emb3 = small_provider.embed(text3)

        # Similar sentences should have higher cosine similarity
        similarity_fox = np.dot(emb1, emb2)
        similarity_quantum = np.dot(emb1, emb3)

        assert similarity_fox > similarity_quantum
        assert similarity_fox > 0.7  # Should be very similar

    def test_empty_string_raises(self, small_provider):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            small_provider.embed("")

    def test_empty_list_raises(self, small_provider):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Text list cannot be empty"):
            small_provider.embed([])

    def test_list_with_empty_string_raises(self, small_provider):
        """Test that list containing empty string raises ValueError."""
        with pytest.raises(ValueError, match="empty strings"):
            small_provider.embed(["Valid text", "  ", "More text"])

    def test_dimensions_validation(self, small_provider):
        """Test dimension validation helper."""
        text = "Test text for validation"
        embedding = small_provider.embed(text)

        # Correct dimensions
        assert small_provider.validate_dimensions(embedding) is True

        # Incorrect dimensions
        wrong_embedding = np.random.rand(768)
        assert small_provider.validate_dimensions(wrong_embedding) is False

    def test_batch_dimensions_validation(self, small_provider):
        """Test dimension validation for batches."""
        texts = ["Text one", "Text two", "Text three"]
        embeddings = small_provider.embed(texts)

        # All correct
        assert small_provider.validate_dimensions(embeddings) is True

    def test_config_storage(self, small_provider):
        """Test that config is stored correctly."""
        config = small_provider.get_config()

        assert config['dimensions'] == 1536
        assert config['api_key_env'] == 'OPENAI_API_KEY'

    def test_missing_api_key_raises(self):
        """Test that missing API key raises ValueError."""
        # Temporarily unset the key
        original_key = os.environ.pop('OPENAI_API_KEY', None)

        try:
            with pytest.raises(ValueError, match="API key not found"):
                OpenAIEmbeddingProvider(
                    model_name="text-embedding-3-small",
                    dimensions=1536,
                    api_key_env="OPENAI_API_KEY"
                )
        finally:
            # Restore the key
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
