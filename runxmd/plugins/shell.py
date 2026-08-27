"""@shell and @print plugins (SPEC §3)."""
from __future__ import annotations

import subprocess

from .base import Result, register


def _timeout(params: dict, ctx: dict):
    raw = params.get("timeout")
    if raw in (None, ""):
        raw = ctx.get("timeout")
    try:
        t = float(raw)
        return t if t > 0 else None
    except (TypeError, ValueError):
        return None


@register("shell")
def run_shell(params: dict, ctx: dict) -> Result:
    cmd = params.get("run", "")
    if not str(cmd).strip():
        return Result(ok=True)
    stdin = params.get("stdin")
    stdin = None if stdin in (None, "") else (
        stdin if isinstance(stdin, str) else str(stdin))
    timeout = _timeout(params, ctx)
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            input=stdin, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Result(ok=False, error=f"@shell step timed out after {timeout}s",
                      code=124)
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
