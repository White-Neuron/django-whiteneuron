# Scaffold Integrity Checklist

Run this checklist immediately after scaffold generation and before migrations/tests.

## 1) Duplicate-content scan

- Check for duplicated `INSTALLED_APPS` entries.
- Check for repeated top-level config sections in generated files.
- Check for repeated shebang blocks in scripts.

Suggested commands:

```bash
rg -n "^INSTALLED_APPS\s*=\s*\[" src
rg -n "^\[project\]" pyproject.toml
rg -n "^#!/usr/bin/env bash" scripts docker
```

Expected:
- Exactly one canonical block per generated file.

## 2) Stale-tail detection

- Verify generated files do not contain old content appended at the end.
- Focus files:
  - `pyproject.toml`
  - `src/<project_name>/settings.py`
  - `scripts/*.sh`
  - `docker/*.yml`, `docker/Dockerfile`

Quick rule:
- If a file contains two independent scaffold blocks, treat as corruption and regenerate that file fully.

## 3) Idempotency check

- Run scaffold generation a second time in dry/update mode.
- Confirm no unintended file diffs.

Suggested command:

```bash
git status --short
```

Expected:
- No new changes from the second scaffold pass.

## 4) Recovery policy

If integrity check fails:

1. Stop migrations/tests.
2. Recreate corrupted files from template (full replacement, not append patching).
3. Re-run checklist from step 1.

## 5) Pass criteria

- No duplicate blocks.
- No stale trailing content.
- No unexpected diff on rerun.
- Then proceed to `manage.py check` and `migrate`.
