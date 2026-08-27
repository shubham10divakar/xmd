# runxmd — JOT submission hardening plan

Tracking doc for the improvements needed before submitting the runxmd paper to
the *Journal of Object Technology*. Ordered by how much each strengthens the
paper's central claim ("the answer is already in the file"), not by
implementation difficulty.

**Status legend:** ⬜ not started · 🔧 in progress · ✅ done · ⏸️ deferred

Last updated: 2026-08-27

**Progress:** Tier A ✅ complete (A1 A2 A4 A6) on branch `jot-tier-a`, 117 tests
green. Tier B + Tier C not started. Remaining open sub-items are the non-blocking
follow-ups noted under each finished section (pre-commit/Action wiring,
`readme_showcase` regen on a full-interpreter box, `agent --autonomous`
tagging).

---

## Verification summary

All 10 review items were checked against the codebase on 2026-08-27. Every item
is real — nothing was already done or misdiagnosed.

| # | Claim | Evidence in code |
|---|---|---|
| 1 | No provenance, no `verify` | `_write_render_doc` (`executor.py:324`) writes raw content, no header. No `verify` subcommand in `cli.py`. |
| 2 | Failed step continues, exit always 0 | `run_steps` (`executor.py:187`) returns `all(...)` but nobody consumes it; `main()` returns `0` unconditionally (`cli.py:69–71`, `99`). |
| 3 | Per-step isolation, no sessions | `_make_inline_runner` (`lang.py:53`): `mkstemp` → `subprocess.run` → `unlink` per step. Listed as P5 "kernel mode" in `TODO-v1.0.3.md`. |
| 4 | Windows separators / absolute paths in committed renders | `file_checks_test_render.md:21` → `scripts\basic.py`; `readme_showcase_render.md:227–232` → `D:\D\my docs\...` + PowerShell stack trace with full home path. No normalization code anywhere. |
| 5 | No caching | Every `run` re-executes. `_run_step` already measures `duration_ms` (`executor.py:210`). |
| 6 | Non-deterministic steps unmarked | `@http`, `@llm`, `agent --autonomous` produce per-run output with no tag in render or provenance. |
| 7 | `run: \|` looks like YAML, isn't | `_parse_steps` / `_dedent_block` (`parser.py:219–277`) hand-rolled scanner. `TODO-v1.0.3.md` P1 admits "three patches; 0-indent band-aid." |
| 8 | Version mismatch | `__version__ = "1.0.2"` (`runxmd/__init__.py:7`); `Development Status :: 3 - Alpha` + classifiers stop at `3.13` (`pyproject.toml`); latest spec `SPEC-v0.0.3.md`; README shows Python 3.14.5. |
| 9 | No adoption artifacts | No `.github/workflows/`, no action, no third-party conversion. |
| 10 | Smaller gaps | No `timeout=` on `lang.py`/`shell.py` subprocess calls; stdout/stderr merged in render; no `if:` on steps (`Step` = `plugin`+`params`, `parser.py:24`); trace exists in `records` but no `--json`; `write` projection injects only `result:` (`_write_output_doc:358`), no exit code. |

**Also found (not on the original list):**

- ⬜ CLI/spec drift: `SPEC-v0.0.3.md:97` documents `--no-write`; actual flags are `--write-back` / `--no-save`. Fix with #8.
- ⬜ `agent.py:117` still uses `to_source` for write-back → reformats whole doc. Relevant to #4's "diffable" argument. (`TODO-v1.0.3.md` P2.)

---

## Build order

`#8` first (credibility, ~1 hr). Then Tier A in full before writing the paper's
results section. `#10`'s exit-code-in-`write` is pulled up next to `#2` — same
defect (a projection that loses failure information).

---

## Tier A — makes the central claim checkable

*Do all four before writing results. ~4–5 days.*

### ✅ A1. Provenance headers + `runxmd verify` — the critical gap

A render currently carries no evidence of *what* it is a render of. A stale
`_render.md` is trusted *more* than unrendered code. This converts "trust the
render" from a social norm into a checkable property — a real safety
contribution to write about.

- [x] New `runxmd/provenance.py`: `source_hash` over normalized source bytes
      (BOM-strip, CRLF→LF, rstrip lines); `build()` → HTML comment;
      `parse_header(text)`; `strip_header(text)` (for A2 `--check`); `verify()`.
- [x] Emit header in `_write_render_doc`, `_write_results_doc`,
      `_write_output_doc` (`executor.py`) via `_provenance_header()`. Fields:
      `source`, `source_sha256`, `runxmd_version`, `generated_utc`, `platform`,
      `interpreters` (reuses `checker._version` for language plugins that ran),
      `non_deterministic_steps`.
- [x] New `cli.py` subcommand: `verify <render> [--source path]`. Exit 0 match,
      3 STALE (+ hash diff summary), 2 no header / source not found.
- [x] `run` / `watch` gain `--no-provenance` for reproducible byte-identical
      output.
- [x] `tests/test_provenance.py` — 11 tests: hash canonicalization, header
      emit/parse, `--no-provenance`, results+output headers, verify 0/2/3,
      explicit `--source`, `.xmd`, `strip_header` idempotence.
- [ ] Wire into a pre-commit hook + the GitHub Action (see C9).

Header shape:

```
<!-- runxmd-provenance
source_sha256: 3f9a...c21
runxmd_version: 1.0.3
generated_utc: 2026-08-27T09:14:22Z
platform: linux-x86_64
interpreters: {python: 3.14.5, node: 24.15.0}
non_deterministic_steps: []
-->
```

### ✅ A2. Strict mode + failure-preserving `write` projection

A failed step is recorded and the run continues (correct for docs, unusable as a
CI doc-test). Best adoption path: "your README's outputs are checked on every
push."

- [x] `run --strict`: any step failure → `main()` returns 1 (with a
      `✗ strict: N step(s) failed` line).
- [x] `run --check`: build a fresh render in memory, `strip_header` both sides
      (so `generated_utc` doesn't force a diff), compare against the committed
      sibling (or the `render(name)` hook target), print a unified diff, exit 1
      on drift or if the render is missing. Writes nothing.
- [x] New `RunReport` (attached as `doc.report`): `all_ok`, `failed_steps`
      `[(workflow, idx, plugin)]`, `check_failed`, `check_target`. `run()` still
      returns the `Document` — non-breaking.
- [x] `_run_step` now returns `exit_code`; each step record carries `code`.
- [x] `_write_output_doc`: injects `status:` (`ok`/`error`), `exit_code:`, and
      `stderr:` (when it differs from `result:`) alongside `result:` — a re-run
      diff now catches a step that started failing even when it prints nothing.
- [x] `tests/test_strict_check.py` — 10 tests. Full suite 97 green.

### ✅ A4. Output normalization

Committed renders currently contain Windows separators and absolute home paths —
not diffable across machines, which kills the `write` projection's purpose.

- [x] New `runxmd/normalize.py`, applied to each step's stdout/stderr in
      `_run_step` before it reaches any writer or the context log. On by
      default; `run --raw` / `normalize=False` disables it.
- [x] Rules: paths under the doc dir → relative; home dir → `~/`; hostname →
      `HOST`; `\` → `/` inside path-like tokens (guarded by a trailing
      `.ext` so escaped strings like `'a\nb'` are left alone).
- [x] `redact:` step param — one literal or `/regex/` per line; replaced with
      `[redacted]`. Stripped from the params handed to the plugin.
- [x] Regenerated `examples/showcase/file_checks_test_render.md` — `scripts\…`
      → `scripts/…`, provenance header added, `runxmd verify` passes.
- [x] `tests/test_normalize.py` — 12 tests (per-rule + integration + `--raw`).
      Full suite 109 green.
- [ ] `readme_showcase_render.md` NOT regenerated here — `node` is absent on
      this machine, so a fresh run would corrupt it. Regenerate on a box with
      all 10 interpreters. It also needs `redact:` for the `modified:` mtimes
      it prints (volatile) — good demo of the param.
- [ ] Strip wall-clock durations — deferred; too broad a rule to apply safely
      without a real use case in hand.

### ✅ A6. Separate deterministic core from non-deterministic surface

`@http`, `@llm`, `agent --autonomous` produce a *sample*, not a computed fact —
quietly contradicts "compute once, read forever."

- [x] `register(name, deterministic=False)` on `@http` and `@llm`;
      `plugins.is_deterministic(name)` reads it (default True).
- [x] Render emits `<!-- non-deterministic: @llm — this output is a sample,
      not a computed fact -->` above such a step's output.
- [x] Provenance `non_deterministic_steps: [2]` now derived from the plugin
      attribute (dropped the hardcoded set in `provenance.py`).
- [x] `run --pure`: refuses non-deterministic steps before dispatch, records
      them in `RunReport.pure_refused`, CLI exits **2** with a summary line.
- [x] `tests/test_determinism.py` — 8 tests (attribute, render marker,
      provenance indices, `--pure` exit 2, deterministic steps unaffected).
      Full suite 117 green.
- [ ] `agent --autonomous` non-determinism (LLM-generated steps) — not tagged
      yet; separate code path in `agent.py`. Note for a follow-up.
- [ ] Paper: state Properties 1–2 over the `--pure` subset precisely.

---

## Tier B — strengthens specific paper sections

*~3–4 days. B3 dominates.*

### ✅ B3. Opt-in sessions

Per-step isolation is defensible but is the first thing every notebook user
hits. `session: name` lets Property 2 become "order-independent *for the default
configuration*" with sessions as a documented opt-out — stronger than either
pole.

- [x] `session: <name>` step param (parser already captures it; `_run_step`
      consumes it, excluded from the params handed to the plugin alongside
      `result` / `redact`).
- [x] `_Sessions` accumulator in the executor: keyed by name, holds the
      concatenated `run:` code and the last full stdout for that session.
      A later same-session step runs `prelude + "\n" + run`, then its reported
      output is `full_stdout` with the recorded prelude stdout prefix-subtracted.
- [x] **Works for all 10 languages with zero REPL/pipe protocol** — chose
      re-execution + prefix-subtraction over a `subprocess.Popen` pool. Trade-off
      (documented): side effects in earlier session steps re-run.
- [x] Default (no `session:`) stays fully isolated.
- [x] `tests/test_sessions.py` — 6 tests: shared scope, default isolation still
      NameErrors, step-2 output excludes step-1's, distinct names don't share,
      `session` not leaked to plugin, 3-step accumulation. Suite 123 green.
- [x] SPEC §6.2 + README "Sharing state between steps" — documented as an
      explicit opt-out of Property 2.

### ✅ B5. Content-addressed caching

Cheap; makes `runxmd watch` on a slow-step doc pleasant; gives the overhead
section a number.

- [x] New `runxmd/cache.py`. Key =
      `sha256(runxmd_version, plugin, params, interpreter_version, script_bytes)`.
- [x] Cache dir = `RUNXMD_CACHE_DIR` env or `~/.cache/runxmd`; atomic write via
      `os.replace`.
- [x] **Opt-in** `run --cache` / `watch --cache` (not on by default — silent
      caching would miss external deps a step reads outside `path:`, the same
      staleness class A1 fixes). `--force` ignores existing entries.
- [x] Scope: language plugins only. `@shell` / `@read` / `@write` / `@http` /
      `@llm` / `session:` steps never cached; exit-127 and failures not stored.
- [x] `RunReport.cache_hits` / `cache_misses`; `· cache: N hit, M miss` line.
- [x] `tests/test_cache.py` — 7 tests: hit skips execution (proven via an
      append-marker file), `--force` re-executes, changed step code = miss,
      prose-only edit still hits, cached output == fresh, no `--cache` = no
      caching, `@print` not cached. Suite 130 green.
- [ ] Cold-vs-warm timing number for the paper's overhead section — measure on
      a doc with a genuinely slow step (`duration_ms` is already recorded).

### ⬜ B10. Remaining smaller items

- [ ] Per-step `timeout:` param (default ~30s) on `subprocess.run` in
      `lang.py` / `shell.py` — closes the "runaway loop hangs the run" hole.
- [ ] `stdin:` step param.
- [ ] Keep `stderr` as its own field end-to-end (render shows it separately).
- [ ] `--json` trace output — dump the `records` list via one `json.dumps` in
      `cli.py`.
- [ ] Step-level `if:` on memory / context values — evaluate in `_run_step`
      before dispatch; record skipped steps as `skipped`.

---

## Tier C — adoption + hygiene (runs in parallel with writing)

### ✅ C8. Version hygiene + doc sync

- [x] `__version__` → `1.0.3`; README status badge → `v1.0.3`; Status section
      header → `v1.0.3`; `Development Status :: 4 - Beta`.
- [x] Added `Programming Language :: Python :: 3.14` to classifiers.
- [x] Spec/package version mapping note added to `SPEC-v0.0.3.md` §8 and the
      README Status section (spec keeps `v0.0.x`, current doc is v0.0.3 @ pkg
      v1.0.3).
- [x] Fixed the `--no-write` line in `SPEC-v0.0.3.md` → `--write-back` /
      `--no-save`.
- [x] Documented the whole trust layer: `verify` subcommand + `--strict` /
      `--check` / `--pure` / `--raw` / `--no-provenance` in both README
      (Commands table + a `runxmd verify` section) and `SPEC-v0.0.3.md` §6.1.
- [x] ROADMAP "Where it is now" → v1.0.3 with a trust-layer paragraph.
- [x] Regenerated `file_checks_test_render.md` so its header reads
      `runxmd_version: 1.0.3`; `verify` passes.

### ⬜ C7. Decide what the grammar actually is

`run: |` looks like a YAML block scalar; users will assume YAML quoting /
escaping / anchors and be wrong in hard-to-debug ways.

- [ ] Pick (a) a documented YAML subset (state exactly which), or (b) keep the
      bespoke parser but document every divergence explicitly. (a) preferred —
      less support burden later.
- [ ] `runxmd validate` rejects constructs it can't handle rather than silently
      misparsing (also `TODO-v1.0.3.md` P1).
- [ ] Regression tests for every patched heuristic: prose-with-colon, 0-indent
      prose between steps, `result:` alongside `run:`, multi-param block
      scalars.

### ⬜ C9. Adoption path

- [ ] GitHub Action wrapping `runxmd verify` + `run --check` on every push.
- [ ] VS Code extension: run the step under the cursor. (Stretch.)
- [ ] Convert a real third-party project's README to `.xmd` and open a PR. Pick
      one with many code blocks + a maintainer who cares about docs. Either
      merged (adoption story) or the review tells you what blocks adoption.
      Conversion surfaces stale outputs in their docs → publishable finding
      (Case Study 3).

---

## Effort summary

| Tier | Items | Estimate |
|---|---|---|
| A | A1, A2 (+exit codes), A4, A6 | ~4–5 days |
| B | B3, B5, B10 | ~3–4 days (B3 dominates) |
| C | C8, C7, C9 (+ Action) | ~1 day code + ongoing |

Start with A1 (provenance + `verify`) — self-contained, and every other Tier A
item references its header format.
