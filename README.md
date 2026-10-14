# django-whiteneuron

A modern Django Admin extension focused on UI/UX, dashboard, feedback, file management, and advanced admin integrations — built on top of [django-unfold](https://github.com/unfoldadmin/django-unfold).

[![PyPI version](https://img.shields.io/pypi/v/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![Python](https://img.shields.io/pypi/pyversions/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)

![django-whiteneuron](https://raw.githubusercontent.com/White-Neuron/django-whiteneuron/main2.0/docs/images/main.png)

## Current Version
v0.4.0.0

## Changelog

### Latest: v0.4.0.0 (2026-10-13)
**Feature release: daisyUI multi-theme admin, server monitoring dashboard, django-unfold 0.109, security hardening and performance work**
- **Added**: 35 daisyUI themes selectable from the user menu (**Themes**); each theme also re-colors Unfold and drives its dark mode. `WN_ADMIN_THEMES` limits the picker (`[]` hides it); `WN_THEMES="nord,dracula" bash scripts/tailwind.sh` builds a smaller CSS bundle.
- **Added**: `whiteneuron.monitoring` — Grafana-style **Server monitoring** dashboard (CPU, memory, disk, load, network, disk I/O, request throughput, p50/p95/p99 latency, error rate, Apdex, slowest endpoints, DB/cache latency) with time ranges, auto-refresh, host selector and shared crosshair. Collect with `manage.py monitoring_collector` or the Celery task `whiteneuron.monitoring.tasks.collect_metrics`; configure with `WN_MONITORING`. New dependency: `psutil`.
- **Changed**: `django-unfold>=0.109.0,<0.111` (the cap is raised after each Unfold release is re-tested against the template overrides); template overrides ported; uses the avatar badge (unread notifications), sidebar sub-navigation (Celery "Schedules"), `SITE_VERSION`, theme-aware dashboard charts.
- **Security**: escaped notification/grid HTML (stored XSS), whitelisted `?display_fields` (a GET could call `obj.delete()`) and limited the column picker to fields shown on the change form (never `password`; extra exclusions via `ModelAdmin.field_selection_exclude`), staff-only per-user notification WebSocket with origin check, sandboxed uploaded-HTML preview, private exports scoped to the selected rows, `X-Forwarded-For` read from the right (`TRUSTED_PROXY_COUNT`, `IGNORE_X_FORWARDED_FOR`), open-redirect fix in guest login, new-user signal no longer overwrites passwords, `secrets`-based passwords redacted after sending (never passed to the task broker), POST-only feedback resolve, notification IDOR fix.
- **Performance**: activity logging 1 INSERT per request (was 3–4 queries), dashboard 4 queries (was ~16) + 60s cache, one `bulk_create` + one broadcast per notification, new indexes, atomic rate-limit counters, request-scoped admin state (grid view / page size no longer shared between users), thumbnails built at upload (regenerated if the file is missing), N+1 fixes, 14KB logo instead of 187KB.
- **Fixed**: dashboard date ranges overlapped by a day, `App.__str__` crash on create, export action signature, `readonly_fields` growing per request, header horizontal overflow on phones, `_(f"…")` strings that could never be translated, Chart.js crash on oklch theme colors, notification WebSocket reconnect loops, monitoring collector stopping when the cache is down, missing site branding (sidebar logo/title) on the monitoring dashboard and admin index, flash messages shown twice on the admin index, changelist toolbar (filter / grid / page-size) hidden for admins without `search_fields`, "Next" enabled on the last page and Previous/Next stuck disabled when Django ignores `?all`, unreadable monitoring colors under several themes, markdown preview styles (md2html_tailwind4 classes were never compiled); Vietnamese translations updated.
- **Compatibility**: `ModelAdmin.request` still works (now request-scoped, not stored on the shared instance); the *Server monitoring* sidebar link follows the `monitoring.view_metricsample` permission; in the default light/dark modes daisyUI components take their base/primary colors from `UNFOLD["COLORS"]`.
- **Validation**: 42 package tests pass (`manage.py test whiteneuron`, also under the package's own settings via `whiteneuron.base.testing.package_test_settings`, and from a clean wheel install with django-unfold 0.110.0), `check` clean, `makemigrations` reports no changes, no untranslated Vietnamese strings, Tailwind build and `uv build` succeed; 101 admin URLs swept in a README-style project; changelists, add/change forms, the monitoring dashboard under all 35 themes and the theme picker checked in Chromium (desktop + mobile).
- **Breaking / behavior changes**:
  - `SECRET_KEY` is required when `DEBUG=False` (build commands such as `collectstatic` are exempt).
  - `WN_ASYNC_TASKS` (Celery for email, export, GPT translation) is opt-in; without it these run inline.
  - Client IP: auto mode uses the right-most public `X-Forwarded-For` hop — set `TRUSTED_PROXY_COUNT`, or `IGNORE_X_FORWARDED_FOR=True` when the app is not behind a proxy.
  - Whole-page cache middleware only with `USE_CACHE_MIDDLEWARE=True`; `EXTENSIONS.modeltranslation` and `compressed_fields` removed (dropped by Unfold); new notifications store plain-text titles and JSON `changed_data`.
  - Project overrides of `unfold/helpers/navigation_user.html` should be compared with Unfold 0.109.
- **Upgrade Guidance**: `pip install --upgrade django-whiteneuron`, add `"whiteneuron.monitoring"` to `INSTALLED_APPS`, run `migrate` (indexes + monitoring table), `compilemessages`, and start `monitoring_collector` on each host.
- **Rollback**: revert to v0.3.8.0 after `migrate monitoring zero`, `migrate base 0027` and `migrate notification 0012` (index-only migrations; no data loss).

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.8.0 (2026-09-25)
**Bugfixes: Django 6 format_html crash in Image previews, app mosaic thumbnail URLs, SHOW_FILE_MANAGEMENT sidebar flag**
- **Fixed**: `Image.imgThumbnail()` and `Image.imgPreview()` admin methods — replaced f-string interpolation inside `format_html()` with the proper template + args pattern; resolves the rendering crash on Django 6 and ensures interpolated values are HTML-escaped.
- **Fixed**: App changelist mosaic thumbnails (`templates/admin/base/app_change_list.html`) — relative `thumbnail_url` paths are now wrapped in `{% static %}` while absolute/protocol-relative URLs pass through unchanged, fixing broken thumbnail images.
- **Fixed**: `SHOW_FILE_MANAGEMENT=False` is no longer silently ignored — the Unfold sidebar is built conditionally at definition time instead of post-processing by title match; when disabled, File Management items merge into the System section before Notifications config.
- **Compatibility**: No breaking changes; safe for all v0.3.x users. Django 6.0.x only.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.7.0 (2026-08-23)
**Security: Patch 6 CVEs across django, cryptography, sqlparse, setuptools**
- **Fixed**: Upgraded `django` lower bound to patch CVE-2026-15830 (GeoDjango DoS).
- **Fixed**: Upgraded `pyopenssl` to `>=26.4.0` — patches CVE-2026-69247 (Bleichenbacher oracle attack).
- **Fixed**: Added `sqlparse >=0.6.0` via transitive deps — patches 3 DoS CVEs (CVE-2026-71491, CVE-2026-54284, CVE-2026-59893).
- **Fixed**: Added `setuptools >=75.1.0` to build-system — patches CVE-2025-47273.
- **Compatibility**: No breaking changes; safe for all v0.3.x users. Django 6.0.x only.

### Latest: v0.3.5 (2026-07-15)
**Feature: Public/private file access control and HTML file support**
- **Added**: `is_public`, `allowed_users`, `allowed_groups` fields to `BaseFile` model — files can now be marked public or restricted to specific users/groups.
- **Added**: `_check_access()` permission logic in download/preview views — enforces access control before serving files.
- **Added**: `HTMLFile` model with inline preview support.
- **Improved**: Admin UI — public/private badge column, conditional Access Control fieldset for private files.
- **Compatibility**: No breaking changes; safe for all v0.3.x users.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.4.12 (2026-06-27)
**Cleanup: Remove .DS_Store from tracking, feedback list in admin, remove md2html-tailwind4 uv source**
- **Removed**: 7 `.DS_Store` files removed from git tracking — added `*/.DS_Store` to `.gitignore`.
- **Added**: `FeedbackBaseAdmin.render_change_form()` loads and passes `feedback_list` context for displaying feedback entries per model instance in admin change form.
- **Removed**: `[tool.uv.sources]` block for `md2html-tailwind4` from `pyproject.toml`.
- **Updated**: Tailwind CSS regenerated with v4.1.16.
- **Compatibility**: No breaking changes; safe for all v0.3.x users.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.4.10 (2026-06-12)
**Security patch: Upgrade Django to 6.0.6+ (CVE-2026-8404, CVE-2026-48587, CVE-2026-6873)**
- **Fixed**: Upgraded `django` lower bound from `>=6.0.6` to `>=6.0.6,<7.0.0` — patches 5 security vulnerabilities: CVE-2026-8404 (CVSS 5.3), CVE-2026-48587 (CVSS 5.3), CVE-2026-6873 (CVSS 4.3), CVE-2026-7666 (CVSS 2.3), CVE-2026-35193 (CVSS 2.3).
- **Compatibility**: No breaking changes; safe for all v0.3.x users. Django 6.0.x only — pinned upper bound `<7.0.0`.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.4.8 (2026-05-24)
**Feature: Badge callback caching layer for dashboard performance optimization**
- **Added**: Django cache-backed badge callbacks for dashboard model badges with 60s TTL to reduce database queries.
- **Added**: Per-user cached notification badge with 60s TTL and unauthenticated user guard.
- **Improved**: Replaced `timezone.now()` with `timezone.localtime()` across all badge queries.
- **Compatibility**: No breaking changes; safe for all v0.3.x users. Requires Django cache backend configured.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.4.6.2 (2026-05-14)
**Improvement: Configurable rate-limit exempt paths and user activity exclude paths**
- **Improved**: `RateLimitMiddleware` now reads `RATE_LIMIT_EXEMPT_PATHS` from Django settings — comma-separated list of additional path prefixes to exclude from rate limiting.
- **Improved**: `UserActivityMiddleware` now reads `USER_ACTIVITY_EXCLUDE_PATHS` from Django settings — semicolon-separated list of `path,condition` pairs for excluding paths from activity tracking and rate limiting.
- **Compatibility**: No breaking changes; safe for all v0.3.x users. New settings are optional.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.3.4 (2026-04-30)
**Patch release: Remove synchronization module, add language switcher template, update Vietnamese i18n**
- **Removed**: `synchronization/` module — cleaned up unused sync models, admin, views, tests, and migrations
- **Added**: Language switcher template for Unfold admin (`language_switch.html`) with multi-language support via `show_languages` context variable
- **Improved**: Vietnamese translations updated — removed stale synchronization references, added new entries for user profile and HTML editor
- **Compatibility**: No breaking changes; safe for all v0.3.3.x users
- **Validation**: Build, migrations (no changes), and manual admin UI/UX validation performed
- **Upgrade Guidance**: No manual migration required; upgrade recommended for all users on v0.3.3.x
- **Rollback**: Safe to revert to v0.3.3.3; no schema changes introduced

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## Table of Contents

- [Changelog](#changelog)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Modules](#modules)
- [Middleware & Security](#middleware--security)
- [Frontend](#frontend)
- [Environment Variables](#environment-variables)
- [Management Commands](#management-commands)
- [Building & Releasing](#building--releasing)
- [Documentation](#documentation)
- [Contact](#contact)

## Giới thiệu

Xem [docs/INTRODUCTION.md](docs/INTRODUCTION.md) để tìm hiểu chi tiết về django-whiteneuron — tại sao nên dùng, tính năng nổi bật và ai phù hợp.

## Features

| Category | Feature | Description |
|---|---|---|
| **Core** | Custom User Model | UUID-based user model with bot support, avatar, biography |
| **Core** | Soft Delete System | `BaseModel` with soft delete, restore, and audit trail (`created_by`, `updated_by`) |
| **Core** | Auto Notifications | Real-time WebSocket notifications on CRUD operations via `BaseModel.save()` |
| **Dashboard** | Admin Dashboard | Custom dashboard callback with badge system, cache-backed for performance |
| **Security** | Rate Limiting | IP-based and user-based rate limiting with Redis backend (429 responses) |
| **Security** | IP Blacklist | Static (`.env` CIDR) + dynamic (admin-managed, Redis TTL) blocking |
| **Security** | UA Blacklist | User-Agent substring/regex matching via admin panel or `.env` |
| **Tracking** | Activity Logs | `UserActivity`, `AnonymousActivity`, `VisitProfile` — full request audit trail |
| **Files** | File Management | Excel/PDF upload with SHA-256 integrity verification |
| **Feedback** | Feedback System | Per-model feedback collection, viewable in admin change forms |
| **Admin** | Grid View | Card-based user listing with avatar, badges, and role indicators |
| **Admin** | Import/Export | `django-import-export` integration for data portability |
| **Admin** | Simple History | `django-simple-history` tracking on all models |
| **Admin** | Guardian Integration | Object-level permissions via `django-guardian` |
| **Editor** | CKEditor 5 | Rich text editing with Tailwind-styled output |
| **Email** | Login Notifications | Auto-generate password + send login email on user creation |

## Installation

### From PyPI (recommended)

```bash
pip install django-whiteneuron
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add django-whiteneuron
```

### Specific version from PyPI

```bash
uv add "django-whiteneuron==0.3.4.12"
```

### From GitHub tag

```bash
uv add "git+https://github.com/White-Neuron/django-whiteneuron.git@v0.3.4.12"
```

### From local source

```bash
uv pip install -e .
```

## Quick Start

```bash
# 1. Add to INSTALLED_APPS (top of list)
# settings.py
INSTALLED_APPS = [
    "whiteneuron",
    "whiteneuron.base",
    "whiteneuron.feedbacks",
    "whiteneuron.file_management",
    "whiteneuron.contrib",
    "whiteneuron.dashboard",
    # ... your other apps
]

# 2. Set custom user model
AUTH_USER_MODEL = "base.User"

# 3. Add middleware (order matters)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whiteneuron.base.middleware.RateLimitMiddleware",   # ← immediately after SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whiteneuron.base.middleware.ReadonlyExceptionHandlerMiddleware",
    "whiteneuron.base.middleware.UserActivityMiddleware",  # ← after AuthenticationMiddleware
    "whiteneuron.base.middleware.ThreadLocalMiddleware",
]

# 4. Run migrations
python manage.py migrate

# 5. Create superuser and start
python manage.py createsuperuser
python manage.py runserver
```

Access the admin at: `http://127.0.0.1:8000/admin/`

## Configuration

### UNFOLD Settings Example

```python
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_HEADER": _("White Neuron"),
    "SITE_TITLE": _("White Neuron Admin"),
    "SITE_SUBHEADER": _("Admin panel"),
    "SITE_ICON": {
        "light": lambda request: static("base/images/logo/WhiteNeuron-128.png"),
        "dark": lambda request: static("base/images/logo/WhiteNeuron-128.png"),
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: static("base/images/logo/WhiteNeuron-32.png"),
        },
    ],
    "SHOW_HISTORY": False,
    "SHOW_LANGUAGES": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "DASHBOARD_CALLBACK": "whiteneuron.dashboard.views.dashboard_callback",
    "LOGIN": {
        "image": lambda request: static("base/images/login-bg.jpg"),
    },
    "STYLES": [
        lambda request: static("base/css/styles.css"),
        lambda request: static("base/css/btn-styles.css"),
        lambda request: static("base/css/loading.css"),
    ],
    "SCRIPTS": [
        lambda request: static("base/js/loading.js"),
        lambda request: static("base/js/whiteneuron.js"),
    ],
    "BORDER_RADIUS": "6px",
}
```

### Server monitoring dashboard

`whiteneuron.monitoring` adds a Grafana-style dashboard at **System → Server monitoring**
(superusers, or staff with the `view_metricsample` permission):

- **Overview**: uptime, CPU, memory, disk, load, throughput, 5xx error rate and p95 latency,
  with sparklines and green / orange / red thresholds.
- **System**: CPU / memory / disk gauges, per-core heatmap, CPU, load, memory, disk I/O,
  network and disk space time series.
- **Application** (from the request logs `UserActivityMiddleware` already writes): requests
  per minute by outcome, p50 / p95 / p99 latency, status-code breakdown, Apdex score, and the
  slowest endpoints (IDs are grouped, e.g. `/user/:id/change/`).
- **Process & dependencies**: database and cache round-trip time, app memory and threads.
- Time range 5m–7d, auto-refresh (off–5m), host selector, shared crosshair across charts,
  shareable URLs (`?range=6h&refresh=30s&host=web-1`), follows the selected admin theme.

Add `"whiteneuron.monitoring"` to `INSTALLED_APPS`, run `migrate`, then collect samples on
each host (the dashboard also stores a sample while it is open, at most once per interval):

```bash
python manage.py monitoring_collector              # long-running, e.g. a systemd service
python manage.py monitoring_collector --once       # single sample (cron)
```

or schedule the Celery task `whiteneuron.monitoring.tasks.collect_metrics` with celery beat.

```python
WN_MONITORING = {
    "INTERVAL": 15,          # seconds between samples
    "RETENTION_DAYS": 7,     # older samples are pruned automatically
    "DISK_PATH": "/",        # filesystem shown in the disk panels
    # "HOST": "web-1",       # defaults to the machine hostname
}
```

### Admin themes (daisyUI)

All 35 daisyUI themes are compiled into `base/css/styles.css` and selectable from the user menu (**Themes**). The selected theme also re-colors Unfold (primary/base palettes), and its light/dark scheme drives Unfold's dark mode. The choice is stored per browser.

```python
# Optional: limit the themes offered in the picker (Light/Dark/System are always available)
WN_ADMIN_THEMES = ["corporate", "nord", "dracula", "forest"]  # [] hides the picker
```

To ship a smaller CSS bundle, compile only some themes: `WN_THEMES="nord,dracula" bash scripts/tailwind.sh`.

## Modules

| Module | Description | Key Models |
|---|---|---|
| `whiteneuron.base` | Core models, admin, middleware, utilities | `User`, `BaseModel`, `Image`, `Mail`, `App`, `IPBlacklist`, `UABlacklist` |
| `whiteneuron.dashboard` | Dashboard callback and badge system | — |
| `whiteneuron.notification` | WebSocket real-time notifications | `Notification`, `NotificationConfig` |
| `whiteneuron.file_management` | File upload with integrity verification | `ExcelFile`, `PDFFile` |
| `whiteneuron.feedbacks` | Per-model feedback collection | — |

## Middleware & Security

### Rate Limiting

```python
RATE_LIMIT_REQUESTS = 60   # max requests per window (by IP)
RATE_LIMIT_WINDOW     = 60  # in seconds
USER_RATE_LIMIT_REQUESTS = 60  # by authenticated user
USER_RATE_LIMIT_WINDOW   = 60
```

When limit exceeded:
- API (`/api/` or `Accept: application/json`) → JSON `{"detail": "Too many requests."}` (429)
- Browser → renders `429.html` with `Retry-After` header

### IP Blacklist

**Static** — `.env` (CIDR ranges, loaded at startup):
```env
IP_BLACKLIST=185.220.101.5,194.165.16.0/22,2001:db8::/32
```

**Dynamic** — Admin panel + Redis (real-time):
- Permanent block: leave `blocked_until` empty
- Temporary block: set `blocked_until` → Redis TTL auto-expires

### UA Blacklist

Static via `.env`:
```env
UA_BLACKLIST=GPTBot,ClaudeBot,https://openai.com
```

Dynamic via admin — supports regex patterns with real-time cache rebuild.

## Frontend (Tailwind 4 + daisyUI 5)

```bash
npm install -D @tailwindcss/cli@next daisyui@latest
bash scripts/tailwind.sh
```

Or directly:
```bash
npx @tailwindcss/cli -i styles.css -o whiteneuron/static/base/css/styles.css --minify
```

## Environment Variables

Copy `env.example` to `.env` and configure. Key variables:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | — |
| `DEBUG` | Debug mode | `True` |
| `DATABASE` | Database type (`sqlite`/`postgres`) | `sqlite` |
| `REDIS` / `CACHE_REDIS_LOCATION` | Redis connection | `redis://127.0.0.1:6379` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `RATE_LIMIT_REQUESTS` | IP rate limit count | `60` |
| `IP_BLACKLIST` | Static IP blocks (CIDR) | — |
| `UA_BLACKLIST` | Static UA blocks | — |

See `env.example` for the full list.

## Management Commands

| Command | Description |
|---|---|
| `init_admin` | Create initial admin user |
| `init_guest` | Create guest user account |
| `init_groupuser` | Initialize group users |
| `cleanup_old_activities` | Remove old activity records |
| `update_visit_profiles` | Update visit profile data |

## Building & Releasing

```bash
bash scripts/build.sh
```

This builds Tailwind CSS assets, runs migrations, and creates the Python package via `uv build`.

## Error Pages

Templates in `whiteneuron/templates/` are used automatically when `DEBUG=False`:

| Template | Error |
|---|---|
| `400.html` | Bad Request |
| `403.html` | Forbidden |
| `404.html` | Not Found |
| `429.html` | Too Many Requests |
| `500.html` | Server Error |

## Documentation

- **Giới thiệu**: Xem [docs/INTRODUCTION.md](docs/INTRODUCTION.md) — tài liệu giới thiệu dự án, tính năng nổi bật và ai nên dùng.
- **Hướng dẫn chi tiết**: Xem [docs/GUIDE.md](docs/GUIDE.md) cho tài liệu module, model, middleware và cấu hình đầy đủ.
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md) for full version history.
- **CKEditor 5 Customization**: See [docs/CKEDITOR5_CUSTOMIZATION.md](docs/CKEDITOR5_CUSTOMIZATION.md).

## Contact

- Email: [anhnt@whiteneuron.com](mailto:anhnt@whiteneuron.com)
- Website: [https://whiteneuron.ai](https://whiteneuron.ai)
- GitHub: [https://github.com/White-Neuron/django-whiteneuron](https://github.com/White-Neuron/django-whiteneuron)

## License

MIT License.
