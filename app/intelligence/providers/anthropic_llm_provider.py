"""
Anthropic LLM Provider for Claude models.

Provides access to Anthropic's Claude models (Claude 3.5 Sonnet, etc.)
with streaming support.
"""

import logging
import os
from typing import Optional, Generator, Dict, Any

from app.intelligence.providers.abstract_llm import AbstractLLMProvider

logger = logging.getLogger(__name__)


class AnthropicLLMProvider(AbstractLLMProvider):
    """
    LLM provider using Anthropic's Claude models.
    
    Supports:
    - Claude Sonnet 4.5, Sonnet 4, Opus 4.1, Haiku 3.5
    - Streaming generation
    - System prompts
    - Temperature control
    - Large context windows (200k tokens)
    """
    
    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key_env: str = "ANTHROPIC_API_KEY",
        temperature: float = 0.7,
        context_window: int = 200000,
        **kwargs
    ):
        """
        Initialize Anthropic LLM provider.
        
        Args:
            model_name: Model to use (e.g., claude-3-5-sonnet-20241022, claude-3-opus-20240229)
            api_key_env: Environment variable containing API key
            temperature: Default temperature (0.0-1.0)
            context_window: Maximum context window size
        """
        super().__init__(model_name, **kwargs)
        
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: poetry add anthropic"
            )
        
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {api_key_env}")
        
        self.client = Anthropic(api_key=api_key)
        self.default_temperature = temperature
        self.context_window = context_window
        
        logger.info(
            f"Initialized Anthropic provider with {model_name} "
            f"(context: {context_window})"
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Anthropic (blocking).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate (default: 1024)
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        temperature = temperature or self.default_temperature
        max_tokens = max_tokens or 1024  # Anthropic requires max_tokens
        
        try:
            kwargs_dict = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            if system_prompt:
                kwargs_dict["system"] = system_prompt
            
            response = self.client.messages.create(**kwargs_dict)
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise RuntimeError(f"Anthropic generation failed: {e}")
    
    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate text using Anthropic with streaming.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate (default: 1024)
            temperature: Sampling temperature
            
        Yields:
            Text chunks as they're generated
        """
        temperature = temperature or self.default_temperature
        max_tokens = max_tokens or 1024  # Anthropic requires max_tokens
        
        try:
            kwargs_dict = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            if system_prompt:
                kwargs_dict["system"] = system_prompt
            
            with self.client.messages.stream(**kwargs_dict) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            raise RuntimeError(f"Anthropic streaming failed: {e}")
    
    def get_context_window(self) -> int:
        """Get maximum context window size."""
        return self.context_window
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Anthropic uses similar tokenization to GPT models.
        Uses simple heuristic: ~4 chars per token.
        """
        return len(text) // 4
