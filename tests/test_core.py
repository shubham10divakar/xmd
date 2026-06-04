"""Core runtime behaviour: parsing, memory substitution, write-back, ownership."""
from __future__ import annotations

from runxmd import executor
from runxmd.memory import substitute
from runxmd.parser import parse, to_source


def test_parse_sections(sample_content):
    doc = parse(sample_content)
    assert doc.title == "Sample Doc"
    assert doc.section("goal").text.startswith("Prove")
    assert doc.section("memory").memory["name"] == "world"

    tasks = doc.section("tasks").tasks
    assert [t.done for t in tasks] == [False, True]
    assert tasks[0].text == "first task"

    wf = doc.workflows()[0]
    assert wf.name == "main"
    assert wf.steps[0].plugin == "print"


def test_substitution_replaces_known_key():
    assert substitute("hi {{ memory.name }}", {"name": "bob"}) == "hi bob"


def test_substitution_missing_key_is_empty_string():
    assert substitute("x{{ memory.nope }}y", {}) == "xy"


def test_substitution_passes_non_strings_through():
    assert substitute(42, {}) == 42
    assert substitute(None, {}) is None


def test_substitution_supports_dotted_runtime_keys():
    assert substitute("{{ memory.runtime.status }}", {"runtime.status": "ok"}) == "ok"


def test_roundtrip_is_stable(sample_content):
    """Serializing a parsed doc and reparsing it must be a fixed point."""
    once = to_source(parse(sample_content))
    twice = to_source(parse(once))
    assert once == twice


def test_field_ownership_protects_agent_keys(write_doc):
    """An @on_done hook may write runtime.* but must NOT clobber agent-owned keys."""
    content = (
        "# Owned\n\n"
        "@memory\n"
        'mine: "keep"\n'
        'runtime.status: "pending"\n\n'
        "@workflow w\n"
        "- @print\n"
        '  text: "noop"\n\n'
        "@on_done\n"
        'set: memory.mine = "HACKED"\n'
        'set: memory.runtime.status = "done"\n'
    )
    path = write_doc("owned.xmd", content)

    warnings: list[str] = []
    executor.run(str(path), write_back=True, out=warnings.append)

    memory = parse(path.read_text(encoding="utf-8")).section("memory").memory
    assert memory["mine"] == "keep"            # agent-owned key preserved
    assert memory["runtime.status"] == "done"  # runtime-owned key updated
    assert any("refused" in w for w in warnings)


def test_run_returns_document_and_runs_named_workflow_only(write_doc):
    content = (
        "# Two\n\n"
        "@memory\n"
        'x: "1"\n\n'
        "@workflow first\n"
        "- @print\n"
        '  text: "in first"\n\n'
        "@workflow second\n"
        "- @print\n"
        '  text: "in second"\n'
    )
    path = write_doc("two.md", content)

    lines: list[str] = []
    executor.run(str(path), workflow_name="second", write_back=False, out=lines.append)
    output = "\n".join(lines)

    assert "in second" in output
    assert "in first" not in output


def test_implicit_workflow_from_top_level_steps(write_doc):
    """Steps written at the top level without @workflow run as an implicit workflow."""
    content = (
        "# Bare Script\n\n"
        "- @print\n"
        '  text: "implicit step one"\n'
        "- @print\n"
        '  text: "implicit step two"\n'
    )
    path = write_doc("bare.md", content)
    lines: list[str] = []
    executor.run(str(path), write_back=False, out=lines.append)
    output = "\n".join(lines)
    assert "implicit step one" in output
    assert "implicit step two" in output


def test_implicit_workflow_coexists_with_named_workflow(write_doc):
    """Top-level steps and a named @workflow both run."""
    content = (
        "# Mixed\n\n"
        "- @print\n"
        '  text: "top-level step"\n\n'
        "@workflow named\n"
        "- @print\n"
        '  text: "in named workflow"\n'
    )
    path = write_doc("mixed.md", content)
    lines: list[str] = []
    executor.run(str(path), write_back=False, out=lines.append)
    output = "\n".join(lines)
    assert "top-level step" in output
    assert "in named workflow" in output


def test_plain_prose_without_steps_has_no_implicit_workflow(write_doc):
    """Prose-only docs (no - @plugin lines) produce no implicit workflow."""
    content = "# Notes\n\nJust some prose with no steps.\n"
    path = write_doc("prose.md", content)
    doc = parse(path.read_text(encoding="utf-8"))
    assert doc.workflows() == []
