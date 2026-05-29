"""Filesystem plugins — @write and @read (SPEC §3).

    - @write
      path: out/report.txt
      content: |
        hello {{ memory.user }}

    - @read
      path: out/report.txt
"""
from __future__ import annotations

import os

from .base import Result, register


@register("write")
def run_write(params: dict, ctx: dict) -> Result:
    path = str(params.get("path", "")).strip()
    if not path:
        return Result(ok=False, error="@write requires a 'path' param", code=2)
    content = params.get("content", params.get("text", ""))
    content = content if isinstance(content, str) else str(content)
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return Result(ok=True, output=f"wrote {len(content)} chars to {path}")
    except OSError as e:
        return Result(ok=False, error=str(e), code=1)


@register("read")
def run_read(params: dict, ctx: dict) -> Result:
    path = str(params.get("path", "")).strip()
    if not path:
        return Result(ok=False, error="@read requires a 'path' param", code=2)
    try:
        with open(path, encoding="utf-8") as f:
            return Result(ok=True, output=f.read())
    except OSError as e:
        return Result(ok=False, error=str(e), code=1)
