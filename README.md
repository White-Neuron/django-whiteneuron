# django-whiteneuron

A modern Django Admin extension focused on UI/UX, dashboard, feedback, file management, and advanced admin integrations — built on top of [django-unfold](https://github.com/unfoldadmin/django-unfold).

[![PyPI version](https://img.shields.io/pypi/v/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![Python](https://img.shields.io/pypi/pyversions/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/django-whiteneuron)](https://pypi.org/project/django-whiteneuron/)

## Current Version

- 0.2.40

## Compatibility

- Python >= 3.11
- Django >= 5.1.6
- django-unfold >= 0.85.0
- Tailwind CSS 4.x + daisyUI 5.x (for the bundled frontend styles)

## Changelog

### v0.2.40 (2026-03-31) — latest
**Improve: App Dashboard — two-level category/app grid, UI polish, i18n fixes**
- **Added**: Two-level App dashboard grid — category cards (level 1) expand to app cards (level 2) via Alpine.js client-side navigation, no page reload.
- **Added**: `app_change_list.html` model-specific template — category mosaic (2×2 icon grid), app card grid, back button, smooth transitions.
- **Improved**: Category mosaic — handles 1 app (single large icon), 2–3 apps (placeholder fill), 4 apps (full 2×2), 5+ apps (3 icons + "+N" counter on 4th cell).
- **Improved**: App card icon — removed incorrect `static()` wrapper on `thumbnail_url` (already a full URL).
- **Improved**: Search bar hidden on App dashboard (not usable in two-level layout).
- **Fixed**: `changelist_view` queryset evaluated once via `list(qs)` to avoid double `get_queryset()` / double `init_app_db()` call.
- **Fixed**: Translation `"Active"` → `"Hoạt động"` (was incorrectly `"Hành động"` = Action).
- **Fixed**: Removed incorrect `{% trans %}` on DB values (`category`, `app.name`) — Django `{% trans %}` only resolves catalog entries, DB values are already stored in the target language.

### v0.2.39 (2026-03-31)
**Fix: `get_client_ip()` — validate IP headers, fix block-all bug with Cloudflare Tunnel**
- **Fixed**: `CF-Connecting-IP` and `True-Client-IP` headers were not validated before use — raw strings could flow directly into Redis cache keys, causing incorrect rate limiting or unintended blocks.
- **Fixed**: `REMOTE_ADDR` was also used without validation — now normalized through `_parse_ip()` before use.
- **Fixed**: Block-all-users bug — when using Cloudflare **Tunnel** (`cloudflared`), `CF-Connecting-IP` is not set; code fell through to XFF which contained the Cloudflare Edge IP as the first entry → all users shared one IP bucket → blocking one user blocked everyone.
- **Added**: `_parse_ip()` helper — normalizes and validates IP strings via `ipaddress.ip_address()`, returns `None` for invalid input; applied to all header sources (CF, XFF, REMOTE_ADDR).
- **Improved**: XFF parsing refactored — uses an explicit loop with `_parse_ip()` per entry instead of a list comprehension calling `is_global_ip()` on raw strings.
- **Fixed**: `env.example` — corrected `BEHIND_CLOUDFLARE` default to `False` and added clear comment distinguishing Cloudflare Proxy vs Cloudflare Tunnel.

### v0.2.38 (2026-03-31)
**Security: UA Blacklist — block bots/crawlers by User-Agent**
- **Added**: `UABlacklist` model (`base/ua_blacklists`) — block requests by User-Agent pattern, managed via Django Admin in real-time.
- **Added**: `UABlacklistAdmin` — UI with Activate/Deactivate actions, `is_regex` toggle, shown in System sidebar under `block` icon, superuser only.
- **Added**: `RateLimitMiddleware._is_ua_blacklisted()` — two-layer check: static keywords from `UA_BLACKLIST` env (loaded at startup) + dynamic patterns from Redis cache (managed via admin, real-time).
- **Added**: `UA_BLACKLIST` setting in `env.example` — comma-separated substring keywords loaded at startup (no Redis required), e.g. `GPTBot,ClaudeBot,https://openai.com`.
- **Added**: Dynamic patterns support `is_regex=True` — executes `re.search(pattern, ua, re.IGNORECASE)`, invalid regex patterns are safely skipped per-entry.
- **Fixed**: Cache miss fallback — when Redis restarts or on first boot, patterns are loaded from DB and cache is warmed automatically (no bots slip through during cold start).
- **Added**: Migration `base/0016_uablacklist.py`.

### v0.2.37 (2026-03-31)
**Security: guest login — remove hardcoded password, passwordless login view**
- **Security**: Removed hardcoded password `'whiteneuron-guest-2024@'` from `init_guest.py` — guest user now created with `set_unusable_password()`, cannot be authenticated via password at all.
- **Security**: Removed JavaScript-based guest login button that exposed the password in plain HTML source — replaced with a server-side `GuestLoginView` (POST-only, CSRF-protected).
- **Added**: `GuestLoginView` at `base/guest-login/` — bypasses password authentication entirely, calls `login()` directly, validates `next` redirect with `url_has_allowed_host_and_scheme()`.
- **Improved**: `init_guest` command now sets `is_staff=True` explicitly on user creation.
- **CI**: Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to GitHub Actions workflow — prevents deprecation warnings for Node.js 20 before June 2026 deadline.

### v0.2.36 (2026-03-30)
**Security: init_admin — remove hardcoded password, random generation, auto email delivery**
- **Security**: Removed hardcoded password `'wnadmin2024&'` from `init_admin.py` — replaced with `secrets.choice()` (CSPRNG) generating a 20-character password (uppercase, lowercase, digits, special chars).
- **Added**: `INIT_ADMIN_PASSWORD` env var support — uses fixed password from `.env` if set, otherwise generates randomly.
- **Added**: `INIT_ADMIN_EMAIL` env var (required) — email recipient for the temporary password; no longer hardcoded.
- **Added**: Automatically sends password via `send_email_login()` using the standard project email template (company signature, login link) when password is random.
- **Added**: `--reset-password` flag for `init_admin` command — resets password for an existing admin without affecting normal CI/CD runs.
- **Fixed**: Double DB write when creating a new user — now a single `save()` call.
- **Fixed**: Email validation happens before writing password to DB — prevents password being changed without email delivery.
- **Improved**: `send_email_login()` accepts `is_reset` param — email subject adapts to context (new account vs reset).
- **Removed**: Unused `templates/admin/base/email_password.html`.

### v0.2.35 (2026-03-29)
**Dynamic IP Blacklist: Redis + Model + Admin**
- **Added**: `IPBlacklist` model (`base/ip_blacklists`) — manage blocked IPs in real-time via Django Admin, supports permanent and temporary blocks (`blocked_until` with Redis TTL auto-expiry).
- **Added**: `IPBlacklistAdmin` — IP blacklist management UI with Activate/Deactivate actions, shown in System sidebar under `block` icon, superuser only.
- **Added**: **"Block IP address"** action in `UserActivityAdmin` — select activity records → block IP immediately in Redis, no Daphne restart required.
- **Improved**: `RateLimitMiddleware._is_blacklisted()` also checks `cache.get('blacklist:dynamic:<ip>')` after static env blacklist — hybrid two-layer static + dynamic blocking.
- **Added**: Migration `base/0015_ipblacklist.py`.

### v0.2.34 (2026-03-29)
**IP Blacklist: permanent IP/CIDR blocking via `.env`**
- **Added**: `RateLimitMiddleware._is_blacklisted()` — checks IP/CIDR blacklist before rate limiting, returns 403 immediately for blocked IPs.
- **Added**: Parse `IP_BLACKLIST` from settings (comma-separated IPs and/or CIDRs), supports IPv4 and IPv6 — single IPs use `set` lookup O(1), CIDR ranges use `ip_network` match.
- **Added**: `IP_BLACKLIST` setting in `settings.py` and corresponding variable in `env.example`.

### v0.2.33 (2026-03-29)
**Rate Limiting fix for Docker + Daphne**
- **Fixed**: `_is_rate_limited()` and `_is_user_rate_limited()` now catch `except Exception: return False` — handles `ConnectionError` when Redis is unreachable in Docker (previously unhandled exception caused requests to crash or bypass rate limiting).
- **Fixed**: Default `RATE_LIMIT_REQUESTS` lowered from 300 → 60 req/60 s, `USER_RATE_LIMIT_REQUESTS` from 200 → 60 — appropriate for an admin panel.
- **Fixed**: `User.display_header()` uses `reverse('admin:base_user_change')` instead of hardcoded `/admin/base/user/` — prevents broken links when changing admin prefix.
- **Fixed**: Default `BEHIND_CLOUDFLARE=True` since deployments always use Cloudflare Tunnel.

### v0.2.32 (2026-03-29)
**Security hardening & Gunicorn production readiness**
- **Security**: `get_client_ip()` only trusts `CF-Connecting-IP` / `True-Client-IP` when `BEHIND_CLOUDFLARE=True` — prevents rate limit bypass via spoofed headers.
- **Fixed**: `UserActivityMiddleware.__call__()` caches `do_not_track()` result in `skip` — avoids double invocation per request.
- **Removed**: Unused `import logging` from middleware.py.

### v0.2.31 (2026-03-29)
**Rate Limiting, Security Hardening & Error Pages**
- **Added**: `RateLimitMiddleware` — global IP-based rate limiting (60 req/60 s default) placed immediately after `SecurityMiddleware`, works for both API and browser requests.
- **Improved**: `UserActivityMiddleware` adds per-user rate limiting (60 req/60 s default).
- **Added**: `/ws/` added to `UserActivityMiddleware` `exclude_paths` — WebSocket handshakes are not logged and not counted toward rate limits.
- **Security**: Sanitizes `POST` data before writing to `UserActivity` — masks sensitive fields (password, token, api_key, etc.).
- **Security**: Switched to `cache.incr()` first pattern (atomic on Redis) to prevent race conditions.
- **Added**: Full error templates: `400.html`, `403.html`, `404.html`, `429.html`, `500.html`.
- **Added**: Minimal `base.html` skeleton for error pages — no dependency on external static files.
- **Added**: Startup warning when running production without Redis (rate limiting inaccurate on multi-worker).

### v0.2.30 (2026-03-29)
- **Improved**: `AppAdmin.get_queryset()` returns only active apps the user actually has access to.
- **Improved**: `superuser` retains visibility over all active apps.

### v0.2.29 (2026-03-28)
- **Fixed**: `NotificationAdmin` no longer returns 403 when clicking `View Linked Object`.
- **Improved**: View linked object action routed via a dedicated detail action, better compatibility with Unfold.
- **Improved**: Safe handling when notification has no `obj_link`.

### v0.2.28 (2026-03-28)
- **Improved**: Grid view of user/app uses more intuitive icons for role and status.
- **Improved**: Standardized `verbose_name` for multiple fields in `Notification` and `NotificationConfig`.
- **Added**: Migration `notification/0012` to sync field-level metadata.

### v0.2.27 and earlier
See [releases](https://github.com/White-Neuron/django-whiteneuron/releases) for full history.

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
