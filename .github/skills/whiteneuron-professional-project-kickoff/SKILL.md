---
name: whiteneuron-professional-project-kickoff
description: 'Create a production-ready new Django project with django-whiteneuron as core, using uv, profile-driven scaffolding, and smart auto-selection of features/scripts/settings based on proven Whiteneuron project patterns.'
argument-hint: 'Project name, destination path, project profile (portal-cms|catalog-api|admin-core), scope (admin-only|admin+api), deployment target (local|staging|prod), and source mode (workspace|git-tag).'
user-invocable: true
---

# Whiteneuron Professional Project Kickoff

## Outcome
This skill creates a new Django project that uses `django-whiteneuron` as core, with a professional baseline architecture and smart automation decisions derived from existing production-like projects.

It optimizes bootstrap by selecting the right app stack, scripts, env variables, and admin configuration from a chosen profile instead of a one-size-fits-all template.

## Use When
- User asks to start a new project using `django-whiteneuron` as core.
- Team needs a clean, repeatable bootstrap flow for development and early production.
- User wants to leverage the most suitable built-in features instead of custom-building admin capabilities from scratch.
- User wants the setup to be "professional + optimized" with minimal trial-and-error.

## Required Inputs
- Project name
- Destination directory
- Project profile:
  - `portal-cms` (similar to WN-Portal)
  - `catalog-api` (similar to Rehab-Technique-Catalog)
  - `admin-core` (minimal baseline)
- Scope:
  - `admin-only`
  - `admin+api`
- Deployment target:
  - `local`
  - `staging`
  - `prod`
- Source mode for library:
  - `workspace` (default when inside monorepo/workspace)
  - `git-tag` (default outside monorepo)

If user does not provide inputs, assume:
- profile = `admin-core`
- scope = `admin-only`
- deployment target = `local`
- source mode = `workspace` (in this repository) else `git-tag`

## Default Policy
- Package manager: `uv`
- Python floor: align with `django-whiteneuron` minimum supported version
- Start with smallest safe feature set, then add optional features by explicit need
- Prefer explicit configuration over magic defaults
- Validate with `manage.py check` and `migrate` before handoff
- Default profile: `admin-core`
- For `portal-cms`, async stack is enabled by default (Redis/Celery/Channels profile path)
- Bootstrap scripts policy: generate a full operations script set from day 1 (WN-Portal style)

## Reference Patterns (Learned From Existing Projects)
- Rehab-Technique-Catalog project pattern:
  - profile archetype: `catalog-api`
  - stack highlights: DRF + drf-yasg + django-filter + domain import scripts
  - source mode pattern: `tool.uv.sources` with Git tag pin for django-whiteneuron
  - runtime pattern: `src/` layout + `scripts/runserver.sh` and `scripts/migrate.sh`
- WN-Portal project pattern:
  - profile archetype: `portal-cms`
  - stack highlights: multi-app CMS, i18n, static/media pipeline, optional Redis/Celery
  - source mode pattern: same Git tag pin strategy
  - operations pattern: extensive scripts for migrations, static, i18n, user provisioning, async workers

Use these as defaults for profile-specific decisions, but do not copy business-domain code.

## Template Assets (Mandatory Use)
Before creating files, load and apply these templates:
- Layout template: [project-layout-template.md](./assets/project-layout-template.md)
- Base model/admin template: [model-admin-template.md](./assets/model-admin-template.md)
- Settings bootstrap template: [settings-bootstrap-template.md](./assets/settings-bootstrap-template.md)
- Settings safety guide: [settings-options-safety-guide.md](./assets/settings-options-safety-guide.md)
- UNFOLD baseline template: [unfold-baseline-template.md](./assets/unfold-baseline-template.md)
- UNFOLD key features reference: [unfold-key-features-reference.md](./assets/unfold-key-features-reference.md)
- Historical UNFOLD upgrade reports (recommended input): [docs/reports/unfold-upgrades](../../../docs/reports/unfold-upgrades)
- Environment template: [env-example-template.env](./assets/env-example-template.env)
- Docker template: [docker-bootstrap-template.md](./assets/docker-bootstrap-template.md)
- Script templates directory: [assets/scripts](./assets/scripts)
- Docker executable templates directory: [assets/docker](./assets/docker)
- Preflight checklist: [preflight-checklist-template.md](./assets/preflight-checklist-template.md)
- Scaffold integrity checklist: [scaffold-integrity-checklist.md](./assets/scaffold-integrity-checklist.md)

Rule: do not handcraft structure/config from memory when a template exists. Start from template, then adapt profile-specific deltas.
Rule: if any mandatory template is missing, stop and report a template-inventory failure before scaffolding.
Rule: scaffolding must be idempotent. Re-running bootstrap must not append or duplicate old content.

## Required Project Layout (Must Follow Template)
The generated project must follow template-aligned structure from day 1.

Top-level baseline:
- `src/`
- `scripts/`
- `docker/`
- `docs/`
- `pyproject.toml`
- `uv.lock`
- `README.md`
- `.env.example`
- `styles.css` (if frontend/admin styling enabled)

Inside `src/`:
- `src/manage.py`
- `src/<project_name>/` (settings/urls/asgi/wsgi)
- `src/apps/` (all business apps; do not scatter apps at root)
- `src/templates/`
- `src/static/`
- `src/media/`
- `src/staticfiles/` is runtime output (create during collectstatic, do not treat as source tree)

Profile-specific directory requirements:
- `admin-core`:
  - minimal: `src/apps/`, `src/templates/`, `src/static/`, `scripts/`, `docker/`
- `catalog-api` (Rehab-like):
  - required: `src/apps/api/`, `src/apps/<domain>/`, `docs/`, `docker/data/` (if import sources needed)
  - optional: `src/locale/` for i18n
- `portal-cms` (WN-Portal-like):
  - required: multiple content apps under `src/apps/`, `src/templates/`, `src/static/`, `src/media/`, `src/staticfiles/`
  - recommended: docs files for setup/deploy/checklist at root

Structure constraints:
- Keep all project code under `src/`.
- Keep operational scripts under `scripts/` only.
- Keep container artifacts under `docker/` only.
- Do not create parallel app roots outside `src/apps/`.

## Procedure
0. Preflight template inventory (mandatory fail-fast)
- Validate all mandatory template files and directories exist before generating any project file.
- If one or more templates are missing:
  - stop immediately
  - report missing files
  - do not continue with fallback hand-written scaffolding

0.1 Workspace hygiene and idempotent scaffold guard (mandatory)
- Before writing files, detect destination state:
  - empty/new destination -> normal scaffold
  - existing/non-empty destination -> require explicit mode: `clean-recreate` or `merge-safe`
- In `clean-recreate` mode:
  - remove only target project tree then regenerate from templates
- In `merge-safe` mode:
  - update only mapped files with deterministic replacement (no append)
- Never append generated blocks to existing config files.
- Use full-file replacement for generated targets where practical (`pyproject.toml`, settings, script files, compose files).
- After generation, run [scaffold-integrity-checklist.md](./assets/scaffold-integrity-checklist.md).

1. Discovery and fit
- Confirm project goals, actor types, and primary admin workflows.
- Ask/derive profile:
  - `portal-cms`: content-heavy website management
  - `catalog-api`: data catalog + API integration first
  - `admin-core`: generic internal admin platform
- Decide whether API stack is needed at bootstrap (`admin+api`) or deferred.

2. Workspace-safe initialization
- Create project directory.
- Initialize project with `uv init`.
- Add Django and core dependencies.
- Add `django-whiteneuron` using the correct source strategy:
  - `workspace` mode (same monorepo/workspace):
    - use `[tool.uv.sources] django-whiteneuron = { workspace = true }`
  - `git-tag` mode (standalone project):
    - pin with `[tool.uv.sources] django-whiteneuron = { git = "https://github.com/White-Neuron/django-whiteneuron.git", rev = "v<stable>" }`
- Create Django project using `src/` layout.
- Create and lock baseline directories immediately:
  - `src/apps`
  - `src/templates`
  - `src/static`
  - `src/media`
  - `src/staticfiles`
  - `scripts`
  - `docker`
  - `docs`
- Validate directory tree against [project-layout-template.md](./assets/project-layout-template.md) before generating app code.

3. Smart profile-based dependency selection
- `admin-core` baseline:
  - `django-whiteneuron`
- `catalog-api` add-ons:
  - `djangorestframework`, `drf-yasg`, `django-filter`
  - optional domain libs (example pattern: excel import stack)
- `portal-cms` add-ons:
  - translation/content/site apps as needed
  - async and cache stack enabled by default (`channels`, `channels-redis`, Celery-related deps, redis-compatible settings)
- Always keep optional dependencies explicit and justified in README handoff.

4. Core settings integration (professional baseline)
- Use base-settings inheritance pattern proven in both references:
  - `from whiteneuron.base.settings import *`
- Review [settings-options-safety-guide.md](./assets/settings-options-safety-guide.md) before applying any project overrides.
- Review [unfold-key-features-reference.md](./assets/unfold-key-features-reference.md) to select profile-appropriate Unfold capabilities.
- If available, review latest report in [docs/reports/unfold-upgrades](../../../docs/reports/unfold-upgrades) for real-world compatibility hotspots before finalizing UNFOLD overrides.
- Start from [settings-bootstrap-template.md](./assets/settings-bootstrap-template.md), then apply profile deltas.
- Apply mandatory UNFOLD overrides from [unfold-baseline-template.md](./assets/unfold-baseline-template.md).
- Configure project identity/env:
  - `PROJECT_NAME`, `NAME`, `URL`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- Integrate `INSTALLED_APPS` with selected profile stack.
- Configure middleware in stable order:
  - security/session/common/auth/messages
  - then whiteneuron middlewares and optional extras
- Set `AUTH_USER_MODEL = "base.User"`.
- Configure `AUTHENTICATION_BACKENDS` with guardian backend.
- Add minimal `UNFOLD` configuration and language/site identity.
- Configure `STATICFILES_DIRS` to include project static + whiteneuron static.

5. Core architecture contract (mandatory for new projects)
- Domain models must inherit from `whiteneuron.base.models.BaseModel` unless there is a strong technical reason not to.
- New admin classes must inherit from `whiteneuron.base.admin.ModelAdmin`.
- Admin registrations must target `base_admin_site` instead of default `admin.site`.
- Use [model-admin-template.md](./assets/model-admin-template.md) for first model/admin of each new app.
- Keep model/meta/admin patterns aligned with existing projects:
  - ordering by `-created_at` where appropriate
  - use audit/meta fields from BaseModel (`created_at`, `created_by`, `updated_at`, `updated_by`, soft-delete semantics)
  - include admin fieldsets and readonly meta fields for traceability
- For relation-heavy models, prefer admin UX features from library stack:
  - `autocomplete_fields`
  - profile-appropriate text editor mode (`wysiwyg`/`ckeditor`)
  - filters/search/list displays following ModelAdmin conventions

6. Smart feature-enablement checklist (to maximize library value)
- Enable and wire these capabilities when they fit product scope:
  - permission-aware navigation/sidebar (UNFOLD navigation + badge callbacks)
  - feedback workflow (`whiteneuron.feedbacks`) for in-admin data correction loop
  - file ingestion workflows (`whiteneuron.file_management`) for operational uploads
  - notification pipeline (`whiteneuron.notification`) for admin events
  - import/export integration for data bootstrap and operational bulk edits
  - i18n/modeltranslation path when multilingual content exists
  - audit/history and soft-delete visibility strategy for admin power users
- Ensure bootstrap includes minimal examples of these integrations when enabled:
  - at least one BaseModel-based app model
  - at least one ModelAdmin registered with `base_admin_site`
  - one navigation section in UNFOLD that links to project app modules

7. Feature-fit selection matrix
- Always include:
  - `whiteneuron`
  - `whiteneuron.base`
  - `whiteneuron.dashboard`
- Include by need:
  - `whiteneuron.feedbacks` for user/internal feedback workflows
  - `whiteneuron.file_management` for admin-managed file ingestion and curation
  - `whiteneuron.notification` for event-driven admin notifications
- Include ecosystem apps only when needed:
  - `channels` / `channels-redis` for realtime notifications
  - `import_export` for data operations
  - `simple_history` for audit trails

8. Auto-generate operational scripts (smart defaults)
- Generate full script set immediately (WN-Portal-style baseline):
  - `scripts/runserver.sh`
  - `scripts/runserver_daphne.sh`
  - `scripts/makemigrations.sh`
  - `scripts/migrate.sh`
  - `scripts/collectstatic.sh`
  - `scripts/create_superuser.sh`
  - `scripts/create_groupuser.sh`
  - `scripts/create_guest.sh`
  - `scripts/makemessages.sh`
  - `scripts/compilemessages.sh`
  - `scripts/tailwind.sh`
  - `scripts/run_celery.sh`
  - `scripts/run_celery_beat.sh`
  - `scripts/backup_to_json.sh` or `scripts/export_backup.sh`
  - `scripts/import_from_backup.sh`
- Generate from executable templates under [assets/scripts](./assets/scripts), then patch values (port, project module, optional features).
- If profile = `catalog-api`:
  - add domain import helper (example: `scripts/import_techniques.py` pattern) and corresponding run instruction
- Ensure each script is executable and documented in README section "Scripts".

9. Environment baseline templates
- Generate `.env.example` with grouped sections:
  - General, Security, Database, Domain, Optional cache/async, Email
- Include sensible defaults:
  - local host + localhost CSRF origin
  - `DATABASE=sqlite` for local bootstrap
  - optional postgres/redis commented blocks
- If deployment target is `staging` or `prod`, include stricter template guidance:
  - `DEBUG=False`, explicit hosts/origins, strong secret key policy
- Initialize from [env-example-template.env](./assets/env-example-template.env), then patch by profile and deployment target.

10. Frontend/admin assets
- Prefer optional mode by default.
- If admin branding/UI customization is requested:
  - install and configure Tailwind + daisyUI
  - create top-level `styles.css`
  - create build command and output path
- Match existing project conventions when extending an existing codebase.

11. Docker bootstrap (generate from proven templates)
- Always scaffold Docker configuration from day 1 using the same structure family as Rehab-Technique-Catalog and WN-Portal.
- Start from [docker-bootstrap-template.md](./assets/docker-bootstrap-template.md).
- Materialize docker files from [assets/docker](./assets/docker), then patch image/service/project names by profile.
- Create `docker/` with at least:
  - `docker/Dockerfile`
  - `docker/docker-compose.yml`
  - `docker/docker-compose.deploy.yml`
  - `docker/.env.docker`
  - `docker/supervisord.conf`
  - `docker/init.sh`
  - `docker/start.sh` or `docker/start_daphne.sh`
  - `docker/docker-start.sh`, `docker/docker-stop.sh`, `docker/docker-clear.sh`, `docker/docker-destroy.sh`
  - `docker/docker-build-and-run.sh`
  - optional `docker/docker-push.sh` for CI/CD handoff
- Compose profile behavior:
  - `catalog-api`: default includes `db` (postgres) + `web`, optional `cloudflared`
  - `portal-cms`: default includes `web`, optional `db` (postgres), optional `cloudflared`
  - `admin-core`: minimal `web` first, add `db` when target is staging/prod
- Docker runtime conventions:
  - mount `.env.docker` as runtime env file
  - mount `media/` and required data folders
  - expose stable service port matching `runserver` script convention
  - keep restart policy conservative in local (`no`), document production override (`unless-stopped`)
- Image/build conventions:
  - use a deterministic base image and timezone setup
  - install dependencies via `uv sync --no-dev`
  - run `collectstatic --noinput` during image build when suitable
  - use non-root runtime user
- If async stack enabled (default for `portal-cms`):
  - ensure redis/celery-related env vars exist in `.env.docker`
  - provide matching process startup strategy (supervisord or split services)

12. Validation gates (mandatory)
- Run:
  - `python manage.py check`
  - `python manage.py migrate --noinput`
- For API scope, run quick endpoint smoke check (health/doc endpoint).
- Validate admin login path and index page manually.
- Ensure no missing app/import errors from the selected feature set.
- Validate container bootstrap:
  - `docker compose -f docker/docker-compose.yml config`
  - `docker compose -f docker/docker-compose.yml up -d --build` (or equivalent helper script)
  - basic health check for web service endpoint
- Validate structure compliance:
  - all required top-level folders exist
  - all Django apps are inside `src/apps/`
  - no duplicate infra folders outside `scripts/` and `docker/`
  - settings and manage.py are in `src/` layout
  - `src/staticfiles/` is treated as runtime output, not scaffold source
- Validate architecture compliance:
  - project app models inherit BaseModel (spot-check representative models)
  - project admins inherit ModelAdmin and register via base_admin_site
  - no new app admin registered to default admin site unless intentionally documented
- Validate scaffold integrity:
  - no duplicated app registration lines in `INSTALLED_APPS`
  - no duplicate top-level sections in generated files (`[project]`, `dependencies`, repeated shebang blocks)
  - no concatenated trailing stale content in `pyproject.toml`, settings, scripts, docker files
  - rerunning generation does not change files unexpectedly (idempotency check)

13. Handover package
- Generate/update README with:
  - setup commands
  - run commands
  - script catalog and when to use each script
  - docker commands and service topology
  - architecture summary
  - enabled `django-whiteneuron` features
  - upgrade path for library source mode (`workspace` vs `git-tag`)
  - profile chosen and deferred features backlog
  - BaseModel/Admin-site adoption notes (what is enforced and where)

## Decision Logic
- Source mode auto-selection:
- If project is inside the same workspace/repository as library source:
  - prefer `workspace` source mode to avoid uv workspace conflicts.
- If project is standalone:
  - prefer `git-tag` pin for reproducibility.

- Profile auto-selection heuristics:
- If user mentions CMS/blog/product/team/content/SEO:
  - pick `portal-cms`.
- If user mentions catalog/API/FHIR/data integration/filtering:
  - pick `catalog-api`.
- Otherwise:
  - pick `admin-core`.

- Scope auto-selection:
- If API endpoints are required in acceptance criteria:
  - use `admin+api`.
- Else:
  - start with `admin-only` and phase API later.

- Default coherence rule:
- If profile is `admin-core` and user gives no scope, keep `admin-only` (do not auto-upgrade to API scope).

- Risk control:
- If optional features increase setup risk:
  - defer optional apps and keep a minimal stable baseline first.
- If dependency resolution fails with workspace+git conflict:
  - switch to one source mode only and document the reason.

- BaseModel/Admin policy:
- By default, all new domain models should inherit BaseModel.
- By default, all admin registration should use `base_admin_site` + `ModelAdmin`.
- Any exception must be explicitly documented in README handover.

- Portal-CMS policy:
- Async stack remains enabled by default unless user explicitly opts out.

- Docker policy:
- Docker config is scaffolded by default for all profiles, with profile-specific compose topology.

- Structure policy:
- If generated structure deviates from template, fix structure before continuing feature/config work.
- Never continue bootstrap with mixed layouts.

- Integrity policy:
- If stale/concatenated content is detected, stop and clean target files before running migrations/tests.
- Do not attempt partial fixes by appending compensating lines.

## Completion Criteria
- Project scaffold created and dependency resolution successful.
- `django-whiteneuron` integrated with a valid settings stack.
- Validation gates pass (`check`, `migrate`).
- README handoff completed with executable commands.
- Final output includes:
  - chosen profile and why
  - enabled features now
  - deferred features and trigger conditions to enable later
- Full operations scripts scaffold exists and is documented.
- Docker directory and compose workflow are generated and runnable.
- Project folder structure matches the required template for selected profile.
- BaseModel and custom Admin Site contracts are implemented and validated.
- Generated files pass scaffold integrity checks (no duplicate/concatenated stale content).

## Anti-Patterns To Avoid
- Installing from package index when package is not published.
- Enabling too many optional apps without a concrete use case.
- Skipping migration/check before declaring bootstrap complete.
- Mixing workspace and git source modes in an inconsistent way.
- Copying domain/business models from reference projects instead of only applying architectural patterns.

## Response Style
- Operational, concise, and professional.
- Explain trade-offs for each enabled/disabled feature.
- Highlight blockers early and provide safe fallback options.