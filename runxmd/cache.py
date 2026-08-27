"""Content-addressed step cache (JOT plan B5).

Opt-in via ``runxmd run --cache``. A step's result is keyed by everything that
can change its output: the plugin name, its params, the interpreter version,
and — for ``*_script`` plugins — the bytes of the referenced file. On a key
match the cached stdout/stderr/exit-code is returned without re-executing.
``--force`` ignores existing entries (but still refreshes them).

Only the language plugins are cacheable — they carry the subprocess cold-start
cost, and unlike ``@shell`` / ``@read`` / ``@write`` / ``@http`` / ``@llm`` their
output is a pure function of the cache key.
"""
from __future__ import annotations

import hashlib
import json
import os

from . import __version__

_VOLATILE = {"result", "status", "exit_code", "stderr", "session", "redact"}


def cache_dir() -> str:
    return os.environ.get("RUNXMD_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "runxmd"
    )


def cacheable(plugin: str) -> bool:
    from .plugins.lang import LANGS, SCRIPT_LANGS
    return plugin in LANGS or plugin in SCRIPT_LANGS


def _interpreter_version(plugin: str) -> str:
    from .checker import _version
    from .plugins.lang import LANGS, SCRIPT_LANGS
    base = plugin[:-7] if plugin.endswith("_script") else plugin
    spec = LANGS.get(base) or (
        (SCRIPT_LANGS.get(plugin) and (SCRIPT_LANGS[plugin], None)) or None
    )
    if not spec:
        return ""
    exe = spec[0][0] if isinstance(spec[0], list) else spec[0]
    try:
        return _version(exe)
    except Exception:  # pragma: no cover - defensive
        return ""


def _script_bytes(plugin: str, params: dict, ctx: dict) -> bytes:
    if not plugin.endswith("_script"):
        return b""
    path = str(params.get("path", "")).strip()
    if not path:
        return b""
    if not os.path.isabs(path):
        src_dir = os.path.dirname(ctx.get("source_path", "") or "")
        if src_dir:
            path = os.path.join(src_dir, path)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return b""


def key_for(plugin: str, params: dict, ctx: dict) -> str:
    h = hashlib.sha256()
    h.update(__version__.encode())
    h.update(b"\0plugin\0" + plugin.encode())
    for k in sorted(params):
        if k in _VOLATILE:
            continue
        h.update(b"\0p\0" + k.encode() + b"=" + str(params[k]).encode("utf-8", "replace"))
    h.update(b"\0iv\0" + _interpreter_version(plugin).encode())
    h.update(b"\0sb\0")
    h.update(hashlib.sha256(_script_bytes(plugin, params, ctx)).digest())
    return h.hexdigest()


def load(key: str):
    try:
        with open(os.path.join(cache_dir(), key + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def store(key: str, *, ok: bool, output: str, error: str, code: int) -> None:
    try:
        d = cache_dir()
        os.makedirs(d, exist_ok=True)
        tmp = os.path.join(d, key + ".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ok": ok, "output": output, "error": error, "code": code}, f)
        os.replace(tmp, os.path.join(d, key + ".json"))
    except OSError:
        pass
