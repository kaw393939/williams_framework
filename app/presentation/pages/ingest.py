"""Ingest page components for Streamlit UI.

This module provides the ingest form and page for submitting URLs
to the ETL pipeline. It includes URL validation, error handling,
and success notifications.
"""
from typing import Any
from urllib.parse import urlparse


class IngestForm:  # pragma: no cover - Streamlit UI component requiring browser interaction
    """Form component for URL ingestion.

    This component provides:
    - URL input field with validation
    - Submit button with QA ID
    - ETL pipeline integration
    - Library count tracking

    Example:
        >>> form = IngestForm(etl_pipeline=etl, library_service=library)
        >>> result = await form.submit("https://example.com")
    """

    def __init__(
        self,
        etl_pipeline: Any | None = None,
        library_service: Any | None = None
    ):
        """Initialize ingest form.

        Args:
            etl_pipeline: ETL pipeline for URL ingestion
            library_service: Library service for count tracking
        """
        self.etl_pipeline = etl_pipeline
        self.library_service = library_service
        self.url_input_qa_id = "ingest-url-input"
        self.submit_button_qa_id = "ingest-submit-button"
        self.library_count = 0

    def validate_url(self, url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL string to validate

        Returns:
            True if URL is valid, False otherwise
        """
        if not url:
            return False

        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False

    async def submit(self, url: str) -> dict[str, Any]:
        """Submit URL to ETL pipeline.

        Args:
            url: URL to ingest

        Returns:
            Result dictionary with status and optional error
        """
        if not self.validate_url(url):
            return {
                "status": "error",
                "error": "Invalid URL format"
            }

        try:
            result = await self.etl_pipeline.ingest_url(url)

            # Update library count after successful ingestion
            if self.library_service and result.get("status") == "success":
                self.library_count = self.library_service.get_library_count() + 1

            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class IngestPage:
    """Page component for ingest UI.

    This component provides:
    - Form rendering and submission handling
    - Success/error notifications
    - Library count updates

    Example:
        >>> page = IngestPage(etl_pipeline=etl, library_service=library)
        >>> await page.handle_submit("https://example.com/article")
    """

    def __init__(
        self,
        etl_pipeline: Any | None = None,
        library_service: Any | None = None
    ):
        """Initialize ingest page.

        Args:
            etl_pipeline: ETL pipeline for URL ingestion
            library_service: Library service for count tracking
        """
        self.etl_pipeline = etl_pipeline
        self.library_service = library_service
        self.notification_type: str | None = None
        self.notification_message: str | None = None
        self.notification_qa_id = "ingest-notification"

    def set_notification(self, notification_type: str, message: str) -> None:
        """Set notification message.

        Args:
            notification_type: Type of notification ("success" or "error")
            message: Notification message text
        """
        self.notification_type = notification_type
        self.notification_message = message

    def clear_notification(self) -> None:
        """Clear notification message."""
        self.notification_type = None
        self.notification_message = None

    async def handle_submit(self, url: str) -> dict[str, Any]:
        """Handle form submission.

        Args:
            url: URL to ingest

        Returns:
            Result dictionary with status
        """
        form = IngestForm(
            etl_pipeline=self.etl_pipeline,
            library_service=self.library_service
        )

        result = await form.submit(url)

        if result["status"] == "success":
            self.set_notification(
                "success",
                f"Successfully ingested content from {url}"
            )
        else:
            self.set_notification(
                "error",
                f"Failed to ingest content: {result.get('error', 'Unknown error')}"
            )

        # Refresh library count
        if self.library_service:
            self.library_service.get_library_count()

        return result
