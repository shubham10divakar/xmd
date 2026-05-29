# XMD Discussion — 2026-05-30

> Notes captured as-is from the design conversation. Covers: the wedge user,
> file-format strategy, the `@memory` design, and the locked scope for v0.0.1.
> Companion to `XMD-in deep.md` (the vision) — this is the first set of
> *build* decisions.

---

## 1. The wedge user — "agent-native, human-adopted, document-as-contract"

The wedge is **not** a narrow human persona, and **not** the vague "everyone"
(which is usually a product death-sentence). It is something more specific:

- **Agents are the native USER.** AI agents (e.g. Claude) already live entirely
  in documents — they read `CLAUDE.md` for config, write `.md` files to persist
  memory across sessions, track tasks and workflows in markdown. But they get
  **nothing executable back**. Memory files are inert notes; task lists don't
  run; workflow docs are walked manually. XMD's 7-layer stack is a description
  of the substrate agents are *currently missing*. An agent can write XMD
  correctly with zero examples because it's just structured markdown.

- **Humans are the ADOPTER.** A human decides to `pip install xmd`, points it at
  a project, and must trust the runtime with real work *today*. Agents use what
  they're handed; humans choose tools.

- **The document is the CONTRACT between them.** Both human and agent read,
  write, and execute the same file. Documents are the one interface both forms
  of intelligence already share. That's *why* it's universal — it names the
  mechanism of universality instead of hand-waving "for everyone."

**The discipline this imposes — every feature must pass BOTH tests:**
1. "Could an agent write this correctly with no examples?"
2. "Does this give a human a reason to trust it with real work today?"
A feature that passes only one is premature.

**Validation loop is tight:** XMD can be dogfooded in a live Claude session. The
test is — *can Claude pick up a `PROJECT.xmd` cold, run it, update memory/tasks
correctly, and hand it back still human-readable?*

---

## 2. Inline-first vs. pure-declarative (the biggest fork)

- **Inline code** (`@shell` / `@python` with the body in the doc) is
  self-contained: parser + executor + one plugin and it runs *today*.
- **Pure-declarative** (`@task name: train_model`) is portable but requires a
  registry + resolver + implementations to exist *before anything runs*.

The original vision docs marked inline code as "bad" (runtime dependency) and
declarative as "preferred" (portable). That reasoning is **correct but
expensive** — portability is a *scaling* feature, and we are not scaling yet at
zero users.

**Decision: inline-first.** Ship the self-contained version, earn users, then
introduce `@task` as an abstraction once a real user says "I keep rewriting the
same `@shell` block." To keep the door open, inline directives use the *same*
`@directive` + `key: value` shape the future declarative form will use, so
migration is natural and no restructuring is needed later.

---

## 3. "Any language?" + "should pip install interpreters?"

- **Can you paste any language?** Yes. The runtime is a **dumb dispatcher**: each
  directive maps to "write body to a temp file → run interpreter X". Adding a
  language is a one-line dispatch entry, not real work.
- **Runs only if that interpreter is installed.** That's the "runtime
  dependency" the vision flagged. Handle it with **detect-don't-install**: if
  `go` isn't found, say so cleanly and skip — never crash, never bundle.
- **Should pip bundle interpreters? NO.** pip installs Python packages, not
  system runtimes (you can't `pip install node`). Bundling = gigabytes, version
  hell, and it's not the runtime's job. Docker doesn't ship Python inside the
  engine. The one language always available is Python itself (the runtime is
  written in it), so `@python` is the one guaranteed-everywhere plugin.

**"Language independence" actually means three different things:**
- A) runtime isn't tied to one language → solved free by the dispatcher.
- B) you can write doc logic in any language → solved free by inline code.
- C) the *document itself* runs anywhere regardless of what's installed → **NOT**
  solved by installing interpreters. That's a *design* property bought with an
  abstraction layer (capability declaration → `@task`+resolver → containers),
  added later when users feel the pain. Installing interpreters makes you *more*
  environment-dependent, not less.

---

## 4. File formats — collapse 13 extensions into ONE

The deep-vision doc proposed 13 extensions (SMD, EMD, AMD, CMD, RMD, LMD, WMD,
TMD, MMD, DMD, NMD, PMD, GMD). Run through our two tests, that fails both:
- **Test 1 fails:** even the native agent user can't reliably tell `.amd` from
  `.smd`, or whether memory is `.mmd`. If the agent needs a lookup table, the
  format failed its user on day one.
- **Test 2 fails:** 13 new extensions is the opposite of trust — editor support,
  "what opens this?", alien diffs. Spending trust before earning any.

Deeper problem: extensions encode meaning in the *filename*, but meaning already
lives *inside* the file via `@directives`. And the 13-extension model
**fragments** the unified document (scatters one project across `AGENT.lmd` +
`MEMORY.mmd` + `TASKS.tmd` + ...) right when *unification* was the whole insight.

**Decision: one extension — `.xmd`.** Concepts (goal, memory, tasks, workflow,
events) are kept as `@directives`; the filename taxonomy is dropped. If a project
ever genuinely needs splitting, split by convenience (`memory.xmd`,
`tasks.xmd`) — still one format, like a codebase has many `.py` files. The
13-extension XOS family is parked as a far-future idea, earned later if a real
need appears.

---

## 5. `@memory` — what it does (all 3 powers, live in v0.0.1)

`@memory` is **persistent state that survives between runs** — the difference
between a script (forgets on exit) and a system (remembers). Three operations:

1. **Read-in (load):** at run start, parse `@memory` `key: value` lines into a
   live dict the run can see.
2. **Reference / substitution:** other sections use `{{ memory.key }}`; the
   runtime substitutes the value before executing the step. This is the one
   feature that makes memory *live* rather than dead text.
3. **Write-back (persist):** when a value changes (e.g. via an `@on_done`
   `set: memory.x = ...` hook), the runtime rewrites the value **into the file**,
   so the next run sees it. The document edits itself.

**Decision: all 3 powers live in v0.0.1.** The minimum that makes XMD different
from a shell script is "the file remembers across runs." Cutting write-back would
make v0.0.1 just a worse Makefile. `@memory` is the load-bearing wall that
everything agentic is later built on.

---

## 6. Locked scope for v0.0.1

- **One format:** `.xmd`. Meaning in `@directives`, not in extensions.
- **Per-section tuned grammars** (chosen over one uniform grammar — each section
  looks like the thing it represents, so the agent writes each in its most
  natural form):
  - `@goal` → prose
  - `@memory` → `key: value`
  - `@tasks` → `- [ ]` / `- [x]` checkboxes
  - `@workflow <name>` → ordered steps, each an inline-code directive
  - `@on_done` → hooks (`set: memory.x = ...`)
- **Inline-first dumb dispatcher** plugins: `@shell`, `@print`, and language
  plugins `@python` / `@node` / `@ruby` / `@bash` (temp-file + interpreter,
  detect-don't-install).
- **All 3 memory powers:** read-in, `{{ memory.x }}` substitution, write-back.
- **CLI:** `xmd run <file> [--workflow N] [--no-write]`, `xmd parse <file>`,
  `xmd validate <file>`. Stdlib only, zero dependencies.
- **The dogfood test:** `xmd run PROJECT.xmd` executes `@workflow`, substitutes
  memory, runs `@on_done`, and writes updated `@memory` back — leaving the file
  still human-readable.

**Deliberately deferred:** IR layer (not needed until a second runtime target
forces it), event watching (`@on_file_change`/`@daily`), the agent engine, the
`@task` declarative abstraction + resolver, distributed/XOS, and the
13-extension family.

---

## Known v0.0.1 limitations (acceptable for now)

- Write-back reformats the whole document (re-serializes from parsed structure),
  so hand-formatting/quote-style is normalized on each run. Documents the
  "self-editing" behavior; refine round-trip fidelity later.
- No increment/expression ops in memory hooks — only `set: memory.x = value`.
- `{{ }}` substitution resolves missing keys to empty string.

---

## 7. Post-v0.0.1 work (same session)

### Field-ownership hazard — FIXED (Option A)
The dogfood test (an agent picking up `PROJECT.xmd` cold, running it, ticking
tasks, updating memory, handing it back) **passed** — agent edits survived runtime
write-back. But it exposed a hazard: two writers (agent hand-edits + runtime
`@on_done`) had no merge protocol; it only worked because they touched disjoint
keys *by convention*. Same-key writes would be silent last-writer-wins.

**Fix (Option A):** the runtime may only write memory keys under the reserved
`runtime.` namespace. A `set:` hook targeting any agent-owned key is **refused**
with a warning; agent state is untouchable by the runtime. Verified: a hook trying
to overwrite `last_session` was refused while `runtime.note` was applied. Now safe
by construction, not convention. (SPEC §4.1.)

### v0.0.2 — capability + reactivity (B and C, together)
- **B — more plugins:** `@http` (GET/POST etc. via stdlib `urllib`, zero deps),
  `@write` / `@read` (filesystem). Verified: `@write` with `{{ memory.user }}`
  substitution → `@read` round-trip, and a live `@http` GET returning 200.
- **C — `xmd watch`:** re-runs the file whenever it changes (polling). The
  reactive/Phase-3 *seed*; the declarative event system (`@on_file_change`,
  `@daily`, `@on_commit`) is still deferred. **Self-trigger guard:** the mtime
  baseline is captured *after* the runtime's own write-back, so write-back never
  causes an infinite re-run loop — verified that `↻ change detected` fires only on
  an external edit, not on the runtime's own write. `--max-runs N` added (stop
  after N runs; useful for CI/tests).

Specs are versioned in the filename (as preferred): `SPEC-v0.0.2.md` supersedes
`SPEC-v0.0.1.md` (kept as history). Package bumped to 0.0.2.
