"""Interpreter availability check — `runxmd check`.

Scans every language plugin's executable, reports installed/missing,
and prints the version string where available.
"""
from __future__ import annotations

import platform
import shutil
import subprocess

_IS_WINDOWS = platform.system() == "Windows"
# PowerShell: 'powershell' on Windows, 'pwsh' (Core) on Linux/macOS
_PS_EXE = "powershell" if _IS_WINDOWS else "pwsh"

# Maps plugin name -> (human label, executable)
_PLUGINS = [
    ("Python",      "python",     "python"),
    ("Node.js",     "node",       "node"),
    ("TypeScript",  "typescript", "ts-node"),
    ("Ruby",        "ruby",       "ruby"),
    ("Bash",        "bash",       "bash"),
    ("Go",          "go",         "go"),
    ("R",           "r",          "Rscript"),
    ("PHP",         "php",        "php"),
    ("Perl",        "perl",       "perl"),
    ("PowerShell",  "powershell", _PS_EXE),
]

# Version command overrides for executables that don't use --version
_VERSION_CMDS: dict[str, list[str]] = {
    "go":         ["go", "version"],
    "perl":       ["perl", "-e", "print $^V"],
    "powershell": ["powershell", "-NoProfile", "-Command",
                   "$v=$PSVersionTable.PSVersion; \"$($v.Major).$($v.Minor).$($v.Build)\""],
    "pwsh":       ["pwsh", "-NoProfile", "-Command",
                   "$v=$PSVersionTable.PSVersion; \"$($v.Major).$($v.Minor).$($v.Build)\""],
}

_INSTALL_HINTS: dict[str, str] = {
    "ts-node":    "npm install -g ts-node  (requires Node.js)",
    "ruby":       "https://www.ruby-lang.org/en/downloads/",
    "go":         "https://go.dev/dl/",
    "Rscript":    "https://cran.r-project.org/",
    "php":        "https://www.php.net/downloads",
    "pwsh":       "https://aka.ms/install-powershell  (PowerShell Core)",
}


def _version(exe: str) -> str:
    """Return a short version string for exe, or empty string on failure.

    Uses the full path from shutil.which so the exact same binary that was
    detected is queried — avoids Windows resolving 'bash' to WSL instead of
    the Git Bash / Cygwin binary that shutil.which actually found.
    """
    full = shutil.which(exe) or exe
    base_cmd = _VERSION_CMDS.get(exe, [exe, "--version"])
    # Replace the bare executable name with its resolved full path.
    cmd = [full if c == exe else c for c in base_cmd]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        # Prefer stdout; only use stderr when exit code is 0 to avoid
        # showing error messages (e.g. WSL-not-found) as a version string.
        raw = r.stdout.strip() or (r.stderr.strip() if r.returncode == 0 else "")
        if raw:
            return raw.splitlines()[0][:60]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def check(out=print) -> None:
    """Print a table of all language plugins and their interpreter status."""
    out("runxmd check — interpreter availability\n")

    col_lang  = 12
    col_plug  = 14
    col_exe   = 12
    col_ver   = 40

    header = (
        f"  {'Language':<{col_lang}} "
        f"{'Plugin':<{col_plug}} "
        f"{'Executable':<{col_exe}} "
        f"{'Status':<8} "
        f"Version"
    )
    out(header)
    out("  " + "-" * (col_lang + col_plug + col_exe + col_ver + 20))

    available = []
    missing = []

    for label, plugin, exe in _PLUGINS:
        found = shutil.which(exe) is not None
        if found:
            ver = _version(exe)
            status = "✓  found"
            ver_str = ver if ver else "(installed)"
            available.append(plugin)
        else:
            status = "✗  missing"
            hint = _INSTALL_HINTS.get(exe, "")
            ver_str = f"install: {hint}" if hint else "not installed"
            missing.append((plugin, exe, hint))

        out(
            f"  {'@' + plugin:<{col_lang + 1}} "
            f"{'@' + plugin + '_script':<{col_plug + 1}} "
            f"{exe:<{col_exe}} "
            f"{status:<10} "
            f"{ver_str}"
        )

    out("")
    out(f"  {len(available)} of {len(_PLUGINS)} languages available.")

    if missing:
        out("")
        out("  Missing interpreters:")
        for plugin, exe, hint in missing:
            line = f"    @{plugin} / @{plugin}_script  →  '{exe}'"
            if hint:
                line += f"\n      install: {hint}"
            out(line)
    else:
        out("  All language plugins are ready.")
