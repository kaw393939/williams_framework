"""
Ollama LLM Provider for local models.

Provides access to locally-hosted open source models (Llama, Mistral, etc.)
via Ollama with GPU acceleration.
"""

import logging
import os
import json
from typing import Optional, Generator, Dict, Any
import httpx

from app.intelligence.providers.abstract_llm import AbstractLLMProvider

logger = logging.getLogger(__name__)


class OllamaLLMProvider(AbstractLLMProvider):
    """
    LLM provider using Ollama for local model inference.
    
    Supports:
    - GPU acceleration (CUDA)
    - Streaming generation
    - Multiple models (llama3.1, llama3.2, mistral, etc.)
    - Zero cost ($0/month)
    """
    
    def __init__(
        self,
        model_name: str = "llama3.2",
        host: Optional[str] = None,
        timeout: int = 120,
        temperature: float = 0.7,
        context_window: int = 8192,
        **kwargs
    ):
        """
        Initialize Ollama LLM provider.
        
        Args:
            model_name: Model to use (llama3.2, llama3.1, mistral, etc.)
            host: Ollama host URL (defaults to OLLAMA_HOST env or localhost)
            timeout: Request timeout in seconds
            temperature: Default temperature (0.0-1.0)
            context_window: Maximum context window size
        """
        super().__init__(model_name, **kwargs)
        
        if host is None:
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        self.host = host.rstrip('/')
        self.timeout = timeout
        self.default_temperature = temperature
        self.context_window = context_window
        self._client = httpx.Client(timeout=timeout)
        
        logger.info(
            f"Initialized Ollama provider with {model_name} "
            f"(host: {self.host}, context: {context_window})"
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
        Generate text using Ollama (blocking).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        temperature = temperature or self.default_temperature
        
        # Build request payload
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = self._client.post(
                f"{self.host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}")
    
    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate text using Ollama with streaming.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Yields:
            Text chunks as they're generated
        """
        temperature = temperature or self.default_temperature
        
        # Build request payload
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            with self._client.stream(
                "POST",
                f"{self.host}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                            
                            # Check if done
                            if chunk.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise RuntimeError(f"Ollama streaming failed: {e}")
    
    def get_context_window(self) -> int:
        """Get maximum context window size."""
        return self.context_window
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count (approximate for Ollama models).
        
        Uses simple heuristic: ~4 chars per token.
        """
        return len(text) // 4
    
    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
