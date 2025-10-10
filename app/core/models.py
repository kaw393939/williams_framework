"""Core Pydantic domain models for the Williams Librarian.

This module contains the primary domain models that represent business entities.
All models use Pydantic for validation and serialization.
"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ScreeningResult(BaseModel):
    """Result of content screening by the AI screener.
    
    This model captures the LLM's assessment of whether content should be
    accepted into the library, along with quality estimates and reasoning.
    
    Attributes:
        screening_score: Overall screening score (0-10)
        decision: Accept, reject, or maybe (needs human review)
        reasoning: LLM's explanation for the decision
        estimated_quality: Predicted quality score if accepted (0-10)
    """
    
    model_config = {"frozen": True}  # Make immutable
    
    screening_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Overall screening score from 0 (lowest) to 10 (highest)"
    )
    
    decision: Literal["ACCEPT", "REJECT", "MAYBE"] = Field(
        ...,
        description="Screening decision: ACCEPT (add to library), REJECT (discard), MAYBE (human review)"
    )
    
    reasoning: str = Field(
        ...,
        min_length=1,
        description="LLM's explanation for the screening decision"
    )
    
    estimated_quality: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Estimated quality score if content is accepted (0-10)"
    )
    
    @field_validator("reasoning")
    @classmethod
    def reasoning_not_empty(cls, v: str) -> str:
        """Validate that reasoning is not empty or whitespace."""
        if not v.strip():
            raise ValueError("reasoning cannot be empty or whitespace")
        return v
