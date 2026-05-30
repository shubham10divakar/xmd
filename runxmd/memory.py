"""Memory substitution — power #2 of three (SPEC §4).

Resolves ``{{ memory.<key> }}`` references inside step params before execution.
Read-in and write-back are handled by the parser + executor; this module is just
the templating layer.
"""
from __future__ import annotations

import re
from typing import Any

_REF = re.compile(r"\{\{\s*memory\.([a-zA-Z0-9_.]+)\s*\}\}")


def substitute(value: Any, memory: dict) -> Any:
    """Replace ``{{ memory.key }}`` in a string. Non-strings pass through.

    Missing keys resolve to empty string (SPEC §4).
    """
    if not isinstance(value, str):
        return value
    return _REF.sub(lambda m: str(memory.get(m.group(1), "")), value)
