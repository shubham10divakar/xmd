"""Provenance headers + verification (JOT plan A1).

Every render / results / output file runxmd writes carries a machine-readable
header recording *what it is a render of*: the SHA-256 of the source, the
runxmd version, when it was generated, the platform, and the interpreter
versions that actually ran. The header is an HTML comment, so it stays
invisible in every Markdown viewer.

``runxmd verify <render>`` re-hashes the source and reports whether the render
is still current — turning "trust the render" from a social norm into a
checkable property.
"""
from __future__ import annotations

import datetime
import hashlib
import os
import platform
import re

from . import __version__

# Plugins whose output differs per run — a render containing them is a *sample*,
# not a computed fact. Recorded in the header; A6 wires this to a plugin
# attribute and adds inline markers + a `--pure` refusal.
NON_DETERMINISTIC = {"http", "llm"}

_HEADER_START = "<!-- runxmd-provenance"
_HEADER_END = "-->"
_HEADER_RE = re.compile(
    r"<!--\s*runxmd-provenance\s*\n(?P<body>.*?)\n\s*-->\s*\n?",
    re.DOTALL,
)


# --------------------------------------------------------------------------- #
# Hashing — canonicalize source bytes so the hash is stable across platforms
# --------------------------------------------------------------------------- #
def normalize_source(text: str) -> str:
    """Strip a UTF-8 BOM, convert CRLF/CR to LF, rstrip each line, and end with
    exactly one newline. A Windows checkout and a Linux checkout of the same
    logical source then hash identically."""
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def source_hash(text: str) -> str:
    return hashlib.sha256(normalize_source(text).encode("utf-8")).hexdigest()


def hash_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return source_hash(f.read())


# --------------------------------------------------------------------------- #
# Header build / parse
# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _interpreter_versions(plugin_names) -> dict:
    """Best-effort ``{lang: version}`` for the language plugins that ran."""
    try:
        from .checker import _version
        from .plugins.lang import LANGS
    except Exception:  # pragma: no cover - defensive
        return {}
    seen: dict = {}
    for name in sorted(set(plugin_names)):
        base = name[:-7] if name.endswith("_script") else name
        spec = LANGS.get(base)
        if not spec or base in seen:
            continue
        v = _version(spec[0][0])
        if v:
            seen[base] = v
    return seen


def _fmt_map(d: dict) -> str:
    return "{" + ", ".join(f"{k}: {v}" for k, v in d.items()) + "}"


def build(
    source_text: str,
    *,
    source_name: str,
    plugin_names=(),
    non_deterministic_steps=(),
) -> str:
    """Return the provenance HTML-comment block (trailing newline included)."""
    fields = {
        "source": source_name,
        "source_sha256": source_hash(source_text),
        "runxmd_version": __version__,
        "generated_utc": _now_iso(),
        "platform": f"{platform.system()}-{platform.machine()}".lower(),
        "interpreters": _fmt_map(_interpreter_versions(plugin_names)),
        "non_deterministic_steps": (
            "[" + ", ".join(str(i) for i in non_deterministic_steps) + "]"
        ),
    }
    lines = [_HEADER_START]
    lines += [f"{k}: {v}" for k, v in fields.items()]
    lines.append(_HEADER_END)
    return "\n".join(lines) + "\n"


def parse_header(text: str):
    """Return the header fields as a dict, or None if no header is present."""
    m = _HEADER_RE.search(text)
    if not m:
        return None
    fields: dict = {}
    for line in m.group("body").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fields[k.strip()] = v.strip()
    return fields


def strip_header(text: str) -> str:
    """Remove the provenance header (and one following blank line) if present.

    Used by ``runxmd run --check`` so the volatile ``generated_utc`` field does
    not make every check fail."""
    new = _HEADER_RE.sub("", text, count=1)
    return new.lstrip("\n") if new != text else text


def prepend(content: str, header: str) -> str:
    return header + "\n" + content


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #
def verify(render_path: str, source_path: str = None):
    """Check that a render still matches its source.

    Returns ``(exit_code, message)``:
      0  render matches the current source
      2  no header, or source cannot be located
      3  source has changed since the render was generated (STALE)
    """
    try:
        with open(render_path, encoding="utf-8") as f:
            render_text = f.read()
    except OSError as e:
        return 2, f"cannot read {render_path}: {e}"

    hdr = parse_header(render_text)
    if hdr is None:
        return 2, f"no runxmd-provenance header in {render_path}"

    if source_path is None:
        src_name = hdr.get("source")
        if not src_name:
            return 2, f"{render_path}: header has no 'source' field — pass --source"
        source_path = os.path.join(os.path.dirname(os.path.abspath(render_path)), src_name)

    if not os.path.isfile(source_path):
        return 2, f"source not found: {source_path}"

    actual = hash_file(source_path)
    expected = hdr.get("source_sha256", "")
    if actual == expected:
        return 0, (
            f"OK     {render_path}\n"
            f"       matches {source_path}  (sha256 {actual[:12]}…)"
        )
    return 3, (
        f"STALE  {render_path}\n"
        f"       source:   {source_path}\n"
        f"       expected: {expected[:12]}…  (recorded when the render was generated)\n"
        f"       actual:   {actual[:12]}…  (current source)\n"
        f"       re-run:   runxmd run {source_path}"
    )
