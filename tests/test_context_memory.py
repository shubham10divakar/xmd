"""Tests for @context_memory — Phase 1 (deterministic raw capture).

The runtime appends one JSON-lines entry per step into the @context_memory
section after a run, opt-in by the section's presence. Append is a byte-
preserving splice (everything outside the section is untouched), and the rolling
summary is substituted into step params via {{ context }}.

Uses only @print so the suite stays fast and interpreter-independent.
"""
from __future__ import annotations

import json

from runxmd import executor
from runxmd.parser import parse


def _silent(*_a):
    return None


def _entries(path) -> list:
    return parse(path.read_text(encoding="utf-8")).section("context_memory").entries


# Empty @context_memory + a two-step workflow.
_TWO_STEP = (
    "# CM Test\n\n"
    "@context_memory\n\n"
    "@workflow main\n"
    "- @print\n"
    '  text: "alpha"\n'
    "- @print\n"
    '  text: "beta"\n'
)


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def test_append_one_entry_per_step(write_doc):
    src = write_doc("doc.md", _TWO_STEP)
    executor.run(str(src), out=_silent)

    entries = _entries(src)
    assert len(entries) == 2
    assert [e["step"] for e in entries] == [1, 2]
    assert [e["output"] for e in entries] == ["alpha", "beta"]


def test_entries_carry_expected_fields(write_doc):
    src = write_doc("doc.md", _TWO_STEP)
    executor.run(str(src), out=_silent)

    e = _entries(src)[0]
    for key in ("time", "run", "step", "plugin", "status", "duration_ms", "output"):
        assert key in e, f"missing field {key!r}"
    assert e["plugin"] == "print"
    assert e["status"] == "ok"
    # one run id shared across the run's steps
    runs = {x["run"] for x in _entries(src)}
    assert len(runs) == 1


def test_rerun_grows_log_and_preserves_prior(write_doc):
    src = write_doc("doc.md", _TWO_STEP)
    executor.run(str(src), out=_silent)
    executor.run(str(src), out=_silent)

    entries = _entries(src)
    assert len(entries) == 4  # 2 steps × 2 runs, appended not overwritten
    # two distinct run ids
    assert len({e["run"] for e in entries}) == 2


def test_entries_are_valid_json(write_doc):
    src = write_doc("doc.md", _TWO_STEP)
    executor.run(str(src), out=_silent)

    # re-read the raw fenced lines and json.loads each
    text = src.read_text(encoding="utf-8")
    body = text.split("```jsonl", 1)[1].split("```", 1)[0]
    rows = [ln for ln in body.splitlines() if ln.strip()]
    assert len(rows) == 2
    for ln in rows:
        json.loads(ln)  # raises if malformed


def test_output_is_single_line_and_truncated(write_doc):
    long = "x" * 500
    doc = (
        "@context_memory\n\n"
        "@workflow main\n"
        "- @print\n"
        f'  text: "{long}"\n'
    )
    src = write_doc("doc.md", doc)
    executor.run(str(src), out=_silent)

    out = _entries(src)[0]["output"]
    assert "\n" not in out
    assert len(out) <= executor.CONTEXT_OUTPUT_CAP


# ---------------------------------------------------------------------------
# Byte-preserving append
# ---------------------------------------------------------------------------

def test_byte_identical_outside_section(write_doc):
    doc = (
        "# Title\n\n"
        "@memory\n"
        'name: "x"\n\n'
        "@workflow main\n"
        "- @print\n"
        '  text: "hi"\n\n'
        "@context_memory\n\n"
        "```jsonl\n"
        "```\n"
    )
    src = write_doc("doc.md", doc)
    before = doc.split("@context_memory")[0]
    executor.run(str(src), out=_silent)
    after = src.read_text(encoding="utf-8").split("@context_memory")[0]
    assert after == before  # memory, workflow, prose all untouched


# ---------------------------------------------------------------------------
# Opt-in / opt-out
# ---------------------------------------------------------------------------

def test_absent_section_is_not_created(write_doc):
    doc = (
        "@workflow main\n"
        "- @print\n"
        '  text: "hi"\n'
    )
    src = write_doc("doc.md", doc)
    original = src.read_text(encoding="utf-8")
    executor.run(str(src), out=_silent)

    assert parse(src.read_text(encoding="utf-8")).section("context_memory") is None
    assert src.read_text(encoding="utf-8") == original


def test_no_save_suppresses_capture(write_doc):
    src = write_doc("doc.md", _TWO_STEP)
    original = src.read_text(encoding="utf-8")
    executor.run(str(src), save_context=False, out=_silent)

    assert _entries(src) == []
    assert src.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Read-back: {{ context }} substitution
# ---------------------------------------------------------------------------

def test_context_token_feeds_downstream_step(write_doc):
    doc = (
        "@context_memory\n"
        "The agent already greeted the user.\n\n"
        "```jsonl\n"
        "```\n\n"
        "@workflow main\n"
        "- @print\n"
        '  text: "memo: {{ context }}"\n'
    )
    src = write_doc("doc.md", doc)
    executor.run(str(src), out=_silent)

    # the injected summary shows up in the step output that got captured
    last = _entries(src)[-1]["output"]
    assert last == "memo: The agent already greeted the user."


# ---------------------------------------------------------------------------
# Extension-agnostic guarantee (.md == .xmd)
# ---------------------------------------------------------------------------

def test_md_and_xmd_capture_identically(write_doc):
    a = write_doc("a.md", _TWO_STEP)
    b = write_doc("b.xmd", _TWO_STEP)
    executor.run(str(a), out=_silent)
    executor.run(str(b), out=_silent)

    def stable(entries):
        return [(e["step"], e["plugin"], e["status"], e["output"]) for e in entries]

    assert stable(_entries(a)) == stable(_entries(b))
