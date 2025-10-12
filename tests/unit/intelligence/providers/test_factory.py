"""Tests for ProviderFactory."""

from unittest.mock import Mock, patch

import pytest
import yaml

from app.intelligence.providers.abstract_embedding import AbstractEmbeddingProvider
from app.intelligence.providers.abstract_llm import AbstractLLMProvider
from app.intelligence.providers.factory import ProviderFactory


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config = {
        'embeddings': {
            'default': 'test-embedding',
            'providers': {
                'test-embedding': {
                    'type': 'sentence-transformers',
                    'model': 'test-model',
                    'dimensions': 384,
                    'cost_per_1k_tokens': 0.0
                },
                'test-embedding-fallback': {
                    'type': 'sentence-transformers',
                    'model': 'fallback-model',
                    'dimensions': 384,
                    'fallback': 'test-embedding'
                }
            }
        },
        'llms': {
            'default': 'test-llm',
            'providers': {
                'test-llm': {
                    'type': 'ollama',
                    'model': 'test-model',
                    'context_window': 4096,
                    'cost_per_1k_tokens': 0.0
                },
                'test-llm-fallback': {
                    'type': 'ollama',
                    'model': 'fallback-model',
                    'context_window': 4096,
                    'fallback': 'test-llm'
                }
            }
        }
    }

    config_file = tmp_path / "test_config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    return str(config_file)


class TestProviderFactory:
    """Test suite for ProviderFactory."""

    def test_config_file_not_found(self):
        """Test that missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ProviderFactory(config_path="/nonexistent/path.yml")

    def test_load_config_success(self, temp_config_file):
        """Test successful config loading."""
        factory = ProviderFactory(config_path=temp_config_file)

        assert 'embeddings' in factory.config
        assert 'llms' in factory.config

    def test_invalid_yaml_raises(self, tmp_path):
        """Test that invalid YAML raises error."""
        bad_config = tmp_path / "bad_config.yml"
        with open(bad_config, 'w') as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            ProviderFactory(config_path=str(bad_config))

    def test_list_embedding_providers(self, temp_config_file):
        """Test listing available embedding providers."""
        factory = ProviderFactory(config_path=temp_config_file)

        providers = factory.list_embedding_providers()
        assert 'test-embedding' in providers
        assert 'test-embedding-fallback' in providers

    def test_list_llm_providers(self, temp_config_file):
        """Test listing available LLM providers."""
        factory = ProviderFactory(config_path=temp_config_file)

        providers = factory.list_llm_providers()
        assert 'test-llm' in providers
        assert 'test-llm-fallback' in providers

    def test_create_embedding_provider_default(self, temp_config_file):
        """Test creating default embedding provider."""
        factory = ProviderFactory(config_path=temp_config_file)

        with patch.object(factory, '_instantiate_embedding_provider') as mock_instantiate:
            mock_provider = Mock(spec=AbstractEmbeddingProvider)
            mock_instantiate.return_value = mock_provider

            provider = factory.create_embedding_provider()

            assert provider == mock_provider
            mock_instantiate.assert_called_once()

    def test_create_embedding_provider_specific(self, temp_config_file):
        """Test creating specific embedding provider."""
        factory = ProviderFactory(config_path=temp_config_file)

        with patch.object(factory, '_instantiate_embedding_provider') as mock_instantiate:
            mock_provider = Mock(spec=AbstractEmbeddingProvider)
            mock_instantiate.return_value = mock_provider

            provider = factory.create_embedding_provider('test-embedding-fallback')

            assert provider == mock_provider

    def test_create_embedding_provider_not_found(self, temp_config_file):
        """Test creating non-existent provider raises ValueError."""
        factory = ProviderFactory(config_path=temp_config_file)

        with pytest.raises(ValueError, match="not found in config"):
            factory.create_embedding_provider('nonexistent-provider')

    def test_create_embedding_provider_caching(self, temp_config_file):
        """Test that providers are cached after first creation."""
        factory = ProviderFactory(config_path=temp_config_file)

        with patch.object(factory, '_instantiate_embedding_provider') as mock_instantiate:
            mock_provider = Mock(spec=AbstractEmbeddingProvider)
            mock_instantiate.return_value = mock_provider

            # First call
            provider1 = factory.create_embedding_provider()
            # Second call (should use cache)
            provider2 = factory.create_embedding_provider()

            assert provider1 == provider2
            # Should only instantiate once
            assert mock_instantiate.call_count == 1

    def test_create_llm_provider_default(self, temp_config_file):
        """Test creating default LLM provider."""
        factory = ProviderFactory(config_path=temp_config_file)

        with patch.object(factory, '_instantiate_llm_provider') as mock_instantiate:
            mock_provider = Mock(spec=AbstractLLMProvider)
            mock_instantiate.return_value = mock_provider

            provider = factory.create_llm_provider()

            assert provider == mock_provider
            mock_instantiate.assert_called_once()

    def test_create_llm_provider_specific(self, temp_config_file):
        """Test creating specific LLM provider."""
        factory = ProviderFactory(config_path=temp_config_file)

        with patch.object(factory, '_instantiate_llm_provider') as mock_instantiate:
            mock_provider = Mock(spec=AbstractLLMProvider)
            mock_instantiate.return_value = mock_provider

            provider = factory.create_llm_provider('test-llm-fallback')

            assert provider == mock_provider

    def test_create_llm_provider_not_found(self, temp_config_file):
        """Test creating non-existent LLM provider raises ValueError."""
        factory = ProviderFactory(config_path=temp_config_file)

        with pytest.raises(ValueError, match="not found in config"):
            factory.create_llm_provider('nonexistent-llm')

    def test_create_llm_provider_caching(self, temp_config_file):
        """Test that LLM providers are cached after first creation."""
        factory = ProviderFactory(config_path=temp_config_file)

        with patch.object(factory, '_instantiate_llm_provider') as mock_instantiate:
            mock_provider = Mock(spec=AbstractLLMProvider)
            mock_instantiate.return_value = mock_provider

            # First call
            provider1 = factory.create_llm_provider()
            # Second call (should use cache)
            provider2 = factory.create_llm_provider()

            assert provider1 == provider2
            # Should only instantiate once
            assert mock_instantiate.call_count == 1

    def test_fallback_on_instantiation_failure_embedding(self, temp_config_file):
        """Test fallback when embedding provider instantiation fails."""
        factory = ProviderFactory(config_path=temp_config_file)

        call_count = 0
        def mock_instantiate(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Provider failed")
            return Mock(spec=AbstractEmbeddingProvider)

        with patch.object(factory, '_instantiate_embedding_provider', side_effect=mock_instantiate):
            # Should try fallback and succeed
            provider = factory.create_embedding_provider('test-embedding-fallback')
            assert provider is not None
            assert call_count == 2  # First attempt + fallback

    def test_fallback_on_instantiation_failure_llm(self, temp_config_file):
        """Test fallback when LLM provider instantiation fails."""
        factory = ProviderFactory(config_path=temp_config_file)

        call_count = 0
        def mock_instantiate(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Provider failed")
            return Mock(spec=AbstractLLMProvider)

        with patch.object(factory, '_instantiate_llm_provider', side_effect=mock_instantiate):
            # Should try fallback and succeed
            provider = factory.create_llm_provider('test-llm-fallback')
            assert provider is not None
            assert call_count == 2  # First attempt + fallback

    def test_no_default_provider_raises(self, tmp_path):
        """Test that missing default provider raises ValueError."""
        config = {
            'embeddings': {
                # No default specified
                'providers': {}
            }
        }

        config_file = tmp_path / "no_default.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        factory = ProviderFactory(config_path=str(config_file))

        with pytest.raises(ValueError, match="No embedding provider specified"):
            factory.create_embedding_provider()
