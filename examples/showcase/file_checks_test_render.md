# File Existence Checks

This document demonstrates checking whether files exist in a directory —
a common guardrail pattern before running a workflow that depends on those files.

Three levels are shown:

1. **Simple inline** — check one file, report found/missing
2. **Medium inline** — check a list of files with size/type info
3. **Advanced script** — full directory audit with guardrail summary

All paths are resolved relative to this file's directory.

---

## Level 1 — Simple: does a specific file exist?

The most basic guardrail: check one file before proceeding.

=== Simple File Check ===
  FOUND    : scripts\basic.py
  Size     : 648 bytes
  Is file  : True

  GUARDRAIL PASS: required file is present

The output above is the live result of checking `scripts/basic.py`.
The heading and this prose are untouched by the runtime.

---

## Level 2 — Medium: check multiple files and report

Check a list of required files and flag any that are missing.

=== Medium File Check ===

File                                     Status         Size
--------------------------------------------------------------
  scripts/basic.py                       FOUND         648 B
  scripts/medium_node.js                 FOUND       1,659 B
  scripts/advanced_fibonacci.py          FOUND       1,384 B
  scripts/medium_powershell.ps1          FOUND       1,189 B

Optional files (missing is OK):
  scripts/nonexistent.sh                 absent
  scripts/nonexistent.rb                 absent

  GUARDRAIL PASS: all 4 required files present

> The table below documents the expected files — it is standard Markdown
> and is never modified by the runtime.

| File | Purpose | Required? |
|---|---|---|
| `scripts/basic.py` | Basic Python ops | ✅ Yes |
| `scripts/medium_node.js` | Node text analysis | ✅ Yes |
| `scripts/advanced_fibonacci.py` | Advanced algorithms | ✅ Yes |
| `scripts/medium_powershell.ps1` | PowerShell Fibonacci | ✅ Yes |
| `scripts/nonexistent.sh` | Placeholder | ❌ Optional |

---

## Level 3 — Advanced: full directory audit via external script

Runs `scripts/advanced_file_check.py` which performs:

- Per-file existence, size, modified date, and read permission
- Groups all files by extension
- Runs a guardrail summary with PASS/FAIL per condition
- Accepts an optional `args:` to audit a different directory

=== File Existence Check ===

  [FOUND  ] Basic Python script
           size     : 648 bytes
           modified : 2026-06-04 23:33
           readable : yes

  [FOUND  ] Medium Node.js script
           size     : 1,659 bytes
           modified : 2026-06-04 23:33
           readable : yes

  [FOUND  ] Advanced Fibonacci script
           size     : 1,384 bytes
           modified : 2026-06-04 23:33
           readable : yes

  [FOUND  ] PowerShell script
           size     : 1,189 bytes
           modified : 2026-06-04 23:33
           readable : yes

  [MISSING] Non-existent file (expected missing)
           path     : scripts\nonexistent.sh

Result : 4/5 found   [PASS]

=== Directory Audit: scripts/ ===

  Total files : 5
  Extensions  : .js, .ps1, .py

  .js            1 file(s)   1,659 bytes total
    medium_node.js                       1,659 bytes   2026-06-04 23:33
  .ps1           1 file(s)   1,189 bytes total
    medium_powershell.ps1                1,189 bytes   2026-06-04 23:33
  .py            3 file(s)   6,009 bytes total
    advanced_fibonacci.py                1,384 bytes   2026-06-04 23:33
    advanced_file_check.py               3,977 bytes   2026-06-04 23:33
    basic.py                               648 bytes   2026-06-04 23:33

=== Guardrail Summary ===

  [PASS] Python scripts present  (3 found)
  [PASS] JS scripts present      (1 found)
  [PASS] PS1 scripts present     (1 found)
  [PASS] scripts/ dir exists

  Overall: ALL CHECKS PASSED

The script above audited the `scripts/` directory relative to this file.
Every heading, table, and blockquote you see around it is preserved exactly
as written — only the `- @python_script` block was replaced with output.

### Running with a custom directory

The script accepts a path argument to audit any directory.
Add an `args:` param to point at any folder on your machine.

| Param | Value | Notes |
|---|---|---|
| `path` | `scripts/advanced_file_check.py` | resolved from this file's directory |
| `args` | e.g. `C:/my-project/src` | overrides the default `scripts/` base |

---

## Summary

| Approach | Plugin | Best for |
|---|---|---|
| Single file check | `@python` inline | Quick guardrail before a step |
| Multi-file check | `@python` inline | Validating a set of dependencies |
| Full audit | `@python_script` | Pre-flight reports, CI checks, scheduled audits |

*All paths resolve relative to this file — run from any directory.*
