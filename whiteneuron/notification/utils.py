from django.core.cache import caches

from .models import Notification

_NOTIFICATION_BADGE_TIMEOUT = 60
BADGE_CACHE_KEY = "badge:notification:{}:unread"
BADGE_MAX = 99  # the badge shows "99+" above this


def count_unread(user):
    """All unread notifications of ``user`` (not only today's), straight from the database."""
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()


def unread_count(user):
    """``count_unread`` cached 60s; every write in the package clears the cache (``clear_unread_cache``)."""
    if not user or not user.is_authenticated:
        return 0
    cache_key = BADGE_CACHE_KEY.format(user.pk)
    cached = caches["default"].get(cache_key)
    if cached is not None:
        return cached
    count = count_unread(user)
    caches["default"].set(cache_key, count, timeout=_NOTIFICATION_BADGE_TIMEOUT)
    return count


def clear_unread_cache(*user_ids):
    """Forget the cached unread count of these users: the next page shows the new number."""
    keys = [BADGE_CACHE_KEY.format(uid) for uid in user_ids if uid is not None]
    if not keys:
        return
    try:
        caches["default"].delete_many(keys)
    except Exception:  # a cache outage must not break the write that triggered this
        import logging

        logging.getLogger(__name__).warning("Could not clear the notification badge cache", exc_info=True)


def badge_text(count):
    """``count`` for a badge: None when 0 (no badge), "99+" above ``BADGE_MAX``."""
    if not count:
        return None
    return f"{BADGE_MAX}+" if count > BADGE_MAX else count


# Former name (it counted only today's notifications); kept for projects that import it.
unread_today_count = unread_count


def notification_badge_callback(request):
    return badge_text(unread_count(request.user))
