"""Compatibility shim.

All packaging metadata lives in ``pyproject.toml`` (the modern standard).
This file exists only so tools/workflows that still expect a ``setup.py`` can
build the project. Normal use:

    python -m build        # build sdist + wheel
    pip install -e .       # editable install
"""
from setuptools import setup

setup()
