"""
Provider factory for config-driven instantiation.

Loads AI service configuration and creates appropriate provider instances
with automatic fallback logic.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from app.intelligence.providers.abstract_embedding import AbstractEmbeddingProvider
from app.intelligence.providers.abstract_llm import AbstractLLMProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory for creating embedding and LLM providers from configuration.

    Supports automatic fallback from hosted to local providers if configured.
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize the provider factory.

        Args:
            config_path: Path to ai_services.yml config file.
                        Defaults to config/ai_services.yml
        """
        if config_path is None:
            config_path = "config/ai_services.yml"

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._embedding_providers = {}
        self._llm_providers = {}

    def _load_config(self) -> dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded AI services config from {self.config_path}")
        return config

    def create_embedding_provider(
        self,
        provider_name: str | None = None
    ) -> AbstractEmbeddingProvider:
        """
        Create an embedding provider instance.

        Args:
            provider_name: Name of provider from config. If None, uses default.

        Returns:
            Initialized embedding provider

        Raises:
            ValueError: If provider_name not found in config
            RuntimeError: If provider instantiation fails
        """
        if provider_name is None:
            provider_name = self.config.get('embeddings', {}).get('default')

        if not provider_name:
            raise ValueError("No embedding provider specified and no default configured")

        # Check cache
        if provider_name in self._embedding_providers:
            return self._embedding_providers[provider_name]

        # Get provider config
        providers = self.config.get('embeddings', {}).get('providers', {})
        provider_config = providers.get(provider_name)

        if not provider_config:
            raise ValueError(f"Embedding provider '{provider_name}' not found in config")

        # Try to instantiate provider
        try:
            provider = self._instantiate_embedding_provider(provider_config)
            self._embedding_providers[provider_name] = provider
            logger.info(f"Created embedding provider: {provider_name}")
            return provider
        except Exception as e:
            # Try fallback if configured
            fallback = provider_config.get('fallback')
            if fallback:
                logger.warning(f"Provider {provider_name} failed, trying fallback {fallback}: {e}")
                return self.create_embedding_provider(fallback)
            raise RuntimeError(f"Failed to create provider {provider_name}: {e}") from e

    def create_llm_provider(
        self,
        provider_name: str | None = None
    ) -> AbstractLLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_name: Name of provider from config. If None, uses default.

        Returns:
            Initialized LLM provider

        Raises:
            ValueError: If provider_name not found in config
            RuntimeError: If provider instantiation fails
        """
        if provider_name is None:
            provider_name = self.config.get('llms', {}).get('default')

        if not provider_name:
            raise ValueError("No LLM provider specified and no default configured")

        # Check cache
        if provider_name in self._llm_providers:
            return self._llm_providers[provider_name]

        # Get provider config
        providers = self.config.get('llms', {}).get('providers', {})
        provider_config = providers.get(provider_name)

        if not provider_config:
            raise ValueError(f"LLM provider '{provider_name}' not found in config")

        # Try to instantiate provider
        try:
            provider = self._instantiate_llm_provider(provider_config)
            self._llm_providers[provider_name] = provider
            logger.info(f"Created LLM provider: {provider_name}")
            return provider
        except Exception as e:
            # Try fallback if configured
            fallback = provider_config.get('fallback')
            if fallback:
                logger.warning(f"Provider {provider_name} failed, trying fallback {fallback}: {e}")
                return self.create_llm_provider(fallback)
            raise RuntimeError(f"Failed to create provider {provider_name}: {e}") from e

    def _instantiate_embedding_provider(self, config: dict[str, Any]) -> AbstractEmbeddingProvider:
        """
        Instantiate an embedding provider from config.

        Args:
            config: Provider configuration dictionary

        Returns:
            Initialized provider instance
        """
        provider_type = config.get('type')
        model_name = config.get('model')

        # Import dynamically to avoid circular dependencies
        if provider_type == 'sentence-transformers':
            from app.intelligence.providers.sentence_transformers_provider import (
                SentenceTransformerProvider,
            )
            return SentenceTransformerProvider(model_name, **config)
        elif provider_type == 'ollama-embedding':
            from app.intelligence.providers.ollama_embedding_provider import OllamaEmbeddingProvider
            return OllamaEmbeddingProvider(model_name, **config)
        elif provider_type == 'openai-embedding':
            from app.intelligence.providers.openai_embedding_provider import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider(model_name, **config)
        else:
            raise ValueError(f"Unknown embedding provider type: {provider_type}")

    def _instantiate_llm_provider(self, config: dict[str, Any]) -> AbstractLLMProvider:
        """
        Instantiate an LLM provider from config.

        Args:
            config: Provider configuration dictionary

        Returns:
            Initialized provider instance
        """
        provider_type = config.get('type')
        model_name = config.get('model')

        # Import dynamically to avoid circular dependencies
        if provider_type == 'ollama':
            from app.intelligence.providers.ollama_llm_provider import OllamaLLMProvider
            return OllamaLLMProvider(model_name, **config)
        elif provider_type == 'openai':
            from app.intelligence.providers.openai_llm_provider import OpenAILLMProvider
            return OpenAILLMProvider(model_name, **config)
        elif provider_type == 'anthropic':
            from app.intelligence.providers.anthropic_llm_provider import AnthropicLLMProvider
            return AnthropicLLMProvider(model_name, **config)
        else:
            raise ValueError(f"Unknown LLM provider type: {provider_type}")

    def list_embedding_providers(self) -> list:
        """List all configured embedding providers."""
        return list(self.config.get('embeddings', {}).get('providers', {}).keys())

    def list_llm_providers(self) -> list:
        """List all configured LLM providers."""
        return list(self.config.get('llms', {}).get('providers', {}).keys())
