"""Execution engine (SPEC §3-4).

Loads a document, runs its workflow(s) top-to-bottom, resolving memory
references per step, applies @on_done hooks, and writes memory back to the file.
"""
from __future__ import annotations

import os
import re
import time

from . import plugins
from .memory import substitute
from .parser import Document, parse, parse_scalar, to_source

# Field ownership (SPEC §4): the runtime may only write memory keys under this
# reserved namespace. Everything else is agent-owned and never touched by the
# runtime — this is what makes the two-author document safe instead of lucky.
RUNTIME_NAMESPACE = "runtime."

_SET_RE = re.compile(r"^set:\s*memory\.([a-zA-Z0-9_.]+)\s*=\s*(.+)$")


def run(
    path: str,
    workflow_name: str = None,
    write_back: bool = True,
    out=print,
) -> Document:
    with open(path, encoding="utf-8") as f:
        doc = parse(f.read())

    mem_sec = doc.section("memory")
    memory = dict(mem_sec.memory) if mem_sec else {}
    ctx = {"memory": memory}

    workflows = doc.workflows()
    if workflow_name:
        workflows = [w for w in workflows if w.name == workflow_name]

    if not workflows:
        out("No workflow to run.")
    for wf in workflows:
        out(f"\n▶ workflow: {wf.name or '(unnamed)'}")
        for idx, step in enumerate(wf.steps, 1):
            _run_step(idx, step, memory, ctx, out)

    hooks_sec = doc.section("on_done")
    if hooks_sec:
        _apply_hooks(hooks_sec.hooks, memory, out)

    if write_back and mem_sec is not None:
        mem_sec.memory = memory
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_source(doc))
        out("\n· memory written back")

    return doc


def watch(
    path: str,
    workflow_name: str = None,
    interval: float = 1.0,
    max_runs: int = 0,
    write_back: bool = True,
    out=print,
) -> None:
    """Re-run the document whenever it changes on disk (SPEC §5, reactive seed).

    Self-trigger guard: the mtime baseline is captured *after* our own
    write-back, so the runtime's own writes never cause an infinite re-run loop —
    only an external edit advances the mtime past the baseline.
    """
    out(f"▶ watching {path} (every {interval}s) — edit & save to re-run, Ctrl+C to stop")
    last = None
    runs = 0
    try:
        while True:
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                time.sleep(interval)
                continue
            if mtime != last:
                if last is not None:
                    out("\n↻ change detected")
                run(path, workflow_name=workflow_name, write_back=write_back, out=out)
                runs += 1
                try:  # baseline AFTER write-back so we don't self-trigger
                    last = os.path.getmtime(path)
                except OSError:
                    last = mtime
                if max_runs and runs >= max_runs:
                    out(f"\n· reached max-runs={max_runs}, stopping")
                    return
            time.sleep(interval)
    except KeyboardInterrupt:
        out("\n· stopped")


def _run_step(idx, step, memory, ctx, out) -> None:
    plugin = plugins.get(step.plugin)
    label = f"  step {idx} @{step.plugin}"
    if plugin is None:
        out(f"{label} ✗ unknown plugin")
        return
    params = {k: substitute(v, memory) for k, v in step.params.items()}
    result = plugin(params, ctx)
    if result.ok:
        out(f"{label} ✓")
        _emit(result.output, out)
    else:
        out(f"{label} ✗ (exit {result.code})")
        _emit(result.error or result.output, out)


def _emit(text, out) -> None:
    if text and text.strip():
        for ln in text.rstrip().splitlines():
            out(f"      {ln}")


def _apply_hooks(hooks, memory, out) -> None:
    for h in hooks:
        m = _SET_RE.match(h.strip())
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        if not key.startswith(RUNTIME_NAMESPACE):
            out(
                f"  ⚠ refused: @on_done may only write runtime-owned memory "
                f"('{RUNTIME_NAMESPACE}*'); '{key}' is agent-owned and was left "
                f"untouched."
            )
            continue
        memory[key] = parse_scalar(raw)
