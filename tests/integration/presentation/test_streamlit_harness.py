"""Integration test ensuring the Streamlit harness mounts with factory data."""

import pytest
from streamlit.testing.v1 import AppTest

from app.presentation.app import run_app
from tests.factories.streamlit import make_state_provider


@pytest.mark.integration
def test_streamlit_app_renders_library_section() -> None:
    state_provider = make_state_provider()
    runner = AppTest.from_function(run_app, kwargs={"state_provider": state_provider})
    runner.run()

    assert runner.title[0].value == "Williams Librarian"
    assert runner.subheader[0].value == "Library Totals"
    # Library column renders first item title as markdown header
    assert any(block.value.startswith("### AI Research Roadmap") for block in runner.markdown)
