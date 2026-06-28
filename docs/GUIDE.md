# django-whiteneuron — Detailed Guide

This guide covers all modules, models, middleware, and configuration options in detail. For a quick overview, see [README.md](../README.md).

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Installation & Setup](#2-installation--setup)
3. [Core Models](#3-core-models)
4. [Middleware System](#4-middleware-system)
5. [Dashboard Module](#5-dashboard-module)
6. [Notification Module](#6-notification-module)
7. [File Management Module](#7-file-management-module)
8. [Feedback Module](#8-feedback-module)
9. [Admin Customizations](#9-admin-customizations)
10. [Environment Configuration](#10-environment-configuration)
11. [Management Commands](#11-management-commands)
12. [Frontend Build System](#12-frontend-build-system)
13. [Error Pages & Templates](#13-error-pages--templates)
14. [Security Checklist](#14-security-checklist)

---

## 1. Architecture Overview

```
django-whiteneuron/
├── whiteneuron/
│   ├── base/              # Core: models, admin, middleware, utilities
│   ├── dashboard/         # Dashboard callback with KPI charts
│   ├── notification/      # WebSocket real-time notifications
│   ├── file_management/   # File upload with integrity verification
│   ├── feedbacks/         # Per-model feedback collection
│   └── contrib/           # Contrib apps placeholder
```

**Key design principles:**

- **`BaseModel`** — All domain models inherit from `BaseModel`, which provides soft delete, audit trail (`created_by`, `updated_by`), and auto-notification on CRUD operations.
- **Middleware chain** — Security (rate limit → IP/UA blacklist) → Activity tracking → Thread-local request context.
- **Redis-backed caching** — Rate limits, blacklists, badge callbacks all use Redis for accuracy in multi-worker deployments.

---

## 2. Installation & Setup

### Step 1: Install the package

```bash
pip install django-whiteneuron
# or
uv add django-whiteneuron
```

### Step 2: Configure `INSTALLED_APPS`

Add these **at the top** of your `INSTALLED_APPS`:

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

### Step 3: Set the custom user model

```python
AUTH_USER_MODEL = "base.User"
```

### Step 4: Configure middleware (order matters)

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whiteneuron.base.middleware.RateLimitMiddleware",     # ← immediately after SecurityMiddleware
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

### Step 5: Run migrations and start

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## 3. Core Models

### `User` (AUTH_USER_MODEL)

Custom user model extending `AbstractUser`.

| Field | Type | Description |
|---|---|---|
| `uuid` | UUIDField | Unique identifier, auto-generated |
| `avatar` | ImageField | User avatar image |
| `biography` | TextField | User bio text |
| `is_bot` | BooleanField | Designates bot accounts |
| `show_softdelete` | BooleanField | Whether to show soft-deleted items in list views |

**Methods:**
- `display_avatar()` — Returns HTML for avatar display (bot icon or image)
- `display_header()` — Returns HTML card with avatar + username link to admin change page
- `full_name` property — Returns `"last_name first_name"` with "(bot)" suffix if applicable

### `BaseModel` (Abstract base class)

All domain models should inherit from this. Provides:

| Feature | Description |
|---|---|
| **Soft Delete** | `.delete()` marks `is_deleted=True`, `.hard_delete()` removes permanently, `.restore()` undeletes |
| **Audit Trail** | Auto-sets `created_by`, `updated_by`, `created_at`, `updated_at` from the current request user |
| **Auto Notifications** | On `save()`, creates `Notification` objects for all superusers (create/update events) |
| **M2M Tracking** | Automatically tracks ManyToMany field changes via Django signals, updates timestamps and sends notifications |

**Usage:**

```python
from whiteneuron.base.models import BaseModel

class Article(BaseModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    categories = models.ManyToManyField(Category)  # M2M changes are tracked automatically
```

### `SoftDeleteModel` (Abstract base class)

Minimal soft delete without audit fields. Use when you don't need `created_by`/`updated_by`.

| Method | Description |
|---|---|
| `.delete()` | Soft deletes (sets `is_deleted=True`, `deleted_at=now`) |
| `.hard_delete()` | Permanently removes from database |
| `.restore()` | Restores a soft-deleted object |

### `Image` Model

System image management with automatic thumbnail and preview generation.

| Field | Type | Description |
|---|---|---|
| `image` | ImageField | Original uploaded image |
| `thumbnail` | ImageField | Auto-generated 256x256 thumbnail |
| `preview` | ImageField | Auto-generated max 1280x1280 preview |
| `description` | TextField | Optional description |

**Methods:**
- `imgThumbnail()` — Returns HTML preview of thumbnail in admin
- `imgPreview()` — Returns HTML with full-size image link and preview
- `set_image_from_pilimage(pilimage, fname)` — Sets image from a PIL Image object
- `hard_delete()` — Deletes file from storage along with the record

**EXIF Orientation Handling:** Automatically rotates images based on EXIF orientation tag (values 3, 6, 8).

### `Mail` Model

Email notification tracking.

| Field | Type | Description |
|---|---|---|
| `subject` | CharField | Email subject |
| `content` | TextField | HTML email content |
| `receiver` | EmailField | Recipient address |
| `status` | CharField | `pending`, `sent`, or `failed` |

**Method:** `.send()` — Sends via SMTP (Gmail SSL on port 465), updates status.

### `App` Model

Dashboard sidebar app entries. Managed through UNFOLD `SIDEBAR.navigation` settings, not directly in admin.

| Field | Type | Description |
|---|---|---|
| `name` | CharField | Display name |
| `icon` | CharField | Material Symbols Outlined icon name or URL |
| `url` | URLField | Target URL |
| `category` | CharField | Grouping category |
| `permission` | CharField | Permission function string to gate access |

### `IPBlacklist` Model

Dynamic IP blocking managed via admin panel.

| Field | Type | Description |
|---|---|---|
| `ip_address` | GenericIPAddressField | Single IPv4 or IPv6 address |
| `reason` | CharField | Reason for blocking |
| `is_active` | BooleanField | Whether the block is active |
| `blocked_until` | DateTimeField | Temporary block expiry (empty = permanent) |

**Cache sync:** On save/delete, automatically updates Redis cache key `blacklist:dynamic:<ip>`.

### `UABlacklist` Model

Dynamic User-Agent blocking with substring or regex matching.

| Field | Type | Description |
|---|---|---|
| `pattern` | CharField | Substring or regex pattern |
| `is_regex` | BooleanField | Whether to treat as Python regex |
| `reason` | CharField | Reason for blocking |
| `is_active` | BooleanField | Whether the rule is active |

**Cache:** Rebuilds Redis cache key `blacklist:ua_patterns` on every save/delete.

### `VisitProfile`, `UserActivity`, `AnonymousActivity`

Tracking models for visit and activity logging.

- **`VisitProfile`** — Groups activities by IP + User-Agent combination
- **`UserActivity`** — Logged requests by authenticated users (FK to `User`)
- **`AnonymousActivity`** — Logged requests by unauthenticated visitors

All include: `path`, `method`, `data` (JSON), `status_code`, `timestamp`, `timelapse`.

---

## 4. Middleware System

### `RateLimitMiddleware`

IP-based rate limiting with Redis backend.

| Setting | Default | Description |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | 300 | Max requests per window per IP |
| `RATE_LIMIT_WINDOW` | 60 | Window size in seconds |
| `RATE_LIMIT_EXEMPT_PATHS` | — | Additional comma-separated path prefixes to exempt |

**Flow:**
1. Check static `.env` blacklist (O(1) for IPs, CIDR support)
2. Check Redis dynamic blacklist (`blacklist:dynamic:<ip>`)
3. If blacklisted → 403 immediately
4. Check UA blacklist (static keywords + dynamic patterns from cache/DB)
5. If UA blocked → 403
6. Increment rate limit counter in Redis
7. If exceeded → 429 with `Retry-After` header

**Exempt paths:** `/static/`, `/media/`, `/__debug__/`, `/__reload__/`, `/.well-known/` plus any configured via `RATE_LIMIT_EXEMPT_PATHS`.

### `UserActivityMiddleware`

Authenticated user rate limiting + activity logging.

| Setting | Default | Description |
|---|---|---|
| `USER_RATE_LIMIT_REQUESTS` | 200 | Max requests per window per authenticated user |
| `USER_RATE_LIMIT_WINDOW` | 60 | Window size in seconds |
| `USER_ACTIVITY_EXCLUDE_PATHS` | — | Semicolon-separated `path,condition` pairs to exclude from logging/rate-limiting |

**Features:**
- Per-user rate limiting (separate from IP-based)
- Automatic activity logging for all requests (authenticated + anonymous)
- Body data sanitization: masks sensitive fields (`password`, `token`, `api_key`, etc.) and detects JWT/long base64/hex values
- Reads request body early (up to 1MB) before DRF consumes it, stores as JSON for logging

**Excluded paths by default:** `/media/`, `/static/`, `/__reload__/`, `/base/useractivity/`, `/__debug__/`, `/jsi18n/`, `/.well-known/`, `/ws/` (WebSocket), `/health/`.

### `ReadonlyExceptionHandlerMiddleware`

Catches `OperationalError('attempt to write a readonly database')` and redirects to login with a warning message.

### `ThreadLocalMiddleware`

Stores the current request in thread-local storage so models can access it during `save()`.

### `AutoGuestLoginMiddleware`

Automatically logs in the `guest` user when accessing paths containing "login" (if `SKIP_GUEST_LOGIN=False`).

### `ForceDefaultLanguageMiddleware`

Uses `LANGUAGE_CODE` as default unless the user has explicitly chosen a language via cookie or URL prefix.

---

## 5. Dashboard Module

### `dashboard_callback(request, context)`

The DASHBOARD_CALLBACK function for UNFOLD. Provides:

**KPI Cards:**
- User activities count (with comparison to previous period)
- Anonymous visits count (with comparison to previous period)
- Success rate percentages

**Charts:**
- 28-day rolling chart showing user/anonymous activity trends
- Separate datasets for success and error counts
- Average trend lines

**Time filters:** Today, 7 days, Week, Month, Year — all with period-over-period comparisons.

**Usage in settings:**
```python
UNFOLD = {
    "DASHBOARD_CALLBACK": "whiteneuron.dashboard.views.dashboard_callback",
}
```

---

## 6. Notification Module

### `Notification` Model

Real-time notifications delivered via WebSocket + JavaScript alerts.

| Field | Type | Description |
|---|---|---|
| `user` | FK → User | Recipient of the notification |
| `title` | CharField | Notification title |
| `content` | TextField | HTML content body |
| `obj_link` | CharField | Link to the related object in admin |
| `flag` | CharField | Type: `info`, `success`, `warning`, `error`, `danger` |
| `action` | CharField | Event type: `create`, `update`, `delete`, `restore` |
| `changed_data` | TextField | JSON-serialized field changes |
| `is_read` | BooleanField | Read/unread status |
| `action_by` | FK → User | User who triggered the event |

**Methods:**
- `.mark_as_read()` / `.mark_as_unread()` — Toggle read status
- `.mark_as_read_all(user)` / `.mark_as_unread_all(user)` — Bulk operations
- `.alert()` — Sends WebSocket notification + JavaScript alert to admin users

### `NotificationConfig` Model

Per-model event configuration for notifications.

| Field | Type | Description |
|---|---|---|
| `model` | FK → ContentType | Target Django model |
| `event_type` | CharField | `all`, `create`, `update`, `delete` |
| `send_to_admin` | BooleanField | Notify superusers |
| `send_to_user` | BooleanField | Notify the object owner |
| `send_to_group_user` | BooleanField | Notify group members |

---

## 7. File Management Module

### `BaseFile` (Abstract)

Base class for file models with SHA-256 integrity verification.

**Features:**
- Automatic hash computation on upload (`compute_file_hash()`)
- Integrity verification: `.verify_integrity()` compares stored hash against current file content
- Status tracking: `pending`, `done`, `error`
- Method tracking: `upload` (manual) or `auto` (programmatic)

### `ExcelFile` / `PDFFile`

Concrete implementations storing files in `/excels/` and `/pdfs/` upload directories.

**Usage:**
```python
from whiteneuron.file_management.models import ExcelFile, PDFFile

# Upload via admin or programmatically
excel = ExcelFile.objects.create(
    title="Report Q1",
    file=my_file_field,  # Uploaded file
)
# Hash is auto-computed on save
assert excel.verify_integrity() == True
```

---

## 8. Feedback Module

Per-model feedback collection system. Feedback entries are viewable in the admin change form via `FeedbackBaseAdmin.render_change_form()`, which passes a `feedback_list` context variable.

**Integration:** Add `FeedbackBaseAdmin` as a mixin or use it directly for your model admins to show related feedback on the change form.

---

## 9. Admin Customizations

### User Admin (`UserAdmin`)

- **Grid View**: Card-based listing with avatar, status badges (Active/Inactive), role indicators (Staff/Admin/Bot)
- **Activity Inline**: Shows `UserActivity` records in a tabbed inline
- **Auto email on creation**: Generates random password and sends login credentials via email
- **Custom form**: Password not required during user creation (auto-generated)

### App Admin (`AppAdmin`)

Read-only dashboard view that renders sidebar apps from UNFOLD settings. Filters by permission if the user is not a superuser.

### IP/UA Blacklist Admins

- Activate/deactivate bulk actions
- `IPBlacklistAdmin.block_ip` action on UserActivity records for quick blocking
- Auto Redis cache sync on save/delete

---

## 10. Environment Configuration

See `env.example` for the full list. Key settings:

### Database

```env
DATABASE=sqlite        # or postgres
# PostgreSQL (uncomment when using)
# DATABASE_NAME=mydb
# DATABASE_USER=myuser
# DATABASE_PASSWORD=mypassword
# DATABASE_HOST=localhost
# DATABASE_PORT=5432
```

### Redis & Cache

```env
USE_CACHE=True
CACHENAME=redis
CACHE_REDIS_LOCATION=redis://127.0.0.1:6379
CELERY_BROKER_URL=redis://localhost:6379/0
```

**Django cache backend configuration:**
```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("CACHE_REDIS_LOCATION"),
    }
}
```

### Rate Limiting

```env
RATE_LIMIT_REQUESTS=60       # IP-based requests per window
RATE_LIMIT_WINDOW=60         # Window in seconds
USER_RATE_LIMIT_REQUESTS=60  # Per-authenticated-user limit
USER_RATE_LIMIT_WINDOW=60    # Window in seconds
BEHIND_CLOUDFLARE=False      # Trust CF-Connecting-IP header (True for Cloudflare Proxy, False for Tunnel)
```

### Blacklists

```env
# Static IP blocks (comma-separated IPs and CIDR ranges)
IP_BLACKLIST=185.220.101.5,194.165.16.0/22

# Static UA blocks (comma-separated substrings, case-insensitive)
UA_BLACKLIST=GPTBot,ClaudeBot,https://openai.com
```

### Feature Flags

```env
SHOW_CELERY_TASKS=True
SHOW_FILE_MANAGEMENT=True
SHOW_FEEDBACKS=True
IGNORE_ACCEPT_LANGUAGE_FOR_DEFAULT=True
SKIP_GUEST_LOGIN=False
```

---

## 11. Management Commands

| Command | Description | Usage |
|---|---|---|
| `init_admin` | Create initial admin user with random password and email notification | `python manage.py init_admin` |
| `init_guest` | Create guest user account for auto-login | `python manage.py init_guest` |
| `init_groupuser` | Initialize group users | `python manage.py init_groupuser` |
| `cleanup_old_activities` | Remove old activity records (configurable retention) | `python manage.py cleanup_old_activities` |
| `update_visit_profiles` | Update visit profile data from existing activities | `python manage.py update_visit_profiles` |

---

## 12. Frontend Build System

### Dependencies

```bash
npm install -D @tailwindcss/cli@next daisyui@latest
```

### Build CSS

```bash
# Using the provided script
bash scripts/tailwind.sh

# Or directly
npx @tailwindcss/cli -i styles.css -o whiteneuron/static/base/css/styles.css --minify
```

The build process:
1. Reads `styles.css` (Tailwind 4 + daisyUI 5 configuration)
2. Outputs minified CSS to `whiteneuron/static/base/css/styles.css`
3. Also generates `btn-styles.css` and `loading.css`

### Custom Styles/Scripts in UNFOLD

```python
UNFOLD = {
    "STYLES": [
        lambda request: static("base/css/styles.css"),
        lambda request: static("base/css/btn-styles.css"),
        lambda request: static("base/css/loading.css"),
    ],
    "SCRIPTS": [
        lambda request: static("base/js/loading.js"),
        lambda request: static("base/js/whiteneuron.js"),
    ],
}
```

---

## 13. Error Pages & Templates

Templates in `whiteneuron/templates/` are automatically used by Django when `DEBUG=False`:

| Template | HTTP Status | Notes |
|---|---|---|
| `400.html` | 400 Bad Request | — |
| `403.html` | 403 Forbidden | Used by IP/UA blacklist middleware |
| `404.html` | 404 Not Found | — |
| `429.html` | 429 Too Many Requests | Rendered by middleware, passes `{{ retry_after }}` context variable |
| `500.html` | 500 Server Error | — |

No need to register `handler400/403/404/500` — Django resolves templates automatically via `APP_DIRS=True`.

---

## 14. Security Checklist

When deploying django-whiteneuron, verify:

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` set in `.env` (not in code)
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] Redis is running and accessible for rate limiting / blacklists
- [ ] `RATE_LIMIT_REQUESTS` and `USER_RATE_LIMIT_REQUESTS` are appropriate for your traffic
- [ ] Static IP blacklist includes known bad actors via `IP_BLACKLIST` in `.env`
- [ ] UA blacklist blocks known bots/scrapers (`UA_BLACKLIST`)
- [ ] Dynamic blacklists managed via admin (temporary blocks with TTL)
- [ ] `BEHIND_CLOUDFLARE=True` if behind Cloudflare Proxy, `False` if using Cloudflare Tunnel
- [ ] Database is not in readonly mode during normal operation
- [ ] Email configuration works for login notifications on user creation
- [ ] Celery worker is running for async tasks (if applicable)

---

## Version

Current version: **v0.3.4.12**

For full changelog, see [CHANGELOG.md](../CHANGELOG.md).
