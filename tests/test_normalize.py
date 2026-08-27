"""Output normalization (JOT plan A4).

Renders must diff across machines: absolute paths, home dir, hostname, and
Windows separators in step output get rewritten to portable forms. `--raw`
(executor: normalize=False) turns it off. A step's `redact:` param blanks
volatile substrings the generic rules can't know about.
"""
from __future__ import annotations

import os
import socket

from runxmd import executor
from runxmd.normalize import normalize_output


# ---------------------------------------------------------------------------
# Unit — the individual rules
# ---------------------------------------------------------------------------

def test_backslash_path_token_becomes_forward_slash():
    assert normalize_output("see scripts\\sub\\basic.py here") == \
        "see scripts/sub/basic.py here"


def test_escaped_string_without_extension_is_left_alone():
    # 'a\nb' must not be mangled into 'a/nb'
    assert normalize_output("value 'a\\nb' printed") == "value 'a\\nb' printed"


def test_absolute_path_under_base_dir_becomes_relative(tmp_path):
    p = str(tmp_path / "scripts" / "run.py")
    out = normalize_output(f"found {p}", base_dir=str(tmp_path))
    assert out == "found scripts/run.py"


def test_home_dir_becomes_tilde():
    home = os.path.expanduser("~")
    if home == "~":
        return
    out = normalize_output(f"cache at {home}/x/y.txt")
    assert out == "cache at ~/x/y.txt"


def test_hostname_is_masked():
    host = socket.gethostname()
    if len(host) <= 2:
        return
    assert "HOST" in normalize_output(f"running on {host} now")


def test_redact_literal():
    assert normalize_output("token=abc123 done", redact="abc123") == \
        "token=[redacted] done"


def test_redact_regex():
    out = normalize_output("id 5f3a-9c21 end", redact="/[0-9a-f]{4}-[0-9a-f]{4}/")
    assert out == "id [redacted] end"


def test_redact_multiline_param():
    out = normalize_output("a SECRET b TOKEN c", redact="SECRET\nTOKEN")
    assert out == "a [redacted] b [redacted] c"


def test_non_string_passes_through():
    assert normalize_output(None) is None
    assert normalize_output("") == ""


# ---------------------------------------------------------------------------
# Integration — through executor.run, using @print (no interpreter needed)
# ---------------------------------------------------------------------------

def _doc(text: str) -> str:
    return f"# Norm\n\n- @print\n  text: \"{text}\"\n"


def test_run_normalizes_render_output(tmp_path):
    src = tmp_path / "n.md"
    abs_path = str(tmp_path / "data" / "out.csv")
    src.write_text(_doc(f"wrote {abs_path}"), encoding="utf-8")

    executor.run(str(src), out=lambda *a: None)
    render = (tmp_path / "n_render.md").read_text(encoding="utf-8")
    assert "data/out.csv" in render
    assert str(tmp_path) not in render


def test_raw_mode_keeps_output_verbatim(tmp_path):
    src = tmp_path / "n.md"
    abs_path = str(tmp_path / "data" / "out.csv")
    src.write_text(_doc(f"wrote {abs_path}"), encoding="utf-8")

    executor.run(str(src), normalize=False, out=lambda *a: None)
    render = (tmp_path / "n_render.md").read_text(encoding="utf-8")
    # the raw absolute path is still there, unmodified
    assert abs_path in render


def test_redact_param_applied_in_render(tmp_path):
    src = tmp_path / "n.md"
    src.write_text(
        "# Norm\n\n- @print\n  text: \"api_key=SUPERSECRET ok\"\n  redact: SUPERSECRET\n",
        encoding="utf-8",
    )
    executor.run(str(src), out=lambda *a: None)
    render = (tmp_path / "n_render.md").read_text(encoding="utf-8")
    assert "SUPERSECRET" not in render
    assert "[redacted]" in render
