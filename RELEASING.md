# Releasing XMD

Packaging metadata lives in `pyproject.toml` (setuptools backend). The version is
single-sourced from `xmd/__init__.py` (`__version__`).

## One-time setup

1. **Pick the distribution name.** The import/CLI name is `xmd`. The PyPI project
   name is also `xmd` in `pyproject.toml` — **verify it's available** at
   https://pypi.org/project/xmd/ . If taken, change `name` in `pyproject.toml` to
   e.g. `xmd-runtime` (the `pip install` name changes; `import xmd` stays the same).
2. **Create accounts + tokens:** https://pypi.org and https://test.pypi.org , then
   create API tokens (Account Settings → API tokens). Store them, or put them in
   `~/.pypirc`.
3. **Install the build tools:**
   ```bash
   python -m pip install --upgrade build twine
   ```

## Each release

1. **Bump the version** in `xmd/__init__.py` (e.g. `0.0.2` → `0.0.3`).
2. **Update the SPEC + changelog** (cut `SPEC-vX.Y.Z.md`, update the README badge).
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
5. **Test-publish first** (recommended), then install from TestPyPI to confirm:
   ```bash
   twine upload --repository testpypi dist/*
   pip install --index-url https://test.pypi.org/simple/ --no-deps xmd
   ```
6. **Publish for real:**
   ```bash
   twine upload dist/*
   ```
7. **Tag the release** and push the tag:
   ```bash
   git tag v0.0.2
   git push origin v0.0.2
   ```

## Smoke test before publishing

```bash
pip install -e .
xmd --version
xmd run examples/PROJECT.xmd --no-write
```
