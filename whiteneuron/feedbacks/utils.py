from django.core.cache import caches

from .models import FeedbackData

_BADGE_TIMEOUT = 60


def feedback_data_badge_callback(request):
    """Open feedbacks waiting for someone (#47): all of them for superusers, else the user's own.

    Was "feedbacks updated today", which said nothing about the work left."""
    user = request.user
    if not user.is_authenticated:
        return 0
    key = "badge:feedback:open:" + ("all" if user.is_superuser else str(user.pk))
    cached = caches["default"].get(key)
    if cached is not None:
        return cached
    qs = FeedbackData.objects.filter(status=FeedbackData.OPEN)
    if not user.is_superuser:
        qs = qs.filter(user=user)
    count = qs.count()
    caches["default"].set(key, count, _BADGE_TIMEOUT)
    return count
