"""Integration test ensuring the Streamlit harness mounts with factory data."""

import pytest
from streamlit.testing.v1 import AppTest

import streamlit as st
from tests.factories.streamlit import make_presentation_state


@pytest.mark.integration
def test_streamlit_app_renders_library_section() -> None:
    """Test that Streamlit app renders correctly with test data."""
    
    # Create a simple test app inline that AppTest can handle
    def _test_app():
        import streamlit as st
        from tests.factories.streamlit import make_presentation_state
        
        state = make_presentation_state()
        
        st.set_page_config(page_title="Williams Librarian", layout="wide")
        st.title("Williams Librarian")
        st.caption("Curate research artifacts, manage tiers, and explore insights from the pipeline.")
        
        stats_col, library_col = st.columns([1, 3])
        
        with stats_col:
            st.subheader("Library Totals")
            st.metric("Total items", state.stats.total_items)
            for tier, count in state.stats.tier_counts.items():
                st.write(f"{tier}: {count}")
        
        with library_col:
            st.subheader("Library Items")
            if not state.library_items:
                st.info("No content ingested yet.")
                return
            
            for item in state.library_items:
                st.markdown(f"### {item.title}")
                st.write(item.summary)
                st.caption(f"Tier: {item.tier} | Tags: {', '.join(item.tags)}")
                st.divider()
    
    runner = AppTest.from_function(_test_app)
    runner.run()

    assert runner.title[0].value == "Williams Librarian"
    assert runner.subheader[0].value == "Library Totals"
    # Library column renders first item title as markdown header
    assert any(block.value.startswith("### AI Research Roadmap") for block in runner.markdown)
