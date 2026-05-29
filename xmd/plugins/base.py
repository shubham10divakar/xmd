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


def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def get(name: str):
    return REGISTRY.get(name)
