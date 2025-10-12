"""Deterministic embedding utilities for offline testing.

This module provides a lightweight embedding generator that does not rely on
external services. It creates reproducible unit-norm vectors based on the input
text, which is sufficient for tests and local development without network
access.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Final

DEFAULT_DIMENSIONS: Final[int] = 384


def _normalise(vector: Iterable[float]) -> list[float]:
    """Normalise a vector to unit length."""
    values = list(vector)
    norm = math.sqrt(sum(component ** 2 for component in values))
    if norm == 0:
        # Avoid division by zero – return zero vector instead.
        return [0.0 for _ in values]
    return [component / norm for component in values]


@lru_cache(maxsize=1024)
def _generate_embedding(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> tuple[float, ...]:
    """Generate a deterministic embedding for *text*.

    The implementation uses a seeded pseudo-random number generator based on
    the SHA-256 hash of the text. Each token contributes to the overall vector,
    keeping the result stable for the same input while remaining inexpensive to
    compute.
    """
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    if not cleaned:
        return tuple(0.0 for _ in range(dimensions))

    # Seed from the overall text to keep deterministic.
    base_seed = int(hashlib.sha256(cleaned.encode("utf-8")).hexdigest(), 16)

    # Split into small chunks to vary the vector across the sentence.
    tokens = cleaned.split()
    if not tokens:  # pragma: no cover - cleaned is guaranteed non-empty here
        tokens = [cleaned]

    # Create raw values by mixing token hashes and base seed.
    raw_values: list[float] = []
    for idx in range(dimensions):
        token = tokens[idx % len(tokens)]
        token_seed = int(hashlib.sha256(f"{token}-{idx}-{base_seed}".encode()).hexdigest(), 16)
        # Map 256-bit value to the range [-1, 1].
        normalised = (token_seed % 10_000_000) / 5_000_000 - 1.0
        raw_values.append(normalised)

    return tuple(_normalise(raw_values))


async def generate_embedding(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    """Asynchronously generate a deterministic embedding for *text*."""
    return list(_generate_embedding(text, dimensions))
