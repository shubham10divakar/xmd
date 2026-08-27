"""Provenance headers + `runxmd verify` (JOT plan A1).

A render must carry evidence of what it is a render of. `runxmd verify`
re-hashes the source and reports whether the render is still current.

These use @print only — no external interpreter — so they run everywhere.
"""
from __future__ import annotations

from runxmd import executor, provenance
from runxmd.cli import main

DOC = """# Prov Doc

Some prose before the step.

- @print
  text: "hello provenance"

Some prose after.
"""


# ---------------------------------------------------------------------------
# Hashing is canonical across line endings / trailing whitespace
# ---------------------------------------------------------------------------

def test_source_hash_is_line_ending_agnostic():
    lf = "a\nb\nc\n"
    crlf = "a\r\nb\r\nc\r\n"
    trailing = "a  \nb\t\nc\n\n\n"
    assert provenance.source_hash(lf) == provenance.source_hash(crlf)
    assert provenance.source_hash(lf) == provenance.source_hash(trailing)


def test_source_hash_changes_with_content():
    assert provenance.source_hash("a\n") != provenance.source_hash("b\n")


# ---------------------------------------------------------------------------
# Header is emitted, parseable, and carries the expected fields
# ---------------------------------------------------------------------------

def test_render_carries_provenance_header(write_doc):
    path = write_doc("prov.md", DOC)
    executor.run(str(path), out=lambda *a: None)

    render = (path.parent / "prov_render.md").read_text(encoding="utf-8")
    hdr = provenance.parse_header(render)
    assert hdr is not None
    assert hdr["source"] == "prov.md"
    assert hdr["source_sha256"] == provenance.hash_file(str(path))
    assert hdr["runxmd_version"]
    assert hdr["generated_utc"].endswith("Z")
    assert "non_deterministic_steps" in hdr


def test_header_is_invisible_html_comment(write_doc):
    path = write_doc("prov.md", DOC)
    executor.run(str(path), out=lambda *a: None)
    render = (path.parent / "prov_render.md").read_text(encoding="utf-8")
    assert render.lstrip().startswith("<!-- runxmd-provenance")
    # prose still intact after the comment
    assert "hello provenance" in render


def test_no_provenance_flag_omits_header(write_doc):
    path = write_doc("prov.md", DOC)
    executor.run(str(path), add_provenance=False, out=lambda *a: None)
    render = (path.parent / "prov_render.md").read_text(encoding="utf-8")
    assert provenance.parse_header(render) is None


def test_results_and_output_files_carry_header(write_doc):
    doc = DOC + "\n@on_done\nresults\nwrite\n"
    path = write_doc("prov.md", doc)
    executor.run(str(path), out=lambda *a: None)

    for name in ("prov_results.md", "prov_output.md"):
        text = (path.parent / name).read_text(encoding="utf-8")
        assert provenance.parse_header(text) is not None, name


# ---------------------------------------------------------------------------
# verify — 0 match, 3 stale, 2 no header
# ---------------------------------------------------------------------------

def test_verify_passes_when_source_unchanged(write_doc, capsys):
    path = write_doc("prov.md", DOC)
    executor.run(str(path), out=lambda *a: None)
    render = path.parent / "prov_render.md"

    rc = main(["verify", str(render)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_verify_reports_stale_after_source_edit(write_doc, capsys):
    path = write_doc("prov.md", DOC)
    executor.run(str(path), out=lambda *a: None)
    render = path.parent / "prov_render.md"

    path.write_text(DOC.replace("hello provenance", "goodbye provenance"),
                    encoding="utf-8")

    rc = main(["verify", str(render)])
    out = capsys.readouterr().out
    assert rc == 3
    assert "STALE" in out


def test_verify_errors_without_header(write_doc, capsys):
    plain = write_doc("plain_render.md", "just a plain file\n")
    rc = main(["verify", str(plain)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "no runxmd-provenance header" in out


def test_verify_accepts_explicit_source(write_doc, capsys):
    path = write_doc("prov.xmd", DOC)
    executor.run(str(path), out=lambda *a: None)
    render = path.parent / "prov_render.xmd"

    rc = main(["verify", str(render), "--source", str(path)])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# strip_header — used by `run --check` so the timestamp doesn't force a diff
# ---------------------------------------------------------------------------

def test_strip_header_removes_block_only(write_doc):
    path = write_doc("prov.md", DOC)
    executor.run(str(path), out=lambda *a: None)
    render = (path.parent / "prov_render.md").read_text(encoding="utf-8")

    body = provenance.strip_header(render)
    assert provenance.parse_header(body) is None
    assert "hello provenance" in body
    assert body == provenance.strip_header(body)  # idempotent
