# runxmd Showcase — A Living README

> **What you are reading is itself a runnable document.**
> Every `- @python`, `- @node`, `- @perl`, and `- @powershell` block below
> executes when you run `runxmd run readme_showcase.md`.
> The render output (`readme_showcase_render.md`) keeps all the prose, tables,
> headings, and blockquotes you see here — only the code blocks are replaced
> with their actual output.

Run it now:

```bash
runxmd run readme_showcase.md
```

---

## What runxmd aims to achieve

`runxmd` turns a Markdown file into a **living document** — one that executes,
captures its own results, and renders them back inline. The goal is a single file
that is simultaneously:

- **Human-readable** — renders perfectly in GitHub, VS Code, and every viewer
- **Machine-executable** — `runxmd run` replaces code blocks with real output
- **LLM-friendly** — the render file strips code, keeps prose and results

| Property | Plain `.md` | `.md` + runxmd |
|---|---|---|
| Renders in GitHub / VS Code | ✅ | ✅ |
| Human-readable prose | ✅ | ✅ |
| Code blocks actually execute | ❌ | ✅ |
| Output rendered back inline | ❌ | ✅ |
| Source file untouched | ✅ | ✅ |
| LLM-ready render output | ❌ | ✅ |

---

## Part 1 — Python

Python `3.14.5` is available. Three complexity levels: basic inline,
medium inline, and advanced via an external script.

### 1a · Basic — arithmetic and collections

Plain built-ins, no imports. Shows that the simplest snippet works
with zero boilerplate.

=== Python Basic ===
Numbers : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Sum     : 55
Evens   : [2, 4, 6, 8, 10]
Squares : [1, 4, 9, 16, 25, 36]

Words   : ['runxmd', 'makes', 'markdown', 'executable']
Sorted  : ['executable', 'makes', 'markdown', 'runxmd']
Longest : executable

The output above replaced the code block. Every table, heading, and
prose line around it is untouched — standard Markdown passes straight through.

### 1b · Medium — data analysis with stdlib

Using `collections.Counter` and formatted output. No third-party libraries.

=== Python Medium: Text Analysis ===
Words: 13  Unique: 11

Word         Count  Bar
------------------------------
to               2  ##
be               2  ##
or               1  #
not              1  #
that             1  #
is               1  #

Avg word length : 3.5 chars
Longest word    : question

> **Note on inline snippets:** each `- @python` step is an isolated subprocess.
> Variables from step 1a are not visible here — each snippet is self-contained.
> Use `@python_script` with a shared file if you need state across snippets.

### 1c · Advanced — external script (`scripts/advanced_fibonacci.py`)

Runs a full `.py` file from disk: Fibonacci with `@lru_cache` and
Sieve of Eratosthenes. External scripts can be as large and complex as needed.

=== Fibonacci with Memoization ===
  fib(10) =           55
  fib(20) =        6,765
  fib(30) =      832,040
  fib(40) =  102,334,155
  fib(50) = 12,586,269,025

  Computed in 0.013 ms
  Cache hits : 52

=== Primes up to 100 (25 found) ===
  [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
  Sum of primes: 1060

| Algorithm | Time complexity | Space complexity |
|---|---|---|
| Fibonacci (memoized) | O(n) | O(n) |
| Sieve of Eratosthenes | O(n log log n) | O(n) |

The table above documents the algorithms in the script that just ran.
It is ordinary Markdown and is never modified by the runtime.

---

## Part 2 — Node.js

Node.js `v24.15.0` is available. JavaScript runs inline with `@node`
and from external files with `@node_script`.

### 2a · Basic — arrays and functional methods

=== Node.js Basic ===
Numbers : 1,2,3,4,5,6,7,8,9,10
Sum     : 55
Evens   : 2,4,6,8,10
Squared : 1,4,9,16,25,36,49,64,81,100

Words   : runxmd,makes,markdown,executable
Sorted  : executable,makes,markdown,runxmd
Longest : executable

### 2b · Medium — external script (`scripts/medium_node.js`)

Word frequency analysis and a grade classifier in a single external file.

=== Node.js: Word Frequency ===
Text   : "the quick brown fox jumps over the lazy dog the fox and the dog"
Words  : 14  Unique: 9

Top words:
  the      #### (4)
  fox      ## (2)
  dog      ## (2)
  quick    # (1)
  brown    # (1)

=== Grade Classifier ===
  Alice    94  A
  Carol    88  B
  Eve      79  C
  Bob      72  C
  Dave     61  F

  Average: 78.8
  Passing: 4/5

1. External scripts can `require()` local modules normally.
2. `path:` is relative to the directory you run `runxmd` from.
3. `args:` passes command-line arguments to the script.

---

## Part 3 — Perl

Perl is available at `/usr/bin/perl`. Excellent for regex and text
manipulation — a natural fit for document processing.

### 3a · Basic — regex and arrays

=== Perl Basic: Regex + Arrays ===
All   : apple apricot banana avocado cherry blueberry

Starts with 'a' : apple apricot avocado
Length > 6      : apricot avocado blueberry

Avg length : 6.7 chars
Reversed   : blueberry, cherry, avocado, banana, apricot, apple

### 3b · Medium — hash operations and ranking

=== Perl Medium: Hash + Ranking ===

Name       Score  Grade
----------------------------
Carol         95  A  #########
Alice         92  A  #########
Dave          88  B  ########
Bob           78  C  #######
Eve           73  C  #######

Average : 85.2
Passing : 5/5

---

## Part 4 — PowerShell

Windows PowerShell is available. Both inline (`@powershell`) and external
scripts (`@powershell_script`) are supported.

### 4a · Basic — system info and string operations

=== PowerShell Basic ===
User    : Subham
Machine : DESKTOP-VL4MVVM
Date    : 2026-06-04 23:34:02

String operations:
  Original : runxmd makes markdown executable
  Upper    : RUNXMD MAKES MARKDOWN EXECUTABLE
  Words    : 4
  Length   : 32 chars

Squares 1-8:
  1 x 1 = 1
  2 x 2 = 4
  3 x 3 = 9
  4 x 4 = 16
  5 x 5 = 25
  6 x 6 = 36
  7 x 7 = 49
  8 x 8 = 64

### 4b · Medium — external script (`scripts/medium_powershell.ps1`)

Fibonacci sequence and top processes by memory — from an external `.ps1` file.

D:\D\my : The term 'D:\D\my' is not recognized as the name of a cmdlet, function, script file, or operable program. 
Check the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:1 char:1
+ D:\D\my docs\my docs\projects\XMD\App\xmd\examples\showcase\scripts/m ...
+ ~~~~~~~
    + CategoryInfo          : ObjectNotFound: (D:\D\my:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException

| PowerShell feature used | Purpose |
|---|---|
| `function` with `param()` | Reusable Fibonacci generator |
| `@()` array syntax | Building sequences |
| `Measure-Object` | Sum and max of arrays |
| `Get-Process` + `Sort-Object` | Process introspection |
| `-f` format operator | Aligned column output |

---

## What stays unchanged in the render output

Everything you have read up to this point — headings, prose, tables, blockquotes,
numbered lists, bullet lists, bold text, italic text, inline code — is **standard
Markdown** and passes through to the render file byte-for-byte.

Only the `- @plugin` step blocks are replaced with their output.

| Markdown element | In source? | In render output? |
|---|---|---|
| `# ## ###` headings | ✅ | ✅ unchanged |
| Prose paragraphs | ✅ | ✅ unchanged |
| `\| table \|` | ✅ | ✅ unchanged |
| `> blockquote` | ✅ | ✅ unchanged |
| `- bullet list` | ✅ | ✅ unchanged |
| `1. numbered list` | ✅ | ✅ unchanged |
| `` `inline code` `` | ✅ | ✅ unchanged |
| ` ``` fenced block ``` ` | ✅ | ✅ unchanged |
| `---` horizontal rule | ✅ | ✅ unchanged |
| `**bold** / *italic*` | ✅ | ✅ unchanged |
| `- @plugin` step block | ✅ in source | replaced with output in render |

---

## Summary

| Language | Inline plugin | Script plugin | Version |
|---|---|---|---|
| Python | `@python` | `@python_script` | 3.14.5 |
| Node.js | `@node` | `@node_script` | v24.15.0 |
| Perl | `@perl` | `@perl_script` | available |
| PowerShell | `@powershell` | `@powershell_script` | available |

*Run `runxmd run readme_showcase.md` from this directory to regenerate the render output.*
