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

- @python
  run: |
    import pathlib

    target = pathlib.Path("scripts/basic.py")
    print("=== Simple File Check ===")
    if target.exists():
        size = target.stat().st_size
        print(f"  FOUND    : {target}")
        print(f"  Size     : {size} bytes")
        print(f"  Is file  : {target.is_file()}")
        print()
        print("  GUARDRAIL PASS: required file is present")
    else:
        print(f"  MISSING  : {target}")
        print()
        print("  GUARDRAIL FAIL: required file is missing")

The output above is the live result of checking `scripts/basic.py`.
The heading and this prose are untouched by the runtime.

---

## Level 2 — Medium: check multiple files and report

Check a list of required files and flag any that are missing.

- @python
  run: |
    import pathlib

    required = [
        "scripts/basic.py",
        "scripts/medium_node.js",
        "scripts/advanced_fibonacci.py",
        "scripts/medium_powershell.ps1",
    ]
    optional = [
        "scripts/nonexistent.sh",
        "scripts/nonexistent.rb",
    ]

    print("=== Medium File Check ===")
    print()
    print(f"{'File':<40} {'Status':<10} {'Size':>8}")
    print("-" * 62)

    missing = []
    for path_str in required:
        p = pathlib.Path(path_str)
        if p.exists():
            size = f"{p.stat().st_size:,} B"
            print(f"  {path_str:<38} FOUND      {size:>8}")
        else:
            missing.append(path_str)
            print(f"  {path_str:<38} MISSING         -")

    print()
    print("Optional files (missing is OK):")
    for path_str in optional:
        p = pathlib.Path(path_str)
        status = "present" if p.exists() else "absent"
        print(f"  {path_str:<38} {status}")

    print()
    if missing:
        print(f"  GUARDRAIL FAIL: {len(missing)} required file(s) missing:")
        for m in missing:
            print(f"    - {m}")
    else:
        print(f"  GUARDRAIL PASS: all {len(required)} required files present")

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

- @python_script
  path: scripts/advanced_file_check.py

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
