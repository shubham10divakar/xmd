# XMD Specification — v0.0.1

> The smallest version of XMD that is *real*: a runtime that executes a
> document, lets it remember across runs, and hands it back human-readable.
> Status: **building**. This spec defines exactly what v0.0.1 does — nothing more.

---

## 0. Design rules (the two-test rule)

Every feature must pass **both**:
1. Could an agent write this correctly with **no examples**?
2. Does this give a human a reason to **trust it with real work today**?

Consequences baked into this version:
- **One file format** — `.xmd`. Meaning lives in `@directives`, not in filenames.
- **Inline-first** — the document carries the actual code; the runtime dispatches.
- **Detect-don't-install** — the runtime never installs interpreters; it uses
  what's present and fails gracefully when something is missing.
- **Stdlib only** — zero third-party dependencies.

---

## 1. File model

An `.xmd` file is UTF-8 text. It has:

- An optional **title**: the first Markdown heading (`# ...`) before any section.
- An ordered list of **sections**, each introduced by a directive at column 0:
  `@<kind> [name]`. A section's body is every line until the next `@...` or EOF.

```text
# Project Title          ← title (optional)

@goal                    ← section: kind=goal
...body...

@workflow build          ← section: kind=workflow, name=build
...body...
```

Line beginning with `@` (after left-strip) at the start of a logical line opens a
section. A `-  @shell` *step* line does **not** open a section (it starts with `-`).

---

## 2. Sections (per-section tuned grammars)

Each section's body uses the grammar most natural to what it represents.

### 2.1 `@goal` — prose
Free text. The human intent / agent instruction. No parsing beyond "trim".
```text
@goal
Ship xmd v0.0.1 — a runtime that executes this very file.
```

### 2.2 `@memory` — `key: value` state
One `key: value` per line. Blank lines and `# comments` ignored. Scalar typing:
quoted → string; `true`/`false` → bool; `null`/`none`/empty → null; integer/float
→ number; otherwise → string.
```text
@memory
last_session: "agreed on inline-first"
runtime_status: "building"
runs: 0
```
See §4 for the three memory powers.

### 2.3 `@tasks` — checkboxes
GitHub-style. `- [ ]` = open, `- [x]` = done. Anything after the box is the text.
```text
@tasks
- [x] design PROJECT.xmd
- [ ] build parser
```

### 2.4 `@workflow <name>` — ordered inline-code steps
A list of steps. Each step opens with `- @<plugin>` and is followed by indented
`key: value` params. A `key: |` line begins a block scalar (multi-line body,
common indentation stripped).
```text
@workflow build_and_check
- @print
  text: "Last session: {{ memory.last_session }}"
- @shell
  run: echo XMD runtime is alive
- @python
  run: |
    print("hello from python plugin")
```
Steps run **top to bottom**. (No dependency graph in v0.0.1 — that's a later layer.)

### 2.5 `@on_done` — hooks
Runs after the workflow(s) complete. v0.0.1 supports one hook form:
```text
@on_done
set: memory.runtime.status = "checked"
```
`set: memory.<key> = <value>` assigns into memory (value parsed as a scalar, §2.2).
**A hook may only write keys under the `runtime.` namespace** (field ownership,
§4.1); a `set:` targeting any other key is refused and the agent-owned value is
left untouched.

---

## 3. Plugins (inline-first dumb dispatcher)

A plugin is a handler for a directive name. Contract:

```python
def plugin(params: dict, ctx: dict) -> Result
# Result(ok: bool, output: str, error: str, code: int)
```

Built-in plugins in v0.0.1:

| Directive  | Behavior |
|------------|----------|
| `@print`   | Returns `text` (or `run`) as output. No side effects. |
| `@shell`   | Runs `run` via the system shell; captures stdout/stderr/exit code. |
| `@python`  | Writes `run` to a temp `.py`, runs `python`. |
| `@node`    | Writes `run` to a temp `.js`, runs `node`. |
| `@ruby`    | Writes `run` to a temp `.rb`, runs `ruby`. |
| `@bash`    | Writes `run` to a temp `.sh`, runs `bash`. |

**Detect-don't-install:** language plugins check for the interpreter first
(`shutil.which`). If absent, the step fails with a clear message
(`'node' not found … install it to run @node steps, or skip this step.`) — the
run continues; nothing is installed.

Adding a language later = one entry in the dispatch table. That's the point.

---

## 4. Memory — the three powers

1. **Read-in** — at run start, `@memory` is parsed into a live `dict`.
2. **Substitution** — before a step runs, every `{{ memory.<key> }}` in its
   params is replaced with the value. Missing key → empty string.
3. **Write-back** — after the run (including `@on_done` hooks), the updated
   memory is serialized back into the file. The document edits itself.

Write-back can be disabled with `--no-write` (useful for dry runs / parsing).

### 4.1 Field ownership (two-author safety)

An `.xmd` file has two writers: the **agent/human** (who hand-edits the document)
and the **runtime** (which persists state via `@on_done`). To stop them silently
clobbering each other, ownership is split by namespace:

- **`runtime.*` keys are runtime-owned.** Only the runtime writes them (via
  `set:` hooks). Do not hand-author these — the runtime may overwrite them.
- **Every other memory key is agent-owned.** The runtime reads them (and preserves
  them verbatim on write-back) but will **never** modify them. A `set:` hook
  targeting an agent-owned key is **refused** with a warning.

This makes the shared document safe by construction rather than by convention:
`{{ memory.last_session }}` (agent-owned) can never be clobbered by the runtime,
while `{{ memory.runtime.status }}` is the runtime's to manage.

> **Known limitation:** write-back re-serializes the whole document from its
> parsed form, so formatting/quote-style is normalized each run. Round-trip
> fidelity is refined in a later version.

---

## 5. CLI

```bash
runxmd run <file> [--workflow NAME] [--no-write]   # execute workflow(s); persist memory
runxmd parse <file>                                # print parsed structure as JSON
runxmd validate <file>                             # check it parses; report sections
```

`run` executes all `@workflow` sections (or just `--workflow NAME`), printing each
step's result, then applies `@on_done` and writes memory back unless `--no-write`.

---

## 6. Out of scope for v0.0.1 (deferred, by design)

- Intermediate Representation (IR) layer — not needed until a 2nd runtime target.
- Event watching (`@on_file_change`, `@daily`, `@on_commit`) — Phase 3.
- Agent engine (goal → task generation → self-coordination) — Phase 4.
- `@task` declarative abstraction + resolver (true portability) — earned later.
- Distributed runtime / XOS platform / 13-extension family — far future.

---

## 7. The dogfood acceptance test

> `runxmd run PROJECT.xmd` runs `@workflow build_and_check`, substitutes
> `{{ memory.last_session }}`, executes the shell + python steps, applies the
> `@on_done` hook, and writes the updated `@memory` back to the file — and the
> file is still readable by a human afterward.

If that loop works, v0.0.1 is done.
