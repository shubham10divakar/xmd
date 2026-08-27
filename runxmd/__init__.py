"""XMD — a runtime that executes documents.

Parse an .xmd document, run its workflows with inline-code plugins, resolve and
persist memory. The document becomes the system.

v1.0.3 adds the trust layer: provenance headers + `runxmd verify`, `run
--strict` / `--check`, output normalization, and `run --pure`.
"""

__version__ = "1.0.3"
