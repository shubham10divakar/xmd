# Agent Memory Demo

@goal
Show how a `.md` file remembers across runs. Run it more than once:

    runxmd run examples/agent_memory.md

Each run appends entries to `@context_memory` below — the file becomes its own
working memory. `{{ context }}` injects the rolling summary back into a step.

@context_memory

<!-- rolling summary: regenerated from the log below by @on_done: summarize -->
No summary yet — run once (with ANTHROPIC_API_KEY set) to populate this.

```jsonl
```

@workflow main
- @print
  text: "checked the project; prior context = {{ context }}"
- @print
  text: "done"

@on_done
summarize
