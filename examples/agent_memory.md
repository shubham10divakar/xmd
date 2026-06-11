# Agent Memory Demo

@goal
Show how a `.md` file remembers across runs. Run it more than once:

    runxmd run examples/agent_memory.md

Each run appends entries to `@context_memory` below — the file becomes its own
working memory. `{{ context }}` injects the rolling summary back into a step.

@context_memory

<!-- rolling summary: in Phase 2 an @llm step regenerates this from the log below -->
No summary yet — run again after Phase 2 wires up the summarizer.

```jsonl
```

@workflow main
- @print
  text: "checked the project; prior context = {{ context }}"
- @print
  text: "done"
