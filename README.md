# django-whiteneuron

A modern Django Admin extension focused on UI/UX, dashboard, feedback, file management, and advanced admin integrations — built on top of [django-unfold](https://github.com/unfoldadmin/django-unfold).

[![PyPI version](https://img.shields.io/pypi/v/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![Python](https://img.shields.io/pypi/pyversions/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)

![django-whiteneuron](https://raw.githubusercontent.com/White-Neuron/django-whiteneuron/main2.0/docs/images/main.png)

## Current Version
v0.3.4.11

## Changelog
### Latest: v0.3.4.11 (2026-06-18)
**Security: Upgrade cryptography ≥48.0.1, pyopenssl ≥26.2.0**
- **Updated**: `cryptography` minimum version bumped from `>=46.0.7` to `>=48.0.1` — resolves CVE with CVSS 7.5 (affects versions >=0.5.0,<48.0.1). Resolved to cryptography==49.0.0 by uv lock.
- **Updated**: `pyopenssl` pinned version changed from `==26.0.0` to `>=26.2.0` — required for compatibility with cryptography ≥48.0.1 (pyopenssl 26.3.0 resolved).
- **Compatibility**: No breaking changes; safe for all v0.3.x users. pyopenssl constraint relaxed from exact pin to minimum version.

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
uv add "django-whiteneuron==0.2.37"
```

### From GitHub tag

```bash
uv add "git+https://github.com/White-Neuron/django-whiteneuron.git@v0.2.37"
```

### From local source

```bash
uv pip install -e .
```

## Django Configuration

Add the apps at the top of `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "whiteneuron",
    "whiteneuron.base",
    "whiteneuron.feedbacks",
    "whiteneuron.file_management",
    "whiteneuron.contrib",
    "whiteneuron.dashboard",
    # ... your other apps
]
```

Add the required middleware **(order matters)**:

```python
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
```

Set the custom user model:

```python
AUTH_USER_MODEL = "base.User"
```

## UNFOLD Configuration Example

```python
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_HEADER": _("White Neuron"),
    "SITE_TITLE": _("White Neuron Admin"),
    "SITE_SUBHEADER": _("Admin panel"),
    # Use SITE_ICON instead of SITE_LOGO to keep SITE_TITLE rendering correctly
    "SITE_ICON": {
        "light": lambda request: static("base/images/logo/WhiteNeuron.png"),
        "dark": lambda request: static("base/images/logo/WhiteNeuron.png"),
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("base/images/logo/WhiteNeuron.png"),
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

## Frontend (Tailwind 4 + daisyUI 5)

Install frontend dependencies:

```bash
npm install -D @tailwindcss/cli@next daisyui@latest
```

Build CSS using the provided script:

```bash
bash scripts/tailwind.sh
```

Or run directly:

```bash
npx @tailwindcss/cli -i styles.css -o whiteneuron/static/base/css/styles.css --minify
```

## Running the Local Example

```bash
cd whiteneuron
python manage.py migrate
python manage.py runserver
```

Access the admin at: http://127.0.0.1:8000/admin/

## Building and Releasing the Package

To build the package (including Tailwind assets, migrations, and Python wheel):

```bash
bash scripts/build.sh
```

This script will:
- Build Tailwind CSS assets
- Run Django migrations
- Build the Python package using `uv build`

For a full release (with version bump, git tag, and release notes), follow the interactive prompts in `scripts/build.sh` or use the skill-driven workflow.

## Rate Limiting

`RateLimitMiddleware` limits by IP; `UserActivityMiddleware` limits by authenticated user. Redis is required for accuracy in multi-worker environments.

```python
# settings.py (hoặc env)
RATE_LIMIT_REQUESTS = 60   # số request tối đa / window (theo IP)
RATE_LIMIT_WINDOW    = 60   # tính bằng giây

USER_RATE_LIMIT_REQUESTS = 60  # theo user đã đăng nhập
USER_RATE_LIMIT_WINDOW   = 60
```

Corresponding env vars: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `USER_RATE_LIMIT_REQUESTS`, `USER_RATE_LIMIT_WINDOW`.

When the limit is exceeded:
- API requests (`/api/` or `Accept: application/json`) → JSON `{"detail": "Too many requests."}` with status 429.
- Browser requests → renders `429.html` template with `Retry-After` header.

## IP Blacklist

Two protection layers operate in parallel. Both are checked before rate limiting and return 403 immediately.

### Static — `.env` (CIDR ranges, infrastructure bans)

Loaded at startup, supports IPv4/IPv6 and CIDR:

```env
# .env
IP_BLACKLIST=185.220.101.5,194.165.16.0/22,2001:db8::/32
```

Requires a **Daphne/Gunicorn restart** to apply new entries.

### Dynamic — Django Admin + Redis (real-time)

Managed via **System → IP Blacklist** in the admin panel (superuser only):

- **Permanent block**: leave `blocked_until` empty
- **Temporary block**: set `blocked_until` → Redis TTL auto-expires, no cron needed
- **Quick block from logs**: *User Activity* → select records → **Block IP address** action → Redis key set immediately, no restart needed

```
Request → check static env blacklist (O(1))
        → check cache.get('blacklist:dynamic:<ip>') (1 Redis GET)
        → 403 nếu match, không tốn rate limit check
```

## Error Pages

Error templates live in `whiteneuron/templates/` and are used automatically by Django when `DEBUG=False`:

| Template | Error | Notes |
|---|---|---|
| `400.html` | Bad Request | |
| `403.html` | Forbidden | |
| `404.html` | Not Found | |
| `429.html` | Too Many Requests | Rendered manually by middleware, passes `{{ retry_after }}` |
| `500.html` | Server Error | |

No need to register `handler400/403/404/500` — Django resolves templates automatically via `APP_DIRS=True`.

## Environment Configuration

Copy `env.example` to your environment file and update variables such as `DATABASE`, `REDIS`, `EMAIL`, and `ALLOWED_HOSTS`.

## Contact

- Email: [anhnt@whiteneuron.com](mailto:anhnt@whiteneuron.com)
- Website: [https://whiteneuron.ai](https://whiteneuron.ai)
- GitHub: [https://github.com/White-Neuron/django-whiteneuron](https://github.com/White-Neuron/django-whiteneuron)

## License

MIT License.
