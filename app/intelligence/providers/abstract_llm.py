"""
Abstract base class for LLM providers.

Defines the interface that all LLM providers (local and hosted) must implement.
This allows seamless switching between Ollama, OpenAI, Anthropic, etc.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator, Optional


class AbstractLLMProvider(ABC):
    """
    Abstract interface for Large Language Model providers.
    
    All LLM providers must implement this interface to ensure
    consistent behavior across local and hosted services.
    """
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the LLM provider.
        
        Args:
            model_name: Name/identifier of the LLM
            **kwargs: Provider-specific configuration (temperature, max_tokens, etc.)
        """
        self.model_name = model_name
        self.config = kwargs
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion (blocking).
        
        Args:
            prompt: User prompt/query
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            ValueError: If prompt is empty or invalid
            RuntimeError: If generation fails
        """
        pass
    
    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate text completion with streaming (non-blocking).
        
        Args:
            prompt: User prompt/query
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific parameters
            
        Yields:
            Text chunks as they're generated
            
        Raises:
            ValueError: If prompt is empty or invalid
            RuntimeError: If generation fails
        """
        pass
    
    @abstractmethod
    def get_context_window(self) -> int:
        """
        Get the context window size for this model.
        
        Returns:
            Maximum number of tokens in context window
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using provider's tokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        pass
    
    def get_model_name(self) -> str:
        """Get the model name for this provider."""
        return self.model_name
    
    def get_config(self) -> dict:
        """Get the configuration for this provider."""
        return self.config
    
    def validate_prompt_length(self, prompt: str, system_prompt: Optional[str] = None) -> bool:
        """
        Validate that prompt fits within context window.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            True if prompt + system prompt fit in context window
        """
        total_tokens = self.count_tokens(prompt)
        if system_prompt:
            total_tokens += self.count_tokens(system_prompt)
        
        return total_tokens < self.get_context_window()
