# XMD Specification — v0.0.3

> Supersedes `SPEC-v0.0.2.md`. v0.0.3 adds the **agent engine** (Layer 7):
> `xmd agent` turns a `@goal` into `@tasks`, executes them, and updates memory —
> the document begins managing itself. Plus the `@llm` plugin that powers planning.
> Everything from v0.0.2 (plugins, memory, `watch`, field ownership) carries forward.
> Status: **built & verified** (LLM-backed planning requires `ANTHROPIC_API_KEY`).

---

## 0. Design rules (unchanged)

Two-test rule for every feature: *Could an agent write this with no examples?*
and *Does it give a human a reason to trust it with real work today?* One file
format, inline-first, detect-don't-install, stdlib only.

---

## 1–4. File model, sections, plugins, memory

As in [`SPEC-v0.0.2.md`](./SPEC-v0.0.2.md), with these additions:

- **`@llm` plugin** — calls the Anthropic Messages API via stdlib `urllib`. Params:
  `prompt` (required), `model` (default `claude-sonnet-4-6`), `max_tokens`. Reads
  the key from `ANTHROPIC_API_KEY`; if unset, fails gracefully (the runtime never
  stores or bundles a key — same spirit as detect-don't-install).
- **Field ownership (§4.1) still holds:** mechanical write-back (`xmd run`,
  `@on_done`) may only write `runtime.*` memory. See §5.1 for how the agent
  command differs.

Full plugin set: `@print`, `@shell`, `@python`/`@node`/`@ruby`/`@bash`, `@http`,
`@write`, `@read`, `@llm`.

---

## 5. The agent engine (Layer 7)

```bash
xmd agent <file> [--replan] [--autonomous] [--model M] [--max-tokens N] [--dry-run]
```

The loop:

```text
Read @goal
   ↓
Plan → generate @tasks   (via @llm; skipped if tasks already exist unless --replan)
   ↓
Execute each open task
   ↓
Update @memory (runtime.*) + write the document back
```

### 5.1 Agent-author mode (ownership)

`xmd agent` is **agent-author** mode. Unlike `xmd run` (mechanical; `runtime.*`
only), the agent command is authorized to **write `@tasks`** generated from the
goal and to tick them as they complete. This is a deliberate, explicit boundary:
authoring tasks is what makes the document self-organizing, and it only happens
when the user explicitly invokes `agent`. Memory progress it writes is still
namespaced (`runtime.agent_runs`, `runtime.tasks_done_last`).

### 5.2 Planning

If `@tasks` is empty (or `--replan`), the goal is sent to `@llm`, which returns up
to 8 ordered task lines. A task may be linked to a workflow with ` -> name`. With
no API key, planning degrades gracefully and the agent executes any pre-existing
tasks instead (agent-in-the-loop mode).

### 5.3 Execution — two modes (both built)

For each open task:

1. **Explicit workflow link (default, safe).** If the task text ends with
   ` -> workflow_name` and that `@workflow` exists, the agent runs it and ticks
   the task on success. No model-generated code is executed.
   ```text
   - [ ] write a note file -> write_note
   ```
2. **LLM-emitted steps (`--autonomous`).** For a task with no workflow link, the
   LLM generates XMD steps (`@shell`/`@python`/`@write`/`@read`/`@http`) which the
   agent then runs. Gated behind `--autonomous` because it executes
   model-generated commands — it must be an explicit choice.

A task with no workflow link and **without** `--autonomous` is skipped (left open)
with a note, never silently dropped.

### 5.4 `--dry-run`

Shows the plan and what would execute, without running anything or writing the
file.

---

## 6. CLI (full)

```bash
xmd run <file> [--workflow NAME] [--no-write]
xmd watch <file> [--interval S] [--max-runs N] [--no-write]
xmd agent <file> [--replan] [--autonomous] [--model M] [--max-tokens N] [--dry-run]
xmd parse <file>
xmd validate <file>
xmd --version
```

---

## 7. Out of scope (still deferred)

- Declarative event triggers (`@on_file_change`, `@daily`, `@on_commit`) —
  `xmd watch` remains the polling seed.
- Intermediate Representation (IR), the `@task` portable-resolver abstraction,
  multi-agent / distributed (XOS).
- Prompt caching / streaming in `@llm` (kept minimal for now).

---

## 8. Changelog

- **v0.0.3** — agent engine (`xmd agent`: plan → execute → update, agent-author
  mode); `@llm` plugin; reusable `run_workflow` / `run_steps` executor helpers.
- **v0.0.2** — `@http`, `@write`, `@read`; `xmd watch`; field ownership (§4.1).
- **v0.0.1** — parser, executor, CLI, shell/inline-language plugins, three memory
  powers.

---

## 9. Acceptance tests (passing)

- `xmd agent examples/AGENT.xmd` reads the goal, runs the three linked workflows,
  ticks all tasks, writes `runtime.*` progress, and leaves the file readable.
- `--dry-run` previews without executing or writing.
- With no `ANTHROPIC_API_KEY`: planning and `--autonomous` step-generation both
  fail gracefully (clear message, no crash, tasks left open), and the agent still
  executes any pre-existing workflow-linked tasks.
