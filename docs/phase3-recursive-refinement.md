# Phase 3 — Recursive refinement of `@context_memory`

> Living design doc. We keep updating the approach here and discuss in the
> **Open questions** / **Discussion log** sections at the bottom.
> Status: **planning** (Phases 1–2 are built; this builds on them).
> Parent: [`context-memory-design.md`](context-memory-design.md) §4.2.

---

## 1. Why Phase 3 exists

Phase 2 does **one** summarization pass: read the whole raw log → emit one
summary. That works only while the raw log fits in the model's context window.
As the log grows, a single pass fails in two ways:

1. **Scale** — the log eventually exceeds the window; one pass physically can't
   read it all.
2. **Quality** — a single shallow pass over a large log crushes older facts;
   important detail is lost and not recoverable in that one shot.

**Recursive refinement** fixes both by building the summary through *multiple
passes*, always grounded in the raw log so it converges toward fidelity rather
than drifting away.

---

## 2. Two different recursions (be precise)

"Recursive" means two distinct things here. The engine supports both; they
compose.

### 2.A Recursion over DATA — hierarchical / map-reduce (handles SCALE)

Recursion over the *size* of the log (RAPTOR / tree-summarization style):

```
raw entries:   e1 e2 e3 e4 e5 e6 e7 e8 ...
  level 1:     s1 = summ(e1..e4)   s2 = summ(e5..e8)   ...     (chunk → summarize)
  level 2:     S  = summ(s1, s2, ...)                          (summarize summaries)
  ...          recurse until everything fits in ONE pass → root summary
```

It's a fold/reduce **tree**. Depth ≈ log_fanin(N). The recursion **bottoms out**
when the current level fits in one window. Each node summarizes raw entries (or
lower summaries that are themselves faithful reductions of raw entries).

### 2.B Recursion over QUALITY — iterative self-refine (handles QUALITY)

Recursion as **fixpoint iteration**: apply the same improve-operator until the
summary stops changing.

```
S0 = draft(log)
loop:  defects = critique(Sk, log)        # grounded against the raw log
       if defects are immaterial: stop    # convergence (fixpoint)
       S(k+1) = revise(Sk, defects, log)
       if diff(Sk, S(k+1)) < ε: stop       # convergence (stability)
```

`S_{k+1} = refine(S_k, critique(S_k, log))`. Converges to a stable, faithful
summary. (cf. Self-Refine, Reflexion.)

### 2.C Composition

Typical pipeline: **hierarchical** to get a draft that *fits* (scale) →
**self-refine** to *polish* it (quality) → **verify** (grounding). Each stage is
optional and pluggable.

---

## 3. The anti-drift invariant (non-negotiable)

Every refinement step is **grounded in the raw log**, never in a prior summary
alone:

- In 2.A, leaf nodes summarize raw entries; higher nodes summarize faithful
  sub-summaries.
- In 2.B, the **critique** compares the candidate against the raw log, so errors
  are caught against ground truth instead of being propagated.
- Cross-run (from Phase 2): a fresh refinement run re-derives from the log; we
  never seed "truth" from yesterday's summary.

The raw jsonl log is the single source of truth. The summary is always
reconstructable from it.

---

## 4. Termination — recursion must stop

Three bounds, all enforced (an unbounded loop is a bug):

1. **Max depth / max rounds `N`** — hard cap (default small, e.g. depth ≤ 4,
   rounds ≤ 3).
2. **Size / token budget** — stop once the summary is within the target size.
3. **Convergence** — stop when successive summaries differ below ε (normalized
   edit distance) **or** the critique reports no material defects.

For 2.A the natural stop is "fits in one window." For 2.B it is "critique finds
nothing material" (a fixpoint) or stability.

---

## 5. Grounding / verification pass (anti-hallucination)

After refinement, optionally verify each salient claim against the log:

- For each claim, is it supported by ≥1 log entry?
- Unsupported claims are **dropped or flagged**.

Two implementations: (a) **LLM-based** — "which of these claims are NOT supported
by the log?"; (b) **deterministic pre-filter** — do the claim's key tokens / ids
appear in the log? Start LLM-based with an optional deterministic pre-filter.

---

## 6. Strategy interface (pluggable, like plugins)

```python
@dataclass
class RefineOpts:
    strategy: str = "single"      # single | hierarchical | self_refine | reflection | salience | restructure
    max_rounds: int = 3           # for iterative strategies
    max_depth: int = 4            # for hierarchical
    chunk_tokens: int = 2000      # leaf chunk size (token budget)
    window_tokens: int = 8000     # "fits in one pass" threshold
    converge_eps: float = 0.05    # normalized-diff stop threshold
    model: str | None = None
    max_tokens: int = 512
    verify: bool = False

@dataclass
class RefineResult:
    summary: str
    rounds: int
    strategy: str
    converged: bool
    dropped_claims: list[str]     # from verification

def refine(log: list[dict], opts: RefineOpts) -> RefineResult: ...
```

Strategies register in a small registry (`STRATEGIES[name] -> fn`). The engine
may run one strategy or **chain** them (e.g. `hierarchical → self_refine →
verify`). All LLM calls go through the existing `executor._llm_complete` seam, so
the whole engine is testable with no API key.

Lives in a new module `runxmd/context_refine.py` to keep `executor.py` lean.

---

## 7. Core strategies — pseudocode

### 7.1 `hierarchical` (scale)
```python
def hierarchical(log, opts):
    units = [render_entry(e) for e in log]            # one text per entry
    depth = 0
    while tokens(units) > opts.window_tokens and depth < opts.max_depth:
        groups = chunk_by_tokens(units, opts.chunk_tokens)
        units = [llm_summarize(join(g), opts) for g in groups]   # map
        depth += 1
    return llm_summarize(join(units), opts), depth   # final fold (reduce)
```

### 7.2 `self_refine` (quality)
```python
def self_refine(log, opts):
    S = draft(log, opts)                 # may itself be hierarchical output
    for k in range(opts.max_rounds):
        defects = llm_critique(S, log, opts)         # grounded
        if not defects.material:
            return S, k, True            # converged: fixpoint
        S2 = llm_revise(S, defects, log, opts)
        if normalized_diff(S, S2) < opts.converge_eps:
            return S2, k + 1, True        # converged: stable
        S = S2
    return S, opts.max_rounds, False     # hit the cap
```

### 7.3 engine
```python
def run_refine(log, opts):
    fn = STRATEGIES[opts.strategy]
    summary, rounds, converged = fn(log, opts)
    dropped = []
    if opts.verify:
        summary, dropped = verify_against_log(summary, log, opts)
    return RefineResult(summary, rounds, opts.strategy, converged, dropped)
```

Other strategies (later): `reflection` (synthesize higher-level insights as a
layer), `salience` (score recency × importance × relevance, keep top-k),
`restructure` (emit Facts / Decisions / Open / Next).

---

## 8. Incremental refinement (the key optimization)

Most of the log is **unchanged** between runs — only the tail (new entries) is
new. Re-summarizing everything every run is wasteful (and on paid models,
expensive). So:

- **Cache leaf summaries** keyed by a hash of their entry-range. Unchanged chunks
  reuse their cached summary; only new/changed chunks are re-summarized, then the
  tree is re-folded.
- Open question: store the cache **in-file** (a second hidden fence in
  `@context_memory`) for cross-run incrementality, or **in-memory** only
  (simpler, recompute leaves each run). See Open questions.

This makes steady-state refinement roughly O(new entries), not O(all entries).

---

## 9. Integration with the existing code

- Phase 2's `_summarize_context` becomes the **`single`** strategy (baseline).
- **Trigger** (to decide — see Open questions): extend the `@on_done` directive,
  e.g. `summarize(strategy=self_refine, rounds=3)` or a dedicated `refine`
  directive, or a config block inside `@context_memory`.
- **Write-back**: reuse `_set_section_summary` (byte-preserving) for the result.
- **Metadata** (rounds, strategy, converged, dropped claims): store as an HTML
  comment in the section and/or a `runtime.*` memory key — to decide.
- **Seam**: all model calls via `executor._llm_complete` (monkeypatchable).

---

## 10. Testability (deterministic, no API key)

Monkeypatch `_llm_complete` with a deterministic fake "model":

- `hierarchical`: fake summary = `"L:" + count(entries)`; assert N entries reduce
  to one root and depth ≤ max_depth; assert termination.
- `self_refine`: fake critique returns "material" for k rounds then "clean";
  assert it stops at convergence and `rounds == k`.
- convergence-by-stability: fake revise returns an identical string; assert stop.
- `verify`: plant an unsupported claim; assert it is dropped.
- grounding: assert each level's prompt contains log-derived tokens, never
  invented ones; assert the prior summary is not fed as truth.

---

## 11. Open questions (discuss & update)

1. **Trigger syntax** — `summarize(strategy=…, rounds=…)` vs a separate `refine`
   directive vs a config block in `@context_memory`?
2. **Default strategy & defaults** — `single` (current) until the log is large,
   then auto-`hierarchical`? Or always the chosen strategy? Default rounds/chunk?
3. **Incremental cache location** — in-file (cross-run, more surface) vs in-memory
   (simpler, recompute each run)?
4. **Metadata storage** — HTML comment vs `runtime.*` memory vs a structured
   header block?
5. **Structured vs free-prose summary** — does targeting Facts/Decisions/Open/Next
   help convergence and downstream agent use? Make it a strategy or the default?
6. **Convergence metric** — edit-distance ε, critique-says-done, or both (AND/OR)?
7. **Verification** — LLM-based, deterministic token-presence, or hybrid? Default
   on or off (latency/cost)?
8. **Auto-escalation** — start `single`, escalate to `hierarchical` when the log
   crosses the window, escalate to `self_refine` when quality matters? Who decides?

---

## 12. Discussion log

- _2026-06-11_ — Doc created. Proposed two-recursion model (data vs quality),
  anti-drift invariant carried from Phase 2, pluggable strategy interface,
  incremental-cache optimization. Awaiting decisions on the Open questions before
  implementation.
