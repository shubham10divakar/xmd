"""Plugin contract + registry (SPEC §3).

A plugin is a handler for a directive name:

    def plugin(params: dict, ctx: dict) -> Result
"""
from __future__ import annotations

from dataclasses import dataclass

REGISTRY: dict = {}


@dataclass
class Result:
    ok: bool
    output: str = ""
    error: str = ""
    code: int = 0


def register(name: str, *, deterministic: bool = True):
    """Register a plugin handler.

    ``deterministic=False`` marks a plugin whose output varies per run (``@http``,
    ``@llm``). Renders tag such steps, provenance records their indices, and
    ``runxmd run --pure`` refuses to execute them — so a claim of "computed
    once, read forever" can be stated precisely over the deterministic subset.
    """
    def deco(fn):
        fn.deterministic = deterministic
        REGISTRY[name] = fn
        return fn
    return deco


def get(name: str):
    return REGISTRY.get(name)


def is_deterministic(name: str) -> bool:
    return getattr(REGISTRY.get(name), "deterministic", True)
