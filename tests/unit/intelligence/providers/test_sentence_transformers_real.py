"""
REAL tests for SentenceTransformerProvider.

These tests download and use actual models from HuggingFace.
First run will download models (~100MB), subsequent runs use cache.
"""

import pytest
import numpy as np
import os

from app.intelligence.providers.sentence_transformers_provider import SentenceTransformerProvider


# Skip tests if running in CI without model cache
pytestmark = pytest.mark.skipif(
    os.getenv('CI') == 'true' and not os.path.exists(os.path.expanduser('~/.cache/torch')),
    reason="Skip model download in CI"
)


class TestSentenceTransformerProviderReal:
    """Test suite using REAL SentenceTransformers models."""
    
    @pytest.fixture
    def mini_provider(self):
        """Create provider with all-MiniLM-L6-v2 (384 dims, fast)."""
        return SentenceTransformerProvider(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            normalize_embeddings=True
        )
    
    @pytest.fixture
    def mpnet_provider(self):
        """Create provider with all-mpnet-base-v2 (768 dims, higher quality)."""
        return SentenceTransformerProvider(
            model_name="all-mpnet-base-v2",
            device="cpu",
            normalize_embeddings=True
        )
    
    def test_initialization(self, mini_provider):
        """Test that provider initializes correctly."""
        assert mini_provider.get_model_name() == "all-MiniLM-L6-v2"
        assert mini_provider.get_dimensions() == 384
        assert mini_provider.supports_batch() is True
    
    def test_embed_single_text(self, mini_provider):
        """Test embedding single text with real model."""
        text = "This is a test document about artificial intelligence."
        
        embedding = mini_provider.embed(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32
        
        # Check normalization (L2 norm should be ~1.0)
        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01
    
    def test_embed_batch_text(self, mini_provider):
        """Test batch embedding with real model."""
        texts = [
            "Artificial intelligence is transforming technology.",
            "Machine learning models can process vast amounts of data.",
            "Natural language processing enables computers to understand text."
        ]
        
        embeddings = mini_provider.embed(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)
        assert all(emb.shape == (384,) for emb in embeddings)
        
        # Check that similar texts have similar embeddings
        # First two are about AI/ML (should be more similar)
        similarity_12 = np.dot(embeddings[0], embeddings[1])
        similarity_13 = np.dot(embeddings[0], embeddings[2])
        
        # Both should be positive (similar direction)
        assert similarity_12 > 0.3
        assert similarity_13 > 0.3
    
    def test_semantic_similarity(self, mini_provider):
        """Test that semantically similar texts have similar embeddings."""
        text1 = "The cat sits on the mat."
        text2 = "A feline rests on the rug."
        text3 = "Quantum mechanics is a branch of physics."
        
        emb1 = mini_provider.embed(text1)
        emb2 = mini_provider.embed(text2)
        emb3 = mini_provider.embed(text3)
        
        # Similar sentences should have higher cosine similarity
        similarity_cat = np.dot(emb1, emb2)
        similarity_physics = np.dot(emb1, emb3)
        
        assert similarity_cat > similarity_physics
        assert similarity_cat > 0.5  # Should be quite similar
    
    def test_empty_string_raises(self, mini_provider):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            mini_provider.embed("")
    
    def test_empty_list_raises(self, mini_provider):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Text list cannot be empty"):
            mini_provider.embed([])
    
    def test_list_with_empty_string_raises(self, mini_provider):
        """Test that list containing empty string raises ValueError."""
        with pytest.raises(ValueError, match="empty strings"):
            mini_provider.embed(["Valid text", "", "More text"])
    
    def test_different_model_dimensions(self, mpnet_provider):
        """Test provider with different model (768 dims)."""
        assert mpnet_provider.get_dimensions() == 768
        
        text = "Testing higher dimensional embeddings."
        embedding = mpnet_provider.embed(text)
        
        assert embedding.shape == (768,)
    
    def test_dimensions_validation(self, mini_provider):
        """Test dimension validation helper."""
        text = "Test text"
        embedding = mini_provider.embed(text)
        
        # Correct dimensions
        assert mini_provider.validate_dimensions(embedding) is True
        
        # Incorrect dimensions
        wrong_embedding = np.random.rand(768)
        assert mini_provider.validate_dimensions(wrong_embedding) is False
    
    def test_batch_dimensions_validation(self, mini_provider):
        """Test dimension validation for batches."""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = mini_provider.embed(texts)
        
        # All correct
        assert mini_provider.validate_dimensions(embeddings) is True
        
        # One incorrect
        embeddings_mixed = [embeddings[0], np.random.rand(768)]
        assert mini_provider.validate_dimensions(embeddings_mixed) is False
    
    def test_config_storage(self, mini_provider):
        """Test that config is stored correctly."""
        config = mini_provider.get_config()
        
        assert config['device'] == 'cpu'
        assert config['normalize_embeddings'] is True
