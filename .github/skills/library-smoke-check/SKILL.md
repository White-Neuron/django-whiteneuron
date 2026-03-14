---
name: library-smoke-check
description: 'Smoke-check Python package artifacts and metadata after uv build, before creating/pushing release tags.'
argument-hint: 'Target version (optional), artifact dir (default dist), and strictness (quick|standard).'
user-invocable: true
---

# Library Smoke Check

## Outcome
This skill validates build artifacts and package metadata quickly after `uv build` and before tag/push operations.

## Use When
- Build just completed and you need fast confidence before release.
- You want to verify wheel/sdist presence, naming, metadata consistency, and installability signals.

## Required Inputs
- Artifact directory:
  - default: `dist/`
- Target version:
  - optional; if omitted use version from `pyproject.toml`
- Strictness:
  - `quick`: artifact presence + filename checks
  - `standard` (default): includes metadata and package checks

## Procedure
1. Resolve expected package info
- Read `name` and `version` from `pyproject.toml`.
- Normalize expected filename token (e.g., `django_whiteneuron`).

2. Check artifact existence
- Ensure both wheel and sdist exist in `dist/`:
  - `*.whl`
  - `*.tar.gz`
- Validate artifact filenames contain expected version.

3. Validate wheel metadata (standard)
- Inspect wheel `METADATA` and verify:
  - `Name` matches expected package name
  - `Version` matches target/pyproject version

4. Validate distribution integrity (standard)
- Run `twine check` (recommended via `uvx twine check dist/*`).
- Report warnings/errors clearly.

5. Optional import smoke (standard)
- Create disposable venv and install built wheel.
- Run a minimal import check (e.g., package import and `__version__` read if available).

6. Output a release gate summary
- `PASS` when all required checks succeed.
- `FAIL` with exact failing checks and remediation commands.

## Decision Logic
- If `quick` mode passes but `standard` fails, block tag/push and report why.
- If version mismatch appears, require rebuilding artifacts before release.
- If `twine check` fails, do not proceed to tag/push.

## Completion Criteria
- Artifact presence verified.
- Metadata consistency verified.
- Actionable PASS/FAIL gate returned with next steps.
