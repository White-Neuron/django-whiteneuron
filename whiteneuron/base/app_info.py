"""Data for the admin "About" page: application, base package and runtime versions."""
import datetime
import logging
import platform
import socket
import sqlite3
import time
from importlib import metadata

from django.conf import settings
from django.db import connection
from django.utils import formats, timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

import whiteneuron

logger = logging.getLogger(__name__)

BASE_PACKAGE = "django-whiteneuron"
CHANGELOG_URL = "https://github.com/White-Neuron/django-whiteneuron/releases"

# Shown in "Dependencies" (superusers only); missing packages are skipped
KEY_PACKAGES = [
    "django", "django-unfold", "celery", "django-celery-beat", "channels", "channels-redis",
    "redis", "django-import-export", "django-modeltranslation", "django-simple-history",
    "django-guardian", "django-ninja", "gunicorn", "uvicorn", "daphne", "whitenoise",
    "pillow", "pandas", "openai", "sentry-sdk",
]

# Module import time ~ worker start: good enough for an "uptime" without psutil
_STARTED_AT = timezone.now()
_STARTED_MONOTONIC = time.monotonic()


def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def parse_date(value):
    """ISO date/datetime (str) -> date, so templates format it in the active language."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)  # free text such as "Q4 2026": shown as is


def database_info():
    vendor = connection.vendor
    version = None
    try:
        if vendor == "sqlite":
            version = sqlite3.sqlite_version
        elif vendor == "postgresql":
            connection.ensure_connection()
            number = connection.pg_version  # e.g. 160004
            version = f"{number // 10000}.{number % 10000}" if number >= 100000 else str(number)
        elif vendor == "mysql":
            connection.ensure_connection()
            version = ".".join(map(str, connection.mysql_version))
        else:
            version = getattr(connection.Database, "version", None)
    except Exception:  # unreachable database must not break the page
        logger.warning("Could not read the database version", exc_info=True)
    name = connection.display_name
    return f"{name} {version}" if version else name


def cache_backend():
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    return backend.rsplit(".", 1)[-1] or "-"


def format_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def display(value):
    """Rows hold raw values; dates are formatted here, in the active language."""
    if value is None or value == "":
        return "-"
    if isinstance(value, datetime.datetime):
        return formats.date_format(timezone.localtime(value) if timezone.is_aware(value) else value, "DATETIME_FORMAT")
    if isinstance(value, datetime.date):
        return formats.date_format(value, "DATE_FORMAT")
    return value


def _rows(rows):
    return [(label, display(value)) for label, value in rows]


def extra_application_rows(request):
    """Rows added by the project: APP_INFO_CALLBACK = "path.to.func", func(request) -> [(label, value)]."""
    path = getattr(settings, "APP_INFO_CALLBACK", None)
    if not path:
        return []
    try:
        return [(label, value) for label, value in import_string(path)(request) or []]
    except Exception:
        logger.warning("APP_INFO_CALLBACK %s failed", path, exc_info=True)
        return []


def get_app_info(request):
    base_version = package_version(BASE_PACKAGE) or whiteneuron.__version__
    application = [
        (_("Name"), _(settings.NAME) if getattr(settings, "NAME", None) else None),
        (_("Version"), getattr(settings, "VERSION", None)),
        (_("Release date"), parse_date(getattr(settings, "RELEASE_DATE", None))),
        (_("Build"), getattr(settings, "BUILD_ID", None)),
        (_("Debug mode"), _("On") if settings.DEBUG else _("Off")),
        *extra_application_rows(request),
    ]
    base = [
        (_("Package"), BASE_PACKAGE),
        (_("Version"), base_version),
        (_("Release date"), parse_date(whiteneuron.__release_date__)),
    ]
    info = {
        "app_version": display(getattr(settings, "VERSION", None)),
        "app_release_date": display(parse_date(getattr(settings, "RELEASE_DATE", None))),
        "base_version": display(base_version),
        "base_release_date": display(parse_date(whiteneuron.__release_date__)),
        "changelog_url": CHANGELOG_URL,
        "application": _rows(application),
        "base": _rows(base),
        "runtime": None,
        "packages": None,
    }
    # host, database and dependency versions help attackers: superusers only
    if request.user.is_superuser:
        info["runtime"] = _rows([
            (_("Python"), f"{platform.python_version()} ({platform.python_implementation()})"),
            (_("Operating system"), f"{platform.system()} {platform.release()} ({platform.machine()})"),
            (_("Host name"), socket.gethostname()),
            (_("Database"), database_info()),
            (_("Cache"), cache_backend()),
            (_("Time zone"), settings.TIME_ZONE),
            (_("Default language"), settings.LANGUAGE_CODE),
            (_("Server time"), timezone.now()),
            (_("Process started"), _STARTED_AT),
            (_("Uptime"), format_duration(time.monotonic() - _STARTED_MONOTONIC)),
        ])
        info["packages"] = [(name, version) for name in KEY_PACKAGES if (version := package_version(name))]
    return info
