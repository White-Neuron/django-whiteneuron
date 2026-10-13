from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import ADMIN_GROUP, user_group


def notify_admin(message, type="info", obj_link=None, action=None, changed_data=None, user_ids=None):
    """Push a toast to connected admin pages.

    With ``user_ids`` only those users receive it; without, it goes to the legacy
    superuser group.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    event = {
        "type": "send_notification",
        "message": {
            "title": "🔔",
            "content": message,
            "type": type,
            "obj_link": obj_link,
            "action": action,
            "changed_data": changed_data if changed_data else "",
        },
    }
    groups = [user_group(uid) for uid in user_ids] if user_ids else [ADMIN_GROUP]
    for group in groups:
        async_to_sync(channel_layer.group_send)(group, event)
