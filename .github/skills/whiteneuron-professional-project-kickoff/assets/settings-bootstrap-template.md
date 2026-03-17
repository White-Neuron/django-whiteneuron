# Settings Bootstrap Template

Use this as the starting point for `src/<project_name>/settings.py`.

Before applying this template, review:
- [settings-options-safety-guide.md](./settings-options-safety-guide.md)

```python
from dotenv import load_dotenv
from django.templatetags.static import static
from whiteneuron.base.settings import *
from whiteneuron.base.settings import _, environ

load_dotenv()

PROJECT_NAME = environ.get("PROJECT_NAME", "myproject")
NAME = environ.get("NAME", "My Project")
URL = environ.get("URL", "http://localhost:8000")

DEBUG = environ.get("DEBUG", "False") == "True"
ROOT_URLCONF = f"{PROJECT_NAME}.urls"
WSGI_APPLICATION = f"{PROJECT_NAME}.wsgi.application"

AUTH_USER_MODEL = "base.User"
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

# Optional feature toggles
BROWSER_RELOAD = environ.get("BROWSER_RELOAD", "False") == "True"
USE_CACHE = environ.get("USE_CACHE", "False") == "True"
SHOW_CELERY_TASKS = environ.get("SHOW_CELERY_TASKS", "True") == "True"
SHOW_FILE_MANAGEMENT = environ.get("SHOW_FILE_MANAGEMENT", "True") == "True"
SHOW_FEEDBACKS = environ.get("SHOW_FEEDBACKS", "True") == "True"

INSTALLED_APPS += [
    # project apps under src/apps
]

ALLOWED_HOSTS = environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:8000").split(",")

# Optional CORS for API use cases
CORS_ALLOWED_ORIGINS = environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:8000").split(",")

UNFOLD["SITE_HEADER"] = _(NAME)
UNFOLD["SITE_TITLE"] = _(NAME)
UNFOLD["ENVIRONMENT"] = f"{PROJECT_NAME}.utils.environment_callback"
UNFOLD["STYLES"] = [lambda request: static("css/styles.css")] + UNFOLD["STYLES"]
UNFOLD["SHOW_LANGUAGES"] = True

# Recommended baseline additions
UNFOLD["DASHBOARD_CALLBACK"] = "whiteneuron.dashboard.views.dashboard_callback"
UNFOLD["SITE_SUBHEADER"] = _("Admin panel")

STATIC_URL = "static/"
import whiteneuron
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WHITENEURON_PATH = Path(whiteneuron.__file__).parent

STATICFILES_DIRS = [
    BASE_DIR / "static",
    WHITENEURON_PATH / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Production safety baseline
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Integrations
SENTRY_DSN = environ.get("SENTRY_DSN")
CELERY_BROKER_URL = environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
```

## Profile notes

- catalog-api: add `rest_framework`, `drf_yasg`, `django_filters`.
- portal-cms: enable content apps, i18n, and async/cache settings.
- admin-core: keep app list minimal first.

## Safety notes

- Never hardcode secrets in settings source.
- Keep security flags enabled when `DEBUG=False`.
- Only enable feature toggles when related apps/routes are configured.
- Ensure `PROJECT_NAME.utils.environment_callback` exists when setting `UNFOLD["ENVIRONMENT"]`.
- Ensure `src/static/css/styles.css` exists when prepending `UNFOLD["STYLES"]`.
