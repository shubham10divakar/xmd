"""Agent engine (Layer 7) — goal -> tasks -> execute -> memory.

`xmd agent` is **agent-author** mode: unlike `xmd run` (which may only write
`runtime.*` memory, per field ownership), the agent command is authorized to
author `@tasks` generated from the `@goal`. The document grows itself.

Two execution modes (both built):

  1. **Explicit workflow link** — a task annotated `-> workflow_name` runs that
     `@workflow` and is ticked on success. Default; safe, human-authored.
  2. **LLM-emitted steps** — for a task with no workflow link, the LLM generates
     XMD steps which the agent then runs. Gated behind `--autonomous`, because it
     executes model-generated commands and must be an explicit choice.

Planning (goal -> task list) uses the `@llm` plugin (Anthropic via stdlib
urllib; key from `ANTHROPIC_API_KEY`). With no key, planning degrades gracefully
and the agent still executes any pre-existing tasks (agent-in-the-loop mode).
"""
from __future__ import annotations

import re

from . import executor, plugins
from .parser import Section, Task, _parse_steps, parse, to_source

_MAX_TASKS = 8


def agent_run(
    path: str,
    replan: bool = False,
    autonomous: bool = False,
    model: str = None,
    max_tokens: int = 1024,
    dry_run: bool = False,
    out=print,
):
    with open(path, encoding="utf-8") as f:
        doc = parse(f.read())

    goal_sec = doc.section("goal")
    goal = (goal_sec.text if goal_sec else "").strip()
    if not goal:
        out("✗ no @goal to work from — add a @goal section.")
        return doc
    out(f"◆ goal: {goal}")

    mem_sec = doc.section("memory")
    memory = dict(mem_sec.memory) if mem_sec else {}
    ctx = {"memory": memory}
    tasks_sec = doc.section("tasks")
    workflow_names = [w.name for w in doc.workflows() if w.name]

    # 1. PLAN -----------------------------------------------------------------
    if replan or not (tasks_sec and tasks_sec.tasks):
        out("\n· planning tasks from goal …")
        planned = _plan(goal, workflow_names, model, max_tokens, out)
        if planned:
            if tasks_sec is None:
                tasks_sec = Section(kind="tasks")
                doc.sections.append(tasks_sec)
            if replan:
                tasks_sec.tasks = []
            tasks_sec.tasks.extend(Task(done=False, text=t) for t in planned)
            out(f"· planned {len(planned)} task(s)")
            for t in planned:
                out(f"    - {t}")
        else:
            out("· no plan produced — executing any existing tasks instead")

    # 2. EXECUTE --------------------------------------------------------------
    open_tasks = [t for t in (tasks_sec.tasks if tasks_sec else []) if not t.done]
    if not open_tasks:
        out("\n· no open tasks to execute")
    done = 0
    for task in open_tasks:
        target = _target_workflow(task.text)
        wf = doc.section("workflow", target) if target else None
        if wf is not None:
            out(f"\n● task: {task.text}")
            if dry_run:
                out(f"  → would run workflow '{target}'")
                continue
            ok = executor.run_workflow(wf, memory, ctx, out)
        elif autonomous:
            out(f"\n● task (autonomous): {task.text}")
            if dry_run:
                out("  → would ask the LLM to generate + run steps")
                continue
            ok = _exec_via_llm(task.text, goal, memory, ctx, model, max_tokens, out)
        else:
            out(
                f"\n○ task skipped — no '-> workflow' link "
                f"(use --autonomous to let the LLM run it): {task.text}"
            )
            continue
        if ok:
            task.done = True
            done += 1
        else:
            out(f"  ! left open (failed): {task.text}")

    # 3. MEMORY + write-back --------------------------------------------------
    if dry_run:
        out("\n· dry run — nothing written")
        return doc
    memory["runtime.agent_runs"] = int(memory.get("runtime.agent_runs", 0) or 0) + 1
    memory["runtime.tasks_done_last"] = done
    hooks_sec = doc.section("on_done")
    if hooks_sec:
        executor._apply_hooks(hooks_sec.hooks, memory, out)
    if mem_sec is None:
        mem_sec = Section(kind="memory")
        doc.sections.append(mem_sec)
    mem_sec.memory = memory
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_source(doc))
    out(f"\n✓ agent run complete — {done} task(s) executed; memory updated")
    return doc


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _target_workflow(text: str):
    if "->" in text:
        return _slug(text.rsplit("->", 1)[1])
    return None


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", s.strip()).strip("_")


def _plan(goal, workflow_names, model, max_tokens, out):
    llm = plugins.get("llm")
    if llm is None:
        return []
    wf_hint = ""
    if workflow_names:
        wf_hint = (
            "\nExisting workflows you may link a task to with ' -> name': "
            + ", ".join(workflow_names)
        )
    prompt = (
        "You are a planning assistant for the XMD document runtime. Given a "
        f"project GOAL, output up to {_MAX_TASKS} concrete, ordered tasks — one "
        "per line, no numbering, no prose. If a task is fulfilled by an existing "
        "workflow, append ' -> workflow_name'." + wf_hint + "\n\nGOAL:\n" + goal
    )
    res = llm({"prompt": prompt, "model": model, "max_tokens": max_tokens}, {})
    if not res.ok:
        out(f"  · planner unavailable: {res.error}")
        return []
    tasks = []
    for line in res.output.splitlines():
        clean = line.strip().lstrip("-*0123456789. \t").strip()
        if clean:
            tasks.append(clean)
    return tasks[:_MAX_TASKS]


def _exec_via_llm(task_text, goal, memory, ctx, model, max_tokens, out):
    llm = plugins.get("llm")
    if llm is None:
        out("  · @llm unavailable — cannot generate steps")
        return False
    prompt = (
        "You generate XMD workflow steps. For the TASK below, output ONLY steps "
        "in this exact format (no prose, no code fences):\n"
        "- @shell\n  run: <command>\n"
        "Allowed plugins: @shell, @python (run: block), @write (path, content), "
        "@read (path), @http (url). Keep it minimal and safe.\n\n"
        f"GOAL: {goal}\nTASK: {task_text}"
    )
    res = llm({"prompt": prompt, "model": model, "max_tokens": max_tokens}, {})
    if not res.ok:
        out(f"  · step generation failed: {res.error}")
        return False
    steps = _parse_steps(res.output.splitlines())
    if not steps:
        out("  · LLM returned no runnable steps")
        return False
    out(f"  · LLM generated {len(steps)} step(s)")
    return executor.run_steps(steps, memory, ctx, out)
