# Preflight Checklist Template

Use this checklist before scaffolding any new project files.

## Template inventory (must exist)

- `assets/project-layout-template.md`
- `assets/model-admin-template.md`
- `assets/settings-bootstrap-template.md`
- `assets/env-example-template.env`
- `assets/docker-bootstrap-template.md`
- `assets/scripts/*.template`
- `assets/docker/*.template`

## Environment/tooling

- `uv` is available.
- Python version is compatible with django-whiteneuron.
- Destination directory is writable.

## Source mode safety

- If inside same workspace as django-whiteneuron source: use `workspace` source mode.
- If standalone: use `git-tag` source mode.
- Do not mix source modes in one scaffold session.

## Stop conditions (hard fail)

- Missing any mandatory template file.
- Dependency source mode conflict unresolved.
- Destination path conflicts with existing unrelated project files.
- Destination is non-empty but scaffold mode (`clean-recreate` or `merge-safe`) is not explicitly chosen.
- Tooling path would append to existing generated files instead of deterministic replacement.

## Proceed conditions

- All checks pass.
- Profile and scope are confirmed or auto-selected by rule.
- File generation strategy is idempotent (safe to rerun without duplication).
