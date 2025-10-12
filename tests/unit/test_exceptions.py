"""Unit tests for custom exceptions.

Following TDD RED-GREEN-REFACTOR cycle.
"""
import pytest

from app.core.exceptions import (
    BudgetExceededError,
    ExtractionError,
    LibrarianException,
    PluginError,
    ScreeningError,
    StorageError,
)
from app.core.exceptions import ValidationError as LibrarianValidationError


class TestLibrarianException:
    """Test suite for base exception."""

    def test_librarian_exception_basic(self):
        """Test creating basic LibrarianException."""
        exc = LibrarianException("Something went wrong")
        assert str(exc) == "Something went wrong"
        assert isinstance(exc, Exception)

    def test_librarian_exception_with_details(self):
        """Test exception with details dict."""
        exc = LibrarianException(
            "Error occurred",
            details={"url": "https://example.com", "code": 500}
        )
        assert "Error occurred" in str(exc)
        assert exc.details["url"] == "https://example.com"
        assert exc.details["code"] == 500

    def test_librarian_exception_inheritance(self):
        """Test that all custom exceptions inherit from LibrarianException."""
        assert issubclass(ExtractionError, LibrarianException)
        assert issubclass(ScreeningError, LibrarianException)
        assert issubclass(BudgetExceededError, LibrarianException)
        assert issubclass(PluginError, LibrarianException)
        assert issubclass(LibrarianValidationError, LibrarianException)
        assert issubclass(StorageError, LibrarianException)


class TestExtractionError:
    """Test suite for ExtractionError."""

    def test_extraction_error_basic(self):
        """Test creating ExtractionError."""
        exc = ExtractionError("Failed to extract content")
        assert "extract" in str(exc).lower()

    def test_extraction_error_with_url(self):
        """Test ExtractionError with URL."""
        exc = ExtractionError(
            "Extraction failed",
            details={"url": "https://example.com", "reason": "timeout"}
        )
        assert exc.details["url"] == "https://example.com"
        assert exc.details["reason"] == "timeout"

    def test_extraction_error_can_be_raised(self):
        """Test that ExtractionError can be raised and caught."""
        with pytest.raises(ExtractionError) as exc_info:
            raise ExtractionError("Test error")
        assert "Test error" in str(exc_info.value)

    def test_extraction_error_caught_as_base(self):
        """Test that ExtractionError can be caught as LibrarianException."""
        with pytest.raises(LibrarianException):
            raise ExtractionError("Test")


class TestScreeningError:
    """Test suite for ScreeningError."""

    def test_screening_error_basic(self):
        """Test creating ScreeningError."""
        exc = ScreeningError("Screening failed")
        assert "Screening failed" in str(exc)

    def test_screening_error_with_details(self):
        """Test ScreeningError with content details."""
        exc = ScreeningError(
            "LLM screening failed",
            details={"content_id": "123", "model": "gpt-5"}
        )
        assert exc.details["content_id"] == "123"


class TestBudgetExceededError:
    """Test suite for BudgetExceededError."""

    def test_budget_exceeded_error_basic(self):
        """Test creating BudgetExceededError."""
        exc = BudgetExceededError("Monthly budget exceeded")
        assert "budget" in str(exc).lower()

    def test_budget_exceeded_error_with_amounts(self):
        """Test BudgetExceededError with budget details."""
        exc = BudgetExceededError(
            "Budget limit reached",
            details={
                "current": 105.50,
                "limit": 100.00,
                "period": "monthly"
            }
        )
        assert exc.details["current"] == 105.50
        assert exc.details["limit"] == 100.00
        assert exc.details["period"] == "monthly"

    def test_budget_exceeded_prevents_operation(self):
        """Test that budget error can prevent operations."""
        def expensive_operation():
            raise BudgetExceededError("Daily limit exceeded")

        with pytest.raises(BudgetExceededError) as exc_info:
            expensive_operation()
        assert "limit exceeded" in str(exc_info.value).lower()


class TestPluginError:
    """Test suite for PluginError."""

    def test_plugin_error_basic(self):
        """Test creating PluginError."""
        exc = PluginError("Plugin failed to load")
        assert "Plugin" in str(exc)

    def test_plugin_error_with_plugin_info(self):
        """Test PluginError with plugin details."""
        exc = PluginError(
            "Plugin execution failed",
            details={
                "plugin_name": "custom_extractor",
                "version": "1.0.0",
                "error": "ImportError"
            }
        )
        assert exc.details["plugin_name"] == "custom_extractor"
        assert exc.details["version"] == "1.0.0"


class TestValidationError:
    """Test suite for LibrarianValidationError."""

    def test_validation_error_basic(self):
        """Test creating validation error."""
        exc = LibrarianValidationError("Invalid input")
        assert "Invalid input" in str(exc)

    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        exc = LibrarianValidationError(
            "Validation failed",
            details={"field": "quality_score", "value": -1, "reason": "must be >= 0"}
        )
        assert exc.details["field"] == "quality_score"


class TestStorageError:
    """Test suite for StorageError."""

    def test_storage_error_basic(self):
        """Test creating StorageError."""
        exc = StorageError("Failed to save file")
        assert "save" in str(exc).lower() or "failed" in str(exc).lower()

    def test_storage_error_with_path(self):
        """Test StorageError with file path."""
        exc = StorageError(
            "Storage operation failed",
            details={
                "path": "/library/tier-a/doc.md",
                "operation": "write",
                "error": "Permission denied"
            }
        )
        assert exc.details["path"] == "/library/tier-a/doc.md"
        assert exc.details["operation"] == "write"


class TestExceptionDetails:
    """Test exception details functionality."""

    def test_exception_details_optional(self):
        """Test that details are optional."""
        exc = LibrarianException("Error")
        assert hasattr(exc, "details")
        # Details should be either None or empty dict
        assert exc.details is None or exc.details == {}

    def test_exception_details_can_be_accessed(self):
        """Test accessing exception details."""
        exc = ExtractionError(
            "Error",
            details={"key": "value"}
        )
        assert exc.details is not None
        assert exc.details["key"] == "value"

    def test_multiple_exceptions_different_details(self):
        """Test that different exceptions have independent details."""
        exc1 = ExtractionError("Error 1", details={"id": 1})
        exc2 = ExtractionError("Error 2", details={"id": 2})

        assert exc1.details["id"] == 1
        assert exc2.details["id"] == 2
