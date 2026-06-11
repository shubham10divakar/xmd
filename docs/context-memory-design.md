# `@context_memory` — Markdown files as self-curating working memory for agents

> Status: **design / planning** (not yet built). Target: runxmd v1.1 seed.
> This document is both the implementation plan and the justification record
> (intended to support a future research write-up).

---

## 1. Problem

LLM/agent systems lose state between steps and runs. The model's context window
is finite, so long-horizon tasks either (a) re-stuff an ever-growing prompt until
it overflows, or (b) offload memory to external infrastructure — typically a
**vector database** (embeddings + similarity retrieval).

Both are heavy. (a) doesn't scale and bloats cost/latency; (b) needs infra
(embedding model, vector store, chunking, an index that can go stale), is opaque
to humans, and retrieves by cosine distance rather than by relevance-reasoning.

## 2. Idea

Use the **`.md` document itself as the agent's working memory.** A runxmd file
runs, records what happened into a `@context_memory` section, and on the next run
feeds a **curated rolling summary** of that memory back into the LLM's prompt.

The file *is* the database: plain text, git-diffable, human-readable and
human-editable, zero infrastructure. State lives in the document, not the window
— which lets smaller / lower-context (and free) models sustain long tasks.

## 3. Why this is justifiable (the core argument)

Two observations turn this from "a write-only log" into a real, distinctive
mechanism. **Record these — they are the crux of the justification.**

### 3.1 Free models make a rolling summary affordable and continuous
The useful form of memory is **not** "append all raw outputs and inject the
blob" — that is noise and bloats context. The useful form is a **curated rolling
summary** the model rewrites to stay tight and relevant. The only objection to
doing this every step was cost. With **free / cheap models, that objection is
gone**: you can summarize continuously. (Remaining costs are latency and summary
quality, addressed in §5.)

### 3.2 If memory fits in context, it beats a vector DB — and the summary keeps it fitting
A vector DB exists to retrieve a relevant slice of knowledge that is *too large
to fit* in context. But for an **agent's own bounded working memory**, a rolling
summary keeps the total small enough to **include whole** — so no retrieval is
needed at all. No embeddings, no similarity search, no chunking, no stale index.

Deeper point: **the summary is the retrieval.** A vector DB ranks chunks by
embedding distance; a rolling summary keeps what matters by the LLM *reasoning*
about relevance. For working state, relevance-by-reasoning beats
relevance-by-cosine-distance.

### 3.3 Scope boundary (state honestly)
`@context_memory` replaces a vector DB **for bounded agent working memory /
state**, not for large-corpus knowledge retrieval. A flat Markdown file has no
semantic search; reading it all is O(n) tokens and breaks past a point. For
thousands of documents you still want retrieval. This is working memory, not a
knowledge base.

### 3.4 When it is and isn't useful
- **Useful:** the *same document is run repeatedly* (watch / scheduled / agent
  loop) with an **LLM in the loop** that needs continuity across runs.
- **Not useful:** one-shot runs (nothing reads the memory back), or no LLM (it
  degrades to a debug/audit log). Do not oversell it for these.

## 4. Architecture — every part earns its place

Three roles, with a clean separation that avoids the classic failure modes:

| Part | Role | Injected into prompt? | Author |
|------|------|----------------------|--------|
| **Raw log** (`jsonl` entries) | Durable **source of truth**: append-only, deterministic, cheap | **No** (avoids noise) | runtime (auto) |
| **Rolling summary** (prose) | The **curated working memory** that is fed to the model | **Yes** (bounded) | LLM |
| **Read-back token** | Surfaces the summary to steps/agents | — | — |

### 4.1 The anti-drift rule
The rolling summary is regenerated **from the raw log**, *not* from the previous
summary. This kills compounding "summary-of-a-summary" drift — the raw log is
ground truth and the summary is always reconstructable from it faithfully.

### 4.2 Recursive refinement of the summary

A single summarization pass is the baseline. The memory gets **better** when the
summary is **refined recursively** rather than written once. Refinement is a
pluggable *strategy*; all share one invariant: **iterate to improve quality, but
verify each iteration against the raw log**, so refinement converges toward
fidelity, not away from it. (The cross-run anti-drift rule still holds — a
refinement run may re-seed its first draft from the raw log.) Free / cheap models
make multi-pass refinement affordable (ties back to §3.1).

Strategies (selectable):

1. **Hierarchical / map-reduce** — when the raw log exceeds one context window:
   chunk it, summarize each chunk, then summarize the chunk-summaries. Recursive
   by construction; scales past the window. (cf. RAPTOR-style abstractive trees.)
2. **Self-refine (critique loop)** — draft → critique the draft *against the raw
   log* for completeness / redundancy / contradiction → revise → repeat until a
   stop condition. (cf. Self-Refine, Reflexion.)
3. **Reflection / insight synthesis** — periodically derive higher-level insights
   from accumulated entries ("what decisions / patterns emerged") and keep them as
   a distinct layer above raw facts. (cf. Generative Agents' reflection.)
4. **Salience pruning** — score facts (recency × importance × relevance), keep the
   high-salience set, drop noise — bounds memory size.
5. **Restructuring** — reorganize into a structured memory: *Facts / Decisions /
   Open questions / Next actions* — better for both human reading and agent use.

**Stopping criteria** (bounded by design): max rounds **N**, a token budget, or
**convergence** (successive summaries differ below a threshold). Default: small N
+ convergence, so it self-terminates.

**Grounding / anti-hallucination:** a verification pass flags claims in the
refined summary not supported by the raw log; unsupported claims are dropped or
marked. The log stays the arbiter of truth.

### 4.3 Section layout
```markdown
@context_memory

<!-- rolling summary: regenerated each run from the log below; this is what gets injected -->
The agent has verified the src/ folder (3 files) and deployed to staging.
Outstanding: confirm prod health check.

```jsonl
{"time":"2026-06-11T10:30:02Z","run":"7f3a","step":1,"plugin":"python","status":"ok","output":"GUARDRAIL_PASS: 3 files"}
{"time":"2026-06-11T10:30:03Z","run":"7f3a","step":2,"plugin":"shell","status":"ok","output":"deployed to staging"}
```
```

- `{{ context }}` (or `{{ context_memory }}`) substitutes the **summary prose**
  (what you inject).
- The `jsonl` log is internal source-of-truth, used to regenerate the summary.

## 5. Honest risks & mitigations
- **Summary drift / lost signal** (esp. weak free models): mitigated by §4's
  rule — regenerate from the raw log, not from the prior summary.
- **Latency** of summarizing every run: make summary regeneration opt-in /
  throttled (e.g. every N runs, or only when the log grew).
- **Demand risk:** value exists only for *repeated* LLM runs. Validate the
  workflow before investing heavily; otherwise prefer the 1.0.3 robustness work.
- **Overlap with `@write`/`@read`:** a user could hand-roll this today. The
  feature's value-add is the blessed convention + automatic capture +
  regenerate-from-source discipline + read-back token, not a brand-new capability.
- **Over-refinement** (§4.4): extra passes add latency and can over-compress
  (lose needed detail) or, if ungrounded, drift. Mitigated by convergence-based
  stopping, log-grounded verification, and a structured/min-detail target.

---

## 6. Implementation plan

### Phase 1 — Raw capture + read-back plumbing (deterministic, no API key) ✅ BUILT
> Implemented & tested (`tests/test_context_memory.py`, 10 tests; full suite 62
> green). `@context_memory` parsed (summary + jsonl log); byte-preserving
> `_append_to_section`; per-step `duration_ms`; `{{ context }}` substitution;
> `--no-save`; example `examples/agent_memory.md`.

1. **Parser (`parser.py`)** — add `"context_memory"` to `KNOWN_KINDS`; add
   `entries: list[dict]` + `summary: str` to `Section`; `_parse_context_memory`
   reads the leading prose as `summary` and the `jsonl` fence into `entries`
   (tolerant of malformed lines). `_serialize_section` support for full
   reserialize / `write` mode.
2. **Generic append-writer (`executor.py`)** — `_append_to_section(path, kind,
   new_lines, fenced=...)`: targeted text splice into the raw source (find the
   section, insert before its closing fence / next `@` / EOF). **Does not use
   `to_source`**, so everything outside the section stays byte-identical. Built
   generic so `@human_memory` reuses it. (Also a down-payment on the
   `TODO-v1.0.3` P2 minimal-diff write-back.)
3. **Executor wiring (`run()`)** — one `run_id` per run; measure per-step
   `duration_ms`; if `@context_memory` is present and not `--no-save`, build
   records from `wf_results` and append raw `jsonl` entries. Add
   `"context_memory"` to `_SKIP_SECTION_KINDS`.
4. **Read-back** — `ctx["context_memory"]` = parsed entries + summary;
   `{{ context }}` substitutes the summary text.
5. **CLI** — `--no-save` on `run`/`watch`.
6. **Tests (deterministic)** — append grows the log; re-run preserves prior
   entries; valid JSON per entry; output truncation/newline-collapse;
   byte-identical outside the section; opt-in by presence; `.md` == `.xmd`;
   `{{ context }}` feeds a downstream step; agent-owned `@memory` untouched.

### Phase 2 — Rolling summary (the payoff; needs a model, free tier fine)
7. **Summarizer step/hook** — an `@llm` pass that reads the **raw log** and
   regenerates the `summary` prose (per §4 anti-drift rule). Throttle/opt-in.
8. **Inject only the summary** via `{{ context }}`.
9. **Acceptance demo — "remembers across runs":** a doc whose `@llm` step
   visibly builds on prior runs because the summary was injected; with the
   section removed, it starts fresh each time. This is the proof the loop closes.

### Phase 3 — Recursive refinement engine (§4.4 made real)
10. **Strategy interface** — a `refine(log, prev_summary, opts) -> summary`
    contract so strategies are pluggable. Ship **self-refine** and
    **hierarchical** first; reflection / salience / restructuring later.
11. **Stop conditions** — max rounds `N`, token budget, and convergence
    (diff-below-threshold); default small `N` + convergence so it self-terminates.
12. **Grounding pass** — verify the refined summary against the raw log; drop or
    mark unsupported claims.
13. **Config surface** — opt-in and tunable: strategy, max rounds, token budget
    (via `@context_memory` config line and/or `agent`/CLI flags).
14. **Tests** — convergence terminates within `N`; hierarchical handles an
    oversized log (mock model); grounding drops an unsupported claim
    (deterministic mock model — no live API needed).

### Phase 4 — `@human_memory` (deferred, designed-in)
15. Reuse `_append_to_section`. First a readable bullet per run; later
    LLM-generated prose derived from `@context_memory`.

### Phase 5 — Research evaluation (for the write-up)
16. Compare on a recurring-agent task: **(a) no memory, (b) full-history stuffing,
    (c) vector-DB RAG, (d) `@context_memory` single-pass summary, (e)
    `@context_memory` + recursive refinement.** Measure: task success/quality,
    tokens-per-run, latency, and summary fidelity/drift over many runs.
    Hypotheses: (d/e) match or beat (c) on bounded working-memory tasks at lower
    cost with full human inspectability; (e) > (d) on fidelity/quality as the log
    grows, at the cost of extra (cheap, on free models) passes.

---

## 7. Decisions locked
- Per-step raw entries grouped by `run` id.
- Opt-in by section presence; `--no-save` to disable.
- Raw log = JSONL (machine-faithful, arbitrary fields); summary = prose.
- Inject **only** the summary; never the raw log.
- Summary regenerated **from the raw log**, never from the prior summary.
- Append via targeted splice, never `to_source` (byte-identical elsewhere).
- Positioning: vector-DB alternative **for bounded working memory**, not RAG.
- Refinement is a **pluggable strategy** (self-refine + hierarchical first);
  default = small `N` rounds + convergence stop; opt-in and tunable.
- Every refinement iteration is **verified against the raw log**; the log is the
  arbiter of truth (refinement converges toward fidelity, not away).
