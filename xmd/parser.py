"""XMD parser — turns an .xmd document into structured sections.

The parser never executes anything. It only understands structure (SPEC §1-2).
It is also responsible for serializing a Document back to .xmd text, which is
how memory write-back works (SPEC §4).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

KNOWN_KINDS = {"goal", "memory", "tasks", "workflow", "on_done"}

_TASK_RE = re.compile(r"^- \[([ xX])\]\s*(.*)$")
_STEP_RE = re.compile(r"^-\s*@(\w+)\s*$")


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Step:
    plugin: str
    params: dict = field(default_factory=dict)


@dataclass
class Task:
    done: bool
    text: str


@dataclass
class Section:
    kind: str
    name: Optional[str] = None
    text: str = ""                       # goal
    memory: dict = field(default_factory=dict)   # memory
    tasks: list = field(default_factory=list)    # tasks
    steps: list = field(default_factory=list)    # workflow
    hooks: list = field(default_factory=list)    # on_done
    raw: list = field(default_factory=list)      # unknown kinds


@dataclass
class Document:
    title: str = ""
    sections: list = field(default_factory=list)

    def section(self, kind: str, name: Optional[str] = None) -> Optional[Section]:
        for s in self.sections:
            if s.kind == kind and (name is None or s.name == name):
                return s
        return None

    def workflows(self) -> list:
        return [s for s in self.sections if s.kind == "workflow"]


# --------------------------------------------------------------------------- #
# Scalars
# --------------------------------------------------------------------------- #
def parse_scalar(v: str) -> Any:
    """Type a raw value string (SPEC §2.2)."""
    v = v.strip()
    if (len(v) >= 2) and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", ""):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def _format_scalar(v: Any, quote_strings: bool = True) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"' if quote_strings else v
    return str(v)


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def parse(source: str) -> Document:
    if source.startswith("﻿"):  # tolerate a UTF-8 BOM (common on Windows)
        source = source[1:]
    lines = source.splitlines()
    doc = Document()
    n = len(lines)

    # Title: first markdown heading before any section directive.
    i = 0
    while i < n and not lines[i].lstrip().startswith("@"):
        stripped = lines[i].strip()
        if stripped.startswith("#") and not doc.title:
            doc.title = stripped.lstrip("#").strip()
        i += 1

    # Sections.
    while i < n:
        if not lines[i].lstrip().startswith("@"):
            i += 1
            continue
        header = lines[i].strip()[1:].strip()
        parts = header.split(None, 1)
        kind = parts[0]
        name = parts[1] if len(parts) > 1 else None
        body: list = []
        i += 1
        while i < n and not lines[i].lstrip().startswith("@"):
            body.append(lines[i])
            i += 1
        doc.sections.append(_build_section(kind, name, body))
    return doc


def _build_section(kind: str, name: Optional[str], body: list) -> Section:
    sec = Section(kind=kind, name=name)
    if kind == "goal":
        sec.text = "\n".join(body).strip()
    elif kind == "memory":
        sec.memory = _parse_kv(body)
    elif kind == "tasks":
        sec.tasks = _parse_tasks(body)
    elif kind == "workflow":
        sec.steps = _parse_steps(body)
    elif kind == "on_done":
        sec.hooks = [ln.strip() for ln in body if ln.strip()]
    else:
        sec.raw = [ln for ln in body]
    return sec


def _parse_kv(body: list) -> dict:
    data: dict = {}
    for line in body:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if ":" in s:
            k, v = s.split(":", 1)
            data[k.strip()] = parse_scalar(v)
    return data


def _parse_tasks(body: list) -> list:
    tasks: list = []
    for line in body:
        m = _TASK_RE.match(line.strip())
        if m:
            tasks.append(Task(done=m.group(1).lower() == "x", text=m.group(2).strip()))
    return tasks


def _parse_steps(body: list) -> list:
    steps: list = []
    cur: Optional[Step] = None
    i, n = 0, len(body)
    while i < n:
        raw = body[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        m = _STEP_RE.match(stripped)
        if m:
            cur = Step(plugin=m.group(1), params={})
            steps.append(cur)
            i += 1
            continue
        if cur is not None and ":" in stripped:
            key, val = stripped.split(":", 1)
            key, val = key.strip(), val.strip()
            if val == "|":  # block scalar
                block: list = []
                i += 1
                while i < n:
                    bl = body[i]
                    if _STEP_RE.match(bl.strip()):
                        break
                    block.append(bl)
                    i += 1
                cur.params[key] = _dedent_block(block)
                continue
            cur.params[key] = parse_scalar(val)
        i += 1
    return steps


def _dedent_block(block: list) -> str:
    while block and not block[-1].strip():
        block.pop()
    while block and not block[0].strip():
        block.pop(0)
    indents = [len(b) - len(b.lstrip()) for b in block if b.strip()]
    pad = min(indents) if indents else 0
    return "\n".join(b[pad:] if len(b) >= pad else b for b in block)


# --------------------------------------------------------------------------- #
# Serialization (memory write-back, SPEC §4)
# --------------------------------------------------------------------------- #
def to_source(doc: Document) -> str:
    out: list = []
    if doc.title:
        out.append(f"# {doc.title}")
        out.append("")
    for sec in doc.sections:
        out.append(_serialize_section(sec))
    return "\n".join(out).rstrip() + "\n"


def _serialize_section(sec: Section) -> str:
    lines = ["@" + sec.kind + (f" {sec.name}" if sec.name else "")]
    if sec.kind == "goal":
        if sec.text:
            lines.append(sec.text)
    elif sec.kind == "memory":
        for k, v in sec.memory.items():
            lines.append(f"{k}: {_format_scalar(v)}")
    elif sec.kind == "tasks":
        for t in sec.tasks:
            lines.append(f"- [{'x' if t.done else ' '}] {t.text}")
    elif sec.kind == "workflow":
        for st in sec.steps:
            lines.append(f"- @{st.plugin}")
            for k, v in st.params.items():
                if isinstance(v, str) and "\n" in v:
                    lines.append(f"  {k}: |")
                    lines.extend(f"    {bl}" for bl in v.split("\n"))
                else:
                    # workflow params (commands) are emitted unquoted for readability
                    lines.append(f"  {k}: {_format_scalar(v, quote_strings=False)}")
    elif sec.kind == "on_done":
        lines.extend(sec.hooks)
    else:
        lines.extend(sec.raw)
    lines.append("")
    return "\n".join(lines)
