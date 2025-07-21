from django.shortcuts import render


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils.translation import gettext_lazy as _

def notify_admin(message, type="info", obj_link=None, action=None):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "admin_notifications",
        {
            "type": "send_notification",
            "message": {
                "title": f"🔔",
                "content": message,
                "type": type,
                'obj_link': obj_link,
                'action': action,
            }
        }
    )
