"""Advanced file check script — existence, size, permissions, directory audit."""
import os
import pathlib
import sys
from datetime import datetime


def check_file(path):
    p = pathlib.Path(path)
    if p.exists():
        stat = p.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        readable = os.access(p, os.R_OK)
        return {
            "found": True,
            "path": str(p),
            "size": stat.st_size,
            "mtime": mtime,
            "readable": readable,
        }
    return {"found": False, "path": str(p)}


def audit_dir(directory, pattern="*"):
    p = pathlib.Path(directory)
    if not p.exists():
        return None, f"not found: {directory}"
    return sorted(p.glob(pattern)), None


# ── 1. Specific file checks ──────────────────────────────────────────────────

# Accept optional base directory from args (defaults to scripts/)
base = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("scripts")

targets = [
    (base / "basic.py",             "Basic Python script"),
    (base / "medium_node.js",        "Medium Node.js script"),
    (base / "advanced_fibonacci.py", "Advanced Fibonacci script"),
    (base / "medium_powershell.ps1", "PowerShell script"),
    (base / "nonexistent.sh",        "Non-existent file (expected missing)"),
]

print("=== File Existence Check ===\n")
found = 0
for path, label in targets:
    info = check_file(path)
    tag = "FOUND  " if info["found"] else "MISSING"
    print(f"  [{tag}] {label}")
    if info["found"]:
        found += 1
        print(f"           size     : {info['size']:,} bytes")
        print(f"           modified : {info['mtime']}")
        print(f"           readable : {'yes' if info['readable'] else 'NO - permission denied'}")
    else:
        print(f"           path     : {info['path']}")
    print()

status = "PASS" if found >= len(targets) - 1 else "FAIL"
print(f"Result : {found}/{len(targets)} found   [{status}]")

# ── 2. Directory audit ───────────────────────────────────────────────────────

print(f"\n=== Directory Audit: {base}/ ===\n")

all_files, err = audit_dir(base)
if err:
    print(f"  ERROR: {err}")
    sys.exit(1)

# Group by extension
by_ext: dict = {}
for f in all_files:
    if f.is_file():
        ext = f.suffix or "(no ext)"
        by_ext.setdefault(ext, []).append(f)

print(f"  Total files : {sum(len(v) for v in by_ext.values())}")
print(f"  Extensions  : {', '.join(sorted(by_ext.keys()))}\n")

for ext, files in sorted(by_ext.items()):
    total = sum(f.stat().st_size for f in files)
    print(f"  {ext:<14} {len(files)} file(s)   {total:,} bytes total")
    for f in files:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"    {f.name:<35} {size:>6,} bytes   {mtime}")

# ── 3. Guardrail summary ─────────────────────────────────────────────────────

print("\n=== Guardrail Summary ===\n")
py_files, _ = audit_dir(base, "*.py")
js_files, _ = audit_dir(base, "*.js")
ps_files, _ = audit_dir(base, "*.ps1")

checks = [
    (bool(py_files), f"Python scripts present  ({len(py_files or [])} found)"),
    (bool(js_files), f"JS scripts present      ({len(js_files or [])} found)"),
    (bool(ps_files), f"PS1 scripts present     ({len(ps_files or [])} found)"),
    (base.exists(),  f"scripts/ dir exists"),
]

all_pass = True
for passed, label in checks:
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {label}")
    if not passed:
        all_pass = False

print()
print(f"  Overall: {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
