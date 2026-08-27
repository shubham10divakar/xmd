"""Static checks for `runxmd validate` (JOT plan C7).

The step grammar is a hand-rolled line scanner, **not** YAML (see
`GRAMMAR.md`). Its most dangerous failure mode is misparsing silently. This
module surfaces the constructs it cannot handle — YAML-isms a user will reach
for and be wrong about — plus structural problems the parser tolerates.

`lint(source, doc)` returns a list of `(severity, message)` where severity is
``"error"`` (validate exits non-zero) or ``"warn"`` (printed, exit unaffected).
"""
from __future__ import annotations

import re

from . import plugins
from .executor import (_RENDER_RE, _RESULTS_RE, _SET_RE, _SUMMARIZE_RE,
                       _WRITE_RE)
from .parser import KNOWN_KINDS

_STEP_LINE = re.compile(r"^\s*-\s*@(\w+)\s*$")
_PARAM_LINE = re.compile(r"^(\s+)([A-Za-z0-9_\-]+):\s*(.*)$")
_ANCHOR = re.compile(r"(?:^|\s):?\s*[&*][A-Za-z0-9_]+\b")
_FLOW = re.compile(r"^[\[{].*[\]}]$")

# @plugins that are legitimately parameterless
_NO_PARAM_OK = {"print"}


def _hook_ok(h: str) -> bool:
    h = h.strip()
    return bool(
        _SET_RE.match(h) or _RENDER_RE.match(h) or _RESULTS_RE.match(h)
        or _WRITE_RE.match(h) or _SUMMARIZE_RE.match(h)
    )


def lint(source: str, doc) -> list:
    out: list = []
    lines = source.splitlines()

    # ---- raw-source scan: indentation + YAML-isms in step/param regions ----
    in_block = False
    block_indent = 0
    for n, raw in enumerate(lines, 1):
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))

        if in_block:
            if stripped and indent <= block_indent and _PARAM_LINE.match(raw):
                in_block = False
            elif stripped and not raw.startswith(" ") and not raw.startswith("\t"):
                in_block = False
            else:
                continue

        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            out.append(("error", f"line {n}: tab in indentation — use spaces"))

        m = _PARAM_LINE.match(raw)
        if m:
            key, val = m.group(2), m.group(3).strip()
            if val == ">" or val.startswith("> "):
                out.append(("error", f"line {n}: folded scalar '>' is not supported — use '|'"))
            elif val == "|" or val.startswith("|"):
                in_block, block_indent = True, len(m.group(1))
            elif _FLOW.match(val):
                out.append(("error",
                            f"line {n}: flow collection {val!r} is read as a literal string, "
                            f"not parsed — use a '|' block or separate keys"))
            if _ANCHOR.search(" " + val):
                out.append(("error",
                            f"line {n}: YAML anchor/alias syntax is not supported"))

    # ---- parsed-doc structural checks ----
    for sec in doc.sections:
        if sec.kind not in KNOWN_KINDS:
            out.append(("warn",
                        f"@{sec.kind}: unknown section — passed through as inert prose"))
        if sec.kind == "on_done":
            for h in sec.hooks:
                if not _hook_ok(h):
                    out.append(("error", f"@on_done: unrecognized hook {h!r}"))

    for wf in doc.workflows():
        wname = wf.name or "(unnamed)"
        for i, step in enumerate(wf.steps, 1):
            if plugins.get(step.plugin) is None:
                out.append(("error",
                            f"workflow {wname} step {i}: unknown plugin @{step.plugin}"))
            real = {k: v for k, v in step.params.items() if k != "result"}
            if not real and step.plugin not in _NO_PARAM_OK:
                out.append(("warn",
                            f"workflow {wname} step {i}: @{step.plugin} has no params "
                            f"— possible misparse of an indented line"))
            for k, v in step.params.items():
                if isinstance(v, str) and any(
                        _STEP_LINE.match(ln) for ln in v.splitlines()):
                    out.append(("warn",
                                f"workflow {wname} step {i}: param {k!r} contains a line "
                                f"that looks like a step (`- @…`) — block scalar may have "
                                f"over-captured"))
    return out
