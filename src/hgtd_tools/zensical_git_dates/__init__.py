# reorder-python-imports: skip-file
"""Zensical Git Last Updated Date Markdown Extension."""
from .extension import GitDatesExtension
from .extension import makeExtension

__all__ = ["GitDatesExtension", "makeExtension"]
