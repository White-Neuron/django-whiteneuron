# yourapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.is_staff:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add("admin_notifications", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if not self.channel_layer:
            return
        await self.channel_layer.group_discard("admin_notifications", self.channel_name)

    async def receive(self, text_data):
        # Có thể xử lý tin nhắn từ client nếu muốn
        pass

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["message"]))
