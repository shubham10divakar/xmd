"""Opt-in `session:` — shared scope across steps (JOT plan B3).

Default is per-step isolation (a runtime property, not a bug). `session: name`
is the documented opt-out: steps sharing a name see each other's definitions.
Implemented by re-execution + stdout prefix-subtraction, so it works for every
language with no REPL protocol.
"""
from __future__ import annotations

import shutil

import pytest

from runxmd import executor

pytestmark = pytest.mark.skipif(
    shutil.which("python") is None, reason="'python' not on PATH"
)


def _run(tmp_path, body: str):
    src = tmp_path / "s.md"
    src.write_text("# S\n\n" + body, encoding="utf-8")
    lines: list[str] = []
    doc = executor.run(str(src), out=lines.append)
    render = (tmp_path / "s_render.md").read_text(encoding="utf-8")
    return doc, "\n".join(lines), render


SESSION_DOC = """- @python
  session: main
  run: |
    x = 41

- @python
  session: main
  run: |
    print("x is", x + 1)
"""

ISOLATED_DOC = """- @python
  run: |
    x = 41

- @python
  run: |
    print("x is", x + 1)
"""


def test_session_shares_definitions(tmp_path):
    doc, log, render = _run(tmp_path, SESSION_DOC)
    assert doc.report.all_ok
    assert "x is 42" in render


def test_default_is_isolated(tmp_path):
    doc, log, render = _run(tmp_path, ISOLATED_DOC)
    # second step can't see x → NameError, run not ok
    assert doc.report.all_ok is False
    assert "NameError" in log


def test_session_step_output_excludes_earlier_step_output(tmp_path):
    body = (
        "- @python\n  session: a\n  run: |\n    print(\"FIRST-STEP-LINE\")\n\n"
        "- @python\n  session: a\n  run: |\n    print(\"SECOND-STEP-LINE\")\n"
    )
    doc, log, render = _run(tmp_path, body)
    # the render replaces each step with its own output; step 2's block must
    # not re-print step 1's line
    after = render.split("FIRST-STEP-LINE", 1)[1]
    assert after.count("FIRST-STEP-LINE") == 0
    assert "SECOND-STEP-LINE" in render


def test_distinct_session_names_do_not_share(tmp_path):
    body = (
        "- @python\n  session: one\n  run: |\n    y = 5\n\n"
        "- @python\n  session: two\n  run: |\n    print(y)\n"
    )
    doc, log, render = _run(tmp_path, body)
    assert doc.report.all_ok is False
    assert "NameError" in log


def test_session_param_not_passed_to_plugin(tmp_path):
    # @print echoes its params-free text; a stray session kwarg must not break it
    body = "- @print\n  session: x\n  text: \"hello\"\n"
    doc, log, render = _run(tmp_path, body)
    assert doc.report.all_ok
    assert "hello" in render


def test_three_step_session_accumulates(tmp_path):
    body = (
        "- @python\n  session: m\n  run: |\n    a = 1\n\n"
        "- @python\n  session: m\n  run: |\n    b = a + 1\n\n"
        "- @python\n  session: m\n  run: |\n    print(a, b, a + b)\n"
    )
    doc, log, render = _run(tmp_path, body)
    assert doc.report.all_ok
    assert "1 2 3" in render
