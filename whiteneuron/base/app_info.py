"""Data for the admin "About" page: application, base package and runtime versions."""
import datetime
import logging
import platform
from importlib import metadata

import psutil
from django.conf import settings
from django.db import connection
from django.utils import formats, timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

import whiteneuron

logger = logging.getLogger(__name__)

BASE_PACKAGE = "django-whiteneuron"
CHANGELOG_URL = "https://github.com/White-Neuron/django-whiteneuron/releases"
BUILD_ID_LENGTH = 12  # a short commit hash identifies the build; longer values are cut


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


def process_started():
    try:
        return datetime.datetime.fromtimestamp(psutil.Process().create_time(), tz=datetime.timezone.utc)
    except Exception:  # restricted /proc: leave it out rather than fail
        return None


def format_uptime(started):
    """Days/hours/minutes in the active language (Django's timesince has no Vietnamese)."""
    seconds = max(0, int((timezone.now() - started).total_seconds()))
    days, seconds = divmod(seconds, 86400)
    hours, minutes = divmod(seconds // 60, 60)
    parts = []
    if days:
        parts.append(ngettext("%(count)d day", "%(count)d days", days) % {"count": days})
    if hours:
        parts.append(ngettext("%(count)d hour", "%(count)d hours", hours) % {"count": hours})
    if not days:
        parts.append(ngettext("%(count)d minute", "%(count)d minutes", minutes) % {"count": minutes})
    return ", ".join(parts)


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
        (_("Build"), (getattr(settings, "BUILD_ID", None) or "")[:BUILD_ID_LENGTH]),
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
    }
    # Superusers only, and deliberately limited: no host name, OS/kernel, IP, paths, database
    # server version, connection settings or full dependency list (fingerprinting / CVE lookup).
    if request.user.is_superuser:
        started = process_started()
        info["runtime"] = _rows([
            ("Python", platform.python_version()),
            ("Django", package_version("django")),
            ("Django Unfold", package_version("django-unfold")),
            (_("Database"), connection.display_name),
            (_("Debug mode"), _("On") if settings.DEBUG else _("Off")),
            (_("Time zone"), settings.TIME_ZONE),
            (_("Server time"), timezone.now()),
            (_("Process started"), started),
            (_("Uptime"), format_uptime(started) if started else None),
        ])
    return info
