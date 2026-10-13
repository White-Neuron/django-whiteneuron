import json

from channels.generic.websocket import AsyncWebsocketConsumer

ADMIN_GROUP = "admin_notifications"  # legacy broadcast group: superusers only


def user_group(user_id):
    return f"notifications_user_{user_id}"


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.is_staff:
            # accept first: closing during the handshake reaches the browser as 1006
            # (a generic failure it retries); 4401 tells the client to stop
            await self.accept()
            await self.close(code=4401)
            return
        # each user only receives notifications addressed to them
        self.joined = [user_group(user.pk)]
        if user.is_superuser:
            self.joined.append(ADMIN_GROUP)
        for group in self.joined:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if not self.channel_layer:
            return
        for group in getattr(self, "joined", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data):
        pass

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["message"]))
