"""Scenario 1 — guardrail: check if any file exists in a specific folder.

The guardrail is an ordinary .md file with a @workflow that uses @python to
inspect a folder and prints GUARDRAIL_PASS or GUARDRAIL_FAIL to stdout.
The test matrix covers the three meaningful states of the folder:

  1. Folder exists and contains files  → GUARDRAIL_PASS
  2. Folder exists but is empty        → GUARDRAIL_FAIL
  3. Folder does not exist             → GUARDRAIL_FAIL

A fourth test confirms the .xmd extension produces byte-identical output
(the extension-agnostic guarantee applied to a guardrail document).
"""
from __future__ import annotations

import pathlib
import shutil

import pytest

from runxmd import executor
from runxmd.parser import parse

# Skip the whole module if `python` is not on PATH — the @python plugin
# delegates to the `python` executable and will fail clearly if it is absent.
pytestmark = pytest.mark.skipif(
    shutil.which("python") is None,
    reason="'python' not found on PATH — @python steps cannot run",
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_guardrail_doc(folder: pathlib.Path) -> str:
    """Build a self-contained guardrail .md with the folder path baked in.

    Using forward slashes keeps the embedded path safe across platforms
    (pathlib.Path accepts them on Windows too).
    """
    folder_str = str(folder).replace("\\", "/")
    return (
        "# Guardrail: Check Files in Folder\n\n"
        "@goal\n"
        "Verify the target folder contains at least one file.\n\n"
        "@memory\n"
        f'folder: "{folder_str}"\n'
        'runtime.check_passed: "pending"\n\n'
        "@workflow check_folder\n"
        "- @python\n"
        "  run: |\n"
        "    import pathlib\n"
        f'    folder = pathlib.Path("{folder_str}")\n'
        "    if not folder.exists():\n"
        '        print("GUARDRAIL_FAIL: folder does not exist")\n'
        "    else:\n"
        "        files = [f for f in folder.rglob('*') if f.is_file()]\n"
        "        count = len(files)\n"
        "        if count > 0:\n"
        '            print("GUARDRAIL_PASS: " + str(count) + " file(s) found")\n'
        "            for f in sorted(files):\n"
        '                print("  - " + f.name)\n'
        "        else:\n"
        '            print("GUARDRAIL_FAIL: folder exists but contains no files")\n\n'
        "@on_done\n"
        'set: memory.runtime.check_passed = "true"\n'
    )


def _run(doc_path: pathlib.Path, write_back: bool = False) -> str:
    lines: list[str] = []
    executor.run(str(doc_path), write_back=write_back, out=lines.append)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scenario 1a — files exist: guardrail should PASS
# ---------------------------------------------------------------------------

def test_guardrail_passes_when_files_exist(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("# source\n", encoding="utf-8")
    (src / "utils.py").write_text("# helpers\n", encoding="utf-8")

    doc = tmp_path / "guardrail.md"
    doc.write_text(_make_guardrail_doc(src), encoding="utf-8")

    output = _run(doc)

    assert "GUARDRAIL_PASS" in output
    assert "GUARDRAIL_FAIL" not in output
    assert "2 file(s) found" in output


# ---------------------------------------------------------------------------
# Scenario 1b — folder exists but is empty: guardrail should FAIL
# ---------------------------------------------------------------------------

def test_guardrail_fails_when_folder_is_empty(tmp_path):
    src = tmp_path / "src"
    src.mkdir()  # exists, but empty

    doc = tmp_path / "guardrail.md"
    doc.write_text(_make_guardrail_doc(src), encoding="utf-8")

    output = _run(doc)

    assert "GUARDRAIL_FAIL" in output
    assert "GUARDRAIL_PASS" not in output


# ---------------------------------------------------------------------------
# Scenario 1c — folder does not exist at all: guardrail should FAIL
# ---------------------------------------------------------------------------

def test_guardrail_fails_when_folder_missing(tmp_path):
    src = tmp_path / "src"  # intentionally not created

    doc = tmp_path / "guardrail.md"
    doc.write_text(_make_guardrail_doc(src), encoding="utf-8")

    output = _run(doc)

    assert "GUARDRAIL_FAIL" in output
    assert "GUARDRAIL_PASS" not in output


# ---------------------------------------------------------------------------
# Scenario 1d — .xmd extension is identical to .md (extension-agnostic guarantee)
# ---------------------------------------------------------------------------

def test_guardrail_xmd_and_md_produce_identical_output(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("# app\n", encoding="utf-8")

    content = _make_guardrail_doc(src)
    md_path = tmp_path / "guardrail.md"
    xmd_path = tmp_path / "guardrail.xmd"
    md_path.write_text(content, encoding="utf-8")
    xmd_path.write_text(content, encoding="utf-8")

    md_lines: list[str] = []
    xmd_lines: list[str] = []
    executor.run(str(md_path), write_back=False, out=md_lines.append)
    executor.run(str(xmd_path), write_back=False, out=xmd_lines.append)

    # auto-results message includes the output filename which differs by extension;
    # strip it — the guarantee is about workflow execution output, not file paths.
    strip = lambda lines: [l for l in lines if "written" not in l]
    assert strip(md_lines) == strip(xmd_lines)


# ---------------------------------------------------------------------------
# Write-back: runtime.check_passed is persisted to the file after the run
# ---------------------------------------------------------------------------

def test_guardrail_writes_back_runtime_memory(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    doc = tmp_path / "guardrail.md"
    doc.write_text(_make_guardrail_doc(src), encoding="utf-8")

    _run(doc, write_back=True)

    memory = parse(doc.read_text(encoding="utf-8")).section("memory").memory
    assert memory["runtime.check_passed"] == "true"
