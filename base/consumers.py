from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

from base.models import Conversation, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close(code=4401)
            return

        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        conversation = await self._get_conversation_if_participant(user.id, self.conversation_id)
        if conversation is None:
            await self.close(code=4403)
            return

        self.group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        body = (content.get("body") or "").strip()
        if not body:
            return
        if len(body) > 5000:
            body = body[:5000]

        message = await self._persist_message(self.conversation_id, user.id, body)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message_id": message.id,
                "sender_id": user.id,
                "body": message.body,
                "created_at": message.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send_json(
            {
                "message_id": event["message_id"],
                "sender_id": event["sender_id"],
                "body": event["body"],
                "created_at": event["created_at"],
            }
        )

    @database_sync_to_async
    def _get_conversation_if_participant(self, user_id, conversation_id):
        return Conversation.objects.filter(
            Q(id=conversation_id) & (Q(roaster_id=user_id) | Q(farmer_id=user_id))
        ).first()

    @database_sync_to_async
    def _persist_message(self, conversation_id, sender_id, body):
        message = Message.objects.create(
            conversation_id=conversation_id,
            sender_id=sender_id,
            body=body,
        )
        Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())
        return message
