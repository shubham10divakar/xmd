"""The headline guarantee: runxmd runs both `.md` and `.xmd` — identically.

`.xmd` is not a separate format; it is the same Markdown grammar with a name that
signals "this one is runnable". The runtime parses *content*, never the filename.
These tests pin that contract down so it cannot silently regress.
"""
from __future__ import annotations

import pytest

from runxmd import executor
from runxmd.parser import parse

# .md (plain Markdown) and .xmd (the runnable-by-convention label) must behave the
# same. .txt is included to prove the runtime truly ignores the extension.
EXTENSIONS = [".md", ".xmd", ".txt"]


@pytest.mark.parametrize("ext", EXTENSIONS)
def test_run_is_extension_agnostic(write_doc, ext):
    path = write_doc(f"doc{ext}")
    lines: list[str] = []
    executor.run(str(path), write_back=False, out=lines.append)
    output = "\n".join(lines)
    assert "hello world" in output            # substitution happened
    assert "@print ✓" in output               # the step ran and succeeded


def test_md_and_xmd_produce_byte_identical_output(write_doc):
    """The same content as a.md and b.xmd must yield the exact same run output."""
    md = write_doc("a.md")
    xmd = write_doc("b.xmd")

    md_lines: list[str] = []
    xmd_lines: list[str] = []
    executor.run(str(md), write_back=False, out=md_lines.append)
    executor.run(str(xmd), write_back=False, out=xmd_lines.append)

    assert md_lines == xmd_lines


@pytest.mark.parametrize("ext", EXTENSIONS)
def test_write_back_works_for_any_extension(write_doc, ext):
    path = write_doc(f"doc{ext}")
    executor.run(str(path), write_back=True, out=lambda *a: None)

    reparsed = parse(path.read_text(encoding="utf-8"))
    memory = reparsed.section("memory").memory
    assert memory["runtime.status"] == "done"   # @on_done hook persisted to disk


@pytest.mark.parametrize("ext", EXTENSIONS)
def test_plain_markdown_with_no_workflow_is_harmless(write_doc, ext):
    """A normal prose .md/.xmd (no @workflow) runs cleanly and changes nothing."""
    prose = "# Just Notes\n\nThis is an ordinary Markdown file with no workflow.\n"
    path = write_doc(f"notes{ext}", prose)

    lines: list[str] = []
    executor.run(str(path), write_back=True, out=lines.append)

    assert any("No workflow to run." in ln for ln in lines)
    assert path.read_text(encoding="utf-8") == prose   # file untouched
