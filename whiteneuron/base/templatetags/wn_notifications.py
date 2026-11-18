from django import template
from django.conf import settings

register = template.Library()

TRUE_VALUES = {"1", "true", "yes", "on"}


def notifications_websocket_enabled():
    """Whether pages open the /ws/notifications/ WebSocket (real-time toasts).

    ``WN_NOTIFICATIONS_WEBSOCKET`` (True/False, or the env string) decides; unset, it is on
    only when the project runs under ASGI (``ASGI_APPLICATION``). Under WSGI there is no
    WebSocket route, and every page load would log failed connections.
    """
    value = getattr(settings, "WN_NOTIFICATIONS_WEBSOCKET", None)
    if value is None or value == "":
        return bool(getattr(settings, "ASGI_APPLICATION", None))
    if isinstance(value, str):
        return value.strip().lower() in TRUE_VALUES
    return bool(value)


@register.simple_tag
def notifications_websocket():
    return notifications_websocket_enabled()


NOTIFICATION_BADGE_CALLBACK = "whiteneuron.notification.utils.notification_badge_callback"
DEFAULT_POLL_SECONDS = 60


@register.simple_tag
def notifications_unread_url():
    """URL of the JSON API's unread count, or "" when the project has not mounted the API."""
    from django.urls import NoReverseMatch, reverse

    try:
        return reverse("wn_notifications:unread_count")
    except NoReverseMatch:
        return ""


@register.simple_tag
def notifications_poll_seconds():
    """How often a page without the WebSocket refreshes the unread badge
    (``WN_NOTIFICATIONS_POLL_SECONDS``, default 60; 0 turns it off)."""
    try:
        seconds = int(getattr(settings, "WN_NOTIFICATIONS_POLL_SECONDS", DEFAULT_POLL_SECONDS))
    except (TypeError, ValueError):
        return DEFAULT_POLL_SECONDS
    return max(seconds, 0)


@register.filter
def is_notification_badge(item):
    """A sidebar item whose badge is the package's unread count: the page keeps it current."""
    return isinstance(item, dict) and item.get("badge") == NOTIFICATION_BADGE_CALLBACK


def _empty_badge(value):
    return value is None or str(value).strip() in ("", "None", "0")


@register.filter
def wn_badge_value(value):
    """A sidebar counter as the other badges show it: "+N", "99+" as is, "" for none."""
    if _empty_badge(value):
        return ""
    value = str(value).strip()
    return f"+{value}" if value.isdigit() else value


@register.filter
def wn_unread_badge_class(item, value):
    """Classes of the live unread badge: the hook for whiteneuron.js, the item's own
    badge_class, and "hidden" while there is nothing unread."""
    classes = ["wn-unread-badge"]
    if item.get("badge_class"):
        classes.append(str(item["badge_class"]))
    if _empty_badge(value):
        classes.append("hidden")
    return " ".join(classes)
