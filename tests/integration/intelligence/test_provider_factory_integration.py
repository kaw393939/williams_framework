"""
REAL integration tests for ProviderFactory with actual providers.

Tests factory instantiation with real SentenceTransformers and OpenAI providers.
"""

import os
from pathlib import Path

import pytest
import yaml

from app.intelligence.providers.factory import ProviderFactory
from app.intelligence.providers.openai_embedding_provider import OpenAIEmbeddingProvider
from app.intelligence.providers.sentence_transformers_provider import SentenceTransformerProvider


class TestProviderFactoryIntegration:
    """Integration tests with real embedding providers."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create temporary config for testing."""
        config = {
            'embeddings': {
                'default': 'local-mini',
                'providers': {
                    'local-mini': {
                        'type': 'sentence-transformers',
                        'model': 'all-MiniLM-L6-v2',
                        'dimensions': 384,
                        'device': 'cpu',
                        'normalize_embeddings': True,
                        'batch_size': 32,
                        'cost_per_1k_tokens': 0.0
                    },
                    'local-mpnet': {
                        'type': 'sentence-transformers',
                        'model': 'all-mpnet-base-v2',
                        'dimensions': 768,
                        'device': 'cpu',
                        'normalize_embeddings': True,
                        'fallback': 'local-mini'
                    },
                    'openai-small': {
                        'type': 'openai-embedding',
                        'model': 'text-embedding-3-small',
                        'dimensions': 1536,
                        'api_key_env': 'OPENAI_API_KEY',
                        'fallback': 'local-mini'
                    }
                }
            }
        }

        config_file = tmp_path / "test_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        return str(config_file)

    def test_factory_initialization(self, temp_config):
        """Test factory loads config correctly."""
        factory = ProviderFactory(config_path=temp_config)

        assert 'embeddings' in factory.config
        assert factory.config['embeddings']['default'] == 'local-mini'

    def test_list_providers(self, temp_config):
        """Test listing available providers."""
        factory = ProviderFactory(config_path=temp_config)

        providers = factory.list_embedding_providers()
        assert 'local-mini' in providers
        assert 'local-mpnet' in providers
        assert 'openai-small' in providers

    def test_create_default_provider(self, temp_config):
        """Test creating default provider (SentenceTransformers)."""
        factory = ProviderFactory(config_path=temp_config)

        provider = factory.create_embedding_provider()

        assert isinstance(provider, SentenceTransformerProvider)
        assert provider.get_model_name() == 'all-MiniLM-L6-v2'
        assert provider.get_dimensions() == 384

    def test_create_specific_provider(self, temp_config):
        """Test creating specific provider by name."""
        factory = ProviderFactory(config_path=temp_config)

        provider = factory.create_embedding_provider('local-mpnet')

        assert isinstance(provider, SentenceTransformerProvider)
        assert provider.get_model_name() == 'all-mpnet-base-v2'
        assert provider.get_dimensions() == 768

    def test_provider_caching(self, temp_config):
        """Test that providers are cached after first creation."""
        factory = ProviderFactory(config_path=temp_config)

        # Create provider twice
        provider1 = factory.create_embedding_provider('local-mini')
        provider2 = factory.create_embedding_provider('local-mini')

        # Should be same instance
        assert provider1 is provider2

    def test_embedding_with_factory_provider(self, temp_config):
        """Test actual embedding generation through factory."""
        factory = ProviderFactory(config_path=temp_config)
        provider = factory.create_embedding_provider('local-mini')

        text = "Testing factory-created provider"
        embedding = provider.embed(text)

        assert embedding.shape == (384,)
        assert provider.validate_dimensions(embedding)

    def test_batch_embedding_with_factory(self, temp_config):
        """Test batch embedding through factory provider."""
        factory = ProviderFactory(config_path=temp_config)
        provider = factory.create_embedding_provider('local-mini')

        texts = ["First text", "Second text", "Third text"]
        embeddings = provider.embed(texts)

        assert len(embeddings) == 3
        assert all(emb.shape == (384,) for emb in embeddings)

    def test_switch_providers_via_factory(self, temp_config):
        """Test switching between providers via factory."""
        factory = ProviderFactory(config_path=temp_config)

        # Get 384-dim provider
        provider_384 = factory.create_embedding_provider('local-mini')
        embedding_384 = provider_384.embed("Test")

        # Get 768-dim provider
        provider_768 = factory.create_embedding_provider('local-mpnet')
        embedding_768 = provider_768.embed("Test")

        assert embedding_384.shape == (384,)
        assert embedding_768.shape == (768,)

    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="OpenAI API key not set")
    def test_create_openai_provider(self, temp_config):
        """Test creating OpenAI provider through factory."""
        factory = ProviderFactory(config_path=temp_config)

        provider = factory.create_embedding_provider('openai-small')

        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.get_dimensions() == 1536

    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="OpenAI API key not set")
    def test_openai_embedding_via_factory(self, temp_config):
        """Test OpenAI embedding generation through factory."""
        factory = ProviderFactory(config_path=temp_config)
        provider = factory.create_embedding_provider('openai-small')

        text = "Testing OpenAI through factory"
        embedding = provider.embed(text)

        assert embedding.shape == (1536,)

    def test_config_with_real_ai_services_file(self):
        """Test factory with actual config/ai_services.yml."""
        config_path = "config/ai_services.yml"

        if not Path(config_path).exists():
            pytest.skip("config/ai_services.yml not found")

        factory = ProviderFactory(config_path=config_path)

        # Should load successfully
        providers = factory.list_embedding_providers()
        assert len(providers) > 0

        # Default should work
        default_provider = factory.create_embedding_provider()
        assert default_provider is not None

        # Test embedding
        text = "Test with real config"
        embedding = default_provider.embed(text)
        assert len(embedding.shape) == 1  # 1D array
        assert embedding.shape[0] > 0  # Has dimensions
