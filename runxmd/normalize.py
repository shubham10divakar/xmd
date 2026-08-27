"""Output normalization (JOT plan A4).

Step output often carries machine-local detail — absolute paths, the running
user's home directory, the hostname, OS-specific path separators. Committed
into a render, that output does not diff across machines, which defeats the
purpose of checking a render into version control.

``normalize_output`` rewrites those to portable forms:

  * paths under the document's directory      → relative to it
  * the current user's home directory         → ``~``
  * the hostname                              → ``HOST``
  * ``\\`` inside path-like tokens             → ``/``

On by default; ``runxmd run --raw`` disables it. A step may also declare a
``redact:`` param (one literal or ``/regex/`` per line) to blank out volatile
substrings the generic rules cannot know about.
"""
from __future__ import annotations

import os
import re
import socket

# A path-like token: optional drive / "./" / "../", one or more "segment\",
# then a final "segment.ext". The trailing extension keeps this from matching
# escaped strings like 'a\nb' in program output.
_PATHISH = re.compile(
    r"(?<![\w])"
    r"((?:[A-Za-z]:\\|\.{1,2}\\)?"
    r"(?:[\w.\-]+\\)+"
    r"[\w.\-]+\.[A-Za-z0-9]{1,8})"
)


def _canonical_seps(text: str) -> str:
    return _PATHISH.sub(lambda m: m.group(1).replace("\\", "/"), text)


def _strip_prefix(text: str, prefix: str, replacement: str) -> str:
    if not prefix:
        return text
    for v in sorted({prefix, prefix.replace("\\", "/")}, key=len, reverse=True):
        text = text.replace(v + "\\", replacement).replace(v + "/", replacement)
    return text


def _mask_host(text: str) -> str:
    host = socket.gethostname()
    if host and len(host) > 2:
        text = re.sub(re.escape(host), "HOST", text, flags=re.IGNORECASE)
    return text


def apply_redactions(text: str, redact) -> str:
    if not redact:
        return text
    patterns = redact.splitlines() if isinstance(redact, str) else list(redact)
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue
        if len(pat) >= 2 and pat[0] == "/" and pat[-1] == "/":
            try:
                text = re.sub(pat[1:-1], "[redacted]", text)
            except re.error:
                text = text.replace(pat, "[redacted]")
        else:
            text = text.replace(pat, "[redacted]")
    return text


def normalize_output(text, *, base_dir: str = None, redact=()) -> str:
    """Return `text` with machine-local detail rewritten to portable forms."""
    if not isinstance(text, str) or not text:
        return text
    text = apply_redactions(text, redact)
    if base_dir:
        text = _strip_prefix(text, os.path.abspath(base_dir), "")
    home = os.path.expanduser("~")
    if home and home != "~":
        text = _strip_prefix(text, home, "~/")
    text = _mask_host(text)
    text = _canonical_seps(text)
    return text
