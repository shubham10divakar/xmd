# runxmd grammar

`runxmd` parses a Markdown file with a **hand-rolled line scanner**, not a YAML
parser. `run: |` *looks* like a YAML block scalar, but the surrounding grammar
is a small bespoke thing. This document is the contract: what the parser
accepts, and exactly how it diverges from YAML. `runxmd validate` flags the
divergences it can detect.

> Decision (JOT plan C7): keep the bespoke parser, document every divergence,
> and make `validate` reject — not silently misparse — the constructs it can't
> handle. A documented YAML subset was considered and rejected: it would pull a
> parser dependency (or a large hand-written YAML subset) into a zero-dependency
> tool for a format that is deliberately tiny.

---

## 1. Document structure

```
[ # Title ]
[ prose … ]
@section [name]
   section body
@section [name]
   section body
- @plugin            ← top-level steps = one implicit unnamed workflow
  key: value
```

- **Title** — the first `#` heading before any `@section`.
- **Prose** — any line outside a `@section` and not part of a step. Passed
  through to the render byte-for-byte.
- **Sections** — a line whose first non-whitespace character is `@`. The word
  after `@` is the *kind*; the rest of the line is the optional *name*
  (`@workflow deploy`). A section body runs until the next `@`-line or EOF.
- Known kinds: `@goal`, `@memory`, `@tasks`, `@workflow`, `@on_done`,
  `@context_memory`. Any other `@x` is kept as inert prose (`validate` warns).

## 2. Steps

```
- @plugin
  key: value
  key: |
    block
    scalar
```

- A step starts with `- @word` **alone on its line** (`- @python`, not
  `- @python foo`).
- Params are indented `key: value` lines below it. Indentation must be
  **spaces** (tabs are rejected).
- `key: value` splits on the **first** `:`. The value is typed (§3).
- `key: |` starts a block scalar (§4).

## 3. Scalar typing (`parser.parse_scalar`)

| Input | Result |
|---|---|
| `"…"` or `'…'` | the inner text, **verbatim** — no escape processing (`\n` stays two chars) |
| `true` / `false` (any case) | boolean |
| `null` / `none` / *(empty)* | `None` |
| integer / float literal | `int` / `float` |
| anything else | the string as-is |

## 4. Block scalars (`key: |`)

- The block is every following line more indented than the `key:` line.
- Common leading whitespace is stripped (min-indent dedent).
- The block ends at the first of:
  - a `- @plugin` step line;
  - a `key:`-looking line at **≤** the `key:` line's indent (the next param);
  - a **non-empty column-0 line** when the `key:` line was itself indented
    (inter-step prose, headings, comments).
- `>` (folded scalars) is **not** supported.

## 5. `@memory`

- `key: value` lines, typed per §3.
- `#`-comment lines are ignored **here only**.
- Dotted keys (`runtime.status: "x"`) are literal single keys, not nested maps.

## 6. `@on_done` hooks

One directive per line. Recognised: `set: memory.runtime.<k> = <scalar>`,
`render` / `render(name)`, `results` / `results(name)`, `write` / `write(name)`,
`summarize` / `summarize(model)`. Anything else is rejected by `validate`.

---

## 7. Divergences from YAML — the important list

| YAML feature | runxmd behaviour |
|---|---|
| Anchors / aliases (`&a`, `*a`) | **not supported** — `validate` errors |
| Flow collections (`{a: 1}`, `[1, 2]` as a value) | read as a **literal string**, not parsed — `validate` errors |
| Folded scalars (`key: >`) | **not supported** — `validate` errors; use `\|` |
| Tab indentation | **not supported** — `validate` errors |
| Escape sequences in quotes (`"\n"`, `"\t"`, `"é"`) | **no processing** — the backslash and letter are kept literally |
| Multi-line / implicitly-continued quoted strings | not supported — one value per line, or use `\|` |
| Comments (`# …`) | only stripped inside `@memory`; elsewhere a `#` line is prose, or (if indented under a step) may be swallowed into a block scalar |
| `---` / `...` document markers | no meaning — `---` is just a Markdown horizontal rule in prose |
| Nested mappings via indentation | not supported — params are one level deep; use dotted keys |
| Complex keys, `? key` syntax, merge keys (`<<`) | not supported |
| Number forms: `0x1F`, `1_000`, `1e3`, `.inf`, `.nan` | only plain `int` / `float` via Python's `int()` / `float()` — `1e3` works, `0x1F` and `1_000` become strings |
| `yes` / `no` / `on` / `off` as booleans | **strings** — only `true` / `false` are booleans |
| Duplicate keys | last one wins, silently |

## 8. What `runxmd validate` checks

- File parses; at least one section present.
- Lists every section (and its name).
- **Errors** (exit 1): tab indentation; `>` folded scalars; flow-collection
  values; anchor/alias syntax; unknown `@plugin`; unrecognised `@on_done` hook.
- **Warnings** (exit 0): unknown `@section` kind; a code step with no params
  (likely a misparsed indented line); a block scalar that appears to have
  captured a following `- @…` step.
