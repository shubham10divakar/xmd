"""Regression tests for the parser's accumulated heuristics (JOT plan C7).

Each of these was a real bug during 1.0.2 development. GRAMMAR.md §4 documents
the block-scalar termination rules these pin down.
"""
from __future__ import annotations

from runxmd.parser import parse


def _steps(src):
    return parse(src).workflows()[0].steps


def test_prose_with_colon_between_steps_is_not_absorbed_as_param():
    src = (
        "@workflow w\n"
        "- @print\n"
        "  text: first\n"
        "\n"
        "Note: this sentence has a colon but is prose, not a param.\n"
        "\n"
        "- @print\n"
        "  text: second\n"
    )
    steps = _steps(src)
    assert len(steps) == 2
    assert "Note" not in steps[0].params
    assert steps[1].params["text"] == "second"


def test_zero_indent_prose_ends_a_block_scalar():
    src = (
        "@workflow w\n"
        "- @python\n"
        "  run: |\n"
        "    print('inside the block')\n"
        "\n"
        "This heading-ish prose sits at column 0 and must end the block.\n"
        "\n"
        "- @print\n"
        "  text: after\n"
    )
    steps = _steps(src)
    assert len(steps) == 2
    assert "This heading-ish prose" not in steps[0].params["run"]
    assert steps[1].params["text"] == "after"


def test_result_alongside_run_keeps_both_and_run_is_the_code():
    src = (
        "@workflow w\n"
        "- @python\n"
        "  run: |\n"
        "    print('hello')\n"
        "  result: |\n"
        "    stale output from a previous run\n"
    )
    step = _steps(src)[0]
    assert "print('hello')" in step.params["run"]
    assert "stale output" in step.params["result"]
    assert "result" not in step.params["run"]


def test_multi_param_block_scalars_terminate_on_next_param():
    src = (
        "@workflow w\n"
        "- @python\n"
        "  run: |\n"
        "    line one\n"
        "    line two\n"
        "  args: --flag\n"
    )
    step = _steps(src)[0]
    assert step.params["run"] == "line one\nline two"
    assert step.params["args"] == "--flag"


def test_block_scalar_terminates_on_following_step():
    src = (
        "@workflow w\n"
        "- @python\n"
        "  run: |\n"
        "    only this line\n"
        "- @print\n"
        "  text: next\n"
    )
    steps = _steps(src)
    assert len(steps) == 2
    assert steps[0].params["run"] == "only this line"


def test_dotted_memory_keys_stay_flat():
    doc = parse("@memory\nruntime.status: \"pending\"\nname: bob\n")
    mem = doc.section("memory").memory
    assert mem["runtime.status"] == "pending"
    assert mem["name"] == "bob"
