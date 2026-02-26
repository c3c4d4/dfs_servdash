"""Streamlit Cloud default entrypoint.

This project uses Home.py as the main app script.
Keeping this thin wrapper allows Streamlit Cloud defaults to work.
"""

from Home import *  # noqa: F401,F403
