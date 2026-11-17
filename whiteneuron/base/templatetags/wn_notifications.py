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
