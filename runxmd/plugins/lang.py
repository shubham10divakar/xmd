"""Inline-code language plugins: @python, @node, @ruby, @bash (SPEC §3).

Each writes the step's ``run`` body to a temp file and dispatches to the
interpreter. Detect-don't-install: if the interpreter is missing, the step fails
with a clear message and the run continues — nothing is ever installed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from .base import Result, register

# directive name -> (executable + args prefix, temp-file extension)
LANGS = {
    "python": (["python"], ".py"),
    "node": (["node"], ".js"),
    "ruby": (["ruby"], ".rb"),
    "bash": (["bash"], ".sh"),
}


def _make_runner(name: str, cmd: list, ext: str):
    @register(name)
    def runner(params: dict, ctx: dict, _name=name, _cmd=cmd, _ext=ext) -> Result:
        code = params.get("run", "")
        exe = _cmd[0]
        if shutil.which(exe) is None:
            return Result(
                ok=False,
                error=(
                    f"'{exe}' not found on this machine — install it to run "
                    f"@{_name} steps, or skip this step."
                ),
                code=127,
            )
        fd, path = tempfile.mkstemp(suffix=_ext)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code if isinstance(code, str) else str(code))
            proc = subprocess.run(_cmd + [path], capture_output=True, text=True)
            return Result(
                ok=proc.returncode == 0,
                output=proc.stdout,
                error=proc.stderr,
                code=proc.returncode,
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    return runner


for _name, (_cmd, _ext) in LANGS.items():
    _make_runner(_name, _cmd, _ext)
