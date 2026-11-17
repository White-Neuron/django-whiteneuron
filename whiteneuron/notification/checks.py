from django.conf import settings
from django.core import checks


@checks.register()
def notifications_websocket_check(app_configs=None, **kwargs):
    """Real-time toasts look configured (a Redis channel layer) but are off because
    WN_NOTIFICATIONS_WEBSOCKET is unset and ASGI_APPLICATION is not set: say so at
    `manage.py check` rather than through users noticing that toasts stopped (#51)."""
    from whiteneuron.base.templatetags.wn_notifications import notifications_websocket_enabled

    layer = (getattr(settings, "CHANNEL_LAYERS", None) or {}).get("default", {})
    redis_layer = "channels_redis" in str(layer.get("BACKEND", ""))
    explicit = getattr(settings, "WN_NOTIFICATIONS_WEBSOCKET", None) not in (None, "")
    if not redis_layer or explicit or notifications_websocket_enabled():
        return []
    return [checks.Warning(
        "Real-time notification toasts are off: a Redis channel layer is configured, but "
        "ASGI_APPLICATION is not set and WN_NOTIFICATIONS_WEBSOCKET is unset.",
        hint="Set WN_NOTIFICATIONS_WEBSOCKET=True if this project serves /ws/notifications/ "
             "(ASGI with channels), or WN_NOTIFICATIONS_WEBSOCKET=False to silence this warning.",
        id="whiteneuron.W001",
    )]
