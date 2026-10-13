from django.utils import timezone
from .models import Notification
from django.core.cache import caches

_NOTIFICATION_BADGE_TIMEOUT = 60

def unread_today_count(user):
    """Unread notifications received today by ``user`` (cached 60s)."""
    if not user or not user.is_authenticated:
        return 0
    cache_key = f"badge:notification:{user.id}:unread_today"
    cached = caches["default"].get(cache_key)
    if cached is not None:
        return cached

    c = Notification.objects.filter(
        user=user,
        is_read=False,
        created_at__gte=timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    caches["default"].set(cache_key, c, timeout=_NOTIFICATION_BADGE_TIMEOUT)
    return c


def notification_badge_callback(request):
    return unread_today_count(request.user)
