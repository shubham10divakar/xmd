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
import datetime
import json
import os
import re
import time
import uuid

from dataclasses import dataclass, field as _field

from . import normalize as _normalize
from . import plugins, provenance
from .memory import substitute
from .parser import Document, parse, parse_scalar, to_source

RUNTIME_NAMESPACE = "runtime."


class _Sessions:
    """Accumulated code + stdout per ``session:`` name, for a single run."""

    def __init__(self):
        self._code: dict = {}
        self._out: dict = {}

    def prelude(self, name: str) -> str:
        return self._code.get(name, "")

    def stdout(self, name: str) -> str:
        return self._out.get(name, "")

    def record(self, name: str, full_code: str, full_stdout: str) -> None:
        self._code[name] = full_code
        self._out[name] = full_stdout


@dataclass
class RunReport:
    """Outcome of a run, for callers that need more than the parsed Document.

    ``run()`` still returns the ``Document`` (unchanged public contract); it
    also attaches an instance of this as ``doc.report`` so the CLI can decide
    an exit code without re-deriving anything.
    """
    all_ok: bool = True
    failed_steps: list = _field(default_factory=list)   # (workflow, idx, plugin)
    check_failed: bool = None                           # None → --check not run
    check_target: str = ""
    pure_refused: list = _field(default_factory=list)   # plugin names refused by --pure

_SET_RE = re.compile(r"^set:\s*memory\.([a-zA-Z0-9_.]+)\s*=\s*(.+)$")
_WRITE_RE = re.compile(r"^write(?:\(([^)]+)\))?$")
_RESULTS_RE = re.compile(r"^results(?:\(([^)]+)\))?$")
_RENDER_RE = re.compile(r"^render(?:\(([^)]+)\))?$")
_STEP_LINE_RE = re.compile(r"^(\s*)-\s*@\w+\s*$")
_CONTEXT_REF = re.compile(r"\{\{\s*context(?:_memory)?\s*\}\}")
_SUMMARIZE_RE = re.compile(r"^summarize(?:\(([^)]+)\))?$")

_SKIP_SECTION_KINDS = {"goal", "memory", "tasks", "on_done", "context_memory"}

# Max characters kept per captured step output in a @context_memory log entry.
CONTEXT_OUTPUT_CAP = 200


def run(
    path: str,
    workflow_name: str = None,
    write_back: bool = False,
    save_context: bool = True,
    add_provenance: bool = True,
    check: bool = False,
    normalize: bool = True,
    pure: bool = False,
    out=print,
) -> Document:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    doc = parse(source)
    report = RunReport()
    doc.report = report
    run_id = uuid.uuid4().hex[:4]

    mem_sec = doc.section("memory")
    memory = dict(mem_sec.memory) if mem_sec else {}
    ctx = {"memory": memory, "source_path": os.path.abspath(path),
           "normalize": normalize, "pure": pure}

    ctx_sec = doc.section("context_memory")
    if ctx_sec is not None:
        # Expose the rolling summary + parsed log so steps/agents can read the
        # accumulated context back. Only the summary is substituted into params.
        ctx["context_memory"] = {
            "summary": ctx_sec.summary,
            "entries": list(ctx_sec.entries),
        }

    workflows = doc.workflows()
    if workflow_name:
        workflows = [w for w in workflows if w.name == workflow_name]

    if not workflows:
        out("No workflow to run.")
    wf_results: dict = {}
    for wf in workflows:
        ok, records = run_workflow(wf, memory, ctx, out)
        wf_results[wf.name or ""] = records
        if not ok:
            report.all_ok = False
            report.failed_steps += [
                (wf.name or "", r["idx"], r["plugin"])
                for r in records if not r["ok"]
            ]
        report.pure_refused += [
            r["plugin"] for r in records
            if r.get("code") == 2 and r["error"].startswith("refused:")
        ]

    header = _provenance_header(source, path, wf_results) if add_provenance else ""

    # --check: compare a fresh default render against the committed one and
    # report drift. Nothing is written, no hooks run — this is a read-only
    # doctest for the whole document.
    if check:
        _run_check(source, wf_results, path, doc, header, report, out)
        return doc

    hooks_sec = doc.section("on_done")
    output_written = False
    if hooks_sec:
        output_written = _apply_hooks(
            hooks_sec.hooks, memory, out,
            doc=doc, wf_results=wf_results, source_path=path, source=source,
            header=header,
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
                out, header=header,
            )

    # Append the run's captured records to @context_memory (raw jsonl log).
    # Opt-in by the section's presence; targeted splice keeps the rest of the
    # file byte-identical (does NOT route through to_source).
    if ctx_sec is not None and save_context and wf_results:
        records = _build_context_records(run_id, wf_results)
        if records:
            jsonl = [
                json.dumps({k: v for k, v in r.items() if v is not None},
                           ensure_ascii=False)
                for r in records
            ]
            _append_to_section(path, "context_memory", jsonl, fenced="jsonl")
            out(f"\n· context saved → @context_memory ({len(records)} entries)")

            # @on_done: summarize — regenerate the rolling summary FROM the raw
            # log (never from the prior summary → no compounding drift). Only the
            # summary is later injected via {{ context }}.
            want, smodel = _summary_request(hooks_sec)
            if want:
                all_entries = list(ctx_sec.entries) + records
                new_summary = _summarize_context(all_entries, smodel, out)
                if new_summary:
                    _set_section_summary(path, "context_memory", new_summary)
                    out("· context summarized → @context_memory")

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
    save_context: bool = True,
    add_provenance: bool = True,
    normalize: bool = True,
    pure: bool = False,
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
                run(path, workflow_name=workflow_name, write_back=write_back,
                    save_context=save_context, add_provenance=add_provenance,
                    normalize=normalize, pure=pure, out=out)
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
        ok, output, error, dur, code = _run_step(idx, step, memory, ctx, out)
        records.append({"idx": idx, "plugin": step.plugin,
                        "output": output, "error": error, "ok": ok,
                        "duration_ms": dur, "code": code})
    return all(r["ok"] for r in records), records


def _run_step(idx, step, memory, ctx, out) -> tuple:
    """Run one step; returns (ok, stdout, stderr, duration_ms, exit_code)."""
    plugin = plugins.get(step.plugin)
    label = f"  step {idx} @{step.plugin}"
    if plugin is None:
        out(f"{label} ✗ unknown plugin")
        return False, "", f"unknown plugin: @{step.plugin}", 0, 127
    if ctx.get("pure") and not plugins.is_deterministic(step.plugin):
        out(f"{label} ✗ refused (--pure): @{step.plugin} is non-deterministic")
        return (False, "",
                f"refused: @{step.plugin} is non-deterministic and --pure is set",
                0, 2)
    ctx_summary = (ctx.get("context_memory") or {}).get("summary", "")
    params = {k: _subst_context(substitute(v, memory), ctx_summary)
              for k, v in step.params.items()
              if k not in ("result", "redact", "session")}

    # session: <name> — steps sharing a name run with every earlier session
    # step's code prepended, so a variable defined in one is visible in the
    # next. Default (no session:) stays fully isolated. Implemented by
    # re-execution + output prefix-subtraction, so it works for every language
    # with no REPL protocol; the trade-off is that side effects in earlier
    # session steps re-run each time.
    session = step.params.get("session")
    raw_run = params.get("run")
    sess = ctx.setdefault("_sessions", _Sessions()) if session else None
    prelude = ""
    if sess is not None and isinstance(raw_run, str):
        prelude = sess.prelude(session)
        if prelude:
            params["run"] = prelude + "\n" + raw_run

    t0 = time.perf_counter()
    result = plugin(params, ctx)
    dur = int((time.perf_counter() - t0) * 1000)

    if sess is not None and isinstance(raw_run, str):
        full_code = prelude + "\n" + raw_run if prelude else raw_run
        full_out = result.output or ""
        prev = sess.stdout(session)
        if prelude and full_out.startswith(prev):
            result.output = full_out[len(prev):].lstrip("\n")
        sess.record(session, full_code, full_out)

    if ctx.get("normalize", True):
        base = os.path.dirname(ctx.get("source_path", "") or "")
        redact = step.params.get("redact", ())
        result.output = _normalize.normalize_output(
            result.output, base_dir=base, redact=redact)
        result.error = _normalize.normalize_output(
            result.error, base_dir=base, redact=redact)

    if result.ok:
        out(f"{label} ✓")
        _emit(result.output, out)
    else:
        out(f"{label} ✗ (exit {result.code})")
        _emit(result.error or result.output, out)
    return result.ok, result.output or "", result.error or "", dur, result.code


def _subst_context(value, summary: str):
    """Replace ``{{ context }}`` / ``{{ context_memory }}`` with the rolling
    summary. Non-strings pass through; absent summary resolves to empty string."""
    if not isinstance(value, str):
        return value
    return _CONTEXT_REF.sub(summary, value)


def _emit(text, out) -> None:
    if text and text.strip():
        for ln in text.rstrip().splitlines():
            out(f"      {ln}")


# ---------------------------------------------------------------------------
# Provenance — every output file records what it is a render of (JOT plan A1)
# ---------------------------------------------------------------------------

def _provenance_header(source: str, source_path: str, wf_results: dict) -> str:
    """Build the provenance HTML comment for this run's output files."""
    names: set = set()
    nd: list = []
    gi = 0
    for recs in wf_results.values():
        for r in recs:
            gi += 1
            names.add(r["plugin"])
            if not plugins.is_deterministic(r["plugin"]):
                nd.append(gi)
    return provenance.build(
        source,
        source_name=os.path.basename(source_path) if source_path else "",
        plugin_names=names,
        non_deterministic_steps=nd,
    )


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
                    if not plugins.is_deterministic(r["plugin"]):
                        out_lines.append(
                            f"<!-- non-deterministic: @{r['plugin']} — "
                            f"this output is a sample, not a computed fact -->"
                        )
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


def _render_content(source: str, wf_results: dict, header: str = "") -> str:
    content = _render_source(source, wf_results)
    return provenance.prepend(content, header) if header else content


def _write_render_doc(source: str, wf_results: dict, out_path: str, out,
                      header: str = "") -> None:
    content = _render_content(source, wf_results, header)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    out(f"\n· render written → {out_path}")


# ---------------------------------------------------------------------------
# --check — read-only drift check against the committed render (JOT plan A2)
# ---------------------------------------------------------------------------

def _default_render_path(source_path: str) -> str:
    import pathlib
    p = pathlib.Path(source_path)
    return str(p.parent / (p.stem + "_render" + p.suffix))


def _run_check(source, wf_results, source_path, doc, header, report, out) -> None:
    # Honour an explicit render(name) hook target if one is set.
    target = _default_render_path(source_path)
    hooks_sec = doc.section("on_done")
    if hooks_sec:
        for h in hooks_sec.hooks:
            m = _RENDER_RE.match(h.strip())
            if m and (m.group(1) or "").strip():
                target = (m.group(1) or "").strip()
                break
    report.check_target = target

    fresh = provenance.strip_header(_render_content(source, wf_results, header))
    if not os.path.isfile(target):
        report.check_failed = True
        out(f"✗ check: {target} does not exist — run `runxmd run {source_path}` to create it")
        return
    with open(target, encoding="utf-8") as f:
        committed = provenance.strip_header(f.read())

    if fresh == committed:
        report.check_failed = False
        out(f"✓ check: {target} is up to date")
        return

    report.check_failed = True
    import difflib
    diff = list(difflib.unified_diff(
        committed.splitlines(), fresh.splitlines(),
        fromfile=f"{target} (committed)", tofile="fresh run", lineterm="",
    ))
    out(f"✗ check: {target} is stale — {sum(1 for d in diff if d.startswith(('+', '-')) and not d.startswith(('+++', '---')))} changed line(s)")
    for line in diff[:40]:
        out("    " + line)
    if len(diff) > 40:
        out(f"    … ({len(diff) - 40} more diff lines)")


# ---------------------------------------------------------------------------
# Results mode — step outputs only, no prose
# ---------------------------------------------------------------------------

def _write_results_doc(wf_results: dict, out_path: str, out,
                       header: str = "") -> None:
    blocks = []
    for records in wf_results.values():
        for r in records:
            text = (r["output"] if r["ok"] else r["error"]).strip()
            if text:
                blocks.append(text)
    content = "\n\n".join(blocks) + "\n"
    if header:
        content = provenance.prepend(content, header)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    out(f"\n· results written → {out_path}")


# ---------------------------------------------------------------------------
# Write mode — replica with result: fields injected
# ---------------------------------------------------------------------------

def _write_output_doc(doc, wf_results: dict, out_path: str, out,
                      header: str = "") -> None:
    new_doc = copy.deepcopy(doc)
    for sec in new_doc.sections:
        if sec.kind != "workflow":
            continue
        records = wf_results.get(sec.name or "", [])
        for i, step in enumerate(sec.steps):
            for stale in ("result", "status", "exit_code", "stderr"):
                step.params.pop(stale, None)
            if i >= len(records):
                continue
            r = records[i]
            text = (r["output"] if r["ok"] else r["error"]).strip()
            if text:
                step.params["result"] = text
            # Record status + exit code so a re-run diff catches a step that
            # started failing even when it prints nothing (JOT plan A2).
            step.params["status"] = "ok" if r["ok"] else "error"
            step.params["exit_code"] = r.get("code", 0)
            err = (r.get("error") or "").strip()
            if err and err != text:
                step.params["stderr"] = err
    content = to_source(new_doc)
    if header:
        content = provenance.prepend(content, header)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    out(f"\n· output written → {out_path}")


# ---------------------------------------------------------------------------
# Hook dispatcher
# ---------------------------------------------------------------------------

def _apply_hooks(hooks, memory, out,
                 doc=None, wf_results=None, source_path=None, source=None,
                 header="") -> bool:
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
            _write_render_doc(source, wf_results, out_path, out, header=header)
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
            _write_results_doc(wf_results, out_path, out, header=header)
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
            _write_output_doc(doc, wf_results, out_path, out, header=header)
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


# ---------------------------------------------------------------------------
# @context_memory — raw capture (SPEC: context-memory-design §4)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_context_records(run_id: str, wf_results: dict,
                           cap: int = CONTEXT_OUTPUT_CAP) -> list:
    """Turn a run's per-step records into @context_memory log entries.

    One entry per step. Output is whitespace-collapsed to a single line and
    truncated to `cap` chars — the raw log is an index, not an archive (full
    multi-line output lives in the render/output files).
    """
    now = _now_iso()
    records = []
    for wf_name, recs in wf_results.items():
        for r in recs:
            text = (r["output"] if r["ok"] else r["error"]) or ""
            text = " ".join(text.split())
            if len(text) > cap:
                text = text[:cap - 1] + "…"
            records.append({
                "time": now,
                "run": run_id,
                "workflow": wf_name or None,
                "step": r["idx"],
                "plugin": r["plugin"],
                "status": "ok" if r["ok"] else "err",
                "duration_ms": r.get("duration_ms"),
                "output": text,
            })
    return records


def _append_to_section(path: str, kind: str, new_lines: list,
                       *, fenced: str = None) -> None:
    """Append lines into the ``@<kind>`` section of a file, byte-preserving.

    A targeted text splice: everything outside the insertion point is left
    exactly as-is (this deliberately does NOT use ``to_source``, which would
    reformat the whole document). If ``fenced`` is given, lines are inserted
    inside that section's first fenced block (created if absent). The section
    itself is created at EOF if it does not exist. Generic so @human_memory can
    reuse it later.
    """
    with open(path, encoding="utf-8") as f:
        src = f.read()
    lines = src.split("\n")
    header = "@" + kind

    h = None
    for idx, ln in enumerate(lines):
        st = ln.strip()
        if st == header or st.startswith(header + " "):
            h = idx
            break

    if h is None:  # section absent → create it at EOF
        tail = []
        if lines and any(s.strip() for s in lines):
            tail.append("")
        tail.append(header)
        tail.append("")
        if fenced is not None:
            tail += ["```" + fenced, *new_lines, "```"]
        else:
            tail += list(new_lines)
        lines += tail
        _write_lines(path, lines)
        return

    # section body spans (h, end) up to the next "@section" or EOF
    end = len(lines)
    for idx in range(h + 1, len(lines)):
        if lines[idx].lstrip().startswith("@"):
            end = idx
            break

    if fenced is not None:
        open_i = close_i = None
        for idx in range(h + 1, end):
            if lines[idx].strip().startswith("```"):
                if open_i is None:
                    open_i = idx
                else:
                    close_i = idx
                    break
        if open_i is not None and close_i is not None:
            lines[close_i:close_i] = list(new_lines)
        else:  # no fence yet → create one at the end of the section body
            at = end
            while at - 1 > h and not lines[at - 1].strip():
                at -= 1
            lines[at:at] = ["```" + fenced, *new_lines, "```"]
    else:
        at = end
        while at - 1 > h and not lines[at - 1].strip():
            at -= 1
        lines[at:at] = list(new_lines)

    _write_lines(path, lines)


def _write_lines(path: str, lines: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# @context_memory — rolling summary (Phase 2, context-memory-design §4.1)
# ---------------------------------------------------------------------------

def _summary_request(hooks_sec) -> tuple:
    """Scan @on_done for a ``summarize`` / ``summarize(model)`` directive.

    Returns (wanted, model_or_None).
    """
    if hooks_sec is None:
        return False, None
    for h in hooks_sec.hooks:
        m = _SUMMARIZE_RE.match(h.strip())
        if m:
            return True, ((m.group(1) or "").strip() or None)
    return False, None


def _llm_complete(prompt: str, model: str = None, max_tokens: int = 512) -> tuple:
    """Call the @llm plugin; returns (ok, text_or_error).

    Thin indirection so tests can monkeypatch summarization without a live API
    key, and so any future model backend swaps in one place.
    """
    llm = plugins.get("llm")
    if llm is None:
        return False, "@llm plugin unavailable"
    res = llm({"prompt": prompt, "model": model, "max_tokens": max_tokens}, {})
    return (res.ok, res.output if res.ok else res.error)


def _summarize_context(entries: list, model: str, out, max_tokens: int = 512):
    """Regenerate the rolling summary from the raw log (the anti-drift rule).

    The prompt contains the JSON-lines log only — never the previous summary —
    so the summary always reconstructs faithfully from ground truth. Returns the
    new summary text, or None if the model is unavailable (summary left as-is).
    """
    if not entries:
        return None
    log = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    prompt = (
        "You maintain a rolling WORKING-MEMORY summary for an automated agent.\n"
        "Below is the full run log (oldest first), one JSON object per line. "
        "Write a concise summary of the CURRENT state — what has been done, key "
        "outcomes, and anything still outstanding. Summarize ONLY from the log; "
        "do not invent. Output the summary text only, no preamble.\n\n"
        "LOG:\n" + log
    )
    ok, text = _llm_complete(prompt, model, max_tokens)
    if not ok:
        out(f"  ⚠ summarize skipped: {text}")
        return None
    return text.strip() or None


def _set_section_summary(path: str, kind: str, summary: str) -> None:
    """Replace the prose summary of ``@<kind>`` (the lines before its fence),
    byte-preserving everything else. HTML-comment lines in the region are kept.
    """
    with open(path, encoding="utf-8") as f:
        src = f.read()
    lines = src.split("\n")
    header = "@" + kind

    h = None
    for idx, ln in enumerate(lines):
        st = ln.strip()
        if st == header or st.startswith(header + " "):
            h = idx
            break
    if h is None:
        return

    end = len(lines)
    for idx in range(h + 1, len(lines)):
        if lines[idx].lstrip().startswith("@"):
            end = idx
            break

    fence = None
    for idx in range(h + 1, end):
        if lines[idx].strip().startswith("```"):
            fence = idx
            break
    region_end = fence if fence is not None else end

    comments = [ln for ln in lines[h + 1:region_end] if ln.strip().startswith("<!--")]
    new_region = ["", *comments, *summary.strip().split("\n"), ""]
    lines[h + 1:region_end] = new_region
    _write_lines(path, lines)
