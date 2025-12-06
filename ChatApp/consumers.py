import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message
from django.utils.text import slugify


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"notification_{slugify(self.room_name)}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')
        sender = text_data_json.get('sender')
        room_name = text_data_json.get('room_name')

        await self.channel_layer.group_send(
            self.room_group_name,   # ✅ FIXED
            {
                'type': 'send_message',
                'message': {
                    'sender': sender,
                    'message': message,
                    'room_name': room_name
                }
            }
        )

    async def send_message(self, event):
        data = event['message']

        await self.create_message(data)

        await self.send(text_data=json.dumps({
            'sender': data['sender'],
            'message': data['message']
        }))

    @database_sync_to_async
    def create_message(self, data):
        room = Room.objects.get(room_name=data['room_name'])
        Message.objects.create(
            room=room,
            sender=data['sender'],
            message=data['message']
        )
