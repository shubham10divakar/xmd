# Releasing XMD

Packaging metadata lives in `pyproject.toml` (setuptools backend). The version is
single-sourced from `runxmd/__init__.py` (`__version__`).

## One-time setup

1. **Pick the distribution name.** The CLI/package name is `runxmd`. The PyPI
   project name is `runxmd` in `pyproject.toml` — **verify it's available** at
   https://pypi.org/project/runxmd/ before uploading.
2. **Create accounts + tokens:** https://pypi.org and https://test.pypi.org , then
   create API tokens (Account Settings → API tokens). Store them, or put them in
   `~/.pypirc`.
3. **Install the build tools:**
   ```bash
   python -m pip install --upgrade build twine
   ```

## Each release

1. **Bump the version** in `runxmd/__init__.py` (e.g. `1.0.3` → `1.0.4`).
2. **Update the docs + changelog** — README badge + Status header, the SPEC
   changelog (§8), `ROADMAP.md`. Cut a new `SPEC-vX.Y.Z.md` only when the
   contract actually changes.
3. **Build** a clean sdist + wheel:
   ```bash
   # from the repo root
   rm -rf dist build *.egg-info        # PowerShell: Remove-Item -Recurse -Force dist,build,*.egg-info -ErrorAction SilentlyContinue
   python -m build
   ```
4. **Check** the artifacts:
   ```bash
   twine check dist/*
   ```
5. **Smoke-test the built wheel** in a throwaway venv:
   ```bash
   python -m venv /tmp/rx && /tmp/rx/bin/pip install dist/runxmd-*.whl
   /tmp/rx/bin/runxmd --version
   printf '# S\n\n- @print\n  text: "hi"\n' > /tmp/s.md
   /tmp/rx/bin/runxmd run /tmp/s.md && /tmp/rx/bin/runxmd verify /tmp/s_render.md
   ```
6. **Test-publish first** (recommended), then install from TestPyPI to confirm:
   ```bash
   twine upload --repository testpypi dist/*
   pip install --index-url https://test.pypi.org/simple/ --no-deps runxmd
   ```
7. **Publish for real:**
   ```bash
   twine upload dist/*
   ```
8. **Tag the release** and push the tag, then cut the GitHub Release:
   ```bash
   git tag -a v1.0.4 -m "runxmd v1.0.4 — <one-line summary>"
   git push origin v1.0.4
   gh release create v1.0.4 --generate-notes
   ```
