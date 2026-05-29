"""Plugin package — importing it registers all built-in plugins."""
from __future__ import annotations

from . import fs, http, lang, shell  # noqa: F401  (import side-effect: registration)
from .base import REGISTRY, Result, get, register

__all__ = ["REGISTRY", "Result", "get", "register"]
