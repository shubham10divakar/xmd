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

- @python
  run: |
    print("=== Python Basic ===")
    nums = list(range(1, 11))
    print(f"Numbers : {nums}")
    print(f"Sum     : {sum(nums)}")
    print(f"Evens   : {[n for n in nums if n % 2 == 0]}")
    print(f"Squares : {[n**2 for n in nums[:6]]}")
    words = ["runxmd", "makes", "markdown", "executable"]
    print(f"\nWords   : {words}")
    print(f"Sorted  : {sorted(words)}")
    print(f"Longest : {max(words, key=len)}")

The output above replaced the code block. Every table, heading, and
prose line around it is untouched — standard Markdown passes straight through.

### 1b · Medium — data analysis with stdlib

Using `collections.Counter` and formatted output. No third-party libraries.

- @python
  run: |
    from collections import Counter

    text = "to be or not to be that is the question whether tis nobler"
    words = text.split()
    freq = Counter(words)

    print("=== Python Medium: Text Analysis ===")
    print(f"Words: {len(words)}  Unique: {len(freq)}")
    print()
    print(f"{'Word':<12} {'Count':>5}  Bar")
    print("-" * 30)
    for word, count in freq.most_common(6):
        bar = "#" * count
        print(f"{word:<12} {count:>5}  {bar}")
    print()
    lengths = [len(w) for w in words]
    print(f"Avg word length : {sum(lengths)/len(lengths):.1f} chars")
    print(f"Longest word    : {max(words, key=len)}")

> **Note on inline snippets:** each `- @python` step is an isolated subprocess.
> Variables from step 1a are not visible here — each snippet is self-contained.
> Use `@python_script` with a shared file if you need state across snippets.

### 1c · Advanced — external script (`scripts/advanced_fibonacci.py`)

Runs a full `.py` file from disk: Fibonacci with `@lru_cache` and
Sieve of Eratosthenes. External scripts can be as large and complex as needed.

- @python_script
  path: scripts/advanced_fibonacci.py

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

- @node
  run: |
    console.log("=== Node.js Basic ===");
    const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    console.log(`Numbers : ${nums}`);
    console.log(`Sum     : ${nums.reduce((a, b) => a + b, 0)}`);
    console.log(`Evens   : ${nums.filter(n => n % 2 === 0)}`);
    console.log(`Squared : ${nums.map(n => n ** 2)}`);
    const words = ["runxmd", "makes", "markdown", "executable"];
    console.log(`\nWords   : ${words}`);
    console.log(`Sorted  : ${[...words].sort()}`);
    console.log(`Longest : ${words.reduce((a, b) => a.length >= b.length ? a : b)}`);

### 2b · Medium — external script (`scripts/medium_node.js`)

Word frequency analysis and a grade classifier in a single external file.

- @node_script
  path: scripts/medium_node.js

1. External scripts can `require()` local modules normally.
2. `path:` is relative to the directory you run `runxmd` from.
3. `args:` passes command-line arguments to the script.

---

## Part 3 — Perl

Perl is available at `/usr/bin/perl`. Excellent for regex and text
manipulation — a natural fit for document processing.

### 3a · Basic — regex and arrays

- @perl
  run: |
    use strict;
    use warnings;
    print "=== Perl Basic: Regex + Arrays ===\n";
    my @fruits = ("apple", "apricot", "banana", "avocado", "cherry", "blueberry");
    print "All   : @fruits\n\n";
    my @a = grep { /^a/i } @fruits;
    my @long = grep { length($_) > 6 } @fruits;
    print "Starts with 'a' : @a\n";
    print "Length > 6      : @long\n\n";
    my @lengths = map { length($_) } @fruits;
    my $total = 0; $total += $_ for @lengths;
    printf "Avg length : %.1f chars\n", $total / scalar @lengths;
    print "Reversed   : " . join(", ", reverse @fruits) . "\n";

### 3b · Medium — hash operations and ranking

- @perl
  run: |
    use strict;
    use warnings;
    print "=== Perl Medium: Hash + Ranking ===\n\n";
    my %scores = (Alice => 92, Bob => 78, Carol => 95, Dave => 88, Eve => 73);
    my $total = 0; $total += $_ for values %scores;
    my $avg = $total / scalar keys %scores;
    my @ranked = sort { $scores{$b} <=> $scores{$a} } keys %scores;
    printf "%-10s %5s  %s\n", "Name", "Score", "Grade";
    print "-" x 28 . "\n";
    for my $name (@ranked) {
        my $s = $scores{$name};
        my $g = $s >= 90 ? "A" : $s >= 80 ? "B" : $s >= 70 ? "C" : "F";
        my $bar = "#" x int($s / 10);
        printf "%-10s %5d  %s  %s\n", $name, $s, $g, $bar;
    }
    printf "\nAverage : %.1f\n", $avg;
    printf "Passing : %d/%d\n", scalar(grep { $scores{$_} >= 70 } keys %scores), scalar keys %scores;

---

## Part 4 — PowerShell

Windows PowerShell is available. Both inline (`@powershell`) and external
scripts (`@powershell_script`) are supported.

### 4a · Basic — system info and string operations

- @powershell
  run: |
    Write-Output "=== PowerShell Basic ==="
    Write-Output "User    : $env:USERNAME"
    Write-Output "Machine : $env:COMPUTERNAME"
    Write-Output "Date    : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Output ""
    Write-Output "String operations:"
    $msg = "runxmd makes markdown executable"
    Write-Output "  Original : $msg"
    Write-Output "  Upper    : $($msg.ToUpper())"
    Write-Output "  Words    : $($msg.Split(' ').Count)"
    Write-Output "  Length   : $($msg.Length) chars"
    Write-Output ""
    Write-Output "Squares 1-8:"
    1..8 | ForEach-Object { Write-Output ("  {0} x {0} = {1}" -f $_, ($_ * $_)) }

### 4b · Medium — external script (`scripts/medium_powershell.ps1`)

Fibonacci sequence and top processes by memory — from an external `.ps1` file.

- @powershell_script
  path: scripts/medium_powershell.ps1

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
