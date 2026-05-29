"""XMD command-line interface (SPEC §5)."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from . import __version__, executor
from .parser import parse


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="xmd", description="XMD runtime v" + __version__)
    p.add_argument("--version", action="version", version="xmd " + __version__)
    sub = p.add_subparsers(dest="cmd")

    pr = sub.add_parser("run", help="execute workflow(s) and persist memory")
    pr.add_argument("file")
    pr.add_argument("--workflow", help="run only the named workflow")
    pr.add_argument("--no-write", action="store_true", help="do not write memory back")

    pw = sub.add_parser("watch", help="re-run the file whenever it changes")
    pw.add_argument("file")
    pw.add_argument("--workflow", help="run only the named workflow")
    pw.add_argument("--interval", type=float, default=1.0, help="poll seconds")
    pw.add_argument("--max-runs", type=int, default=0, help="stop after N runs (0=forever)")
    pw.add_argument("--no-write", action="store_true", help="do not write memory back")

    pp = sub.add_parser("parse", help="print parsed structure as JSON")
    pp.add_argument("file")

    pv = sub.add_parser("validate", help="check the file parses; list sections")
    pv.add_argument("file")

    args = p.parse_args(argv)

    if args.cmd == "run":
        executor.run(args.file, workflow_name=args.workflow, write_back=not args.no_write)
    elif args.cmd == "watch":
        flush = lambda *a: print(*a, flush=True)  # noqa: E731 — keep watch output live
        executor.watch(
            args.file,
            workflow_name=args.workflow,
            interval=args.interval,
            max_runs=args.max_runs,
            write_back=not args.no_write,
            out=flush,
        )
    elif args.cmd == "parse":
        print(json.dumps(asdict(_load(args.file)), indent=2))
    elif args.cmd == "validate":
        return _validate(args.file)
    else:
        p.print_help()
    return 0


def _validate(path: str) -> int:
    try:
        doc = _load(path)
    except Exception as e:  # noqa: BLE001 — surface any parse failure to the user
        print(f"✗ failed to parse {path}: {e}")
        return 1
    if not doc.sections:
        print(f"✗ {path}: no sections found")
        return 1
    print(f"✓ {path} — title: {doc.title or '(none)'}")
    for s in doc.sections:
        name = f" {s.name}" if s.name else ""
        print(f"  @{s.kind}{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
