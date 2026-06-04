"""Tests for external script plugins (@python_script, @node_script, etc.).

Each _script plugin takes a `path:` param pointing at an existing file and
runs it with the corresponding interpreter — no inline code needed.
"""
from __future__ import annotations

import shutil

import pytest

from runxmd import executor
from runxmd.plugins import get as get_plugin


# ---------------------------------------------------------------------------
# @python_script — always available since runxmd itself is Python
# ---------------------------------------------------------------------------

def test_python_script_runs_file(tmp_path):
    script = tmp_path / "hello.py"
    script.write_text('print("hello from script")\n', encoding="utf-8")

    doc_content = (
        "# Script Test\n\n"
        "- @python_script\n"
        f"  path: {str(script).replace(chr(92), '/')}\n"
    )
    doc = tmp_path / "run.md"
    doc.write_text(doc_content, encoding="utf-8")

    lines: list[str] = []
    executor.run(str(doc), write_back=False, out=lines.append)
    output = "\n".join(lines)

    assert "hello from script" in output
    assert "@python_script ✓" in output


def test_python_script_passes_args(tmp_path):
    script = tmp_path / "greet.py"
    script.write_text(
        "import sys\nprint('hello', sys.argv[1])\n", encoding="utf-8"
    )

    doc_content = (
        "# Args Test\n\n"
        "- @python_script\n"
        f"  path: {str(script).replace(chr(92), '/')}\n"
        "  args: world\n"
    )
    doc = tmp_path / "run.md"
    doc.write_text(doc_content, encoding="utf-8")

    lines: list[str] = []
    executor.run(str(doc), write_back=False, out=lines.append)
    output = "\n".join(lines)

    assert "hello world" in output


def test_python_script_missing_file_fails_gracefully(tmp_path):
    doc_content = (
        "# Missing\n\n"
        "- @python_script\n"
        "  path: nonexistent/script.py\n"
    )
    doc = tmp_path / "run.md"
    doc.write_text(doc_content, encoding="utf-8")

    lines: list[str] = []
    executor.run(str(doc), write_back=False, out=lines.append)
    output = "\n".join(lines)

    assert "@python_script ✗" in output
    assert "not found" in output


def test_python_script_missing_path_param_fails_gracefully(tmp_path):
    doc_content = (
        "# No path\n\n"
        "- @python_script\n"
    )
    doc = tmp_path / "run.md"
    doc.write_text(doc_content, encoding="utf-8")

    lines: list[str] = []
    executor.run(str(doc), write_back=False, out=lines.append)
    output = "\n".join(lines)

    assert "@python_script ✗" in output


# ---------------------------------------------------------------------------
# All _script plugins are registered
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("plugin_name", [
    "python_script", "node_script", "typescript_script", "ruby_script",
    "bash_script", "go_script", "r_script", "php_script",
    "perl_script", "powershell_script",
])
def test_script_plugin_is_registered(plugin_name):
    assert get_plugin(plugin_name) is not None, f"@{plugin_name} not registered"


# ---------------------------------------------------------------------------
# Missing interpreter fails gracefully (not a crash)
# ---------------------------------------------------------------------------

def test_script_plugin_missing_interpreter_fails_gracefully(tmp_path, monkeypatch):
    """If the interpreter isn't on PATH, the step reports ✗ and continues."""
    script = tmp_path / "hello.py"
    script.write_text('print("hi")\n', encoding="utf-8")

    doc_content = (
        "# Interpreter missing\n\n"
        "- @python_script\n"
        f"  path: {str(script).replace(chr(92), '/')}\n"
    )
    doc = tmp_path / "run.md"
    doc.write_text(doc_content, encoding="utf-8")

    # Simulate interpreter not found
    monkeypatch.setattr(shutil, "which", lambda _: None)

    lines: list[str] = []
    executor.run(str(doc), write_back=False, out=lines.append)
    output = "\n".join(lines)

    assert "@python_script ✗" in output
    assert "not found" in output
