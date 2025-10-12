"""Prompt template loading and validation for production use."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.exceptions import ConfigurationError


@dataclass(frozen=True)
class PromptTemplate:
    """Validated prompt template with checksum."""

    name: str
    content: str
    checksum: str


class PromptLoader:
    """Production prompt loader with validation and caching."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialize the prompt loader.

        Args:
            base_path: Optional custom base path for prompts.
                      Defaults to config/prompts in the project root.
        """
        if base_path is None:
            # Default to config/prompts relative to project root
            base_path = Path(__file__).resolve().parent.parent.parent / "config" / "prompts"
        
        self._base_path = base_path
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """Load a prompt template by name.

        Args:
            name: Template name (without .prompt extension).

        Returns:
            PromptTemplate with content and checksum.

        Raises:
            ConfigurationError: If template file doesn't exist.
        """
        # Return cached template if available
        if name in self._cache:
            return self._cache[name]

        # Resolve template path
        template_path = self._base_path / f"{name}.prompt"

        if not template_path.exists():
            raise ConfigurationError(
                f"Prompt template '{name}' not found",
                details={
                    "template": f"{name}.prompt",
                    "path": str(self._base_path),
                    "expected": str(template_path),
                },
            )

        # Load and validate template
        content = template_path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

        template = PromptTemplate(name=name, content=content, checksum=checksum)
        
        # Cache for future use
        self._cache[name] = template
        
        return template
