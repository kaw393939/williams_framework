"""
Abstract base class for embedding providers.

Defines the interface that all embedding providers (local and hosted) must implement.
This allows seamless switching between SentenceTransformers, Ollama, OpenAI, etc.
"""

from abc import ABC, abstractmethod
from typing import Union

import numpy as np


class AbstractEmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.

    All embedding providers must implement this interface to ensure
    consistent behavior across local and hosted services.
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the embedding provider.

        Args:
            model_name: Name/identifier of the embedding model
            **kwargs: Provider-specific configuration
        """
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def embed(self, text: Union[str, list[str]]) -> Union[np.ndarray, list[np.ndarray]]:
        """
        Generate embeddings for input text.

        Args:
            text: Single string or list of strings to embed

        Returns:
            Single embedding array or list of embedding arrays

        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """
        Get the dimensionality of embeddings produced by this provider.

        Returns:
            Number of dimensions (e.g., 384, 768, 1536)
        """
        pass

    @abstractmethod
    def supports_batch(self) -> bool:
        """
        Check if provider supports batch embedding (list input).

        Returns:
            True if batch processing is supported
        """
        pass

    def get_model_name(self) -> str:
        """Get the model name for this provider."""
        return self.model_name

    def get_config(self) -> dict:
        """Get the configuration for this provider."""
        return self.config

    def validate_dimensions(self, embeddings: Union[np.ndarray, list[np.ndarray]]) -> bool:
        """
        Validate that embeddings have correct dimensions.

        Args:
            embeddings: Single embedding or list of embeddings

        Returns:
            True if dimensions match expected dimensions
        """
        expected_dims = self.get_dimensions()

        if isinstance(embeddings, list):
            return all(emb.shape[-1] == expected_dims for emb in embeddings)

        return embeddings.shape[-1] == expected_dims
