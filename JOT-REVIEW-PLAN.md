# runxmd — JOT submission hardening plan

Tracking doc for the improvements needed before submitting the runxmd paper to
the *Journal of Object Technology*. Ordered by how much each strengthens the
paper's central claim ("the answer is already in the file"), not by
implementation difficulty.

**Status legend:** ⬜ not started · 🔧 in progress · ✅ done · ⏸️ deferred

Last updated: 2026-08-27

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

### ⬜ A4. Output normalization

Committed renders currently contain Windows separators and absolute home paths —
not diffable across machines, which kills the `write` projection's purpose.

- [ ] New `runxmd/normalize.py`, applied to each step's captured output before
      any writer. On by default, `--raw` to disable.
- [ ] Rules: absolute paths under doc dir → relative; `\` → `/` in path-like
      tokens; `$HOME` / home-prefix → `~`; strip wall-clock durations from
      render (keep in provenance).
- [ ] `redact:` step param (regexes / literals) for volatile output.
- [ ] Regenerate the two committed showcase renders in the same PR.
- [ ] Tests: golden input/output per rule; `--raw` bypass.

### ⬜ A6. Separate deterministic core from non-deterministic surface

`@http`, `@llm`, `agent --autonomous` produce a *sample*, not a computed fact —
quietly contradicts "compute once, read forever."

- [ ] `deterministic = False` attribute on `@http`, `@llm` handlers.
- [ ] Render: emit `<!-- non-deterministic: @http -->` above such output.
- [ ] Provenance: `non_deterministic_steps: [2, 5]`.
- [ ] `run --pure`: refuse to execute non-deterministic plugins (exit 2).
- [ ] Tests: `--pure` refusal; render tag presence.
- [ ] Paper: state Properties 1–2 over the pure subset precisely.

---

## Tier B — strengthens specific paper sections

*~3–4 days. B3 dominates.*

### ⬜ B3. Opt-in sessions

Per-step isolation is defensible but is the first thing every notebook user
hits. `session: name` lets Property 2 become "order-independent *for the default
configuration*" with sessions as a documented opt-out — stronger than either
pole.

- [ ] `session: name` step param.
- [ ] `SessionPool` in the executor keyed by name, holding a long-lived
      `subprocess.Popen` per language + sentinel-delimited eval protocol.
- [ ] Default stays isolated.
- [ ] Tests: variable defined in step N visible in step N+1 within a session;
      isolation still holds without the param.
- [ ] Time-box fallback: ship Python-only, note the rest as mechanical.
- [ ] Paper: document the session case as an explicit opt-out of Property 2.

### ⬜ B5. Content-addressed caching

Cheap; makes `runxmd watch` on a slow-step doc pleasant; gives the overhead
section a number.

- [ ] Hash `(plugin, params, referenced-script bytes, interpreter version)`.
- [ ] Cache dir under doc or `~/.cache/runxmd`. Skip on hit unless `--force`.
- [ ] Report cold vs warm run time using `duration_ms`.
- [ ] Tests: hit skips execution; `--force` bypasses; script edit busts.

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

### ⬜ C8. Version hygiene — DO FIRST (~1 hr)

- [ ] Pick a version story: `1.0.3-dev`. Sync `runxmd/__init__.py`, README
      badge, `Development Status :: 4 - Beta`.
- [ ] Add `Programming Language :: Python :: 3.14` to classifiers.
- [ ] Rename spec to track the package version, or add a mapping note.
- [ ] Fix the `--no-write` line in `SPEC-v0.0.3.md:97` → `--write-back` /
      `--no-save`.

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
