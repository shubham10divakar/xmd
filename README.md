# XMD — a runtime that turns documents into running systems

> **HTML needed a browser to become useful. XMD needs a runtime to become a system.**
> Without the runtime, an `.xmd` file is just text. With it, the **document becomes
> the system** — documentation, configuration, workflow, and memory in one file
> that both **humans and AI agents** can read, write, and run.

[![status](https://img.shields.io/badge/status-v0.0.2-blue)](./SPEC-v0.0.2.md)
[![deps](https://img.shields.io/badge/dependencies-zero-brightgreen)](#)
[![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)](#)

---

## What is XMD?

XMD is a tiny runtime that **executes Markdown-like documents.** You write a plain
`.xmd` file describing a goal, some state, a checklist, and a workflow — and the
runtime *runs* it: executes the steps, remembers state across runs, and writes the
results back into the same file.

```text
# Project: Nightly Report

@goal
Pull yesterday's numbers and save a report.

@memory
last_run: "never"

@workflow nightly
- @http
  url: https://api.example.com/metrics
- @write
  path: reports/today.json
  content: "{{ memory.last_run }} -> done"

@on_done
set: memory.runtime.status = "ok"
```

```bash
xmd run report.xmd      # runs the workflow, then updates @memory in the file
xmd watch report.xmd    # re-runs automatically whenever you edit the file
```

That's the whole idea: **one document is the program, its config, its state, and
its documentation — all at once.**

---

## What is it aimed at? (the why)

Today, a single automated task is scattered across many systems: a YAML config, a
shell script, a README that explains it, a database row that remembers state, a
cron entry that triggers it. They drift apart and only a developer can follow the
thread.

XMD collapses them into **one readable artifact.** The goal is not "Markdown that
runs code" — it's making the **document the primary unit of computation.**

And there's a specific reason that matters *now*: **AI agents already live in
documents.** They read instruction files, write notes to remember things, and
track tasks as Markdown — but they get nothing executable back. XMD is the missing
runtime beneath all of that.

- **Agents are the native user** — an `.xmd` file is just structured Markdown, so
  an agent can author and maintain it correctly with no special training.
- **Humans are the adopter** — you install it, point it at a file, and trust it
  with real work today.
- **The document is the contract between them** — both read, write, and run the
  same file, safely (see [Field ownership](#memory--state-that-survives)).

If you've ever wanted a script you can *read like a doc* and an agent can *maintain
like a teammate*, that's what XMD is for.

---

## Who is this for?

- **Automators / devops** who are tired of bash + YAML + cron sprawl and want one
  legible file per task.
- **AI / agent builders** who want agents to own runnable, stateful documents
  instead of inert notes.
- **Anyone** who wants a lightweight, dependency-free way to describe and run
  small workflows that remember things between runs.

---

## Install

Zero third-party dependencies — pure Python standard library (≥ 3.9).

```bash
git clone https://github.com/shubham10divakar/xmd.git
cd xmd
pip install -e .
```

Now the `xmd` command is available. Or run without installing:

```bash
python -m xmd.cli run examples/PROJECT.xmd
```

---

## Quick start

Create `hello.xmd`:

```text
# Hello XMD

@goal
Prove the runtime works.

@memory
name: "world"

@workflow hello
- @print
  text: "hello {{ memory.name }}"
- @shell
  run: echo "shell works too"
- @python
  run: |
    print("and so does python")

@on_done
set: memory.runtime.ran_at = "now"
```

Run it:

```bash
xmd run hello.xmd
```

```text
▶ workflow: hello
  step 1 @print ✓
      hello world
  step 2 @shell ✓
      shell works too
  step 3 @python ✓
      and so does python

· memory written back
```

Open `hello.xmd` again — the runtime added `runtime.ran_at` to `@memory`. The
document changed itself.

---

## The `.xmd` format

A file is plain UTF-8 text. An optional title (`# ...`), then sections introduced
by `@directives`. Each section uses the grammar most natural to what it is:

| Section            | What it is            | Grammar |
|--------------------|-----------------------|---------|
| `@goal`            | Human/agent intent    | free prose |
| `@memory`          | State that persists   | `key: value` lines |
| `@tasks`           | A checklist           | `- [ ]` / `- [x]` |
| `@workflow <name>` | Ordered steps to run  | `- @plugin` + indented `key: value` |
| `@on_done`         | Hooks after the run   | `set: memory.runtime.x = value` |

Workflow steps run top to bottom. A `key: |` line starts a multi-line block (handy
for code).

---

## Plugins (what steps can do)

A step is `- @<plugin>` plus params. Built in:

| Plugin    | Does | Key params |
|-----------|------|-----------|
| `@print`  | Echo text (after substitution) | `text` |
| `@shell`  | Run a shell command | `run` |
| `@python` `@node` `@ruby` `@bash` | Run inline code in that language | `run` (block) |
| `@http`   | HTTP request | `url`, `method`, `body`, `content_type` |
| `@write`  | Write a file (creates dirs) | `path`, `content` |
| `@read`   | Read a file into output | `path` |

**Any language, no bundling.** Language plugins just hand your code to the
interpreter already on your machine. If it's missing, the step fails with a clear
message *and the run continues* — XMD never installs anything for you.

```text
- @ruby
  run: puts "only runs if ruby is installed"
```
```text
  step 1 @ruby ✗ (exit 127)
      'ruby' not found on this machine — install it to run @ruby steps, or skip this step.
```

---

## Memory — state that survives

`@memory` is what makes a document a *system* instead of a script. Three powers:

1. **Read-in** — loaded into a live store when the run starts.
2. **Substitution** — `{{ memory.key }}` anywhere in a step is replaced with the
   value before it runs.
3. **Write-back** — changes are written back into the file, so the next run
   remembers.

### Field ownership (safe co-editing)

Because both you/an agent *and* the runtime write to the file, ownership is split
so they can't clobber each other:

- **`runtime.*` keys belong to the runtime.** Only it writes them (via `@on_done`).
- **Every other key belongs to you/the agent.** The runtime reads and preserves
  them but will **never** overwrite them. A hook that tries is refused with a
  warning.

So `{{ memory.notes }}` (yours) is safe; `{{ memory.runtime.status }}` is the
runtime's to manage. Safe by design, not by luck.

---

## Reacting to changes — `xmd watch`

```bash
xmd watch report.xmd                 # re-run on every save
xmd watch report.xmd --interval 0.5  # poll faster
xmd watch report.xmd --max-runs 3    # stop after 3 runs (great for CI)
```

`watch` re-runs whenever the file changes. It will **not** loop on its own
write-back — only your edits trigger a re-run.

---

## Commands

```bash
xmd run <file> [--workflow NAME] [--no-write]      # execute; persist memory
xmd watch <file> [--interval S] [--max-runs N]     # re-run on change
xmd parse <file>                                   # show parsed structure as JSON
xmd validate <file>                                # check it parses; list sections
xmd --version
```

---

## Design principles

- **One file format.** Meaning lives in `@directives`, not in a zoo of extensions.
- **Inline-first.** The document carries the code; the runtime is a thin dispatcher.
- **Detect, don't install.** Use what's on the machine; fail clearly when it's not.
- **Stdlib only.** Zero dependencies, including `@http`.
- **The two-test rule for every feature:** *Could an agent write this with no
  examples? Does it give a human a reason to trust it with real work today?*

---

## Status & roadmap

**Current: v0.0.2** — see [`SPEC-v0.0.2.md`](./SPEC-v0.0.2.md) for the exact contract.

- ✅ Parser, executor, CLI (`run` / `parse` / `validate`)
- ✅ Plugins: shell, inline languages, http, filesystem
- ✅ Memory: read / substitute / write-back, with field-ownership safety
- ✅ Reactive `xmd watch`
- ⏳ Declarative events (`@on_file_change`, `@daily`, `@on_commit`)
- ⏳ Agent engine (`@goal` → auto-generate `@tasks` → execute → update)
- ⏳ Portable `@task` abstraction (run the same intent via any language)

This is early software with a large vision. Contributions and ideas welcome.

---

## License

MIT — see [LICENSE](./LICENSE).
