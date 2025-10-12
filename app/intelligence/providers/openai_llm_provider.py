"""
OpenAI LLM Provider for GPT models.

Provides access to OpenAI's GPT models (GPT-4, GPT-4o, GPT-4o-mini, etc.)
with streaming support.
"""

import logging
import os
from collections.abc import Generator

from app.intelligence.providers.abstract_llm import AbstractLLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(AbstractLLMProvider):
    """
    LLM provider using OpenAI's GPT models.

    Supports:
    - GPT-4o, GPT-4o-mini, GPT-4, GPT-3.5-turbo
    - Streaming generation
    - System prompts
    - Temperature control
    - Token counting via tiktoken
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key_env: str = "OPENAI_API_KEY",
        temperature: float = 0.7,
        context_window: int = 128000,
        **kwargs
    ):
        """
        Initialize OpenAI LLM provider.

        Args:
            model_name: Model to use (gpt-4o-mini, gpt-4o, gpt-4, etc.)
            api_key_env: Environment variable containing API key
            temperature: Default temperature (0.0-2.0)
            context_window: Maximum context window size
        """
        super().__init__(model_name, **kwargs)

        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai package not installed. "
                "Install with: poetry add openai"
            ) from e

        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {api_key_env}")

        self.client = OpenAI(
            api_key=api_key,
            organization=None  # Avoid org mismatch errors
        )
        self.default_temperature = temperature
        self.context_window = context_window

        logger.info(
            f"Initialized OpenAI provider with {model_name} "
            f"(context: {context_window})"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs
    ) -> str:
        """
        Generate text using OpenAI (blocking).

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        temperature = temperature or self.default_temperature

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise RuntimeError(f"OpenAI generation failed: {e}") from e

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate text using OpenAI with streaming.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Text chunks as they're generated
        """
        temperature = temperature or self.default_temperature

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise RuntimeError(f"OpenAI streaming failed: {e}") from e

    def get_context_window(self) -> int:
        """Get maximum context window size."""
        return self.context_window

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Falls back to simple heuristic if tiktoken not available.
        """
        try:
            import tiktoken

            # Get encoding for model
            if "gpt-4" in self.model_name.lower():
                encoding = tiktoken.encoding_for_model("gpt-4")
            else:
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

            return len(encoding.encode(text))

        except Exception:
            # Fallback: ~4 chars per token
            return len(text) // 4
