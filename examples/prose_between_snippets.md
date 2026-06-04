# Markdown Runs Intact

This document demonstrates two things simultaneously:

1. Python snippets at **basic**, **medium**, and **advanced** levels all run correctly.
2. Every Markdown element outside a code step is preserved **byte-for-byte** in the render output.

---

## What stays unchanged after execution

The table below, this prose, blockquotes, bold, italic, lists, and headings are all
standard Markdown. After running `runxmd`, they appear identically in the render output —
only the `- @python` blocks are replaced with their results.

| Markdown element | Syntax | Preserved after run? |
|---|---|---|
| Heading | `# Heading` | ✅ Yes |
| Bold | `**bold**` | ✅ Yes |
| Italic | `*italic*` | ✅ Yes |
| Strikethrough | `~~text~~` | ✅ Yes |
| Table | `\| col \|` | ✅ Yes |
| Blockquote | `> text` | ✅ Yes |
| Ordered list | `1. item` | ✅ Yes |
| Unordered list | `- item` | ✅ Yes |
| Inline code | `` `code` `` | ✅ Yes |
| Fenced code block | ` ``` ` | ✅ Yes |
| Horizontal rule | `---` | ✅ Yes |
| Link | `[text](url)` | ✅ Yes |

> **Rule:** `runxmd` only acts on `- @plugin` step blocks.
> Everything else in the file passes through untouched — the runtime
> never modifies prose, headings, tables, or any other Markdown syntax.

---

## Level 1 — Basic Python

A simple snippet: arithmetic, list comprehension, string formatting.
No imports. Plain Python built-ins only.

- @python
  run: |
    name = "runxmd"
    print(f"Hello from {name}!")
    print()
    nums = list(range(1, 11))
    print(f"Numbers : {nums}")
    print(f"Sum     : {sum(nums)}")
    print(f"Evens   : {[n for n in nums if n % 2 == 0]}")
    print(f"Squares : {[n**2 for n in nums[:5]]}")

The code block above was replaced with its output. The table at the top of this
file, and this prose, are completely unchanged.

---

## Level 2 — Medium Python

Sorting, formatting, basic data analysis. No third-party libraries.

- @python
  run: |
    records = [
        ("Alice", 92), ("Bob", 78), ("Carol", 95),
        ("Dave", 88), ("Eve", 73), ("Frank", 91),
    ]
    avg = sum(s for _, s in records) / len(records)
    passing = [(n, s) for n, s in records if s >= 80]

    print(f"{'Name':<10} {'Score':>5}  Bar")
    print("-" * 32)
    for name, score in sorted(records, key=lambda x: -x[1]):
        bar = "x" * (score // 10)
        flag = " pass" if score >= 80 else " fail"
        print(f"{name:<10} {score:>5}  {bar}{flag}")
    print()
    print(f"Average : {avg:.1f}")
    print(f"Passing : {len(passing)} / {len(records)}")
    print(f"Top     : {sorted(records, key=lambda x: -x[1])[0][0]}")

The table below is standard Markdown — it appears unchanged in the rendered output.

| Metric | Value |
|---|---|
| Pass threshold | 80 |
| Total students | 6 |
| Expected passing | 4 |

---

## Level 3 — Advanced Python

Dijkstra's shortest-path algorithm on a weighted directed graph.
No imports — pure Python data structures only.

- @python
  run: |
    def dijkstra(graph, start):
        dist = {n: float("inf") for n in graph}
        dist[start] = 0
        unvisited = set(graph)
        while unvisited:
            curr = min(unvisited, key=lambda n: dist[n])
            unvisited.remove(curr)
            for neighbor, weight in graph[curr].items():
                if dist[curr] + weight < dist[neighbor]:
                    dist[neighbor] = dist[curr] + weight
        return dist

    graph = {
        "A": {"B": 4, "C": 2},
        "B": {"D": 3, "C": 1},
        "C": {"B": 1, "D": 5},
        "D": {},
    }
    distances = dijkstra(graph, "A")
    print("Shortest paths from A:")
    for node, d in sorted(distances.items()):
        print(f"  A -> {node}  =  {d}")

> **Algorithm note:** Dijkstra's algorithm finds the shortest path in a weighted
> directed graph. Time complexity O((V + E) log V) with a priority queue.
> This blockquote is ordinary Markdown — untouched by the runtime.

---

## Summary

| Item | Behaviour |
|---|---|
| `- @python` step block | Replaced with stdout/stderr output |
| Prose between steps | Preserved exactly as written |
| Tables | Preserved exactly as written |
| Headings | Preserved exactly as written |
| Blockquotes | Preserved exactly as written |
| Bold / italic / lists | Preserved exactly as written |

*The source file is never modified. Output goes to `prose_between_snippets_render.md`.*
