"""RED TESTS FOR S3-404: End-to-end Streamlit ingest flow.

These tests verify that:
1. Ingest form has URL input field with QA ID
2. Ingest form has submit button with QA ID
3. Form submission calls ETL pipeline
4. Success notification appears after ingestion
5. Library count increments after successful ingestion
"""
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.unit
def test_ingest_form_has_url_input_field():
    """Test that ingest form renders URL input field."""
    from app.presentation.pages.ingest import IngestForm

    form = IngestForm()

    assert hasattr(form, "url_input_qa_id")
    assert form.url_input_qa_id == "ingest-url-input"


@pytest.mark.unit
def test_ingest_form_has_submit_button():
    """Test that ingest form renders submit button."""
    from app.presentation.pages.ingest import IngestForm

    form = IngestForm()

    assert hasattr(form, "submit_button_qa_id")
    assert form.submit_button_qa_id == "ingest-submit-button"


@pytest.mark.unit
def test_ingest_form_validates_url_format():
    """Test that ingest form validates URL format."""
    from app.presentation.pages.ingest import IngestForm

    form = IngestForm()

    assert form.validate_url("https://example.com") is True
    assert form.validate_url("http://example.com") is True
    assert form.validate_url("not-a-url") is False
    assert form.validate_url("") is False


@pytest.mark.asyncio
async def test_ingest_form_submit_calls_etl_pipeline():
    """Test that form submission triggers ETL pipeline."""
    from app.presentation.pages.ingest import IngestForm

    mock_etl = AsyncMock()
    mock_etl.ingest_url.return_value = {"status": "success"}

    form = IngestForm(etl_pipeline=mock_etl)
    result = await form.submit("https://example.com")

    mock_etl.ingest_url.assert_called_once_with("https://example.com")
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_form_submit_returns_error_on_failure():
    """Test that form submission returns error on pipeline failure."""
    from app.presentation.pages.ingest import IngestForm

    mock_etl = AsyncMock()
    mock_etl.ingest_url.side_effect = Exception("Pipeline error")

    form = IngestForm(etl_pipeline=mock_etl)
    result = await form.submit("https://example.com")

    assert result["status"] == "error"
    assert "error" in result


@pytest.mark.integration
async def test_ingest_success_increments_library_count():
    """Test that successful ingestion increments library count."""
    from app.presentation.pages.ingest import IngestForm

    # Mock library service to track count
    mock_library = Mock()
    initial_count = 10
    mock_library.get_library_count = Mock(return_value=initial_count)

    # Mock ETL pipeline
    mock_etl = AsyncMock()
    mock_etl.ingest_url.return_value = {"status": "success"}

    form = IngestForm(etl_pipeline=mock_etl, library_service=mock_library)

    # Submit form
    result = await form.submit("https://example.com")

    assert result["status"] == "success"
    # Verify library service was called to refresh count
    assert form.library_count == initial_count + 1


@pytest.mark.integration
def test_ingest_page_renders_success_notification():
    """Test that ingest page shows success notification after submission."""
    from app.presentation.pages.ingest import IngestPage

    page = IngestPage()

    # Simulate successful submission
    page.set_notification("success", "Successfully ingested content!")

    assert page.notification_type == "success"
    assert page.notification_message == "Successfully ingested content!"
    assert hasattr(page, "notification_qa_id")
    assert page.notification_qa_id == "ingest-notification"


@pytest.mark.integration
def test_ingest_page_renders_error_notification():
    """Test that ingest page shows error notification on failure."""
    from app.presentation.pages.ingest import IngestPage

    page = IngestPage()

    # Simulate failed submission
    page.set_notification("error", "Failed to ingest content")

    assert page.notification_type == "error"
    assert page.notification_message == "Failed to ingest content"


@pytest.mark.integration
def test_ingest_page_clears_notification():
    """Test that ingest page can clear notifications."""
    from app.presentation.pages.ingest import IngestPage

    page = IngestPage()
    page.set_notification("success", "Test message")

    page.clear_notification()

    assert page.notification_type is None
    assert page.notification_message is None


@pytest.mark.e2e
async def test_full_ingest_flow_from_url_to_library():
    """Test complete flow: URL submission -> ETL -> Library update -> Notification."""
    from app.presentation.pages.ingest import IngestPage

    # Mock dependencies
    mock_etl = AsyncMock()
    mock_etl.ingest_url.return_value = {
        "status": "success",
        "file_path": "/library/tier-a/test.md",
        "tier": "tier-a"
    }

    mock_library = Mock()
    mock_library.get_library_count = Mock(return_value=5)

    # Create page with mocked dependencies
    page = IngestPage(etl_pipeline=mock_etl, library_service=mock_library)

    # Simulate form submission
    result = await page.handle_submit("https://example.com/article")

    # Verify ETL was called
    mock_etl.ingest_url.assert_called_once_with("https://example.com/article")

    # Verify success notification
    assert page.notification_type == "success"
    assert "success" in page.notification_message.lower()

    # Verify library count was refreshed
    mock_library.get_library_count.assert_called()
