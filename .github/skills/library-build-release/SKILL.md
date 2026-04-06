---
name: library-build-release
description: 'Build and release django-whiteneuron package using scripts/build.sh workflow. Use when building Tailwind, running migrations, uv build, optional version bump, git tag, push, and auto-writing a professional release description.'
argument-hint: 'Release mode (build-only|release), target version (optional), and message language (vi|en).'
user-invocable: true
---

# Library Build And Release

## Outcome
This skill executes a reliable package build/release workflow based on [scripts/build.sh](../../../scripts/build.sh), with professional release messaging and controlled git operations.

## Use When
- Need to build package artifacts before verification or publication.
- Need to create release tag and push source/tag.
- Need to auto-generate a professional release description from changes.

## Required Inputs
- Mode:
  - `build-only` (default)
  - `release`
- Target version:
  - optional, if omitted keep current version in `pyproject.toml`
- Message language:
  - `vi` (default)
  - `en`

## Procedure
1. Preflight checks
- Verify workspace cleanliness and branch context:
  - `git status --short`
  - `git branch --show-current`
- Confirm build dependencies are available and environment is ready.

2. Build flow (from `scripts/build.sh`)
- Build Tailwind assets:
  - `bash scripts/tailwind.sh`
- Run migrations:
  - activate venv, `cd whiteneuron`, run `python manage.py makemigrations`, then return repo root.
- Build package:
  - `uv build`

3. Release decision
- If mode is `build-only`, stop after successful build and summarize artifacts.
- If mode is `release`, continue with version + release metadata steps.

4. Version handling (release mode)
- Read current version from `pyproject.toml`.
- If user provides new version, update `pyproject.toml` professionally:
  - validate semver-like format
  - only edit the exact version field
  - rebuild with `uv build` after version change

5. Professional release description (mandatory in release mode)
- Auto-compose release description with:
  - Scope summary
  - New changes and new features
  - Compatibility/risk notes
  - Validation performed
  - Upgrade guidance and rollback note
- Use [release description template](./assets/release-description-template.md).
- If language is Vietnamese, always write proper Vietnamese diacritics.

6. Changelog & README update (mandatory before git tag)
- **MUST be done before any git commit/tag** — this is a blocking step.
- Update `README.md` changelog:
  - Add new version entry at the top of `## Changelog` section.
  - Move `— latest` tag from previous version to the new one.
  - Follow the existing format: `### v<version> (<date>) — latest`.
- Create release notes file at `docs/reports/releases/<date>-v<version>.md`:
  - Use the professional release description from step 5.
  - Structure: summary, main changes (Added/Fixed/Improved), files changed table, compatibility notes, upgrade guide.
  - Note: `docs/reports/` is gitignored — use `git add -f` to force-stage this file.
- Rebuild with `uv build` once after all content edits (README, release notes, version bump are done).

7. Git operations (release mode)
- Before tag/push, run [library smoke-check skill](../library-smoke-check/SKILL.md) and require PASS.
- Stage only intended files (avoid blind `git add .` when unrelated changes exist).
- Use `git add -f docs/reports/releases/<date>-v<version>.md` for the release notes file.
- Create commit message:
  - `v<version>: <professional-summary>`
- Create annotated tag:
  - `v<version>` with aligned tag message
- Push current branch and tag:
  - `git push && git push origin v<version>`

8. Final report
- Report:
  - version before/after
  - files changed
  - commit + tag created
  - push status
  - generated release description

## Decision Logic
- If unrelated dirty changes exist:
  - do not auto-stage everything; stage only release-related files and list exclusions.
- If build succeeds but release push fails:
  - keep local commit/tag, report exact failure, provide safe retry commands.
- If migration generation creates unexpected schema noise:
  - pause and request confirmation before releasing.

## Completion Criteria
- Build artifacts generated successfully.
- In release mode: versioning, commit, tag, push completed (or failure reported with recovery path).
- Professional release description generated and included in final output.

## Notes
- This skill mirrors `scripts/build.sh` flow, but uses safer git staging and higher-quality release messaging.
