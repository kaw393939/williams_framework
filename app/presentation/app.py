"""Presentation layer app module for backward compatibility.

This module re-exports functions from streamlit_app.py to support
existing test imports that reference app.presentation.app.
"""

from app.presentation.streamlit_app import build_app, render_app, run_app

__all__ = ["build_app", "render_app", "run_app"]
