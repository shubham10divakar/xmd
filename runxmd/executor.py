"""Execution engine (SPEC §3-4).

Loads a document, runs its workflow(s) top-to-bottom, resolving memory
references per step, applies @on_done hooks, and writes memory back to the file.

Three output modes via @on_done:

  render / render(name.md)   [DEFAULT when no hook is present]
    Prose preserved, @sections stripped, each step block replaced with its
    output. Reads like a rendered notebook. → {stem}_render{ext}

  results / results(name.md)
    Step outputs only — no prose, no @sections, no code. For LLM consumption
    or compact reports. → {stem}_results{ext}

  write / write(name.md)
    Replica of the source document with a `result:` field injected into each
    step. Code is preserved; useful for re-running and diffing. → {stem}_output{ext}
"""
from __future__ import annotations

import copy
import os
import re
import time

from . import plugins
from .memory import substitute
from .parser import Document, parse, parse_scalar, to_source

RUNTIME_NAMESPACE = "runtime."

_SET_RE = re.compile(r"^set:\s*memory\.([a-zA-Z0-9_.]+)\s*=\s*(.+)$")
_WRITE_RE = re.compile(r"^write(?:\(([^)]+)\))?$")
_RESULTS_RE = re.compile(r"^results(?:\(([^)]+)\))?$")
_RENDER_RE = re.compile(r"^render(?:\(([^)]+)\))?$")
_STEP_LINE_RE = re.compile(r"^(\s*)-\s*@\w+\s*$")

_SKIP_SECTION_KINDS = {"goal", "memory", "tasks", "on_done"}


def run(
    path: str,
    workflow_name: str = None,
    write_back: bool = False,
    out=print,
) -> Document:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    doc = parse(source)

    mem_sec = doc.section("memory")
    memory = dict(mem_sec.memory) if mem_sec else {}
    ctx = {"memory": memory, "source_path": os.path.abspath(path)}

    workflows = doc.workflows()
    if workflow_name:
        workflows = [w for w in workflows if w.name == workflow_name]

    if not workflows:
        out("No workflow to run.")
    wf_results: dict = {}
    for wf in workflows:
        ok, records = run_workflow(wf, memory, ctx, out)
        wf_results[wf.name or ""] = records

    hooks_sec = doc.section("on_done")
    output_written = False
    if hooks_sec:
        output_written = _apply_hooks(
            hooks_sec.hooks, memory, out,
            doc=doc, wf_results=wf_results, source_path=path, source=source,
        )

    # Default: render mode — prose preserved, steps replaced with results.
    if not output_written and wf_results:
        _any = any(
            (r["output"] if r["ok"] else r["error"]).strip()
            for recs in wf_results.values() for r in recs
        )
        if _any:
            import pathlib as _pl
            _p = _pl.Path(path)
            _write_render_doc(
                source, wf_results,
                str(_p.parent / (_p.stem + "_render" + _p.suffix)),
                out,
            )

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
    write_back: bool = False,
    out=print,
) -> None:
    """Re-run the document whenever it changes on disk."""
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
                try:
                    last = os.path.getmtime(path)
                except OSError:
                    last = mtime
                if max_runs and runs >= max_runs:
                    out(f"\n· reached max-runs={max_runs}, stopping")
                    return
            time.sleep(interval)
    except KeyboardInterrupt:
        out("\n· stopped")


def run_workflow(wf, memory, ctx, out) -> tuple:
    """Run one workflow's steps; returns (all_ok, records)."""
    out(f"\n▶ workflow: {wf.name or '(unnamed)'}")
    return run_steps(wf.steps, memory, ctx, out)


def run_steps(steps, memory, ctx, out) -> tuple:
    """Run a list of steps top-to-bottom; returns (all_ok, records)."""
    records = []
    for idx, step in enumerate(steps, 1):
        ok, output, error = _run_step(idx, step, memory, ctx, out)
        records.append({"idx": idx, "plugin": step.plugin,
                        "output": output, "error": error, "ok": ok})
    return all(r["ok"] for r in records), records


def _run_step(idx, step, memory, ctx, out) -> tuple:
    """Run one step; returns (ok, output, error)."""
    plugin = plugins.get(step.plugin)
    label = f"  step {idx} @{step.plugin}"
    if plugin is None:
        out(f"{label} ✗ unknown plugin")
        return False, "", f"unknown plugin: @{step.plugin}"
    params = {k: substitute(v, memory) for k, v in step.params.items()
              if k != "result"}
    result = plugin(params, ctx)
    if result.ok:
        out(f"{label} ✓")
        _emit(result.output, out)
    else:
        out(f"{label} ✗ (exit {result.code})")
        _emit(result.error or result.output, out)
    return result.ok, result.output or "", result.error or ""


def _emit(text, out) -> None:
    if text and text.strip():
        for ln in text.rstrip().splitlines():
            out(f"      {ln}")


# ---------------------------------------------------------------------------
# Render mode — prose preserved, steps replaced with results
# ---------------------------------------------------------------------------

def _render_source(source: str, wf_results: dict) -> str:
    """Walk source line-by-line: skip @sections, replace step blocks with results."""
    all_results = [r for recs in wf_results.values() for r in recs]
    lines = source.splitlines()
    out_lines: list[str] = []
    n = len(lines)
    i = 0
    step_idx = 0
    skip_section = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # @section header
        if stripped.startswith("@"):
            kind = stripped[1:].split()[0].lower() if stripped[1:].split() else ""
            if kind in _SKIP_SECTION_KINDS:
                skip_section = True
                i += 1
                continue
            elif kind == "workflow":
                skip_section = False
                i += 1  # skip "@workflow name" header, process body normally
                continue
            else:
                skip_section = True
                i += 1
                continue

        # Inside a section to skip (non-@ lines in @goal / @memory / etc.)
        if skip_section:
            i += 1
            continue

        # Step block: - @plugin
        m = _STEP_LINE_RE.match(line)
        if m:
            step_indent = len(m.group(1))
            i += 1
            # Consume all lines belonging to this step
            while i < n:
                bl = lines[i]
                bl_stripped = bl.strip()
                if not bl_stripped:
                    # Blank line — peek ahead to decide if step is done
                    j = i + 1
                    while j < n and not lines[j].strip():
                        j += 1
                    if j >= n:
                        i = j
                        break
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_stripped.startswith("@") or next_indent <= step_indent:
                        i += 1  # consume the blank, step ends here
                        break
                    i += 1
                    continue
                bl_indent = len(bl) - len(bl.lstrip())
                if bl_indent <= step_indent:
                    break  # non-blank, non-indented → step ended
                i += 1

            # Emit result in place of the step block
            if step_idx < len(all_results):
                r = all_results[step_idx]
                text = (r["output"] if r["ok"] else r["error"]).strip()
                if text:
                    out_lines.append(text)
                    out_lines.append("")
            step_idx += 1
            continue

        # Regular prose line
        out_lines.append(line)
        i += 1

    # Trim trailing blank lines
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()

    return "\n".join(out_lines) + "\n"


def _write_render_doc(source: str, wf_results: dict, out_path: str, out) -> None:
    content = _render_source(source, wf_results)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    out(f"\n· render written → {out_path}")


# ---------------------------------------------------------------------------
# Results mode — step outputs only, no prose
# ---------------------------------------------------------------------------

def _write_results_doc(wf_results: dict, out_path: str, out) -> None:
    blocks = []
    for records in wf_results.values():
        for r in records:
            text = (r["output"] if r["ok"] else r["error"]).strip()
            if text:
                blocks.append(text)
    content = "\n\n".join(blocks) + "\n"
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    out(f"\n· results written → {out_path}")


# ---------------------------------------------------------------------------
# Write mode — replica with result: fields injected
# ---------------------------------------------------------------------------

def _write_output_doc(doc, wf_results: dict, out_path: str, out) -> None:
    new_doc = copy.deepcopy(doc)
    for sec in new_doc.sections:
        if sec.kind != "workflow":
            continue
        records = wf_results.get(sec.name or "", [])
        for i, step in enumerate(sec.steps):
            step.params.pop("result", None)
            if i >= len(records):
                continue
            r = records[i]
            text = (r["output"] if r["ok"] else r["error"]).strip()
            if text:
                step.params["result"] = text
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(to_source(new_doc))
    out(f"\n· output written → {out_path}")


# ---------------------------------------------------------------------------
# Hook dispatcher
# ---------------------------------------------------------------------------

def _apply_hooks(hooks, memory, out,
                 doc=None, wf_results=None, source_path=None, source=None) -> bool:
    """Process @on_done hooks; returns True if any output hook ran."""
    import pathlib
    output_written = False

    for h in hooks:
        h = h.strip()

        # render  or  render(filename.md)
        m_r = _RENDER_RE.match(h)
        if m_r:
            if source is None or wf_results is None:
                out("  ⚠ render: no source context — skipped")
                continue
            custom = (m_r.group(1) or "").strip()
            if custom:
                out_path = custom
            else:
                p = pathlib.Path(source_path)
                out_path = str(p.parent / (p.stem + "_render" + p.suffix))
            _write_render_doc(source, wf_results, out_path, out)
            output_written = True
            continue

        # results  or  results(filename.md)
        m_res = _RESULTS_RE.match(h)
        if m_res:
            if wf_results is None:
                out("  ⚠ results: no run context — skipped")
                continue
            custom = (m_res.group(1) or "").strip()
            if custom:
                out_path = custom
            else:
                p = pathlib.Path(source_path)
                out_path = str(p.parent / (p.stem + "_results" + p.suffix))
            _write_results_doc(wf_results, out_path, out)
            output_written = True
            continue

        # write  or  write(filename.md)
        m_w = _WRITE_RE.match(h)
        if m_w:
            if doc is None or wf_results is None:
                out("  ⚠ write: no document context — skipped")
                continue
            custom = (m_w.group(1) or "").strip()
            if custom:
                out_path = custom
            else:
                p = pathlib.Path(source_path)
                out_path = str(p.parent / (p.stem + "_output" + p.suffix))
            _write_output_doc(doc, wf_results, out_path, out)
            # write alone does NOT suppress default render
            continue

        # set: memory.runtime.key = value
        m = _SET_RE.match(h)
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

    return output_written
