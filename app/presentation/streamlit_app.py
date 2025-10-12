"""Minimal Streamlit app wiring to enable headless testing."""
from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.presentation.state import PresentationState, PresentationStats, LibraryItem

_TITLE = "Williams Librarian"
_DESCRIPTION = (
    "Curate research artifacts, manage tiers, and explore insights from the pipeline."
)


def render_app(state: PresentationState) -> None:
    """Render the Streamlit UI for a given presentation state."""

    st.set_page_config(page_title=_TITLE, layout="wide")
    st.title(_TITLE)
    st.caption(_DESCRIPTION)

    stats_col, library_col = st.columns([1, 3])

    with stats_col:
        st.subheader("Library Totals")
        st.metric("Total items", state.stats.total_items)
        for tier, count in state.stats.tier_counts.items():
            st.write(f"{tier}: {count}")

    with library_col:
        st.subheader("Library Items")
        if not state.library_items:
            st.info("No content ingested yet. Run the pipeline to populate the library.")
            return

        for item in state.library_items:
            st.markdown(f"### {item.title}")
            st.write(item.summary)
            st.write(f"Tier: {item.tier}")
            st.write(", ".join(item.tags))
            st.divider()


def run_app(state_provider=None) -> None:
    """Execute the Streamlit app using the supplied state provider."""

    provider = state_provider or default_state_provider
    render_app(provider())


def build_app(state_provider: Callable[[], PresentationState]) -> Callable[[], None]:
    """Create a Streamlit-compatible callable bound to the provided state."""

    def _app() -> None:
        run_app(state_provider)

    return _app


def default_state_provider() -> PresentationState:
    """Return a default, empty state for interactive runs."""
    from pathlib import Path
    
    # Load actual library files from data/library
    library_root = Path("data/library")
    library_items = []
    
    if library_root.exists():
        for tier_dir in ["tier-a", "tier-b", "tier-c", "tier-d"]:
            tier_path = library_root / tier_dir
            if tier_path.exists():
                for md_file in tier_path.glob("*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        # Extract title from first line or use filename
                        lines = content.split("\n")
                        title = lines[0].strip("# ").strip() if lines else md_file.stem
                        
                        library_items.append(
                            LibraryItem(
                                title=title,
                                tier=tier_dir,
                                tags=[],
                                summary=content[:200] + "..." if len(content) > 200 else content,
                            )
                        )
                    except Exception:
                        # Skip files that can't be read
                        pass
    
    # Calculate stats
    tier_counts = {}
    for item in library_items:
        tier_counts[item.tier] = tier_counts.get(item.tier, 0) + 1
    
    return PresentationState(
        library_items=tuple(library_items),
        stats=PresentationStats(total_items=len(library_items), tier_counts=tier_counts),
    )


def main() -> None:
    """Entry point used by `streamlit run`."""

    run_app()


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    main()
