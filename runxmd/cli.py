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
    # Force UTF-8 so the ▶/✓/✗ glyphs render on Windows cp1252 consoles.
    # Guarded with hasattr: notebook streams (Colab/Kaggle/Jupyter) replace
    # sys.stdout with an object that has no reconfigure(), and that's fine.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="runxmd", description="runxmd — the XMD runtime v" + __version__)
    p.add_argument("--version", action="version", version="runxmd " + __version__)
    sub = p.add_subparsers(dest="cmd")

    pr = sub.add_parser("run", help="execute workflow(s) in the file")
    pr.add_argument("file")
    pr.add_argument("--workflow", help="run only the named workflow")
    pr.add_argument("--write-back", action="store_true",
                    help="write runtime.* memory back into the source file (default: off)")
    pr.add_argument("--no-save", action="store_true",
                    help="do not append run records to @context_memory (default: append if section present)")
    pr.add_argument("--no-provenance", action="store_true",
                    help="omit the runxmd-provenance header from output files")
    pr.add_argument("--strict", action="store_true",
                    help="exit non-zero if any step fails (for CI / doc-tests)")
    pr.add_argument("--check", action="store_true",
                    help="don't write; compare a fresh render against the committed "
                         "one and exit non-zero if they differ")
    pr.add_argument("--raw", action="store_true",
                    help="do not normalize step output (keep absolute paths, "
                         "backslashes, home dir, hostname as-is)")
    pr.add_argument("--pure", action="store_true",
                    help="refuse to run non-deterministic steps (@http, @llm); "
                         "the render is then a computed fact, not a sample")
    pr.add_argument("--cache", action="store_true",
                    help="reuse a cached result for a language step whose plugin, "
                         "params, interpreter version and script bytes are unchanged")
    pr.add_argument("--force", action="store_true",
                    help="with --cache: ignore existing cache entries (still refresh them)")
    pr.add_argument("--timeout", type=float, metavar="SECONDS",
                    help="default per-step timeout; a step's own timeout: param wins")
    pr.add_argument("--json", action="store_true",
                    help="print a JSON execution trace to stdout (suppresses normal output)")

    pw = sub.add_parser("watch", help="re-run the file whenever it changes")
    pw.add_argument("file")
    pw.add_argument("--workflow", help="run only the named workflow")
    pw.add_argument("--interval", type=float, default=1.0, help="poll seconds")
    pw.add_argument("--max-runs", type=int, default=0, help="stop after N runs (0=forever)")
    pw.add_argument("--write-back", action="store_true",
                    help="write runtime.* memory back into the source file (default: off)")
    pw.add_argument("--no-save", action="store_true",
                    help="do not append run records to @context_memory (default: append if section present)")
    pw.add_argument("--no-provenance", action="store_true",
                    help="omit the runxmd-provenance header from output files")
    pw.add_argument("--raw", action="store_true",
                    help="do not normalize step output")
    pw.add_argument("--pure", action="store_true",
                    help="refuse to run non-deterministic steps (@http, @llm)")
    pw.add_argument("--cache", action="store_true",
                    help="reuse cached results for unchanged language steps")
    pw.add_argument("--force", action="store_true",
                    help="with --cache: ignore existing cache entries")
    pw.add_argument("--timeout", type=float, metavar="SECONDS",
                    help="default per-step timeout; a step's own timeout: param wins")

    pa = sub.add_parser("agent", help="goal -> tasks -> execute -> memory (Layer 7)")
    pa.add_argument("file")
    pa.add_argument("--replan", action="store_true", help="regenerate tasks from the goal")
    pa.add_argument("--autonomous", action="store_true",
                    help="let the LLM generate + RUN steps for tasks with no workflow link")
    pa.add_argument("--model", help="LLM model id for planning/generation")
    pa.add_argument("--max-tokens", type=int, default=1024)
    pa.add_argument("--dry-run", action="store_true", help="plan/show without executing or writing")

    sub.add_parser("check", help="show which language interpreters are installed")

    pp = sub.add_parser("parse", help="print parsed structure as JSON")
    pp.add_argument("file")

    pv = sub.add_parser("validate", help="check the file parses; list sections")
    pv.add_argument("file")

    pvf = sub.add_parser("verify", help="check a render still matches its source")
    pvf.add_argument("file", help="the _render / _results / _output file to check")
    pvf.add_argument("--source",
                     help="source document (default: read from the render's provenance header)")

    args = p.parse_args(argv)

    if args.cmd == "check":
        from . import checker
        checker.check()
    elif args.cmd == "run":
        doc = executor.run(args.file, workflow_name=args.workflow,
                           write_back=args.write_back,
                           save_context=not args.no_save,
                           add_provenance=not args.no_provenance,
                           check=args.check, normalize=not args.raw,
                           pure=args.pure, cache=args.cache, force=args.force,
                           timeout=args.timeout,
                           out=(lambda *a: None) if args.json else print)
        report = getattr(doc, "report", None)
        if args.json:
            print(json.dumps({
                "file": args.file,
                "runxmd_version": __version__,
                "workflows": getattr(report, "records", {}),
                "all_ok": getattr(report, "all_ok", True),
                "failed_steps": getattr(report, "failed_steps", []),
                "cache": {"hits": getattr(report, "cache_hits", 0),
                          "misses": getattr(report, "cache_misses", 0)},
            }, indent=2, default=str))
        if report is not None:
            if report.check_failed:
                return 1
            if report.pure_refused:
                print(f"\n✗ pure: refused {len(report.pure_refused)} non-deterministic "
                      f"step(s): {', '.join('@' + p for p in report.pure_refused)}")
                return 2
            if args.strict and not report.all_ok:
                n = len(report.failed_steps)
                print(f"\n✗ strict: {n} step(s) failed")
                return 1
    elif args.cmd == "watch":
        flush = lambda *a: print(*a, flush=True)  # noqa: E731 — keep watch output live
        executor.watch(
            args.file,
            workflow_name=args.workflow,
            interval=args.interval,
            max_runs=args.max_runs,
            write_back=args.write_back,
            save_context=not args.no_save,
            add_provenance=not args.no_provenance,
            normalize=not args.raw,
            pure=args.pure,
            cache=args.cache,
            force=args.force,
            timeout=args.timeout,
            out=flush,
        )
    elif args.cmd == "agent":
        from . import agent
        agent.agent_run(
            args.file,
            replan=args.replan,
            autonomous=args.autonomous,
            model=args.model,
            max_tokens=args.max_tokens,
            dry_run=args.dry_run,
        )
    elif args.cmd == "parse":
        print(json.dumps(asdict(_load(args.file)), indent=2))
    elif args.cmd == "validate":
        return _validate(args.file)
    elif args.cmd == "verify":
        from . import provenance
        code, msg = provenance.verify(args.file, args.source)
        print(msg)
        return code
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
