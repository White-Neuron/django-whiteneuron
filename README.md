# django-whiteneuron

A modern Django Admin extension focused on UI/UX, dashboard, feedback, file management, and advanced admin integrations — built on top of [django-unfold](https://github.com/unfoldadmin/django-unfold).

[![PyPI version](https://img.shields.io/pypi/v/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![Python](https://img.shields.io/pypi/pyversions/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)

![django-whiteneuron](https://raw.githubusercontent.com/White-Neuron/django-whiteneuron/main2.0/docs/images/main.png)

## Current Version

- 0.3.2

## Compatibility

- Python >= 3.11
- Django >= 5.2.13
- django-unfold >= 0.89.0
- Tailwind CSS 4.x + daisyUI 5.x (for the bundled frontend styles)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### Latest: v0.3.2 (2026-04-27)
**Feature: VisitProfile-based activity tracking for authenticated + anonymous users, dashboard analytics expansion**
- **Added**: `VisitProfile` model — deduplicates visits by IP+UserAgent; new `AnonymousActivity` model for unauthenticated tracking.
- **Refactored**: `UserActivity` — replaced direct ip_address/user_agent with FK to VisitProfile.
- **Added**: Dashboard KPI cards and 28-day chart expanded for anonymous visit analytics.
- **Added**: Admin views for VisitProfile, AnonymousActivity; inline activity viewing from User detail page.

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

## Building the Package

```bash
uv build
```

Or use the all-in-one build script:

```bash
bash scripts/build.sh
```

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
