"""Redbox is a Python library for working with the Redbox API, data and services."""

# Get version from poetry pyproject.toml

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"
