# XMD Specification — v0.0.3

> Supersedes `SPEC-v0.0.2.md`. v0.0.3 adds the **agent engine** (Layer 7):
> `runxmd agent` turns a `@goal` into `@tasks`, executes them, and updates memory —
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
- **Field ownership (§4.1) still holds:** mechanical write-back (`runxmd run`,
  `@on_done`) may only write `runtime.*` memory. See §5.1 for how the agent
  command differs.

Full plugin set: `@print`, `@shell`, `@python`/`@node`/`@ruby`/`@bash`, `@http`,
`@write`, `@read`, `@llm`.

---

## 5. The agent engine (Layer 7)

```bash
runxmd agent <file> [--replan] [--autonomous] [--model M] [--max-tokens N] [--dry-run]
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

`runxmd agent` is **agent-author** mode. Unlike `runxmd run` (mechanical; `runtime.*`
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
runxmd run <file> [--workflow NAME] [--write-back] [--no-save] \
                  [--strict] [--check] [--pure] [--raw] [--no-provenance]
runxmd watch <file> [--interval S] [--max-runs N] [--write-back] [--no-save] \
                    [--strict] [--pure] [--raw] [--no-provenance]
runxmd agent <file> [--replan] [--autonomous] [--model M] [--max-tokens N] [--dry-run]
runxmd verify <render> [--source FILE]
runxmd check
runxmd parse <file>
runxmd validate <file>
runxmd --version
```

Source files are read-only by default; `--write-back` is opt-in and only ever
touches `runtime.*` memory. `--no-save` suppresses the `@context_memory`
append.

### 6.1 Trust layer (v1.0.3)

- **Provenance.** Every render / results / output file is prefixed with an HTML
  comment recording `source_sha256` (SHA-256 of the source, normalized:
  BOM-stripped, CRLF→LF, per-line rstrip, single trailing newline),
  `runxmd_version`, `generated_utc`, `platform`, the `interpreters` that ran,
  and `non_deterministic_steps`. `--no-provenance` omits it.
- **`runxmd verify <render>`** — re-hashes the source named in the header;
  exit 0 = matches, 3 = STALE, 2 = no header / source not found.
- **`--strict`** — a failed step propagates a non-zero exit code.
- **`--check`** — build a fresh render in memory, compare (header-stripped)
  against the committed one, exit 1 on drift; nothing is written.
- **Normalization** (default on, `--raw` off) — step output has paths under the
  document directory made relative, `$HOME`→`~`, hostname→`HOST`, and `\`→`/`
  inside path-like tokens. A step's `redact:` param (one literal or `/regex/`
  per line) blanks volatile substrings.
- **`--pure`** — refuse to execute non-deterministic plugins (`@http`, `@llm`);
  exit 2 if any are present. Plugins declare this via
  `register(name, deterministic=False)`.

### 6.2 `session:` — opt-in shared scope (v1.0.3)

By default every step runs in a fresh subprocess with **no shared state** —
`@workflow` Property 2 (order-independence of pure steps) holds *for the default
configuration*.

A step may set `session: <name>`. Steps that share a session name run with
every earlier same-session step's `run:` code prepended, so a name bound in one
step is visible in the next:

```markdown
- @python
  session: calc
  run: |
    total = sum(range(100))

- @python
  session: calc
  run: |
    print("total:", total)     # sees `total` from the step above
```

Mechanism: re-execution with prefix-subtraction on stdout (the earlier steps'
output is stripped from what this step reports). This needs no per-language REPL
protocol, but **side effects in earlier session steps re-run** each time a later
step in that session runs. Sessions are therefore an explicit opt-out of
Property 2, not the default.

### 6.3 `--cache` — content-addressed step cache (v1.0.3)

`runxmd run --cache` reuses a language step's cached stdout / stderr / exit code
when nothing that can change its output has changed. The cache key is
`sha256(runxmd_version, plugin, params, interpreter_version, script_bytes)`;
entries live under `RUNXMD_CACHE_DIR` or `~/.cache/runxmd`. `--force` ignores
existing entries (still refreshing them).

Only language plugins (`@python` … `@powershell` and their `*_script` forms)
are cacheable — they carry the subprocess cold-start cost and their output is a
pure function of the key. `@shell`, `@read`, `@write`, `@http`, `@llm`, and
`session:` steps are never cached. Failed runs and "interpreter not found"
(exit 127) are not stored.

### 6.4 Step params: `timeout:`, `stdin:`, `if:` (v1.0.3)

Any code step (`@python` … `@powershell`, `*_script`, `@shell`) accepts:

- **`timeout: <seconds>`** — kill the step after N seconds (exit code 124,
  `... timed out after Ns`). `run --timeout N` sets a default for every step; a
  step's own `timeout:` wins. No timeout by default.
- **`stdin: <text>`** — feed `<text>` to the step's standard input.
- **`if: <guard>`** — run the step only if the guard holds, else mark it
  `skipped` (counts as ok; nothing rendered). Guards:
  `memory.<key>` (truthy), `not memory.<key>`, `memory.<key> <op> <scalar>`
  (`== != > < >= <=`), and `context` (rolling summary non-empty).

`stdout` and `stderr` are captured separately end-to-end; the `write`
projection records `status:` / `exit_code:` / `stderr:` per step, and
render / results show stdout **and** stderr for a failed step.

### 6.5 `--json` trace

`runxmd run --json` suppresses the normal output and prints one JSON object:
`{file, runxmd_version, workflows: {name: [step records]}, all_ok,
failed_steps, cache}`. Each step record is
`{idx, plugin, output, error, ok, duration_ms, code, skipped}`.

---

## 7. Out of scope (still deferred)

- Declarative event triggers (`@on_file_change`, `@daily`, `@on_commit`) —
  `runxmd watch` remains the polling seed.
- Intermediate Representation (IR), the `@task` portable-resolver abstraction,
  multi-agent / distributed (XOS).
- Prompt caching / streaming in `@llm` (kept minimal for now).

---

## 8. Changelog

> Spec-document numbering (`v0.0.x`) is independent of the package version
> (`1.0.x`). This document, `SPEC-v0.0.3.md`, is current as of package
> **v1.0.3**.

- **package v1.0.3** — trust layer (§6.1): provenance headers + `runxmd
  verify`; `run --strict` / `--check`; output normalization + `redact:`;
  `run --pure` + `deterministic=False` plugin flag.
- **v0.0.3** — agent engine (`runxmd agent`: plan → execute → update, agent-author
  mode); `@llm` plugin; reusable `run_workflow` / `run_steps` executor helpers.
- **v0.0.2** — `@http`, `@write`, `@read`; `runxmd watch`; field ownership (§4.1).
- **v0.0.1** — parser, executor, CLI, shell/inline-language plugins, three memory
  powers.

---

## 9. Acceptance tests (passing)

- `runxmd agent examples/AGENT.xmd` reads the goal, runs the three linked workflows,
  ticks all tasks, writes `runtime.*` progress, and leaves the file readable.
- `--dry-run` previews without executing or writing.
- With no `ANTHROPIC_API_KEY`: planning and `--autonomous` step-generation both
  fail gracefully (clear message, no crash, tasks left open), and the agent still
  executes any pre-existing workflow-linked tasks.
