# Guardrail: Check Files in Folder

@goal
Verify that the target folder contains at least one file before the workflow proceeds.
Change `folder` in @memory to point at any directory you want to inspect.

@memory
folder: "src"
runtime.check_passed: "pending"

@workflow check_folder
- @python
  run: |
    import pathlib
    folder = pathlib.Path("{{ memory.folder }}")
    if not folder.exists():
        print("GUARDRAIL_FAIL: folder does not exist:", "{{ memory.folder }}")
    else:
        files = [f for f in folder.rglob("*") if f.is_file()]
        count = len(files)
        if count > 0:
            print("GUARDRAIL_PASS:", count, "file(s) found in {{ memory.folder }}")
            for f in sorted(files):
                print("  -", f.name)
        else:
            print("GUARDRAIL_FAIL: folder exists but contains no files")

@on_done
set: memory.runtime.check_passed = "true"
