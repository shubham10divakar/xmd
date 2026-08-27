"""`runxmd run --strict` and `runxmd run --check` (JOT plan A2).

--strict : a failed step propagates a non-zero exit code (usable as a CI gate).
--check  : compare a fresh render against the committed one; exit 1 on drift.
           Nothing is written.

Portable failure: an unknown plugin (`- @nope`) always fails, no interpreter
needed.
"""
from __future__ import annotations

import pytest

from runxmd import executor
from runxmd.cli import main

OK_DOC = """# Strict OK

- @print
  text: "all good"
"""

FAIL_DOC = """# Strict Fail

- @print
  text: "first ok"

- @nope
  run: whatever
"""


# ---------------------------------------------------------------------------
# --strict
# ---------------------------------------------------------------------------

def test_run_without_strict_exits_zero_on_failure(write_doc, capsys):
    path = write_doc("f.md", FAIL_DOC)
    assert main(["run", str(path)]) == 0  # failure recorded, run continues


def test_run_strict_exits_nonzero_on_failure(write_doc, capsys):
    path = write_doc("f.md", FAIL_DOC)
    rc = main(["run", str(path), "--strict"])
    assert rc == 1
    assert "strict" in capsys.readouterr().out.lower()


def test_run_strict_exits_zero_when_all_pass(write_doc, capsys):
    path = write_doc("ok.md", OK_DOC)
    assert main(["run", str(path), "--strict"]) == 0


def test_report_lists_failed_steps(write_doc):
    path = write_doc("f.md", FAIL_DOC)
    doc = executor.run(str(path), out=lambda *a: None)
    assert doc.report.all_ok is False
    assert doc.report.failed_steps == [("", 2, "nope")]


def test_step_records_carry_exit_code(write_doc):
    path = write_doc("f.md", FAIL_DOC)
    _, records = executor.run_steps(
        __import__("runxmd.parser", fromlist=["parse"]).parse(FAIL_DOC).workflows()[0].steps,
        {}, {}, lambda *a: None,
    )
    assert records[0]["code"] == 0
    assert records[1]["code"] == 127


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------

def test_check_passes_when_render_matches(write_doc, capsys):
    path = write_doc("d.md", OK_DOC)
    main(["run", str(path)])                     # create d_render.md
    capsys.readouterr()
    rc = main(["run", str(path), "--check"])
    assert rc == 0
    assert "up to date" in capsys.readouterr().out


def test_check_fails_when_source_changed(write_doc, capsys):
    path = write_doc("d.md", OK_DOC)
    main(["run", str(path)])
    capsys.readouterr()

    path.write_text(OK_DOC.replace("all good", "CHANGED"), encoding="utf-8")
    rc = main(["run", str(path), "--check"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "stale" in out.lower()


def test_check_fails_when_render_missing(write_doc, capsys):
    path = write_doc("d.md", OK_DOC)
    rc = main(["run", str(path), "--check"])
    assert rc == 1
    assert "does not exist" in capsys.readouterr().out


def test_check_writes_nothing(write_doc):
    path = write_doc("d.md", OK_DOC)
    main(["run", str(path)])
    render = path.parent / "d_render.md"
    before = render.read_text(encoding="utf-8")

    path.write_text(OK_DOC.replace("all good", "CHANGED"), encoding="utf-8")
    main(["run", str(path), "--check"])
    assert render.read_text(encoding="utf-8") == before  # untouched


def test_check_ignores_provenance_timestamp(write_doc, monkeypatch):
    """Two runs seconds apart differ only in generated_utc — --check must
    still say up to date."""
    path = write_doc("d.md", OK_DOC)
    main(["run", str(path)])

    # Force a different timestamp on the next provenance header.
    import runxmd.provenance as prov
    monkeypatch.setattr(prov, "_now_iso", lambda: "2099-01-01T00:00:00Z")

    doc = executor.run(str(path), check=True, out=lambda *a: None)
    assert doc.report.check_failed is False
