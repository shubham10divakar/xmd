"""B10 — per-step timeout, stdin, if: guards, --json trace, stderr in render."""
from __future__ import annotations

import json
import shutil

import pytest

from runxmd import executor
from runxmd.cli import main

pytestmark = pytest.mark.skipif(
    shutil.which("python") is None, reason="'python' not on PATH"
)


def _write(tmp_path, body, name="d.md"):
    p = tmp_path / name
    p.write_text("# D\n\n" + body, encoding="utf-8")
    return p


def _render(tmp_path, name="d_render.md"):
    return (tmp_path / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# timeout:
# ---------------------------------------------------------------------------

def test_step_timeout_param_kills_runaway(tmp_path):
    src = _write(tmp_path,
                 "- @python\n  timeout: 0.3\n  run: |\n    import time\n    time.sleep(3)\n")
    doc = executor.run(str(src), out=lambda *a: None)
    r = doc.report.records[""][0]
    assert r["ok"] is False and r["code"] == 124
    assert "timed out" in r["error"]


def test_global_timeout_applies_when_step_has_none(tmp_path):
    src = _write(tmp_path,
                 "- @python\n  run: |\n    import time\n    time.sleep(3)\n")
    doc = executor.run(str(src), timeout=0.3, out=lambda *a: None)
    assert doc.report.records[""][0]["code"] == 124


def test_step_timeout_overrides_global(tmp_path):
    src = _write(tmp_path,
                 "- @python\n  timeout: 5\n  run: |\n    print('quick')\n")
    doc = executor.run(str(src), timeout=0.1, out=lambda *a: None)
    assert doc.report.records[""][0]["ok"] is True


# ---------------------------------------------------------------------------
# stdin:
# ---------------------------------------------------------------------------

def test_stdin_is_fed_to_the_step(tmp_path):
    src = _write(tmp_path,
                 "- @python\n  stdin: \"hello\"\n  run: |\n"
                 "    import sys\n    print(sys.stdin.read().upper())\n")
    executor.run(str(src), out=lambda *a: None)
    assert "HELLO" in _render(tmp_path)


# ---------------------------------------------------------------------------
# if:
# ---------------------------------------------------------------------------

def _steps(doc):
    return list(doc.report.records.values())[0]


def test_if_false_skips_step(tmp_path):
    body = (
        "@memory\nrun_it: false\n\n"
        "@workflow main\n"
        "- @python\n  if: memory.run_it\n  run: |\n    print('SHOULD-NOT-APPEAR')\n"
    )
    src = _write(tmp_path, body)
    doc = executor.run(str(src), out=lambda *a: None)
    assert _steps(doc)[0]["skipped"] is True
    assert doc.report.all_ok is True
    assert not (tmp_path / "d_render.md").exists() or \
        "SHOULD-NOT-APPEAR" not in _render(tmp_path)


def test_if_true_runs_step(tmp_path):
    body = (
        "@memory\nrun_it: true\n\n"
        "@workflow main\n"
        "- @python\n  if: memory.run_it\n  run: |\n    print('RAN')\n"
    )
    src = _write(tmp_path, body)
    executor.run(str(src), out=lambda *a: None)
    assert "RAN" in _render(tmp_path)


def test_if_numeric_comparison(tmp_path):
    body = (
        "@memory\nn: 5\n\n"
        "@workflow main\n"
        "- @python\n  if: memory.n >= 3\n  run: |\n    print('BIG')\n"
        "- @python\n  if: memory.n < 3\n  run: |\n    print('SMALL')\n"
    )
    src = _write(tmp_path, body)
    executor.run(str(src), out=lambda *a: None)
    render = _render(tmp_path)
    assert "BIG" in render and "SMALL" not in render


def test_if_not_negation(tmp_path):
    body = (
        "@memory\ndisabled: false\n\n"
        "@workflow main\n"
        "- @python\n  if: not memory.disabled\n  run: |\n    print('ENABLED')\n"
    )
    src = _write(tmp_path, body)
    executor.run(str(src), out=lambda *a: None)
    assert "ENABLED" in _render(tmp_path)


# ---------------------------------------------------------------------------
# --json
# ---------------------------------------------------------------------------

def test_json_trace_is_valid_and_structured(tmp_path, capsys):
    src = _write(tmp_path, "- @python\n  run: |\n    print('hi')\n")
    rc = main(["run", str(src), "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data["workflows"][""][0]["plugin"] == "python"
    assert data["workflows"][""][0]["ok"] is True
    assert "duration_ms" in data["workflows"][""][0]


def test_json_suppresses_normal_output(tmp_path, capsys):
    src = _write(tmp_path, "- @python\n  run: |\n    print('hi')\n")
    main(["run", str(src), "--json"])
    out = capsys.readouterr().out
    assert out.lstrip().startswith("{")  # only JSON, no ▶ workflow chatter


# ---------------------------------------------------------------------------
# stderr shown alongside stdout on failure
# ---------------------------------------------------------------------------

def test_render_shows_stdout_and_stderr_on_failure(tmp_path):
    src = _write(tmp_path,
                 "- @python\n  run: |\n    print('PARTIAL-OUTPUT')\n"
                 "    raise SystemExit('BOOM')\n")
    executor.run(str(src), out=lambda *a: None)
    render = _render(tmp_path)
    assert "PARTIAL-OUTPUT" in render
    assert "BOOM" in render
