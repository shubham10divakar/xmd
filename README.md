# runxmd — run your Markdown files

> **You already write `.md` files. Now you can run them.**
> Add a `@workflow` section to any Markdown doc and `runxmd` executes it —
> the same file your team reads is also the program, the config, and the memory.
> Runs both plain `.md` files and `.xmd` files (same format; `.xmd` just signals
> "this Markdown is meant to be run").

[![PyPI version](https://img.shields.io/pypi/v/runxmd)](https://pypi.org/project/runxmd/)
[![Downloads](https://static.pepy.tech/badge/runxmd)](https://pepy.tech/project/runxmd)
[![status](https://img.shields.io/badge/status-v1.0.1-blue)](./SPEC-v0.0.3.md)
[![deps](https://img.shields.io/badge/dependencies-zero-brightgreen)](#)
[![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)](#)

---

## The idea in one sentence

`runxmd` is a runtime that makes Markdown files executable. You keep writing `.md`
files exactly as you do today — they still render in GitHub, VS Code, and every
Markdown viewer. You just also get to *run* them.

---

## `.md` and `.xmd` — same Markdown, one is a signal

`runxmd` runs **both `.md` and `.xmd` files.** They use the **exact same Markdown
grammar** — there is no second syntax to learn, and the runtime parses them
identically. The only difference is the *name*, and the name is just a convention:

- **`.md`** — a regular Markdown file. It might be plain prose, or it might have a
  `@workflow` section or two. Either way, `runxmd` runs whatever executable
  sections it finds.
- **`.xmd`** — *also* plain Markdown, byte-for-byte the same format. The `.xmd`
  extension is an **opt-in label** that says *"this file is the runnable kind — it
  has the workflows, code, and memory."*

Think of it like `script.js` vs `script.test.js`: both are 100% JavaScript, parsed
by the same engine. The `.test.` part doesn't change the language — it just tells
you (and your tools) the file's *role* at a glance. `.xmd` is exactly that:
**"this is the executable kind of Markdown."**

```bash
runxmd run notes.md       # runs — finds the @workflow inside
runxmd run pipeline.xmd   # runs — identical engine, identical grammar
```

Why bother with the `.xmd` label?

- A person scanning a repo sees `README.md` vs `deploy.xmd` and instantly knows
  *which one does something* — without opening it.
- An agent can be told "run the `.xmd` files" without cracking open every `.md`
  to check whether it contains workflows.
- Editors and CI can give `.xmd` a "run" affordance while still rendering it as
  ordinary Markdown everywhere.

**Bottom line:** use `.md` if you just want your existing docs to run; use `.xmd`
when you want to flag "this Markdown is meant to be executed." The runtime treats
them the same — the choice is purely about intent and legibility.

---

## What changes in your Markdown file? Almost nothing.

Take a doc you already have. Add `@workflow`, `@memory`, and `@tasks` sections.
They look like normal Markdown sections — because they are. The runtime just knows
how to execute them.

**Before — a plain Markdown doc:**

```markdown
# Deploy Staging

Steps:
1. Pull latest image
2. Run migration  
3. Restart service

Last run: manually on 2024-01-15
Status: unknown
```

Useful to read. Does nothing. To actually run it you need a separate shell script,
a CI pipeline, or someone following the steps by hand. The "Last run" date goes
stale the moment you forget to update it.

---

**After — the same doc, now runnable:**

```markdown
# Deploy Staging

@goal
Deploy the latest image to staging and verify it.

@memory
last_run: "never"
runtime.status: "unknown"

@tasks
- [ ] pull image
- [ ] run migration
- [ ] restart service

@workflow deploy
- @shell
  run: docker pull myapp:latest
- @shell
  run: docker exec myapp python manage.py migrate
- @shell
  run: docker restart myapp
- @http
  url: https://staging.myapp.com/health

@on_done
set: memory.runtime.status = "deployed"
```

```bash
runxmd run deploy.md      # or name it deploy.xmd — same result
```

Now the steps run. `runtime.status` is written back into the file. Next time
anyone opens it — human or agent — they can see exactly what happened and when.
The doc and the system are the same thing.

---

## What you gain without giving anything up

| | Plain `.md` | `.md` + runxmd |
|--|-------------|----------------|
| Reads in GitHub / VS Code | ✅ | ✅ |
| Human-readable prose | ✅ | ✅ |
| Edit in any text editor | ✅ | ✅ |
| Steps actually execute | ❌ | ✅ |
| State persists between runs | ❌ | ✅ |
| `{{ variables }}` resolve live | ❌ | ✅ |
| File updates itself after running | ❌ | ✅ |
| AI agent can author and run it | ❌ | ✅ |

No new file format. No new tool to learn. Just your Markdown, with a runtime behind it.

---

## Install

```bash
pip install runxmd
```

Zero third-party dependencies — pure Python standard library (≥ 3.9).

Or from source:

```bash
git clone https://github.com/shubham10divakar/xmd.git
cd xmd
pip install -e .
```

### Running the tests

```bash
pip install -e ".[test]"
pytest
```

The suite includes a parametrized check that the **same content runs identically
whether it's named `.md` or `.xmd`** — the extension-agnostic guarantee, pinned down.

---

## Quick start

Add runnable sections to any `.md` file:

```markdown
# Hello

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
runxmd run hello.md
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

Open the file again — `runtime.ran_at` is now in `@memory`. The document updated
itself.

---

## The runnable sections

You add these to any Markdown file. Each one uses the grammar most natural to what
it is:

| Section            | What it does                        | Grammar |
|--------------------|-------------------------------------|---------|
| `@goal`            | Describes the intent (human/agent)  | free prose |
| `@memory`          | State that persists across runs     | `key: value` lines |
| `@tasks`           | A checklist the agent can tick      | `- [ ]` / `- [x]` |
| `@workflow <name>` | Steps to execute in order           | `- @plugin` + params |
| `@on_done`         | Runs after the workflow finishes    | `set: memory.runtime.x = value` |

Everything else in the file — prose, headings, tables, links — is untouched.
The runtime only acts on `@` sections.

---

## Plugins (what a step can do)

A step is `- @plugin` plus indented params:

| Plugin    | Does | Key params |
|-----------|------|-----------|
| `@print`  | Print text (with substitution) | `text` |
| `@shell`  | Run a shell command | `run` |
| `@python` `@node` `@ruby` `@bash` | Run inline code | `run` (multiline block) |
| `@http`   | Make an HTTP request | `url`, `method`, `body` |
| `@write`  | Write a file (creates dirs) | `path`, `content` |
| `@read`   | Read a file into output | `path` |
| `@llm`    | Ask an LLM (needs `ANTHROPIC_API_KEY`) | `prompt`, `model`, `max_tokens` |

**Detect, don't install.** Language plugins use whatever is already on your machine.
If `ruby` is missing, the step fails clearly and the run continues — runxmd never
installs anything for you.

---

## Memory — state that lives in the file

`@memory` is what makes a Markdown file a *system* instead of a static doc.

1. **Read-in** — memory keys are loaded when the run starts.
2. **Substitution** — `{{ memory.key }}` anywhere in a step is replaced live.
3. **Write-back** — changes are written back into the file after the run.

### Safe co-editing (field ownership)

Both you and the runtime write to the same file, so ownership is split:

- **`runtime.*` keys** — only the runtime writes these (via `@on_done`).
- **Everything else** — yours. The runtime reads and preserves them but will
  **never** overwrite them. A hook that tries is refused with a warning.

Your `{{ memory.notes }}` is safe. `{{ memory.runtime.status }}` is the runtime's
to manage. Safe by design, not by convention.

---

## Watch mode — re-run on save

```bash
runxmd watch report.md                 # re-run whenever you save
runxmd watch report.md --interval 0.5  # poll faster
runxmd watch report.md --max-runs 3    # stop after 3 runs (great for CI)
```

`watch` detects saves and re-runs. It will **not** loop on its own write-back —
only your edits trigger a re-run.

---

## Agent mode — let the goal drive itself

`runxmd agent` turns the doc from *a program you run* into *a goal that runs
itself*:

```text
Read @goal → plan @tasks → execute each task → update @memory → write back
```

```bash
runxmd agent project.md              # plan (if no tasks), then run linked workflows
runxmd agent project.md --replan     # regenerate tasks from the goal
runxmd agent project.md --autonomous # LLM generates AND runs steps for unlinked tasks
runxmd agent project.md --dry-run    # show the plan without executing or writing
```

**Two ways a task gets done:**
1. **Workflow link (safe, default):** `- [ ] run migration -> deploy` — the agent
   runs the named workflow and ticks the task.
2. **LLM-emitted steps (`--autonomous`):** the LLM generates steps for unlinked
   tasks and the agent runs them. Opt-in, because it executes model-generated commands.

Planning requires `ANTHROPIC_API_KEY`. Without it, the agent skips planning and
runs any pre-existing linked tasks. See [`examples/AGENT.xmd`](./examples/AGENT.xmd).

---

## Commands

```bash
runxmd run <file> [--workflow NAME] [--no-write]
runxmd watch <file> [--interval S] [--max-runs N] [--no-write]
runxmd agent <file> [--replan] [--autonomous] [--model M] [--max-tokens N] [--dry-run]
runxmd parse <file>
runxmd validate <file>
runxmd --version
```

---

## Why this matters now

AI agents already live in Markdown. They read instruction files, write notes,
track tasks with `- [ ]` checklists — but when they write a doc, nothing runs.
The doc and the system are always two separate things that drift apart.

`runxmd` closes that gap. An agent can write a `.md` file, you can point the
runtime at it, and it executes. The doc is the system. No translation layer.

---

## Design principles

- **Your Markdown, not a new format.** The runtime reads `@sections`; everything
  else is untouched prose.
- **Inline-first.** Code lives in the document; the runtime is a thin dispatcher.
- **Detect, don't install.** Use what's on the machine; fail clearly when it's not.
- **Stdlib only.** Zero dependencies, including `@http`.
- **Two-test rule for every feature:** *Could an agent write this with no examples?
  Does it give a human a reason to trust it with real work today?*

---

## Status & roadmap

**Current: v1.0.1** — see [`SPEC-v0.0.3.md`](./SPEC-v0.0.3.md) for the full contract.

- ✅ Parser, executor, CLI (`run` / `watch` / `agent` / `parse` / `validate`)
- ✅ Plugins: shell, inline languages, http, filesystem, llm
- ✅ Memory: read / substitute / write-back, with field-ownership safety
- ✅ Reactive `runxmd watch`
- ✅ Agent engine (`@goal` → auto-generate `@tasks` → execute → update memory)
- ⏳ Declarative events (`@on_file_change`, `@daily`, `@on_commit`)
- ⏳ Portable `@task` abstraction
- ⏳ Multi-agent / distributed

Contributions and ideas welcome.

---

## License

MIT — see [LICENSE](./LICENSE).
