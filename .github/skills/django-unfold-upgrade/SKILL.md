---
name: django-unfold-upgrade
description: 'Upgrade django-unfold with uv in Whiteneuron projects. Use when asked to update django-unfold, assess compatibility with heavy custom admin code, resolve conflicts professionally, and produce a post-upgrade change report.'
argument-hint: 'Target version (optional), upgrade scope, and strictness level (safe|balanced|aggressive).'
user-invocable: true
---

# Django Unfold Upgrade (uv)

## Outcome
This skill upgrades `django-unfold` safely in a heavily customized codebase, validates behavior, and creates a professional update report after each upgrade.
The report must explicitly summarize newly introduced changes and new features from the installed version.

## Use When
- User asks to upgrade `django-unfold` to latest or a specific version.
- Project has many customizations around Unfold (admin classes, templates, widgets, templatetags, settings).
- Team needs a written report of changes, risks, conflicts, and follow-up actions.
- Package manager is `uv`.

## Required Inputs
- Upgrade target:
  - `latest` (default)
  - specific version like `0.75.2`
- Upgrade strictness:
  - `safe`: minimal behavioral changes, prefer deferring risky refactors
  - `balanced`: fix low/medium compatibility issues now
  - `aggressive`: proactively align with new APIs and deprecations

If user does not provide inputs, assume `latest` + `balanced`.

## Default Policy For This Workspace
- Package manager: `uv`
- Version policy: raise minimum dependency floor in `pyproject.toml` to the upgraded version (not only lockfile refresh)
- Validation depth: `balanced`
- Report language: Vietnamese

## Project-Specific Hotspots
Review these first because they are likely to break with upstream changes:
- [Unfold integration map](./references/project-hotspots.md)
- Local template overrides under `whiteneuron/templates/admin/` and `whiteneuron/templates/unfold/`
- Custom templatetag overrides in `whiteneuron/base/templatetags/`

## Procedure
1. Baseline and discovery
- Confirm current version and dependency constraints:
  - `uv pip show django-unfold`
  - inspect `pyproject.toml` and `uv.lock`
- Determine target version:
  - For `latest`, resolve from PyPI JSON API (or run `uv add "django-unfold"` in a dry/controlled branch and read resolved version from lockfile).
  - Do not use `uv pip index ...` because `uv pip` has no `index` subcommand.
  - For pinned target, validate availability and Python/Django compatibility.
- Read changelog/release notes for all versions between current and target.

2. Impact assessment before upgrade
- Compare release changes against local hotspots in [project-hotspots.md](./references/project-hotspots.md).
- Classify risk by area:
  - `High`: template API changes, component/tag contract changes, admin mixin/decorator behavior changes.
  - `Medium`: CSS class or widget behavior changes.
  - `Low`: docs-only, internal refactors with no public API impact.
- Propose upgrade path:
  - single-step if low risk
  - staged version hops if high risk

3. Upgrade with uv
- Resolve target version first.
- Update dependency floor in `pyproject.toml` to the target version.
- Apply and lock with `uv`:
  - `uv add "django-unfold>=<target_version>"`
- Sync environment:
  - `uv sync`

4. Resolve conflicts professionally
- For each failure, identify source:
  - Upstream breaking change
  - Local customization assumption
  - Integration mismatch with related packages
- Apply smallest safe fix first; avoid unrelated refactors.
- Prefer compatibility adapters/wrappers over broad rewrites when timeline is tight.
- If conflict cannot be safely resolved in current scope, do one of:
  - rollback to last known good version in lockfile
  - keep target but feature-flag affected customization
  - pause and request decision with clear trade-offs

5. Validation gates
- Run technical checks:
  - `uv run python whiteneuron/manage.py check`
  - relevant tests (`uv run pytest` or targeted Django tests)
  - optional static build/smoke checks if admin UI assets changed
- Run behavior checks on critical admin flows:
  - login page, index/dashboard, change list, change form, custom actions, filters, pagination, sidebar navigation
- Confirm no template resolution errors and no import errors from Unfold modules.

6. Post-upgrade report (mandatory)
- Create a report file under:
  - `docs/reports/unfold-upgrades/YYYY-MM-DD-unfold-<from>-to-<to>.md`
- Use [report template](./assets/update-report-template.md).
- Report must include:
  - upgraded versions and commands used
  - a dedicated section for new changes and new features in the installed version
  - classify each new item as: no impact | optional adoption | required code change
  - for each new feature: proposed adoption status (adopt now | defer) with reason
  - compatibility findings by hotspot
  - issues found, fixes applied, unresolved risks
  - rollback plan and recommendations
- Write report in Vietnamese by default.
- If report language is Vietnamese, content must use proper Vietnamese diacritics (không viết không dấu).

## Decision Logic
- If major-version jump or high-risk changelog items: require staged validation and explicit user confirmation before aggressive refactors.
- If only lockfile changes and all checks pass: keep code changes minimal and document no-op compatibility outcome.
- If tests are missing for changed behaviors: call out testing gap as residual risk in report.

## Completion Criteria
- `django-unfold` upgraded to requested target (or blocked with documented reason).
- All agreed validation gates executed and results recorded.
- Critical admin flows verified.
- Post-upgrade report created and shared.
- Any unresolved risk has owner, mitigation, and next step.

## Response Style
- Be explicit, concise, and professional.
- Prioritize findings and risk over verbosity.
- When blocked, provide options with trade-offs instead of vague statements.
