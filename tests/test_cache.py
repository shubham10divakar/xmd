"""Content-addressed step cache — `runxmd run --cache` (JOT plan B5).

A language step whose plugin, params, interpreter version and script bytes are
unchanged reuses its cached stdout/stderr/exit-code instead of re-executing.
Opt-in; `--force` ignores existing entries. Non-language plugins are never
cached.
"""
from __future__ import annotations

import shutil

import pytest

from runxmd import executor

pytestmark = pytest.mark.skipif(
    shutil.which("python") is None, reason="'python' not on PATH"
)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNXMD_CACHE_DIR", str(tmp_path / "_cache"))


def _doc(marker_file, extra_line=""):
    return (
        "# Cache\n\n"
        "- @python\n"
        "  run: |\n"
        f"    open(r\"{marker_file}\", \"a\").write(\"ran\\n\")\n"
        "    print(\"done\")\n"
        f"    {extra_line}\n"
    )


def _run(src, **kw):
    lines: list[str] = []
    doc = executor.run(str(src), out=lines.append, **kw)
    return doc, "\n".join(lines)


def test_cache_hit_skips_execution(tmp_path):
    marker = tmp_path / "marker.txt"
    src = tmp_path / "c.md"
    src.write_text(_doc(marker), encoding="utf-8")

    doc1, _ = _run(src, cache=True)
    doc2, _ = _run(src, cache=True)

    assert doc1.report.cache_misses == 1 and doc1.report.cache_hits == 0
    assert doc2.report.cache_hits == 1 and doc2.report.cache_misses == 0
    # the step body appended exactly once — second run did not execute it
    assert marker.read_text(encoding="utf-8").count("ran") == 1


def test_force_reexecutes(tmp_path):
    marker = tmp_path / "marker.txt"
    src = tmp_path / "c.md"
    src.write_text(_doc(marker), encoding="utf-8")

    _run(src, cache=True)
    _run(src, cache=True, force=True)
    assert marker.read_text(encoding="utf-8").count("ran") == 2


def test_changed_step_code_is_a_miss(tmp_path):
    marker = tmp_path / "marker.txt"
    src = tmp_path / "c.md"
    src.write_text(_doc(marker), encoding="utf-8")
    _run(src, cache=True)

    src.write_text(_doc(marker, extra_line='print("changed")'), encoding="utf-8")
    doc2, _ = _run(src, cache=True)
    assert doc2.report.cache_misses == 1


def test_editing_prose_only_still_hits(tmp_path):
    marker = tmp_path / "marker.txt"
    src = tmp_path / "c.md"
    src.write_text(_doc(marker), encoding="utf-8")
    _run(src, cache=True)

    src.write_text("Some new intro prose.\n\n" + _doc(marker), encoding="utf-8")
    doc2, _ = _run(src, cache=True)
    assert doc2.report.cache_hits == 1


def test_cached_output_matches_fresh(tmp_path):
    marker = tmp_path / "marker.txt"
    src = tmp_path / "c.md"
    src.write_text(_doc(marker), encoding="utf-8")

    _run(src, cache=True)
    render_fresh = (tmp_path / "c_render.md").read_text(encoding="utf-8")
    _run(src, cache=True)
    render_cached = (tmp_path / "c_render.md").read_text(encoding="utf-8")

    # renders differ only in the provenance timestamp
    from runxmd import provenance
    assert provenance.strip_header(render_fresh) == provenance.strip_header(render_cached)


def test_no_cache_flag_means_no_caching(tmp_path):
    marker = tmp_path / "marker.txt"
    src = tmp_path / "c.md"
    src.write_text(_doc(marker), encoding="utf-8")

    _run(src)
    _run(src)
    assert marker.read_text(encoding="utf-8").count("ran") == 2


def test_print_step_is_not_cached(tmp_path):
    src = tmp_path / "p.md"
    src.write_text("# P\n\n- @print\n  text: \"hi\"\n", encoding="utf-8")
    doc, _ = _run(src, cache=True)
    assert doc.report.cache_hits == 0 and doc.report.cache_misses == 0
