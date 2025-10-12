"""
AI Provider Abstraction Layer

This package provides cloud-agnostic interfaces for embedding and LLM providers,
allowing seamless switching between local (SentenceTransformers, Ollama) and
hosted (OpenAI, Anthropic) services via configuration.

Key Components:
- AbstractEmbeddingProvider: Interface for embedding models
- AbstractLLMProvider: Interface for language models
- ProviderFactory: Config-driven instantiation with fallback
"""

from app.intelligence.providers.abstract_embedding import AbstractEmbeddingProvider
from app.intelligence.providers.abstract_llm import AbstractLLMProvider
from app.intelligence.providers.factory import ProviderFactory

__all__ = [
    "AbstractEmbeddingProvider",
    "AbstractLLMProvider",
    "ProviderFactory",
]
