"""Core Pydantic domain models for the Williams Librarian.

This module contains the primary domain models that represent business entities.
All models use Pydantic for validation and serialization.
"""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.core.types import ContentSource


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


class RawContent(BaseModel):
    """Raw extracted content before processing.
    
    This model represents content immediately after extraction from its source,
    before any AI processing or transformation has occurred.
    
    Attributes:
        url: Source URL of the content
        source_type: Type of source (web, youtube, pdf, text)
        raw_text: Raw extracted text content
        metadata: Additional metadata from extraction (flexible dict)
        extracted_at: Timestamp when content was extracted
    """
    
    url: HttpUrl = Field(
        ...,
        description="Source URL of the content"
    )
    
    source_type: ContentSource = Field(
        ...,
        description="Type of content source"
    )
    
    raw_text: str = Field(
        ...,
        min_length=1,
        description="Raw extracted text content"
    )
    
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from extraction process"
    )
    
    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when content was extracted"
    )
    
    @field_validator("raw_text")
    @classmethod
    def raw_text_not_empty(cls, v: str) -> str:
        """Validate that raw_text is not empty or whitespace."""
        if not v.strip():
            raise ValueError("raw_text cannot be empty or whitespace")
        return v
