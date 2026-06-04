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

Hello from runxmd!

Numbers : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Sum     : 55
Evens   : [2, 4, 6, 8, 10]
Squares : [1, 4, 9, 16, 25]

The code block above was replaced with its output. The table at the top of this
file, and this prose, are completely unchanged.

---

## Level 2 — Medium Python

Sorting, formatting, basic data analysis. No third-party libraries.

Name       Score  Bar
--------------------------------
Carol         95  xxxxxxxxx pass
Alice         92  xxxxxxxxx pass
Frank         91  xxxxxxxxx pass
Dave          88  xxxxxxxx pass
Bob           78  xxxxxxx fail
Eve           73  xxxxxxx fail

Average : 86.2
Passing : 4 / 6
Top     : Carol

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

Shortest paths from A:
  A -> A  =  0
  A -> B  =  3
  A -> C  =  2
  A -> D  =  6

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
