"""Tests for @context_memory Phase 2 — the rolling summary.

An `@on_done: summarize` directive regenerates the section's prose summary FROM
the raw jsonl log (never from the prior summary — the anti-drift rule), and only
that summary is injected into steps via {{ context }}. The LLM call is behind
`executor._llm_complete`, monkeypatched here so the whole layer is tested
deterministically with no API key.
"""
from __future__ import annotations

import pytest

from runxmd import executor
from runxmd.parser import parse


def _silent(*_a):
    return None


def _section(path):
    return parse(path.read_text(encoding="utf-8")).section("context_memory")


@pytest.fixture
def fixed_llm(monkeypatch):
    """Make the summarizer return a fixed string; record calls."""
    calls = []

    def fake(prompt, model=None, max_tokens=512):
        calls.append({"prompt": prompt, "model": model, "max_tokens": max_tokens})
        return True, "REMEMBERED-STATE"

    monkeypatch.setattr(executor, "_llm_complete", fake)
    return calls


def _doc(step_text='"did the thing"', summary="", on_done="summarize"):
    head = "@context_memory\n"
    if summary:
        head += summary + "\n"
    head += "\n```jsonl\n```\n"
    return (
        head
        + "\n@workflow main\n"
        + "- @print\n"
        + f"  text: {step_text}\n"
        + (f"\n@on_done\n{on_done}\n" if on_done else "")
    )


# ---------------------------------------------------------------------------
# Core: summarize sets the prose summary
# ---------------------------------------------------------------------------

def test_summarize_sets_summary(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc())
    executor.run(str(src), out=_silent)
    assert _section(src).summary == "REMEMBERED-STATE"
    assert len(fixed_llm) == 1  # summarizer was invoked once


def test_no_directive_leaves_summary_untouched(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc(summary="ORIGINAL", on_done=""))
    executor.run(str(src), out=_silent)
    assert _section(src).summary == "ORIGINAL"
    assert len(fixed_llm) == 0  # never called without the directive


def test_summary_is_replaced_not_appended(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc())
    executor.run(str(src), out=_silent)
    executor.run(str(src), out=_silent)
    # summary replaced each run — exactly one occurrence, not stacked
    text = src.read_text(encoding="utf-8")
    region = text.split("```jsonl", 1)[0]
    assert region.count("REMEMBERED-STATE") == 1
    assert _section(src).summary == "REMEMBERED-STATE"


# ---------------------------------------------------------------------------
# The payoff: remembers across runs
# ---------------------------------------------------------------------------

def test_remembers_across_runs(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc(step_text='"ctx=[{{ context }}]"'))
    executor.run(str(src), out=_silent)  # run 1: empty context, then summary set
    executor.run(str(src), out=_silent)  # run 2: summary injected

    entries = _section(src).entries
    # run 1 step saw no summary; run 2 step saw the summary from run 1
    assert entries[0]["output"] == "ctx=[]"
    assert entries[-1]["output"] == "ctx=[REMEMBERED-STATE]"


# ---------------------------------------------------------------------------
# Anti-drift: summary is derived from the log, NOT the prior summary
# ---------------------------------------------------------------------------

def test_summary_derived_from_log_not_prior_summary(write_doc, fixed_llm):
    doc = _doc(step_text='"unique-marker-output"', summary="BOGUS-PRIOR-SUMMARY")
    src = write_doc("doc.md", doc)
    executor.run(str(src), out=_silent)

    prompt = fixed_llm[0]["prompt"]
    assert "unique-marker-output" in prompt          # the log IS the input
    assert "BOGUS-PRIOR-SUMMARY" not in prompt        # the prior summary is NOT


def test_summarize_passes_log_entries_as_jsonl(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc())
    executor.run(str(src), out=_silent)
    prompt = fixed_llm[0]["prompt"]
    assert '"plugin": "print"' in prompt
    assert '"status": "ok"' in prompt


# ---------------------------------------------------------------------------
# Directive model override
# ---------------------------------------------------------------------------

def test_model_override_from_directive(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc(on_done="summarize(claude-test-model)"))
    executor.run(str(src), out=_silent)
    assert fixed_llm[0]["model"] == "claude-test-model"


def test_default_model_when_unspecified(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc(on_done="summarize"))
    executor.run(str(src), out=_silent)
    assert fixed_llm[0]["model"] is None  # plugin applies its own default


# ---------------------------------------------------------------------------
# Graceful degradation: no model / no key
# ---------------------------------------------------------------------------

def test_graceful_when_model_unavailable(write_doc, monkeypatch):
    monkeypatch.setattr(
        executor, "_llm_complete",
        lambda prompt, model=None, max_tokens=512: (False, "ANTHROPIC_API_KEY not set"),
    )
    src = write_doc("doc.md", _doc(summary="ORIGINAL"))
    executor.run(str(src), out=_silent)  # must not raise

    sec = _section(src)
    assert sec.summary == "ORIGINAL"      # summary left intact
    assert len(sec.entries) == 1          # raw capture still happened


def test_no_summarize_when_nothing_captured(write_doc, fixed_llm):
    # --no-save → no entries appended → no summarization attempted
    src = write_doc("doc.md", _doc(summary="ORIGINAL"))
    executor.run(str(src), save_context=False, out=_silent)
    assert _section(src).summary == "ORIGINAL"
    assert len(fixed_llm) == 0


# ---------------------------------------------------------------------------
# Byte preservation & structure
# ---------------------------------------------------------------------------

def test_byte_identical_outside_section_after_summary(write_doc, fixed_llm):
    doc = (
        "# Title\n\n"
        "@memory\n"
        'name: "x"\n\n'
        "@workflow main\n"
        "- @print\n"
        '  text: "hi"\n\n'
        "@context_memory\n\n"
        "```jsonl\n```\n\n"
        "@on_done\nsummarize\n"
    )
    src = write_doc("doc.md", doc)
    before = doc.split("@context_memory")[0]
    executor.run(str(src), out=_silent)
    after = src.read_text(encoding="utf-8").split("@context_memory")[0]
    assert after == before


def test_html_comment_preserved_through_summary(write_doc, fixed_llm):
    doc = (
        "@context_memory\n"
        "<!-- keep me -->\n"
        "old summary\n\n"
        "```jsonl\n```\n\n"
        "@workflow main\n"
        "- @print\n"
        '  text: "x"\n\n'
        "@on_done\nsummarize\n"
    )
    src = write_doc("doc.md", doc)
    executor.run(str(src), out=_silent)
    text = src.read_text(encoding="utf-8")
    assert "<!-- keep me -->" in text
    assert _section(src).summary == "REMEMBERED-STATE"  # comment dropped from summary


def test_multiline_summary_roundtrips(write_doc, monkeypatch):
    monkeypatch.setattr(
        executor, "_llm_complete",
        lambda prompt, model=None, max_tokens=512: (True, "line one\nline two"),
    )
    src = write_doc("doc.md", _doc())
    executor.run(str(src), out=_silent)
    assert _section(src).summary == "line one\nline two"


def test_section_still_parses_after_summary(write_doc, fixed_llm):
    src = write_doc("doc.md", _doc())
    executor.run(str(src), out=_silent)
    # full document still parses cleanly and the log survives intact
    doc = parse(src.read_text(encoding="utf-8"))
    assert doc.section("context_memory").summary == "REMEMBERED-STATE"
    assert len(doc.section("context_memory").entries) == 1
    assert len(doc.workflows()) == 1
