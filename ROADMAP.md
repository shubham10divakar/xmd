# runxmd — Roadmap

## Overall objective

> **Harden the simple core → make the document *remember* (context_memory) →
> only then make it *react* and *coordinate*.**
> The grand vision survives, but earned one disciplined layer at a time.

This is the center of gravity for every decision. The maximalist vision in
[`docs/vision.md`](docs/vision.md) (Document OS / XOS / XCloud) is the north star
to aim *toward*, not a backlog to sprint. Every feature must still pass the
two-test rule (`SPEC-v0.0.3 §0`): *could an agent write this with no examples?*
and *does it give a human a reason to trust it today?*

---

## Where it is now — v1.0.3 (shipped)

Parser → executor → CLI; plugins (`@print`, `@shell`, `@python`/`@node`/`@ruby`/
`@bash`, `@http`, `@write`, `@read`, `@llm`); three memory powers; field
ownership (`runtime.*`); `watch` (polling); the agent engine (`runxmd agent`:
plan → execute → update); output modes (render/results/write); guardrails;
cross-platform. SPEC at Layer 7.

**v1.0.3 trust layer** (the JOT hardening pass — see [`JOT-REVIEW-PLAN.md`](JOT-REVIEW-PLAN.md)):
provenance headers + `runxmd verify`; `run --strict` / `--check`; output
normalization + `redact:`; `run --pure` + the `deterministic=False` plugin flag.

---

## Horizons

| Horizon | Version | Theme | What |
|---|---|---|---|
| **Now** | **v1.0.3** | **Trust & robustness** (freeze features) | Threat model + `run --dry-run` + `--allow` allowlist (P0); parser diagnostics, deeper `validate` (P1); minimal-diff write-back (P2); output-mode clarity (P3); scope discipline (P4). See [`TODO-v1.0.3.md`](TODO-v1.0.3.md). |
| **In progress** | **v1.1** | **Context memory** — *"make the document remember"* | `@context_memory`: ✅ Phase 1 raw capture + `{{ context }}` read-back, ✅ Phase 2 rolling summary (anti-drift) — **built & on `main`, 76 tests green**. ⬜ Phase 3 recursive refinement · ⬜ Phase 4 `@human_memory` · ⬜ Phase 5 evaluation. Its byte-preserving append-writer also seeds P2. Full design: [`docs/context-memory-design.md`](docs/context-memory-design.md). |
| **Mid** | v1.2+ | **Reactive documents** — *"make it react"* | Declarative events (`@on_file_change`, `@daily`, `@on_commit`) replacing the `watch` polling seed. |
| **Later** | v2.x | **Agentic depth & portability** — *"make it coordinate"* | Portable `@task` IR/resolver; multi-document agent coordination; prompt caching/streaming in `@llm`. |
| **Vision** | — | **XOS — Document OS** | Multi-agent, shared memory (XMemory), distributed runtime (XCloud). Aspirational; gated by the two-test rule. |

## Platform pillars (from the vision)

- **XRuntime** (execution engine) — real today: executor + plugins + agent engine.
- **XMemory** (state layer) — flat `@memory` plus **`@context_memory` (Phases 1–2
  built): a self-curating working memory with an anti-drift rolling summary** —
  the first real step toward XMemory.
- **XOS** (platform) — aspirational; the reactive + coordinate layers are the path.

---

## Sequencing rule

1. **Ship v1.0.3 robustness first** — trust is the gate; an unsandboxed runner that
   misparses silently can't carry bigger features.
2. **Then v1.1 `@context_memory`** — the most defensible, research-worthy next step
   ("Markdown as a vector-DB alternative for agent working memory"); advances
   XMemory and pays down P2.
3. **Treat reactive/distributed (XOS) as vision, not backlog** — pursue only after
   memory proves out, one disciplined layer at a time.
