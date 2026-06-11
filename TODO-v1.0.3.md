# runxmd v1.0.3 — TODO

Carried forward from the v1.0.2 assessment. Ordered by severity. The theme for
1.0.3 is **trust and robustness** — freeze feature growth, harden what exists.

---

## P0 — Security story (currently absent)

The whole premise is "an agent writes a `.md`, you run it." Today that means
unrestricted code execution with no guardrails. This must be addressed before
the tool can be recommended for untrusted input.

- [ ] **Threat model section in README** — state plainly: *"only run `.md` files
      you would run as a shell script. runxmd executes embedded code with no
      sandbox."*
- [ ] **`runxmd run --dry-run`** — show what would execute (plugins, commands,
      script paths) without running anything. Today only `agent` has `--dry-run`.
- [ ] **`--allow` / plugin allowlist** — e.g. `runxmd run file.md --allow python,read`
      so a doc can be run with only safe plugins enabled; `@shell` and script
      plugins refused unless explicitly allowed.
- [ ] **Confirmation for `@shell` and `*_script`** when running a file not
      authored locally (stretch — needs a trust mechanism, maybe a `--yes` flag
      to bypass in CI).
- [ ] Document that `agent --autonomous` = model-generated code execution, in
      bold, at the point of use.

---

## P1 — Parser robustness + diagnostics (currently fragile, silent)

The parser is a hand-rolled line scanner with accumulated heuristics. It
misparses silently — the worst failure mode. Bugs hit during 1.0.2 dev:
prose-with-colon absorbed as a step param; block-scalar termination needed
three patches; 0-indent band-aid.

- [ ] **Surface misparsed steps** — if a line looks like a step (`- @word`) but
      params don't parse, emit a warning instead of silently dropping/misreading.
- [ ] **Warn on spurious params** — a `key: value` prose line absorbed into a
      step should produce "ignored unexpected param 'x' on step N" rather than
      attaching silently.
- [ ] **Deepen `runxmd validate`** — currently only lists sections. Make it
      report: unknown plugins, steps with no recognized params, malformed
      `@on_done` hooks, block-scalar issues.
- [ ] **Consider a real tokenizer** (stretch) — or at least extract the parsing
      heuristics into one documented, tested module with a grammar comment.
- [ ] Add regression tests for every heuristic we patched:
      prose-with-colon, 0-indent prose between steps, `result:` alongside `run:`,
      multi-param block scalars.

---

## P2 — Write-back reformatting

`to_source` re-serializes to canonical style, silently rewriting the user's
file on `--write-back`. Contradicts the "your Markdown, untouched" promise.

- [ ] **Minimal-diff write-back** — only rewrite the `@memory` section's changed
      keys; leave the rest of the file byte-identical.
      *Groundwork landed:* `executor._append_to_section` / `_set_section_summary`
      (added for `@context_memory`) already do byte-preserving, targeted splices
      that avoid `to_source` — reuse that pattern for `@memory` write-back.
- [ ] Failing that, document clearly that `--write-back` reformats the doc.

---

## P3 — Output mode clarity

- [ ] **`write` produces two files** (`_output.md` + default `_render.md`) —
      surprising. Decide: should an explicit output hook suppress the default
      render? Probably yes. Make the rule explicit and tested.
- [ ] Document the full output-mode decision table in one place (which hooks
      suppress the default, which stack).

---

## P4 — Scope discipline

The vision doc reaches for "Document Operating System / XOS / XCloud." The
durable core value is the simple thing: *runnable Markdown that renders results
back.* Apply the SPEC's own two-test rule harder before adding surface.

- [ ] No new plugins or sections in 1.0.3 — robustness only.
- [ ] Re-evaluate whether the agent/LLM layer should be a separate package
      (`runxmd-agent`) so the core stays zero-dep and obviously-safe.

---

## P5 — Nice-to-have / stretch

- [ ] **Shared-state inline steps** (a "kernel" mode) — optional, opt-in; today
      each step is a fresh subprocess with no shared state. Breaks the notebook
      mental model people bring.
- [ ] **Subprocess startup cost** — N cold starts for N snippets. Only worth
      addressing if/when kernel mode lands.

---

## Explicitly NOT in 1.0.3

Deferred from the roadmap — do not start until the above is done:
- Declarative events (`@on_file_change`, `@daily`, `@on_commit`)
- Portable `@task` abstraction / IR
- Multi-agent / distributed (XOS)
