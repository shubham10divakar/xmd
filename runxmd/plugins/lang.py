"""Inline-code and external-script language plugins (SPEC §3).

Two plugin families:

  Inline (@python, @node, @go, ...):
    Write code in the `run:` block — the runtime saves it to a temp file
    and executes it. Good for short, self-contained snippets.

  Script (@python_script, @node_script, @go_script, ...):
    Point at an existing file with `path:`. Optional `args:` are passed
    as command-line arguments. Good for full scripts that live on disk.

Detect-don't-install: if the interpreter is missing the step fails with a
clear message and the run continues — nothing is ever installed.

Supported languages:
  Python, Node.js, TypeScript, Ruby, Bash, Go, R, PHP, Perl, PowerShell
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile

from .base import Result, register

# ── PowerShell: Windows uses 'powershell' + ExecutionPolicy bypass;
#               Linux/macOS use 'pwsh' (PowerShell Core), no policy flag needed.
_IS_WINDOWS = platform.system() == "Windows"
_PS_CMD = (
    ["powershell", "-ExecutionPolicy", "Bypass"] if _IS_WINDOWS else ["pwsh"]
)

# ── Inline plugins ──────────────────────────────────────────────────────────
# name -> (executable + args prefix, temp-file extension)

LANGS = {
    "python":     (["python"],   ".py"),
    "node":       (["node"],     ".js"),
    "typescript": (["ts-node"],  ".ts"),
    "ruby":       (["ruby"],     ".rb"),
    "bash":       (["bash"],     ".sh"),
    "go":         (["go", "run"],".go"),
    "r":          (["Rscript"],  ".R"),
    "php":        (["php"],      ".php"),
    "perl":       (["perl"],     ".pl"),
    "powershell": (_PS_CMD,      ".ps1"),
}


def _make_inline_runner(name: str, cmd: list, ext: str):
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
        # Run in the MD file's directory so relative paths inside the snippet
        # (e.g. pathlib.Path("scripts/foo.py")) resolve from there, not from
        # wherever the user invoked runxmd.
        source_dir = os.path.dirname(ctx.get("source_path", "") or "") or None
        fd, path = tempfile.mkstemp(suffix=_ext)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code if isinstance(code, str) else str(code))
            proc = subprocess.run(
                _cmd + [path], capture_output=True, text=True, cwd=source_dir,
            )
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
    _make_inline_runner(_name, _cmd, _ext)


# ── Script plugins ───────────────────────────────────────────────────────────
# name -> executable + args prefix  (path: param points at the script file)

SCRIPT_LANGS = {
    "python_script":     ["python"],
    "node_script":       ["node"],
    "typescript_script": ["ts-node"],
    "ruby_script":       ["ruby"],
    "bash_script":       ["bash"],
    "go_script":         ["go", "run"],
    "r_script":          ["Rscript"],
    "php_script":        ["php"],
    "perl_script":       ["perl"],
    "powershell_script": _PS_CMD,
}


def _make_script_runner(name: str, cmd: list):
    @register(name)
    def runner(params: dict, ctx: dict, _name=name, _cmd=cmd) -> Result:
        script_path = str(params.get("path", "")).strip()
        if not script_path:
            return Result(ok=False, error=f"@{_name} requires a 'path' param", code=2)

        # Resolve relative paths against the MD file's directory so that
        # `path: scripts/foo.py` works regardless of where runxmd is invoked from.
        if not os.path.isabs(script_path):
            source_dir = os.path.dirname(ctx.get("source_path", "") or "")
            if source_dir:
                script_path = os.path.join(source_dir, script_path)

        if not os.path.isfile(script_path):
            return Result(
                ok=False,
                error=f"script not found: {script_path}",
                code=2,
            )
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
        args_raw = str(params.get("args", "")).strip()
        args = args_raw.split() if args_raw else []
        # Run in the MD file's directory so relative paths inside the script
        # resolve from there, not from the shell's CWD.
        run_dir = os.path.dirname(ctx.get("source_path", "") or "") or None
        proc = subprocess.run(
            _cmd + [script_path] + args,
            capture_output=True, text=True, cwd=run_dir,
        )
        return Result(
            ok=proc.returncode == 0,
            output=proc.stdout,
            error=proc.stderr,
            code=proc.returncode,
        )

    return runner


for _name, _cmd in SCRIPT_LANGS.items():
    _make_script_runner(_name, _cmd)
