"""Shared fixtures for the runxmd test suite."""
from __future__ import annotations

import pytest

# A single sample document exercised across the suite. It uses only @print
# (pure in-process, no external interpreter) so the tests are fast and portable.
SAMPLE = """# Sample Doc

@goal
Prove the runtime runs this file.

@memory
name: "world"
runtime.status: "pending"

@tasks
- [ ] first task
- [x] done task

@workflow main
- @print
  text: "hello {{ memory.name }}"

@on_done
set: memory.runtime.status = "done"
"""


@pytest.fixture
def sample_content() -> str:
    return SAMPLE


@pytest.fixture
def write_doc(tmp_path):
    """Write document content to a temp file and return its path.

    The filename (and therefore its extension) is the caller's choice — this is
    exactly what lets us prove the runtime is extension-agnostic.
    """
    def _write(filename: str, content: str = SAMPLE):
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return p
    return _write


@pytest.fixture
def collect():
    """A capturing `out` callback plus the list it writes to.

    Returns (lines, out) where `out` can be passed to executor.run(out=...).
    """
    lines: list[str] = []
    return lines, lines.append
