# Settings Options And Safety Guide

This guide standardizes settings usage across projects that use django-whiteneuron core.

## Objectives

- Keep settings consistent across projects.
- Reuse proven patterns from portal-cms and catalog-api profiles.
- Avoid risky defaults in staging/production.
- Make profile-specific differences explicit and controlled.

## Layering Strategy (Required)

1. Base layer:
- Import from `whiteneuron.base.settings`.

2. Project layer:
- Override only what the project needs.
- Keep overrides grouped by concern (General, Domain, DB, Cache, Security, Unfold, Integrations).

3. Environment layer:
- Drive behavior by environment variables from `.env` / `.env.example`.
- Do not hardcode secrets or private hosts.

## Option Matrix

### Core identity and runtime

- `PROJECT_NAME`
- `NAME`
- `URL`
- `DEBUG`
- `TIME_ZONE`

Policy:
- Local: `DEBUG=True` allowed.
- Staging/Prod: `DEBUG=False` mandatory.

### Domain and request safety

- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS` (if API/CORS required)

Policy:
- Keep explicit host/origin lists.
- Avoid wildcard origins in production.

### Database

- `DATABASE` = `sqlite|postgres`
- `DATABASE_NAME`
- `DATABASE_USER`
- `DATABASE_PASSWORD`
- `DATABASE_HOST`
- `DATABASE_PORT`

Policy:
- Local bootstrap may use sqlite.
- Staging/Prod should use postgres.

### Cache and async

- `USE_CACHE`
- `CACHENAME` = `default|redis`
- `CACHE_REDIS_LOCATION`
- `CELERY_BROKER_URL`

Policy:
- For portal-cms profile: async stack enabled by default.
- Validate redis endpoints before enabling cache middleware.

### Feature toggles (whiteneuron)

- `SHOW_CELERY_TASKS`
- `SHOW_FILE_MANAGEMENT`
- `SHOW_FEEDBACKS`
- `BROWSER_RELOAD`
- `SKIP_GUEST_LOGIN`

Policy:
- Prefer explicit toggle values in `.env.example`.
- Do not rely on implicit defaults for security-sensitive toggles.

### Observability and integrations

- `SENTRY_DSN`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- optional editor keys (`TINYMCE_KEY`, etc.)

Policy:
- Keep keys empty in `.env.example`.
- Enable Sentry only with valid DSN and environment tagging.

## Security Baseline

### Local baseline

- `DEBUG=True`
- `SECURE_SSL_REDIRECT=False`
- cookie secure flags may be disabled

### Staging/Production baseline

- `DEBUG=False`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- HSTS enabled with explicit policy

Important:
- If project-specific settings disable security flags, that must be documented and justified.

## Unfold/Admin Guidance

- Set `UNFOLD` identity from env-backed `NAME`.
- Keep sidebar/navigation permission-aware.
- Use callback links only for modules enabled in `INSTALLED_APPS`.
- Keep styles/scripts references in project static paths that actually exist.

Mandatory baseline overrides:
- `UNFOLD["SITE_HEADER"] = _(NAME)`
- `UNFOLD["SITE_TITLE"] = _(NAME)`
- `UNFOLD["ENVIRONMENT"] = f"{PROJECT_NAME}.utils.environment_callback"`
- `UNFOLD["STYLES"] = [lambda request: static("css/styles.css")] + UNFOLD["STYLES"]`
- `UNFOLD["SHOW_LANGUAGES"] = True`

Safety notes:
- Keep style list as prepend, do not overwrite base styles.
- Ensure `environment_callback` function exists and import path is valid.

## Profile Presets

### admin-core

- Minimal project apps.
- Admin-first setup.
- Scope default: `admin-only`.

### catalog-api

- Add DRF + drf-yasg + django-filter.
- Add API docs route and basic endpoint smoke checks.
- Keep import pipeline scripts explicit.

### portal-cms

- Multi-app content setup.
- i18n enabled by default.
- Async/cache path enabled by default.

## Validation Checklist (Settings)

Run after settings/bootstrap generation:

1. `python manage.py check`
2. `python manage.py migrate --noinput`
3. Verify admin login and admin index render.
4. If API enabled: verify docs endpoint opens.
5. If docker enabled: `docker compose -f docker/docker-compose.yml config`

## Anti-Patterns

- Hardcoding secrets in settings files.
- Mixing incompatible source modes for django-whiteneuron.
- Enabling cache middleware without a valid cache backend config.
- Disabling production security flags without explicit reason.
- Adding app registrations/navigation entries for features not installed.
