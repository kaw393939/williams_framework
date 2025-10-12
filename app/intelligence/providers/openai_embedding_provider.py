"""
OpenAI embedding provider (hosted API).

Uses OpenAI's text-embedding-3-small and text-embedding-3-large models.
Requires OPENAI_API_KEY environment variable.
"""

import logging
import os
from typing import Union

import numpy as np

from app.intelligence.providers.abstract_embedding import AbstractEmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(AbstractEmbeddingProvider):
    """
    Hosted embedding provider using OpenAI API.

    Supports models:
    - text-embedding-3-small (1536 dim, $0.02/1M tokens)
    - text-embedding-3-large (3072 dim, $0.13/1M tokens)
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize OpenAI embedding provider.

        Args:
            model_name: OpenAI model name
            **kwargs: api_key_env='OPENAI_API_KEY', dimensions=1536, etc.
        """
        super().__init__(model_name, **kwargs)

        # Import here to avoid loading if not used
        from openai import OpenAI

        # Get API key from environment
        api_key_env = kwargs.get('api_key_env', 'OPENAI_API_KEY')
        api_key = os.getenv(api_key_env)

        if not api_key:
            raise ValueError(f"OpenAI API key not found in environment variable: {api_key_env}")

        # Initialize client without organization header to avoid mismatches
        self._client = OpenAI(api_key=api_key, organization=None)
        self._dimensions = kwargs.get('dimensions', 1536)

        logger.info(f"Initialized OpenAI embedding provider: {model_name} ({self._dimensions} dims)")

    def embed(self, text: Union[str, list[str]]) -> Union[np.ndarray, list[np.ndarray]]:
        """
        Generate embeddings using OpenAI API.

        Args:
            text: Single string or list of strings

        Returns:
            Single embedding array or list of embedding arrays
        """
        if isinstance(text, str):
            if not text.strip():
                raise ValueError("Text cannot be empty")

            try:
                response = self._client.embeddings.create(
                    input=text,
                    model=self.model_name,
                    dimensions=self._dimensions
                )

                embedding = np.array(response.data[0].embedding, dtype=np.float32)
                return embedding

            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                raise RuntimeError(f"Failed to generate embedding: {e}")

        elif isinstance(text, list):
            if not text:
                raise ValueError("Text list cannot be empty")

            if any(not t.strip() for t in text):
                raise ValueError("Text list contains empty strings")

            try:
                response = self._client.embeddings.create(
                    input=text,
                    model=self.model_name,
                    dimensions=self._dimensions
                )

                # Extract embeddings in order
                embeddings = [
                    np.array(item.embedding, dtype=np.float32)
                    for item in response.data
                ]

                return embeddings

            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                raise RuntimeError(f"Failed to generate embeddings: {e}")

        else:
            raise TypeError("Text must be str or List[str]")

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def supports_batch(self) -> bool:
        """OpenAI supports batch embedding."""
        return True
