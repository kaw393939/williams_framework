"""
SentenceTransformers embedding provider (local, CPU/GPU).

Uses HuggingFace's sentence-transformers library for local embedding generation.
Supports CPU and GPU acceleration, batch processing.
"""

import logging
from typing import Union, List
import numpy as np

from app.intelligence.providers.abstract_embedding import AbstractEmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformerProvider(AbstractEmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.
    
    Supports models like:
    - all-MiniLM-L6-v2 (384 dim, fast)
    - all-mpnet-base-v2 (768 dim, higher quality)
    """
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize SentenceTransformer provider.
        
        Args:
            model_name: HuggingFace model name
            **kwargs: device='cpu'/'cuda', normalize_embeddings=True, batch_size=32, etc.
        """
        super().__init__(model_name, **kwargs)
        
        # Import here to avoid loading if not used
        from sentence_transformers import SentenceTransformer
        
        device = kwargs.get('device', 'cpu')
        self._model = SentenceTransformer(model_name, device=device)
        self._normalize = kwargs.get('normalize_embeddings', True)
        self._batch_size = kwargs.get('batch_size', 32)
        
        logger.info(f"Loaded SentenceTransformer model: {model_name} on {device}")
    
    def embed(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate embeddings using SentenceTransformers.
        
        Args:
            text: Single string or list of strings
            
        Returns:
            Single embedding array or list of embedding arrays
        """
        if isinstance(text, str):
            if not text.strip():
                raise ValueError("Text cannot be empty")
            
            embedding = self._model.encode(
                text,
                normalize_embeddings=self._normalize,
                convert_to_numpy=True
            )
            return embedding
        
        elif isinstance(text, list):
            if not text:
                raise ValueError("Text list cannot be empty")
            
            if any(not t.strip() for t in text):
                raise ValueError("Text list contains empty strings")
            
            # Use batch encoding for efficiency
            embeddings = self._model.encode(
                text,
                batch_size=self._batch_size,
                normalize_embeddings=self._normalize,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Convert to list of arrays
            return [embeddings[i] for i in range(len(embeddings))]
        
        else:
            raise TypeError("Text must be str or List[str]")
    
    def get_dimensions(self) -> int:
        """Get embedding dimensions from model."""
        return self._model.get_sentence_embedding_dimension()
    
    def supports_batch(self) -> bool:
        """SentenceTransformers supports batch processing."""
        return True
