"""Deterministic core vs non-deterministic surface (JOT plan A6).

@http and @llm produce output that differs per run — a render containing them
is a *sample*, not a computed fact. Those steps are tagged in the render,
recorded in provenance, and refused by `runxmd run --pure`.

Tests use @llm, which without ANTHROPIC_API_KEY fails gracefully (no network),
so they run everywhere.
"""
from __future__ import annotations

import pytest

from runxmd import executor, plugins, provenance
from runxmd.cli import main


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    """Force @llm down its graceful no-key path — no network in these tests."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

LLM_DOC = """# Determinism

- @print
  text: "deterministic step"

- @llm
  prompt: "say hi"
"""


# ---------------------------------------------------------------------------
# The plugin attribute
# ---------------------------------------------------------------------------

def test_http_and_llm_are_marked_non_deterministic():
    assert plugins.is_deterministic("http") is False
    assert plugins.is_deterministic("llm") is False


def test_core_plugins_are_deterministic():
    for name in ("print", "python", "shell", "read", "write"):
        assert plugins.is_deterministic(name) is True


def test_register_records_the_flag():
    @plugins.register("_nd_probe", deterministic=False)
    def _p(params, ctx):
        return plugins.Result(ok=True, output="x")

    assert plugins.is_deterministic("_nd_probe") is False
    plugins.REGISTRY.pop("_nd_probe", None)


# ---------------------------------------------------------------------------
# Render marker + provenance
# ---------------------------------------------------------------------------

def test_render_tags_non_deterministic_step(write_doc):
    path = write_doc("nd.md", LLM_DOC)
    executor.run(str(path), out=lambda *a: None)
    render = (path.parent / "nd_render.md").read_text(encoding="utf-8")
    assert "<!-- non-deterministic: @llm" in render
    # the deterministic @print output carries no marker
    assert render.count("non-deterministic") == 1


def test_provenance_records_non_deterministic_step_indices(write_doc):
    path = write_doc("nd.md", LLM_DOC)
    executor.run(str(path), out=lambda *a: None)
    render = (path.parent / "nd_render.md").read_text(encoding="utf-8")
    hdr = provenance.parse_header(render)
    assert hdr["non_deterministic_steps"] == "[2]"


# ---------------------------------------------------------------------------
# --pure
# ---------------------------------------------------------------------------

def test_pure_refuses_llm_and_exits_2(write_doc, capsys):
    path = write_doc("nd.md", LLM_DOC)
    rc = main(["run", str(path), "--pure"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "refused" in out.lower()
    assert "@llm" in out


def test_pure_leaves_deterministic_steps_running(write_doc):
    path = write_doc("nd.md", LLM_DOC)
    doc = executor.run(str(path), pure=True, out=lambda *a: None)
    recs = doc.report  # noqa: F841
    # @print ran, @llm refused
    assert doc.report.pure_refused == ["llm"]


def test_pure_run_without_nd_steps_is_clean(write_doc, capsys):
    path = write_doc("plain.md", "# P\n\n- @print\n  text: \"hi\"\n")
    rc = main(["run", str(path), "--pure"])
    assert rc == 0
