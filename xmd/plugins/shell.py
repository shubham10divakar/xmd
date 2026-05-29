"""@shell and @print plugins (SPEC §3)."""
from __future__ import annotations

import subprocess

from .base import Result, register


@register("shell")
def run_shell(params: dict, ctx: dict) -> Result:
    cmd = params.get("run", "")
    if not str(cmd).strip():
        return Result(ok=True)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return Result(
        ok=proc.returncode == 0,
        output=proc.stdout,
        error=proc.stderr,
        code=proc.returncode,
    )


@register("print")
def run_print(params: dict, ctx: dict) -> Result:
    text = params.get("text", params.get("run", ""))
    return Result(ok=True, output=str(text))
