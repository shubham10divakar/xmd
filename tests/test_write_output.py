"""Tests for @on_done write / write(name) — Option A output document.

After a run, `write` in @on_done produces a new .md file that is a copy of
the original with a `result:` field injected into each step that ran.

Behaviour matrix:
  - `write`          → {stem}_output{ext} next to the source file
  - `write(name.md)` → name.md (relative to cwd, or absolute)
  - no write hook    → no output file produced; original is unchanged
  - failed step      → result: contains the error text, not empty
  - re-run           → stale result: is replaced, not duplicated
"""
from __future__ import annotations

import pathlib
import shutil

import pytest

from runxmd import executor
from runxmd.parser import parse

pytestmark = pytest.mark.skipif(
    shutil.which("python") is None,
    reason="'python' not found on PATH — @python steps cannot run",
)

# ---------------------------------------------------------------------------
# Shared document builder
# ---------------------------------------------------------------------------

def _doc(on_done_lines: str = "", extra_steps: str = "") -> str:
    return (
        "# Output Test\n\n"
        "@memory\n"
        'runtime.status: "pending"\n\n'
        "@workflow main\n"
        "- @python\n"
        "  run: |\n"
        '    print("hello from python")\n'
        "    x = 1 + 2\n"
        '    print("result:", x)\n'
        + extra_steps
        + "\n@on_done\n"
        + 'set: memory.runtime.status = "done"\n'
        + on_done_lines
    )


# ---------------------------------------------------------------------------
# write  →  {stem}_output{ext}
# ---------------------------------------------------------------------------

def test_write_creates_output_file(tmp_path):
    src = tmp_path / "sample.md"
    src.write_text(_doc("write\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    out = tmp_path / "sample_output.md"
    assert out.exists(), "expected sample_output.md to be created"


def test_write_injects_result_field(tmp_path):
    src = tmp_path / "sample.md"
    src.write_text(_doc("write\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    out_doc = parse((tmp_path / "sample_output.md").read_text(encoding="utf-8"))
    step = out_doc.workflows()[0].steps[0]
    assert "result" in step.params
    assert "hello from python" in step.params["result"]
    assert "result: 3" in step.params["result"]


# ---------------------------------------------------------------------------
# write(custom.md)  →  named file
# ---------------------------------------------------------------------------

def test_write_custom_name(tmp_path):
    custom = tmp_path / "report.md"
    src = tmp_path / "sample.md"
    src.write_text(_doc(f"write({custom})\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    assert custom.exists()
    out_doc = parse(custom.read_text(encoding="utf-8"))
    assert "result" in out_doc.workflows()[0].steps[0].params


# ---------------------------------------------------------------------------
# No write hook  →  default results file is produced; original untouched
# ---------------------------------------------------------------------------

def test_no_hook_produces_default_render_file(tmp_path):
    src = tmp_path / "sample.md"
    original = _doc("")  # no output hook
    src.write_text(original, encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    # default: _render.md is created automatically
    assert (tmp_path / "sample_render.md").exists()
    # _results.md and _output.md are NOT created without explicit hooks
    assert not (tmp_path / "sample_results.md").exists()
    assert not (tmp_path / "sample_output.md").exists()
    # original file is unchanged
    assert src.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Failed step  →  result: contains error text
# ---------------------------------------------------------------------------

def test_failed_step_result_contains_error(tmp_path):
    failing_step = (
        "- @python\n"
        "  run: |\n"
        "    raise ValueError('deliberate failure')\n"
    )
    src = tmp_path / "sample.md"
    src.write_text(_doc("write\n", extra_steps=failing_step), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    out_doc = parse((tmp_path / "sample_output.md").read_text(encoding="utf-8"))
    steps = out_doc.workflows()[0].steps
    # step 2 is the failing one
    assert "result" in steps[1].params
    assert "deliberate failure" in steps[1].params["result"]


# ---------------------------------------------------------------------------
# Re-run  →  stale result: is replaced, not duplicated
# ---------------------------------------------------------------------------

def test_rerun_replaces_stale_result(tmp_path):
    src = tmp_path / "sample.md"
    src.write_text(_doc("write\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)
    executor.run(str(src), write_back=False, out=lambda *a: None)

    out = tmp_path / "sample_output.md"
    out_doc = parse(out.read_text(encoding="utf-8"))
    result_text = out_doc.workflows()[0].steps[0].params["result"]
    # "hello from python" should appear exactly once, not twice
    assert result_text.count("hello from python") == 1


# ---------------------------------------------------------------------------
# Output file is itself valid runxmd (can be re-parsed cleanly)
# ---------------------------------------------------------------------------

def test_output_file_is_valid_runxmd(tmp_path):
    src = tmp_path / "sample.md"
    src.write_text(_doc("write\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    out = tmp_path / "sample_output.md"
    doc = parse(out.read_text(encoding="utf-8"))
    assert len(doc.workflows()) == 1
    assert doc.workflows()[0].steps[0].plugin == "python"


# ---------------------------------------------------------------------------
# results  →  {stem}_results{ext}  — no @sections, no code, just output text
# ---------------------------------------------------------------------------

def test_results_creates_results_file(tmp_path):
    src = tmp_path / "sample.md"
    src.write_text(_doc("results\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    assert (tmp_path / "sample_results.md").exists()


def test_results_contains_only_output_text(tmp_path):
    src = tmp_path / "sample.md"
    src.write_text(_doc("results\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    content = (tmp_path / "sample_results.md").read_text(encoding="utf-8")
    assert "hello from python" in content
    assert "result: 3" in content
    # no xmd sections
    assert "@workflow" not in content
    assert "@memory" not in content
    assert "@goal" not in content
    assert "@on_done" not in content
    # no code
    assert "print(" not in content


def test_results_custom_name(tmp_path):
    custom = tmp_path / "report.md"
    src = tmp_path / "sample.md"
    src.write_text(_doc(f"results({custom})\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    assert custom.exists()
    content = custom.read_text(encoding="utf-8")
    assert "hello from python" in content


def test_write_and_results_both_produced(tmp_path):
    """write and results can coexist in @on_done — each produces its own file."""
    src = tmp_path / "sample.md"
    src.write_text(_doc("write\nresults\n"), encoding="utf-8")

    executor.run(str(src), write_back=False, out=lambda *a: None)

    output = tmp_path / "sample_output.md"
    results = tmp_path / "sample_results.md"
    assert output.exists()
    assert results.exists()
    # output has code, results does not
    assert "print(" in output.read_text(encoding="utf-8")
    assert "print(" not in results.read_text(encoding="utf-8")
