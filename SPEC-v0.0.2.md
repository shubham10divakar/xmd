# XMD Specification — v0.0.2

> Supersedes `SPEC-v0.0.1.md`. v0.0.2 keeps the entire v0.0.1 contract and adds:
> the `@http` and filesystem (`@write`/`@read`) plugins, and the reactive
> `xmd watch` command (Phase-3 seed). The field-ownership rule (§4.1) introduced
> at the end of v0.0.1 is carried forward.
> Status: **built & verified**.

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
- **Stdlib only** — zero third-party dependencies (incl. `@http` via `urllib`).

---

## 1. File model

An `.xmd` file is UTF-8 text (a leading BOM is tolerated). It has:

- An optional **title**: the first Markdown heading (`# ...`) before any section.
- An ordered list of **sections**, each introduced by a directive at column 0:
  `@<kind> [name]`. A section's body is every line until the next `@...` or EOF.

A `-  @shell` *step* line does **not** open a section (it starts with `-`).

---

## 2. Sections (per-section tuned grammars)

### 2.1 `@goal` — prose
Free text describing intent.

### 2.2 `@memory` — `key: value` state
One `key: value` per line. Blank lines and `# comments` ignored. Scalar typing:
quoted → string; `true`/`false` → bool; `null`/`none`/empty → null; int/float →
number; otherwise → string. Keys may be dotted (e.g. `runtime.status`). See §4.

### 2.3 `@tasks` — checkboxes
`- [ ]` open, `- [x]` done. Curated by the agent/human (the runtime does not
write tasks — see §4.1).

### 2.4 `@workflow <name>` — ordered inline-code steps
A list of steps. Each opens with `- @<plugin>` followed by indented `key: value`
params; `key: |` begins a block scalar (common indentation stripped). Steps run
top to bottom (no dependency graph in this version).

### 2.5 `@on_done` — hooks
Runs after the workflow(s) complete. One hook form:
```text
@on_done
set: memory.runtime.status = "checked"
```
`set: memory.<key> = <value>` assigns into memory. **A hook may only write keys
under the `runtime.` namespace** (§4.1); a `set:` to any other key is refused and
the agent-owned value is left untouched.

---

## 3. Plugins (inline-first dumb dispatcher)

Contract: `def plugin(params: dict, ctx: dict) -> Result(ok, output, error, code)`.

| Directive  | Behavior |
|------------|----------|
| `@print`   | Returns `text` (or `run`) as output. No side effects. |
| `@shell`   | Runs `run` via the system shell; captures stdout/stderr/exit. |
| `@python`  | Writes `run` to a temp `.py`, runs `python`. |
| `@node`    | Writes `run` to a temp `.js`, runs `node`. |
| `@ruby`    | Writes `run` to a temp `.rb`, runs `ruby`. |
| `@bash`    | Writes `run` to a temp `.sh`, runs `bash`. |
| `@http`    | **(new)** Request `url` with `method` (default GET), optional `body` + `content_type`. Output: `status` + body (clipped to 2000 chars). |
| `@write`   | **(new)** Write `content` (or `text`) to `path`; creates parent dirs. |
| `@read`    | **(new)** Read `path` into output. |

**Detect-don't-install:** language plugins check for the interpreter first
(`shutil.which`); if absent, the step fails with a clear message and the run
continues — nothing is installed. Adding a language = one dispatch-table entry.

---

## 4. Memory — the three powers

1. **Read-in** — at run start, `@memory` is parsed into a live `dict`.
2. **Substitution** — before a step runs, every `{{ memory.<key> }}` in its
   params is replaced (dotted keys allowed). Missing key → empty string.
3. **Write-back** — after the run (including `@on_done` hooks), updated memory is
   serialized back into the file. Disable with `--no-write`.

> **Known limitation:** write-back re-serializes the whole document, so
> formatting/quote-style is normalized each run (semantics preserved).

### 4.1 Field ownership (two-author safety)

An `.xmd` file has two writers — the **agent/human** (hand-edits) and the
**runtime** (`@on_done` write-back). Ownership is split by namespace so they
cannot clobber each other:

- **`runtime.*` keys are runtime-owned.** Only the runtime writes them. Do not
  hand-author these.
- **Every other memory key is agent-owned.** The runtime reads + preserves them
  but **never** modifies them. A `set:` hook targeting an agent-owned key is
  **refused** with a warning.

Safe by construction, not by convention: `{{ memory.last_session }}` can never be
clobbered by the runtime; `{{ memory.runtime.status }}` is the runtime's to manage.

---

## 5. CLI

```bash
xmd run <file> [--workflow NAME] [--no-write]            # execute; persist memory
xmd watch <file> [--workflow NAME] [--interval S]        # (new) re-run on change
                 [--max-runs N] [--no-write]
xmd parse <file>                                         # parsed structure as JSON
xmd validate <file>                                      # check it parses; list sections
```

**`watch`** re-runs the file whenever its mtime changes. Self-trigger guard: the
mtime baseline is captured *after* the runtime's own write-back, so write-back
never causes an infinite re-run loop — only an external edit advances the
baseline. `--max-runs N` stops after N runs (0 = forever; useful for CI/tests).

---

## 6. Out of scope (deferred, by design)

- Intermediate Representation (IR) — not needed until a 2nd runtime target.
- **Declarative** event triggers (`@on_file_change`, `@daily`, `@on_commit`) —
  `xmd watch` is the minimal polling seed; the declarative event system is later.
- Agent engine (goal → task generation → self-coordination) — Phase 4.
- `@task` declarative abstraction + resolver (true portability) — earned later.
- Distributed runtime / XOS platform / multi-extension family — far future.

---

## 7. Changelog

- **v0.0.2** — `@http`, `@write`, `@read` plugins; `xmd watch` (polling, with
  self-trigger guard + `--max-runs`). Carries forward field ownership (§4.1) and
  UTF-8 BOM tolerance.
- **v0.0.1** — parser, IR-free executor, CLI (`run`/`parse`/`validate`),
  `@print`/`@shell`/`@python`/`@node`/`@ruby`/`@bash`, all three memory powers.

---

## 8. Acceptance tests (all passing)

- `xmd run examples/PROJECT.xmd` runs the workflow, substitutes memory, applies
  `@on_done`, writes memory back — file stays human-readable.
- A `set:` to an agent-owned key is refused; a `runtime.*` key is written.
- `@write` → `@read` round-trips a file with `{{ }}` substitution; `@http` GET
  returns a status + body; a missing interpreter fails gracefully and the run
  continues.
- `xmd watch --max-runs 2` runs once, re-runs on an external edit, and does **not**
  self-trigger from its own write-back.
