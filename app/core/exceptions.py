"""Custom exceptions for the Williams Librarian.

All application-specific exceptions inherit from LibrarianException
to allow for centralized error handling.
"""
from typing import Any


class LibrarianException(Exception):
    """Base exception for all Williams Librarian errors.

    All custom exceptions should inherit from this base class
    to enable centralized exception handling and logging.

    Attributes:
        message: Human-readable error message
        details: Optional dict with additional error context
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """Initialize exception with message and optional details.

        Args:
            message: Human-readable error message
            details: Optional dict with additional context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ExtractionError(LibrarianException):
    """Raised when content extraction fails.

    This can occur during web scraping, PDF parsing, YouTube
    transcript extraction, or any other content extraction operation.

    Example:
        raise ExtractionError(
            "Failed to extract content from URL",
            details={"url": "https://example.com", "reason": "timeout"}
        )
    """
    pass


class ScreeningError(LibrarianException):
    """Raised when AI screening/processing fails.

    This occurs when the LLM fails to screen, process, or analyze
    content for any reason (API errors, invalid responses, etc.).

    Example:
        raise ScreeningError(
            "LLM screening failed",
            details={"model": "gpt-5", "error": "rate_limit"}
        )
    """
    pass


class BudgetExceededError(LibrarianException):
    """Raised when cost budget limits are exceeded.

    Used to enforce daily, monthly, or per-request cost limits
    to prevent unexpected API charges.

    Example:
        raise BudgetExceededError(
            "Monthly budget limit exceeded",
            details={"current": 105.0, "limit": 100.0, "period": "monthly"}
        )
    """
    pass


class PluginError(LibrarianException):
    """Raised when plugin operations fail.

    This covers plugin loading, initialization, execution, and
    any other plugin-related errors.

    Example:
        raise PluginError(
            "Plugin execution failed",
            details={"plugin": "custom_extractor", "error": "ImportError"}
        )
    """
    pass


class ValidationError(LibrarianException):
    """Raised when data validation fails.

    Used for application-level validation errors beyond Pydantic's
    built-in validation (e.g., business rule violations).

    Example:
        raise ValidationError(
            "Invalid quality score",
            details={"field": "quality_score", "value": -1}
        )
    """
    pass


class StorageError(LibrarianException):
    """Raised when storage operations fail.

    This covers file I/O errors, database errors, vector store errors,
    or any other storage-related failures.

    Example:
        raise StorageError(
            "Failed to save file",
            details={"path": "/library/file.md", "error": "permission_denied"}
        )
    """
    pass


class ConfigurationError(LibrarianException):
    """Raised when configuration is invalid or missing.

    This covers missing config files, invalid settings, missing
    templates, and any other configuration-related errors.

    Example:
        raise ConfigurationError(
            "Required template not found",
            details={"template": "summarize.prompt", "path": "/config/prompts"}
        )
    """
    pass
