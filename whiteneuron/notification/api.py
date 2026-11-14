"""JSON API for the logged-in user's notifications and the announcement (release notes).

Notifications (``notifications/``):

    GET  ""                list, newest first; ?page, ?page_size (<= 100), ?unread=1, ?flag=<flag>
    GET  unread-count/     {"unread_count": n}  (all unread, not only today's)
    GET  <id>/             detail, with changed_data
    POST <id>/read/        mark as read
    POST <id>/unread/      mark as unread
    POST read-all/         mark all as read

Announcement (``announcement/``), built from ``ANNOUNCEMENT_CALLBACK`` and
``ANNOUNCEMENT_CONTENT_HTML_FILE`` like the admin header button:

    GET  ""                {"announcement": {title, version, badge, html, is_seen} | null}
    POST seen/             the user has seen the current version

Every endpoint needs a logged-in user (401 otherwise); a user only reaches their own
notifications (404 for others). POST needs the CSRF token (``X-CSRFToken``).
"""
import logging

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from whiteneuron.base.api_utils import api_login_required, json_response, paginate

from .models import AnnouncementReceipt, Notification

logger = logging.getLogger(__name__)

FLAGS = {value for value, _label in Notification._meta.get_field("flag").choices}
BADGE_CACHE_KEY = "badge:notification:{}:unread_today"


def _own(request):
    return Notification.objects.filter(user=request.user)


def _unread_count(request):
    return _own(request).filter(is_read=False).count()


def _changed(request):
    """Keep the sidebar avatar badge (cached 60s) in step with the change."""
    from django.core.cache import caches

    try:
        caches["default"].delete(BADGE_CACHE_KEY.format(request.user.pk))
    except Exception:
        logger.warning("Could not clear the notification badge cache", exc_info=True)


def serialize_notification(n, detail=False):
    data = {
        "id": n.pk,
        "title": n.title,
        "content": n.content,
        "flag": n.flag,
        "action": n.action,
        "obj_link": n.obj_link,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "action_by": n.action_by.get_username() if n.action_by_id else None,
    }
    if detail:
        data["changed_data"] = n.changed_data
    return data


# ── notifications ─────────────────────────────────────────────────────────

@never_cache
@require_GET
@api_login_required
def notification_list(request):
    qs = _own(request).select_related("action_by").order_by("-created_at", "-pk")
    if request.GET.get("unread", "").lower() in ("1", "true", "yes"):
        qs = qs.filter(is_read=False)
    flag = request.GET.get("flag")
    if flag:
        if flag not in FLAGS:
            return json_response({"detail": "Invalid flag.", "allowed": sorted(FLAGS)}, status=400)
        qs = qs.filter(flag=flag)
    data = paginate(request, qs, serialize_notification)
    data["unread_count"] = _unread_count(request)
    return json_response(data)


@never_cache
@require_GET
@api_login_required
def notification_unread_count(request):
    return json_response({"unread_count": _unread_count(request)})


@never_cache
@require_GET
@api_login_required
def notification_detail(request, pk):
    n = _own(request).select_related("action_by").filter(pk=pk).first()
    if n is None:
        return json_response({"detail": "Not found."}, status=404)
    return json_response(serialize_notification(n, detail=True))


def _set_read(request, pk, value):
    if not _own(request).filter(pk=pk).update(is_read=value):
        return json_response({"detail": "Not found."}, status=404)
    _changed(request)
    return json_response({"id": pk, "is_read": value, "unread_count": _unread_count(request)})


@require_POST
@api_login_required
def notification_read(request, pk):
    return _set_read(request, pk, True)


@require_POST
@api_login_required
def notification_unread(request, pk):
    return _set_read(request, pk, False)


@require_POST
@api_login_required
def notification_read_all(request):
    updated = _own(request).filter(is_read=False).update(is_read=True)
    _changed(request)
    return json_response({"updated": updated, "unread_count": 0})


# ── announcement ──────────────────────────────────────────────────────────

def current_announcement(request):
    """The ANNOUNCEMENT_CALLBACK dict (title, version, badge), or None."""
    path = getattr(settings, "ANNOUNCEMENT_CALLBACK", None)
    if not path:
        return None
    try:
        data = import_string(path)(request)
    except Exception:
        logger.warning("ANNOUNCEMENT_CALLBACK %s failed", path, exc_info=True)
        return None
    return data or None


def announcement_html(request):
    content_file = getattr(settings, "ANNOUNCEMENT_CONTENT_HTML_FILE", None)
    if not content_file:
        return ""
    try:
        return render_to_string(str(content_file), request=request)
    except TemplateDoesNotExist:
        logger.warning("Announcement template %r not found (ANNOUNCEMENT_CONTENT_HTML_FILE)", content_file)
        return ""


def _announcement_version(data):
    return str(data.get("version") or getattr(settings, "VERSION", "") or "")


@never_cache
@require_GET
@api_login_required
def announcement(request):
    data = current_announcement(request)
    if data is None:
        return json_response({"announcement": None})
    version = _announcement_version(data)
    return json_response({"announcement": {
        "title": str(data.get("title") or ""),
        "version": version,
        "badge": str(data.get("badge") or ""),
        "html": announcement_html(request),
        "is_seen": bool(version) and AnnouncementReceipt.objects.filter(user=request.user, version=version).exists(),
    }})


@require_POST
@api_login_required
def announcement_seen(request):
    data = current_announcement(request)
    version = _announcement_version(data) if data else ""
    if not version:
        return json_response({"detail": "No announcement."}, status=404)
    AnnouncementReceipt.objects.get_or_create(user=request.user, version=version[:100])
    return json_response({"version": version, "is_seen": True})
