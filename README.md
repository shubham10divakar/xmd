# runxmd — run your Markdown files

> **The simplest thing:** write `- @python`, `- @node`, `- @go` (or any of 10 language
> plugins) directly in a `.md` file. Run it. Get a rendered output file with your prose
> intact and every code block replaced by its result. No new syntax. No `@workflow`
> required to get started.

[![PyPI version](https://img.shields.io/pypi/v/runxmd)](https://pypi.org/project/runxmd/)
[![Downloads](https://static.pepy.tech/badge/runxmd)](https://pepy.tech/project/runxmd)
[![status](https://img.shields.io/badge/status-v1.0.2-blue)](./SPEC-v0.0.3.md)
[![deps](https://img.shields.io/badge/dependencies-zero-brightgreen)](#)
[![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)](#)

---

## The idea in one sentence

`runxmd` adds state and execution to `.md` files. You keep writing Markdown exactly
as you do today — it still renders in GitHub, VS Code, and every viewer.
The difference is that bare `- @plugin` steps execute directly, output renders back
inline, and `@memory` persists state across runs. Static doc → stateful doc. Same file.

---

## The simplest possible file

No `@workflow`. No `@memory`. No annotations at all — just prose and code steps.

```markdown
# Analysis

This document runs three Python snippets and renders the results inline.

- @python
  run: |
    print("=== Arithmetic ===")
    x = 10
    print("x =", x)

This section explains what the next snippet does.
Feel free to write as much prose as you like between steps.

- @python
  run: |
    print("=== String ===")
    msg = "hello world"
    print(msg.upper())

Final note before the last snippet.

- @python
  run: |
    print("=== List ===")
    nums = [1, 2, 3, 4, 5]
    print("sum:", sum(nums))

Closing prose — steps are done.
```

Run it:

```bash
runxmd run analysis.md
```

You get `analysis_render.md` — your original document with every code block
replaced by its output, prose preserved exactly as written:

```markdown
# Analysis

This document runs three Python snippets and renders the results inline.

=== Arithmetic ===
x = 10

This section explains what the next snippet does.
Feel free to write as much prose as you like between steps.

=== String ===
HELLO WORLD

Final note before the last snippet.

=== List ===
sum: 15

Closing prose — steps are done.
```

The source file is **never modified**. The render file is your shareable,
LLM-readable output. Re-run any time to refresh it.

---

## Output modes

Every run produces an output file automatically. You control the format with
an `@on_done` hook — or leave it out to get the default.

| Hook in `@on_done` | Output file | Content |
|--------------------|-------------|---------|
| *(none — default)* | `{stem}_render.md` | Prose kept, steps replaced with results, `@sections` stripped |
| `render` / `render(name.md)` | same, explicit | Same as default, named |
| `results` / `results(name.md)` | `{stem}_results.md` | Step outputs only — no prose, no code, no `@sections` |
| `write` / `write(name.md)` | `{stem}_output.md` | Full replica with `result:` fields injected into each step |

**Default (render)** is best for sharing and LLM consumption — it reads like a
notebook. **results** is best when you want only the raw output. **write** is
best when you want to re-run the file and see diffs over time.

Example — explicitly choose render:

```markdown
@on_done
render(reports/analysis_rendered.md)
```

Example — output only:

```markdown
@on_done
results
```

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

---

## Platform compatibility

`runxmd` runs on **Windows, Linux, and macOS** — the core runtime is pure Python
stdlib with no platform-specific code.

| Platform | Status | Notes |
|---|---|---|
| Windows | ✅ | Full support |
| Linux | ✅ | Full support |
| macOS | ✅ | Full support |

**PowerShell note:** On Windows, `@powershell` uses `powershell -ExecutionPolicy Bypass`.
On Linux and macOS, it uses `pwsh` (PowerShell Core) — install from
[https://aka.ms/install-powershell](https://aka.ms/install-powershell) if needed.

---

## Check what's available on your machine

Before writing a multi-language doc, run:

```bash
runxmd check
```

It scans every interpreter, shows what's installed, and gives install hints for
anything missing:

```
runxmd check — interpreter availability

  Language     Plugin            Executable   Status      Version
  ---------------------------------------------------------------
  @python      @python_script    python       ✓  found    Python 3.14.5
  @node        @node_script      node         ✓  found    v24.15.0
  @typescript  @typescript_script ts-node     ✗  missing  install: npm install -g ts-node
  @ruby        @ruby_script      ruby         ✗  missing  install: https://...
  @bash        @bash_script      bash         ✓  found    GNU bash 5.3.9
  @go          @go_script        go           ✗  missing  install: https://go.dev/dl/
  @r           @r_script         Rscript      ✗  missing  install: https://cran.r-project.org/
  @php         @php_script       php          ✗  missing  install: https://...
  @perl        @perl_script      perl         ✓  found    v5.42.2
  @powershell  @powershell_script powershell  ✓  found    5.1.26100

  5 of 10 languages available.
```

Only install the languages you actually use — `runxmd` never installs anything itself.

---

## `.md` and `.xmd` — same Markdown, one is a signal

`runxmd` runs **both `.md` and `.xmd` files** identically. The only difference
is the name:

- **`.md`** — a regular Markdown file that may or may not have runnable steps.
- **`.xmd`** — the same format, byte-for-byte. The `.xmd` extension is a label
  that signals *"this file is meant to be executed."*

```bash
runxmd run notes.md       # runs — finds steps inside
runxmd run pipeline.xmd   # identical engine, identical grammar
```

---

## Adding `@workflow` when you need it

For simple scripts the bare `- @plugin` syntax is enough. Add `@workflow` when
you need named workflows — so you can run one selectively, or link it from a task.

```markdown
@workflow deploy
- @shell
  run: docker pull myapp:latest
- @shell
  run: docker restart myapp
```

```bash
runxmd run deploy.md --workflow deploy   # run only this workflow
```

---

## Stateful docs with `@memory`

`@memory` makes a Markdown file a *system* instead of a static doc.

```markdown
@memory
name: "world"
runtime.status: "pending"

@workflow hello
- @python
  run: |
    print("hello {{ memory.name }}")

@on_done
set: memory.runtime.status = "done"
render
```

1. **Read-in** — memory keys are loaded at run start.
2. **Substitution** — `{{ memory.key }}` anywhere in a step resolves live.
3. **Write-back** — use `--write-back` to persist `runtime.*` keys back into
   the source file after the run.

### Field ownership

- **`runtime.*` keys** — only the runtime writes these (via `@on_done set:`).
- **Everything else** — yours. The runtime reads them but never overwrites them.

---

## The full section set

| Section | Purpose | Grammar |
|---|---|---|
| `@goal` | Describes intent for humans/agents | free prose |
| `@memory` | Key-value state, optionally persisted | `key: value` lines |
| `@tasks` | Checklist the agent can tick | `- [ ]` / `- [x]` |
| `@workflow <name>` | Named group of steps | `- @plugin` + params |
| `@on_done` | Hooks that run after workflows finish | `set:` / `render` / `results` / `write` |

Steps written **outside** any `@workflow` (top-level in the file) run as an
implicit unnamed workflow — no annotation needed.

---

## Plugins

A step is `- @plugin` plus indented params:

### Inline code plugins

Write code directly in the document using `run: |`:

| Plugin | Language | Key params |
|---|---|---|
| `@print` | — | `text` |
| `@shell` | Shell (`/bin/sh` on Linux, `cmd` on Windows) | `run` |
| `@python` | Python | `run` |
| `@node` | JavaScript | `run` |
| `@typescript` | TypeScript (needs `ts-node`) | `run` |
| `@ruby` | Ruby | `run` |
| `@bash` | Bash | `run` |
| `@go` | Go | `run` |
| `@r` | R (needs `Rscript`) | `run` |
| `@php` | PHP | `run` |
| `@perl` | Perl | `run` |
| `@powershell` | PowerShell (`powershell` on Windows, `pwsh` on Linux/macOS) | `run` |

### External script plugins

Point at an existing file on disk using `path:`:

| Plugin | Runs | Key params |
|---|---|---|
| `@python_script` | `.py` file | `path`, `args` (optional) |
| `@node_script` | `.js` file | `path`, `args` |
| `@typescript_script` | `.ts` file | `path`, `args` |
| `@ruby_script` | `.rb` file | `path`, `args` |
| `@bash_script` | `.sh` file | `path`, `args` |
| `@go_script` | `.go` file | `path`, `args` |
| `@r_script` | `.R` file | `path`, `args` |
| `@php_script` | `.php` file | `path`, `args` |
| `@perl_script` | `.pl` file | `path`, `args` |
| `@powershell_script` | `.ps1` file | `path`, `args` |

```markdown
- @python_script
  path: scripts/analyze.py
  args: --input data.csv
```

`path:` is resolved relative to the **MD file's directory** — so `scripts/foo.py`
always means "next to the file being run", regardless of where you invoke `runxmd` from.
Absolute paths also work. `args:` is split on spaces and passed to the interpreter.

### Other plugins

| Plugin | Does | Key params |
|---|---|---|
| `@http` | Make an HTTP request | `url`, `method`, `body` |
| `@write` | Write a file (creates dirs) | `path`, `content` |
| `@read` | Read a file into output | `path` |
| `@llm` | Call an LLM (needs `ANTHROPIC_API_KEY`) | `prompt`, `model`, `max_tokens` |

**Detect, don't install.** Language plugins use whatever is already on your machine.
If an interpreter is missing, the step fails with a clear message and the run continues —
`runxmd` never installs anything for you.

> **Prerequisites:** `runxmd` itself has zero dependencies (pure Python ≥ 3.9).
> Each language plugin requires its interpreter on `PATH`. Run `runxmd check`
> to see exactly what is available on your machine before writing a multi-language doc.

### Multi-language example

Mix languages freely in the same file:

```markdown
# Polyglot Report

- @python
  run: |
    data = [1, 2, 3, 4, 5]
    print("Python sum:", sum(data))

- @node
  run: |
    const nums = [1, 2, 3, 4, 5];
    console.log("JS sum:", nums.reduce((a, b) => a + b, 0));

- @perl
  run: |
    my @nums = (1..5);
    printf "Perl sum: %d\n", eval join("+", @nums);
```

Each step runs in isolation. If an interpreter is missing, that step is marked ✗
and execution continues with the next step.

---

## Watch mode

```bash
runxmd watch report.md                  # re-run and re-render on every save
runxmd watch report.md --interval 0.5   # poll faster
runxmd watch report.md --max-runs 3     # stop after 3 runs
```

---

## Agent mode

`runxmd agent` turns the doc from *a program you run* into *a goal that runs itself*:

```text
Read @goal → plan @tasks → execute each task → update @memory → write back
```

```bash
runxmd agent project.md              # plan (if no tasks), then run linked workflows
runxmd agent project.md --replan     # regenerate tasks from the goal
runxmd agent project.md --autonomous # LLM generates AND runs steps for unlinked tasks
runxmd agent project.md --dry-run    # show the plan without executing or writing
```

Planning requires `ANTHROPIC_API_KEY`. See [`examples/AGENT.xmd`](./examples/AGENT.xmd).

---

## Commands

```bash
runxmd run <file> [--workflow NAME] [--write-back]
runxmd watch <file> [--interval S] [--max-runs N] [--write-back]
runxmd agent <file> [--replan] [--autonomous] [--model M] [--max-tokens N] [--dry-run]
runxmd check
runxmd parse <file>
runxmd validate <file>
runxmd --version
```

| Flag | Applies to | Effect |
|---|---|---|
| `--write-back` | `run`, `watch` | Persist `runtime.*` memory back into the source file |
| `--workflow NAME` | `run`, `watch` | Run only the named workflow |
| `--write-back` omitted | default | Source file is never modified |

---

## Design principles

- **No annotation required to get started.** A file with bare `- @plugin` steps runs.
- **Source files are read-only by default.** Output always goes to a new file.
- **Render is the default output.** Prose is preserved; only code blocks are replaced.
- **Cross-platform.** Runs on Windows, Linux, and macOS without changes.
- **Your Markdown, not a new format.** Everything outside `@sections` is untouched prose.
- **Inline-first.** Code lives in the document; the runtime is a thin dispatcher.
- **Detect, don't install.** Use what's on the machine; fail clearly when it's not.
- **Stdlib only.** Zero dependencies, including `@http`.

---

## Status & roadmap

**Current: v1.0.2** — see [`SPEC-v0.0.3.md`](./SPEC-v0.0.3.md) for the full contract.

- ✅ Parser, executor, CLI (`run` / `watch` / `agent` / `parse` / `validate` / `check`)
- ✅ Plugins: shell, http, filesystem, llm
- ✅ Inline language plugins: Python, Node.js, TypeScript, Ruby, Bash, Go, R, PHP, Perl, PowerShell
- ✅ External script plugins: `@python_script`, `@node_script`, and one for every supported language
- ✅ Bare steps without `@workflow` — implicit unnamed workflow
- ✅ Render output (default) — prose preserved, code replaced with results
- ✅ Results output — step outputs only, for LLM consumption
- ✅ Write output — replica with `result:` fields for re-running
- ✅ Memory: read / substitute / write-back, with field-ownership safety
- ✅ Reactive `runxmd watch`
- ✅ Agent engine (`@goal` → auto-generate `@tasks` → execute → update memory)
- ✅ `runxmd check` — interpreter availability report with versions and install hints
- ✅ Cross-platform: Windows, Linux, macOS (PowerShell uses `pwsh` on Linux/macOS)
- ⏳ Declarative events (`@on_file_change`, `@daily`, `@on_commit`)
- ⏳ Portable `@task` abstraction
- ⏳ Multi-agent / distributed

Contributions and ideas welcome.

---

## License

MIT — see [LICENSE](./LICENSE).
