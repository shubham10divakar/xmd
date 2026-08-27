"""`runxmd validate` static checks (JOT plan C7).

The grammar is a bespoke line scanner, not YAML. validate must *reject*, not
silently misparse, the YAML-isms a user will reach for. See GRAMMAR.md.
"""
from __future__ import annotations

from runxmd.cli import main
from runxmd.lint import lint
from runxmd.parser import parse


def _lint(src: str):
    return lint(src, parse(src))


def _sev(src: str):
    return {sev for sev, _ in _lint(src)}


# ---------------------------------------------------------------------------
# YAML-isms → errors
# ---------------------------------------------------------------------------

def test_flow_collection_value_is_an_error():
    src = "@workflow w\n- @python\n  data: {a: 1, b: 2}\n  run: |\n    pass\n"
    msgs = [m for s, m in _lint(src) if s == "error"]
    assert any("flow collection" in m for m in msgs)


def test_folded_scalar_is_an_error():
    src = "@workflow w\n- @python\n  run: >\n    folded\n"
    assert any("folded scalar" in m for s, m in _lint(src) if s == "error")


def test_tab_indentation_is_an_error():
    src = "@workflow w\n- @python\n\trun: |\n\t  pass\n"
    assert any("tab in indentation" in m for s, m in _lint(src) if s == "error")


def test_anchor_syntax_is_an_error():
    src = "@workflow w\n- @python\n  run: |\n    x\n  cfg: &base value\n"
    assert any("anchor" in m for s, m in _lint(src) if s == "error")


def test_unknown_plugin_is_an_error():
    src = "@workflow w\n- @pythonn\n  run: |\n    pass\n"
    assert any("unknown plugin @pythonn" in m for s, m in _lint(src) if s == "error")


def test_unrecognised_on_done_hook_is_an_error():
    src = "@workflow w\n- @print\n  text: hi\n\n@on_done\nrënder\n"
    assert any("unrecognized hook" in m for s, m in _lint(src) if s == "error")


# ---------------------------------------------------------------------------
# tolerated-but-suspicious → warnings
# ---------------------------------------------------------------------------

def test_unknown_section_is_a_warning():
    src = "@notes\nsome free text\n\n@workflow w\n- @print\n  text: hi\n"
    sevs = _sev(src)
    assert "warn" in sevs and "error" not in sevs


def test_paramless_code_step_is_a_warning():
    src = "@workflow w\n- @python\n"
    assert any("no params" in m for s, m in _lint(src) if s == "warn")


def test_print_without_params_is_not_flagged():
    src = "@workflow w\n- @print\n"
    assert not any("no params" in m for s, m in _lint(src))


def test_clean_document_has_no_problems():
    src = (
        "# Fine\n\n@workflow w\n- @python\n  run: |\n    print(1)\n"
        "- @print\n  text: \"ok\"\n\n@on_done\nrender\nset: memory.runtime.x = 1\n"
    )
    assert _lint(src) == []


# ---------------------------------------------------------------------------
# validate CLI exit codes
# ---------------------------------------------------------------------------

def test_validate_exits_1_on_error(tmp_path, capsys):
    p = tmp_path / "bad.md"
    p.write_text("@workflow w\n- @nope\n  run: |\n    x\n", encoding="utf-8")
    rc = main(["validate", str(p)])
    assert rc == 1
    assert "unknown plugin" in capsys.readouterr().out


def test_validate_exits_0_with_warnings_only(tmp_path, capsys):
    p = tmp_path / "warn.md"
    p.write_text("@weird\nhi\n\n@workflow w\n- @print\n  text: hi\n", encoding="utf-8")
    rc = main(["validate", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "warning" in out


def test_validate_still_lists_sections(tmp_path, capsys):
    p = tmp_path / "ok.md"
    p.write_text("# T\n\n@workflow main\n- @print\n  text: hi\n", encoding="utf-8")
    rc = main(["validate", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "@workflow main" in out
